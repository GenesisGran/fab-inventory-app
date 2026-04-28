"""Streamlit frontend for the FAB Inventory Tool.

This module provides a small Streamlit app which interacts with a Supabase
backend (Postgres + RLS). Registration is invite-only and invite keys are
burned (marked used) when consumed. Sensitive service credentials must be
provided via Streamlit secrets so they are never exposed in the client.
"""

from __future__ import annotations

import logging
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
import pandas as pd
import streamlit as st

# --- CONFIG & CONSTANTS ---
logger = logging.getLogger(__name__)

# Streamlit secrets (required). Fail fast and show a friendly message when
# secrets are not configured.
try:
    URL: str = st.secrets["SUPABASE_URL"]
    ANON_KEY: str = st.secrets["SUPABASE_KEY"]
except Exception as exc:  # pragma: no cover - runtime environment dependent
    st.error(
        "Missing Streamlit secrets. Please set SUPABASE_URL and SUPABASE_KEY."
    )
    logger.exception("Missing Streamlit secrets: %s", exc)
    raise

SERVICE_KEY: str = st.secrets.get("SUPABASE_SERVICE_KEY", ANON_KEY)
ADMIN_USERNAME: str = "ADMIN"

HEADERS_ANON: Dict[str, str] = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json",
}

HEADERS_ADMIN: Dict[str, str] = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

FOIL_OPTIONS: Dict[str, str] = {
    "Regular": "Regular",
    "Rainbow Foil": "Rainbow Foil",
    "Cold Foil": "Cold Foil",
    "Full Art": "Full Art",
    "Gold Cold Foil": "Gold Cold Foil",
}

BULK_FOIL_MAP: Dict[str, str] = {
    "reg": "Regular",
    "r": "Rainbow Foil",
    "c": "Cold Foil",
    "f": "Full Art",
    "g": "Gold Cold Foil",
}

# Centralized CSS for the "Vault" theme. Kept at top for easy editing.
VAULT_CSS: str = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Montserrat:wght@300;400;700&display=swap');

/* FORCE DARK THEME */
[data-testid="stAppViewContainer"] { background-color: #000000 !important; }
[data-testid="stHeader"] { background: transparent !important; }

p, span, label, h1, h2, h3, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: white !important; }

/* BRAND CENTERING */
.brand-container { text-align: center; width: 100%; display: block; }
.brand-title {
    color: #D4AF37 !important;
    font-family: 'Bebas Neue', cursive;
    text-align: center;
    letter-spacing: 4px;
    line-height: 1.1;
    margin: 0 auto;
}
@media (min-width: 768px) { .brand-title { font-size: 4rem !important; } }
@media (max-width: 767px) { .brand-title { font-size: 1.9rem !important; } }

