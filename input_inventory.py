"""
FAB Inventory Tool - Portfolio Edition
Author: GenesisGran
Live App: https://fab-inventory.streamlit.app/
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

try:
    URL: str = st.secrets["SUPABASE_URL"]
    ANON_KEY: str = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("Missing Streamlit secrets. Please set SUPABASE_URL and SUPABASE_KEY.")
    raise

SERVICE_KEY: str = st.secrets.get("SUPABASE_SERVICE_KEY", ANON_KEY)
ADMIN_USERNAME: str = "ADMIN"

HEADERS_ANON = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}", "Content-Type": "application/json"}
HEADERS_ADMIN = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": "application/json"}

FOIL_OPTIONS = {"Regular": "Regular", "Rainbow Foil": "Rainbow Foil", "Cold Foil": "Cold Foil", "Full Art": "Full Art", "Gold Cold Foil": "Gold Cold Foil"}
BULK_FOIL_MAP = {"reg": "Regular", "r": "Rainbow Foil", "c": "Cold Foil", "f": "Full Art", "g": "Gold Cold Foil"}

# --- THEME ---
VAULT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Montserrat:wght@300;400;700&display=swap');
[data-testid="stAppViewContainer"] { background-color: #000000 !important; }
[data-testid="stHeader"] { background: transparent !important; }
p, span, label, h1, h2, h3, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: white !important; }
.brand-container { text-align: center; width: 100%; display: block; }
.brand-title { color: #D4AF37 !important; font-family: 'Bebas Neue', cursive; letter-spacing: 4px; line-height: 1.1; }
@media (min-width: 768px) { .brand-title { font-size: 4rem !important; } }
@media (max-width: 767px) { .brand-title { font-size: 2rem !important; } }
.brand-sub { text-align: center; color: #555 !important; font-size: 0.85rem; text-transform: uppercase; margin-top: 5px; margin-bottom: 25px; }
.brand-sub a { color: #D4AF37 !important; text-decoration: none; font-weight: 700; }
div[data-baseweb="input"], div[data-baseweb="select"], .stTextArea textarea { border: 1px solid #D4AF37 !important; border-radius: 4px !important; background-color: #0f0f0f !important; color: white !important; }
div.stButton > button { background-color: transparent !important; color: #D4AF37 !important; border: 2px solid #D4AF37 !important; font-family: 'Bebas Neue', cursive; font-size: 1.2rem !important; width: 100%; }
div.stButton > button:hover { background-color: #D4AF37 !important; color: #000 !important; }
footer { visibility: hidden; }
</style>
"""

def apply_ui():
    st.markdown(VAULT_CSS, unsafe_allow_html=True)
    st.markdown('<div class="brand-container"><h1 class="brand-title">FAB INVENTORY TOOL</h1><p class="brand-sub">by <a href="https://github.com/GenesisGran" target="_blank">GenesisGran</a></p></div>', unsafe_allow_html=True)

def api_request(method, endpoint, headers, json=None, params=None):
    url = f"{URL}/rest/v1/{endpoint}"
    try:
        response = httpx.request(method, url, headers=headers, json=json, params=params, timeout=10)
        response.raise_for_status()
        return response.json() if response.content else True
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

def get_inventory(username: str) -> pd.DataFrame:
    data = api_request("GET", "inventory_view", HEADERS_ANON, params={"username": f"eq.{username.upper()}", "select": "*"})
    
    if isinstance(data, list) and len(data) > 0:
        df = pd.DataFrame(data)
        
        # 1. Create 'Set Code' from first 6 chars of print_id
        if "print_id" in df.columns:
            df["Set Code"] = df["print_id"].str[:6]
        else:
            df["Set Code"] = "N/A"

        # 2. Map Color with Emoji
        color_emojis = {"red": "🔴 Red", "yellow": "🟡 Yellow", "blue": "🔵 Blue"}
        if "color" in df.columns:
            df["Color"] = df["color"].str.lower().map(color_emojis).fillna(df["color"].str.capitalize().fillna("N/A"))
        else:
            df["Color"] = "N/A"

        # 3. Class (type_text)
        if "type_text" in df.columns:
            df["Class"] = df["type_text"].fillna("N/A")
        else:
            df["Class"] = "N/A"

        # 4. Aggregate
        group_cols = ["card_name", "Set Code", "set_name", "Class", "Color", "foiling"]
        existing_cols = [c for c in group_cols if c in df.columns]
        
        df_agg = df.groupby(existing_cols, dropna=False)["quantity"].sum().reset_index()
        df_agg = df_agg[df_agg["quantity"] != 0]
        
        # 5. Rename & Order
        rename_map = {"card_name": "Card", "set_name": "Set Name", "foiling": "Finish", "quantity": "Qty"}
        df_final = df_agg.rename(columns=rename_map)
        
        # Specific Order: Card -> Set Code -> Set Name -> Class -> Color -> Finish -> Qty
        ordered_cols = ["Card", "Set Code", "Set Name", "Class", "Color", "Finish", "Qty"]
        present_cols = [c for c in ordered_cols if c in df_final.columns]
        
        return df_final[present_cols]
    
    return pd.DataFrame()

