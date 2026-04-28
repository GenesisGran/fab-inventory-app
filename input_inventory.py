import streamlit as st
import httpx
from datetime import datetime
import pandas as pd
import random
import string

# --- CONFIG & CONSTANTS ---
URL = st.secrets["SUPABASE_URL"]
ANON_KEY = st.secrets["SUPABASE_KEY"]
SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", ANON_KEY) 
ADMIN_USERNAME = "ADMIN" 

headers_anon = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json",
}

headers_admin = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

FOIL_DISPLAY = {
    "Regular": "reg",
    "Rainbow Foil": "r",
    "Cold Foil": "c",
    "Full Art": "f",
    "Gold Cold Foil": "g"
}
FOIL_MAP_INTERNAL = {"r": "Rainbow Foil", "c": "Cold Foil", "reg": "Regular", "f": "Full Art", "g": "Gold Cold Foil"}
PITCH_MAP = {1: "🔴 Red", 2: "🟡 Yellow", 3: "🔵 Blue"}

def local_css():
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-color: #000000 !important;
        /*background-image: url("https://i.ibb.co/v6yM8Z8/image.png") !important; */
        background-size: contain !important;
        background-repeat: no-repeat !important;
        background-position: center top !important;
        background-attachment: fixed !important;
    }}
    [data-testid="stHeader"], [data-testid="stAppViewBlockContainer"] {{
        background: rgba(0,0,0,0) !important;
    }}
    div[data-testid="stVerticalBlock"] > div:has(div.stButton), .stTabs {{
        background: rgba(0, 0, 0, 0.85) !important;
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(212, 175, 55, 0.4);
        margin-bottom: 20px;
    }}
    button[data-baseweb="tab"] {{ color: white !important; }}
    button[aria-selected="true"] {{
        background-color: rgba(212, 175, 55, 0.2) !important;
        border-bottom: 2px solid #d4af37 !important;
    }}
    h1, h2, h3 {{ color: #d4af37 !important; text-shadow: 2px 2px 8px #000000; }}
    .stMarkdown, p, span {{ color: #ffffff !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- DB FUNCTIONS ---
def verify_user(username, password):
    try:
        url = f"{URL}/rest/v1/users?username=eq.{username}&password=eq.{password}"
        resp = httpx.get(url, headers=headers_anon)
        return len(resp.json()) > 0
    except: return False

def register_user(username, password, invite_code):
    try:
        invite_url = f"{URL}/rest/v1/invites?code=eq.{invite_code}&is_used=eq.false"
        invite_resp = httpx.get(invite_url, headers=headers_admin).json()
        if not invite_resp or not isinstance(invite_resp, list) or len(invite_resp) == 0:
            return False, "❌ Invalid/Used Key"
        user_check = httpx.get(f"{URL}/rest/v1/users?username=eq.{username}", headers=headers_admin).json()
        if user_check: return False, "⚠️ Name Taken"
        httpx.post(f"{URL}/rest/v1/users", headers=headers_admin, json={"username": username, "password": password})
        now = datetime.now().isoformat()
        httpx.patch(f"{URL}/rest/v1/invites?code=eq.{invite_code}", headers=headers_admin, json={"is_used": True, "used_by": username, "used_at": now})
        return True, "✅ Registration Complete!"
    except: return False, "🛑 Error"

def check_card_exists(print_id):
    url = f"{URL}/rest/v1/card_prints?print_id=eq.{print_id}&select=print_id"
    resp = httpx.get(url, headers=headers_anon)
    return len(resp.json()) > 0

def get_inventory_data(username):
    query = "qty_change,print_id,card_prints(cards(name,pitch))"
    url = f"{URL}/rest/v1/inventories?username=eq.{username}&select={query}"
    resp = httpx.get(url, headers=headers_anon).json()
    if not resp or not isinstance(resp, list): return []
    vault = {}
    for entry in resp:
        pid = entry.get('print_id', "")
        p_data = entry.get('card_prints', {}) or {}
        c_data = p_data.get('cards', {}) or {}
        if pid not in vault:
            parts = pid.split('-', 1)
            vault[pid] = {"Name": c_data.get('name', '???'), "Set": parts[0], "Foil": parts[1] if len(parts)>1 else "Reg", "Color": PITCH_MAP.get(c_data.get('pitch'), "N/A"), "Total": 0}
        vault[pid]["Total"] += entry.get('qty_change', 0)
    return [v for v in vault.values() if v["Total"] > 0]

def process_bulk_logic(username, text_data):
    lines = text_data.split('\n')
    results = []
    for line in lines:
        parts = line.split()
        if len(parts) < 3: continue
        card_code, f_key, qty = parts[0].upper(), parts[1].lower(), int(parts[2])
        foil = FOIL_MAP_INTERNAL.get(f_key, "Regular")
        print_id = f"{card_code}-{foil}"
        
        if check_card_exists(print_id):
            payload = {"print_id": print_id, "qty_change": qty, "username": username, "updated_at": datetime.now().isoformat()}
            httpx.post(f"{URL}/rest/v1/inventories", headers=headers_anon, json=payload)
            results.append(f"✅ {print_id}")
        else:
            results.append(f"❓ NOT FOUND: {print_id}")
    return results

# --- APP START ---
st.set_page_config(page_title="FaB Inventory Tool 0.0.1", layout="centered")
local_css()

st.title("🛡️ FaB Inventory Tool 0.0.1")

if "username" not in st.session_state:
    mode = st.radio("Mode", ["Login", "Register"], horizontal=True)
    with st.form("auth_form", clear_on_submit=False):
        u = st.text_input("Username").upper().strip()
        p = st.text_input("Password", type="password")
        inv = st.text_input("Invite Key") if mode == "Register" else ""
        if st.form_submit_button("AUTHENTICATE"):
            if mode == "Login":
                if verify_user(u, p):
                    st.session_state.username = u
                    st.rerun()
                else: st.error("Access Denied.")
            elif mode == "Register":
                ok, msg = register_user(u, p, inv)
                if ok: st.success(msg)
                else: st.error(msg)
    st.stop()

# --- MAIN APP ---
st.sidebar.write(f"Logged in: **{st.session_state.username}**")
if st.sidebar.button("Logout"):
    del st.session_state.username
    st.rerun()

tabs = st.tabs(["📑 Single Add", "📦 Bulk Add", "🔍 Inventory", "🎟️ Admin"])

with tabs[0]:
    msg_slot = st.empty() # Clear spot for success/error messages
    with st.form("single"):
        c1, c2, c3 = st.columns([2,2,1])
        cid = c1.text_input("Card ID")
        f_display = c2.selectbox("Foil Type", list(FOIL_DISPLAY.keys()))
        q = c3.number_input("Qty", min_value=1, value=1)
        if st.form_submit_button("ADD CARD"):
            f_internal = FOIL_MAP_INTERNAL.get(FOIL_DISPLAY[f_display])
            print_id = f"{cid.upper()}-{f_internal}"
            
            if check_card_exists(print_id):
                payload = {"print_id": print_id, "qty_change": q, "username": st.session_state.username, "updated_at": datetime.now().isoformat()}
                httpx.post(f"{URL}/rest/v1/inventories", headers=headers_anon, json=payload)
                msg_slot.success(f"⚔️ **{print_id}** successfully added to Archive!")
            else:
                msg_slot.error(f"🚫 **{print_id}** not found in Database. Please check the ID.")

with tabs[1]:
    msg_slot_bulk = st.empty()
    st.caption("Use short codes: `reg`, `r`, `c`, `f`, `g` (e.g., PEN001 r 5)")
    bulk = st.text_area("Paste List")
    if st.button("PROCESS BULK"):
        if bulk:
            results = process_bulk_logic(st.session_state.username, bulk)
            with msg_slot_bulk.container():
                for res in results:
                    if "✅" in res: st.success(res)
                    else: st.warning(res)

with tabs[2]:
    st.session_state.inv_data = get_inventory_data(st.session_state.username)
    search = st.text_input("Search Collection")
    if st.button("FORCE REFRESH"):
        st.session_state.inv_data = get_inventory_data(st.session_state.username)
        st.rerun()
    df = pd.DataFrame(st.session_state.inv_data)
    if not df.empty:
        if search:
            df = df[df['Name'].str.contains(search, case=False) | df['Set'].str.contains(search, case=False)]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else: st.info("Inventory is empty.")

with tabs[3]:
    if st.session_state.username == ADMIN_USERNAME:
        if st.button("Generate Key"):
            code = "FAB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            resp = httpx.post(f"{URL}/rest/v1/invites", headers=headers_admin, json={"code": code})
            if resp.status_code in [200, 201]: st.success(f"Key created: `{code}`")
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            st.subheader("Available Keys")
            resp_active = httpx.get(f"{URL}/rest/v1/invites?is_used=eq.false&select=code", headers=headers_admin).json()
            if isinstance(resp_active, list):
                for i in resp_active: st.code(i['code'])
        with col_inv2:
            st.subheader("Used Keys History")
            resp_used = httpx.get(f"{URL}/rest/v1/invites?is_used=eq.true&select=code,used_by,used_at&order=used_at.desc", headers=headers_admin).json()
            if isinstance(resp_used, list) and len(resp_used) > 0:
                for i in resp_used:
                    st.caption(f"🔑 {i['code']}")
                    st.write(f"User: {i.get('used_by', '???')}")
                    st.text(f"Date: {i.get('used_at', '')[:10]}")
                    st.divider()
    else: st.warning("Admin Access Required")