.brand-sub {
    text-align: center; color: #555 !important; font-size: 0.85rem;
    text-transform: uppercase; margin-top: 5px; margin-bottom: 25px;
}
.brand-sub a { color: #D4AF37 !important; text-decoration: none; font-weight: 700; }

/* INPUT STYLING */
div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea textarea {
    border: 1px solid #D4AF37 !important;
    border-radius: 4px !important;
    background-color: #0f0f0f !important;
    color: white !important;
}

div[data-testid="stNumberInputStepUp"], div[data-testid="stNumberInputStepDown"],
button[aria-label="Show password"] {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    color: #D4AF37 !important;
}

/* BUTTONS */
div.stButton > button {
    background-color: transparent !important;
    color: #D4AF37 !important;
    border: 2px solid #D4AF37 !important;
    font-family: 'Bebas Neue', cursive;
    font-size: 1.2rem !important;
}
div.stButton > button:hover { background-color: #D4AF37 !important; color: #000 !important; }

footer { visibility: hidden; }
</style>
"""


def apply_hardened_css() -> None:
    """Apply the Vault theme CSS to the Streamlit app.

    Keeps visual / accessibility styles in one place so the app is easier to
    maintain and audit for UX consistency.
    """

    st.markdown(VAULT_CSS, unsafe_allow_html=True)


def api_request(
    method: str,
    endpoint: str,
    headers: Dict[str, str],
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
) -> Optional[Union[Dict[str, Any], List[Any], bool]]:
    """Make a simple HTTP request to Supabase REST endpoint.

    Args:
        method: HTTP method (GET, POST, PATCH, etc.).
        endpoint: Supabase REST endpoint (table or view).
        headers: Request headers (anon or service key).
        json: Optional JSON payload for POST / PATCH.
        params: Optional query params for GET requests.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON response, True for an empty successful response, or
        None if an error occurred.
    """

    url = f"{URL}/rest/v1/{endpoint}"
    try:
        response = httpx.request(
            method, url, headers=headers, json=json, params=params, timeout=timeout
        )
        response.raise_for_status()
        return response.json() if response.content else True
    except httpx.HTTPStatusError as exc:
        logger.error("Supabase API error [%s %s]: %s", method, url, exc)
    except Exception as exc:  # pragma: no cover - external failures
        logger.exception("Unexpected error when calling Supabase: %s", exc)
    return None


def verify_user(username: str, password: str) -> bool:
    """Verify a username/password pair against the `users` table.

    This is a minimal wrapper over a Supabase GET. The application relies on
    Row Level Security (RLS) on the DB side; the frontend does not perform
    additional authentication checks beyond this call.
    """

    res = api_request(
        "GET",
        "users",
        HEADERS_ANON,
        params={
            "username": f"eq.{username}",
            "password": f"eq.{password}",
            "select": "username",
        },
    )
    return bool(res)


def register_user(username: str, password: str, invite_code: str) -> Union[bool, str]:
    """Register a new user using an invite code.

    Flow:
    1. Verify the invite code exists and is not used.
    2. Ensure the requested username is not already taken.
    3. Create the new `users` row using the service/Admin key.
    4. Mark (burn) the invite code so it cannot be reused.

    Args:
        username: Requested username (case-insensitive; stored uppercase).
        password: Raw password string (stored as-is in this demo schema).
        invite_code: Single-use invite token.

    Returns:
        True on success, or a user-facing error message string.
    """

    code = invite_code.strip()

    # 1) Check invite key (must exist and be unused)
    invite_check = api_request(
        "GET",
        "invites",
        HEADERS_ANON,
        params={"code": f"eq.{code}", "is_used": "eq.false", "select": "*"},
    )

    if not invite_check:
        return "Invalid or already-used invite key. Please request a new key."

    # 2) Ensure username is available
    uname = username.upper().strip()
    user_check = api_request(
        "GET", "users", HEADERS_ANON, params={"username": f"eq.{uname}", "select": "username"}
    )
    if user_check and len(user_check) > 0:
        return "The chosen username is already taken. Please choose another."

    # 3) Create the user (requires service/admin privileges)
    user_payload = {"username": uname, "password": password}
    user_create = api_request("POST", "users", HEADERS_ADMIN, json=user_payload)
    if user_create is None:
        return "Unable to create account at this time. Please try again later."

    # 4) Burn the invite key (best-effort; log if it fails)
    invite_payload = {
        "is_used": True,
        "used_by": uname,
        "used_at": datetime.now().isoformat(),
    }
    patched = api_request(
        "PATCH",
        "invites",
        HEADERS_ADMIN,
        params={"code": f"eq.{code}"},
        json=invite_payload,
    )
    if patched is None:
        logger.warning("Invite %s was not patched successfully for user %s", code, uname)

    return True


def get_inventory(username: str) -> pd.DataFrame:
    """Retrieve the aggregated inventory for `username`.

    Returns an empty DataFrame when no records are found.
    """
    # Try a few username casings since Postgres string equality is case-sensitive
    for uname in (username, username.upper(), username.lower()):
        data = api_request(
            "GET",
            "inventory_view",
            HEADERS_ANON,
            params={"username": f"eq.{uname}", "select": "*"},
        )
        if isinstance(data, list) and data:
            df = pd.DataFrame(data)
            df_agg = (
                df.groupby(["card_name", "set_name", "foiling", "print_id"])["quantity"]
                .sum()
                .reset_index()
            )
            df_agg = df_agg[df_agg["quantity"] != 0]
            return df_agg.rename(
                columns={
                    "card_name": "Card",
                    "set_name": "Set",
                    "foiling": "Finish",
                    "quantity": "Qty",
                }
            )

    # Safe fallback: fetch all rows, then filter client-side by username if the
    # view includes a username column. This avoids returning other users' data
    # while helping diagnose cases where the server-side filter failed.
    data_all = api_request("GET", "inventory_view", HEADERS_ANON, params={"select": "*"})
    if isinstance(data_all, list) and data_all:
        df_all = pd.DataFrame(data_all)
        if "username" in df_all.columns:
            df_user = df_all[df_all["username"].str.lower() == username.lower()]
            if not df_user.empty:
                df_agg = (
                    df_user.groupby(["card_name", "set_name", "foiling", "print_id"])["quantity"]
                    .sum()
                    .reset_index()
                )
                df_agg = df_agg[df_agg["quantity"] != 0]
                logger.info("Fetched inventory via safe fallback for user %s", username)
                return df_agg.rename(
                    columns={
                        "card_name": "Card",
                        "set_name": "Set",
                        "foiling": "Finish",
                        "quantity": "Qty",
                    }
                )

    return pd.DataFrame()


# --- APP ---
st.set_page_config(page_title="FAB VAULT", layout="wide")
apply_hardened_css()

st.markdown(
    (
        '<div class="brand-container"><h1 class="brand-title">FAB INVENTORY TOOL</h1>'
        '<p class="brand-sub">by <a href="https://github.com/GenesisGran" target="_blank">GenesisGran</a></p></div>'
    ),
    unsafe_allow_html=True,
)


if "username" not in st.session_state:
    mode = st.radio("Access", ["Login", "Register"], horizontal=True, label_visibility="collapsed")
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        if mode == "Login":
            with st.form("login"):
                st.markdown(
                    "<h3 style='text-align:center; font-family:Bebas Neue; color:#D4AF37;'>LOGIN</h3>",
                    unsafe_allow_html=True,
                )
                u = st.text_input("Username").upper().strip()
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Authenticate"):
                    if verify_user(u, p):
                        st.session_state.username = u
                        st.rerun()
                    else:
                        st.error(
                            "Invalid username or password. If you need an account,"
                            " request an invite from an admin."
                        )
        else:
            with st.form("register"):
                st.markdown(
                    "<h3 style='text-align:center; font-family:Bebas Neue; color:#D4AF37;'>CREATE ACCOUNT</h3>",
                    unsafe_allow_html=True,
                )
                u_new = st.text_input("New Username").upper().strip()
                p_new = st.text_input("New Password", type="password")
                i_code = st.text_input("Invite Key").strip()
                if st.form_submit_button("Register"):
                    if u_new and p_new and i_code:
                        result = register_user(u_new, p_new, i_code)
                        if result is True:
                            st.success("Account created successfully. Please log in.")
                        else:
                            st.error(result)
                    else:
                        st.warning("Please complete all registration fields.")
    st.stop()


# Header: logged-in indicator and logout
st.markdown(
    (
        f'<div style="text-align:right; margin-bottom:10px;">'
        f'<span style="color:white;">LOGGED IN: </span>'
        f'<span style="color:#00FF00; background:rgba(0,255,0,0.1); padding:2px 6px; '
        f'border-radius:4px;">{st.session_state.username}</span></div>'
    ),
    unsafe_allow_html=True,
)

_, btn_col = st.columns([8, 1])
with btn_col:
    if st.button("Logout"):
        st.session_state.pop("username", None)
        st.rerun()


# Application tabs
tab_list = ["📑 SINGLE ADD", "📦 BULK ADD", "🔍 INVENTORY"]
if st.session_state.username == ADMIN_USERNAME:
    tab_list.append("🎟️ ADMIN")
tabs = st.tabs(tab_list)


with tabs[0]:
    with st.form("single", clear_on_submit=True):
        card_id = st.text_input("Card ID (DTD206)").upper().strip()
        foil_choice = st.selectbox("Foil Type", list(FOIL_OPTIONS.keys()))
        qty = st.number_input("Qty Change", value=1, step=1)
        if st.form_submit_button("Update Vault"):
            if not card_id:
                st.warning("Please provide a Card ID.")
            else:
                pid = f"{card_id}-{FOIL_OPTIONS[foil_choice]}"
                api_request(
                    "POST",
                    "inventories",
                    HEADERS_ANON,
                    json={
                        "print_id": pid,
                        "qty_change": int(qty),
                        "username": st.session_state.username,
                        "updated_at": datetime.now().isoformat(),
                    },
                )
                st.success(f"Successfully updated inventory for {pid}.")


with tabs[1]:
    bulk = st.text_area("Batch Entry:", height=250, placeholder="ID FOIL QTY")
    if st.button("Process Batch"):
        if bulk:
            for line in bulk.strip().split("\n"):
                parts = line.split()
                if len(parts) < 3:
                    continue
                foil = BULK_FOIL_MAP.get(parts[1].lower(), "Regular")
                pid = f"{parts[0].upper()}-{foil}"
                try:
                    qty_val = int(parts[2])
                except ValueError:
                    logger.warning("Skipping line with invalid quantity: %s", line)
                    continue
                api_request(
                    "POST",
                    "inventories",
                    HEADERS_ANON,
                    json={
                        "print_id": pid,
                        "qty_change": qty_val,
                        "username": st.session_state.username,
                        "updated_at": datetime.now().isoformat(),
                    },
                )
            st.success("Batch processed successfully.")


with tabs[2]:
    inv_df = get_inventory(st.session_state.username)

    # Refresh control
    if st.button("Refresh Inventory"):
        st.experimental_rerun()

    if not inv_df.empty:
        search_text = st.text_input("Search by card name, set, or print id...")
        if search_text:
            pattern = search_text.lower()
            mask = pd.Series(False, index=inv_df.index)
            for col in ("Card", "Set", "Finish", "print_id"):
                if col in inv_df.columns:
                    mask = mask | inv_df[col].astype(str).str.lower().str.contains(pattern)
            inv_df = inv_df[mask]

        st.dataframe(inv_df, use_container_width=True, hide_index=True)
    else:
        st.info("Your vault is currently empty. If you expect data, press 'Refresh Inventory'.")


if st.session_state.username == ADMIN_USERNAME and len(tabs) >= 4:
    with tabs[3]:
        if st.button("Generate New Invite Key"):
            new_k = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
            api_request("POST", "invites", HEADERS_ADMIN, json={"code": new_k, "is_used": False})
            st.success(f"New invite key created: {new_k}")
        st.divider()
        res = api_request("GET", "invites", HEADERS_ADMIN, params={"order": "created_at.desc"})
        if isinstance(res, list):
            st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)