# --- APP START ---
st.set_page_config(page_title="FAB VAULT", layout="wide")
apply_ui()

if "username" not in st.session_state:
    mode = st.radio("Access", ["Login", "Register"], horizontal=True, label_visibility="collapsed")
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        if mode == "Login":
            with st.form("login"):
                st.markdown("<h3 style='text-align:center; color:#D4AF37;'>LOGIN</h3>", unsafe_allow_html=True)
                u = st.text_input("Username").upper().strip()
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Authenticate"):
                    if api_request("GET", "users", HEADERS_ANON, params={"username": f"eq.{u}", "password": f"eq.{p}", "select": "username"}):
                        st.session_state.username = u
                        st.rerun()
                    else: st.error("Access Denied.")
        else:
            with st.form("register"):
                st.markdown("<h3 style='text-align:center; color:#D4AF37;'>CREATE ACCOUNT</h3>", unsafe_allow_html=True)
                u_n = st.text_input("Username").upper().strip()
                p_n = st.text_input("Password", type="password")
                i_c = st.text_input("Invite Key").strip()
                if st.form_submit_button("Register"):
                    check = api_request("GET", "invites", HEADERS_ANON, params={"code": f"eq.{i_c}", "is_used": "eq.false"})
                    if check and api_request("POST", "users", HEADERS_ADMIN, json={"username": u_n, "password": p_n}):
                        api_request("PATCH", "invites", HEADERS_ADMIN, params={"code": f"eq.{i_c}"}, json={"is_used": True, "used_by": u_n})
                        st.success("Success! Please Login.")
                    else: st.error("Invalid Key or User already exists.")
    st.stop()

# Logout area
st.markdown(f'<div style="text-align:right;"><span style="color:white;">LOGGED IN: </span><span style="color:#00FF00;">{st.session_state.username}</span></div>', unsafe_allow_html=True)
if st.button("Logout"):
    st.session_state.pop("username", None)
    st.rerun()

tabs = st.tabs(["📑 SINGLE ADD", "📦 BULK ADD", "🔍 INVENTORY"] + (["🎟️ ADMIN"] if st.session_state.username == ADMIN_USERNAME else []))

with tabs[0]:
    with st.form("single", clear_on_submit=True):
        c_id = st.text_input("Card ID (e.g. DTD206)").upper().strip()
        f_type = st.selectbox("Foil", list(FOIL_OPTIONS.keys()))
        q = st.number_input("Qty", value=1, step=1)
        if st.form_submit_button("Update Vault"):
            if c_id:
                api_request("POST", "inventories", HEADERS_ANON, json={"print_id": f"{c_id}-{FOIL_OPTIONS[f_type]}", "qty_change": int(q), "username": st.session_state.username})
                st.success(f"Added {c_id}")

with tabs[1]:
    bulk = st.text_area("Format: ID FOIL QTY")
    if st.button("Process Batch"):
        if bulk:
            for line in bulk.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 3:
                    f = BULK_FOIL_MAP.get(parts[1].lower(), "Regular")
                    api_request("POST", "inventories", HEADERS_ANON, json={"print_id": f"{parts[0].upper()}-{f}", "qty_change": int(parts[2]), "username": st.session_state.username})
            st.success("Batch Synced.")

with tabs[2]:
    if st.button("Refresh Inventory"): st.rerun()
    df = get_inventory(st.session_state.username)
    if not df.empty:
        s = st.text_input("Filter...")
        if s: df = df[df.apply(lambda r: r.astype(str).str.contains(s, case=False).any(), axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else: st.info("No data found.")

if st.session_state.username == ADMIN_USERNAME and len(tabs) >= 4:
    with tabs[3]:
        if st.button("New Key"):
            k = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
            api_request("POST", "invites", HEADERS_ADMIN, json={"code": k, "is_used": False})
            st.success(f"Key: {k}")
        st.divider()
        res = api_request("GET", "invites", HEADERS_ADMIN, params={"order": "created_at.desc"})
        if isinstance(res, list): st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)