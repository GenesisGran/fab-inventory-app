import streamlit as st
import httpx
from datetime import datetime
import pandas as pd
import random
import string

# --- CONFIG & CONSTANTS ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
ADMIN_USERNAME = "ADMIN" # Change to your preferred admin name

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

FOIL_MAP = {"reg": "Regular", "r": "Rainbow Foil", "c": "Cold Foil", "f": "Full Art", "g": "Gold Cold Foil"}
PITCH_MAP = {1: "🔴 Red", 2: "🟡 Yellow", 3: "🔵 Blue"}

# --- CUSTOM CSS (THE MAGIC) ---
def local_css():
    st.markdown(f"""
    <style>
    /* Background Image */
    .stApp {{
        background: linear_gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), 
                    url("https://fabtcg.com/static/images/hero-backgrounds/enigma.original.jpg");
        background-size: cover;
        background-attachment: fixed;
    }}

    /* Frosted Glass Effect for Containers */
    div[data-testid="stVerticalBlock"] > div:has(div.stButton) {{
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: rgba(20, 20, 25, 0.85) !important;
    }}

    /* Custom Button Styling */
    .stButton > button {{
        background-color: transparent;
        color: #d4af37; /* Gold */
        border: 1px solid #d4af37;
        border-radius: 5px;
        transition: 0.3s;
        text-transform: uppercase;
        font-weight: bold;
        letter-spacing: 1px;
    }}

    .stButton > button:hover {{
        background-color: #d4af37;
        color: black;
        border: 1px solid #d4af37;
    }}

    /* Header Styling */
    h1, h2, h3 {{
        color: #f0f0f0 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        font-family: 'serif';
    }}
    
    /* Input field styling */
    .stTextInput input {{
        background-color: rgba(0,0,0,0.3) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE FUNCTIONS ---
def verify_user(username, password):
    try:
        url = f"{URL}/rest/v1/users?username=eq.{username}&password=eq.{password}"
        resp = httpx.get(url, headers=headers)
        return len(resp.json()) > 0
    except: return False

def register_user(username, password, invite_code):
    try:
        invite_url = f"{URL}/rest/v1/invites?code=eq.{invite_code}&is_used=eq.false"
        invite_resp = httpx.get(invite_url, headers=headers).json()
        if not invite_resp: return False, "❌ Invalid or Expired Key"
        
        user_check = httpx.get(f"{URL}/rest/v1/users?username=eq.{username}", headers=headers).json()
        if user_check: return False, "⚠️ Name Taken"

        httpx.post(f"{URL}/rest/v1/users", headers=headers, json={"username": username, "password": password})
        httpx.patch(f"{URL}/rest/v1/invites?code=eq.{invite_code}", headers=headers, json={"is_used": True})
        return True, "✅ Vault Created!"
    except: return False, "🛑 Error"

def process_bulk_logic(username, text_data):
    lines = text_data.split('\n')
    results = []
    for line in lines:
        parts = line.split()
        if len(parts) < 3: continue
        card_code, f_key, qty = parts[0].upper(), parts[1].lower(), int(parts[2])
        foil = FOIL_MAP.get(f_key, "Regular")
        print_id = f"{card_code}-{foil}"
        payload = {"print_id": print_id, "qty_change": qty, "username": username, "updated_at": datetime.now().isoformat()}
        resp = httpx.post(f"{URL}/rest/v1/inventories", headers=headers, json=payload)
        results.append(f"{'✅' if resp.status_code in [200,201] else '❌'} {print_id}")
    return results

def get_inventory_data(username):
    query = "qty_change,print_id,card_prints(cards(name,pitch))"
    url = f"{URL}/rest/v1/inventories?username=eq.{username}&select={query}"
    resp = httpx.get(url, headers=headers).json()
    if not resp or isinstance(resp, dict): return []
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

def generate_new_invite():
    code = "FAB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    httpx.post(f"{URL}/rest/v1/invites", headers=headers, json={"code": code})
    return code

# --- APP START ---
st.set_page_config(page_title="The Archive of Rathe", page_icon="⚔️", layout="centered")
local_css()

# Atmospheric Header
st.markdown("<h1 style='text-align: center;'>⚔️ THE ARCHIVE OF RATHE</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #aaa;'>Inventory Management for Flesh and Blood</p>", unsafe_allow_html=True)

if "username" not in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        mode = st.radio("Access Mode", ["Login", "Register"], horizontal=True)
        with st.form("auth_form"):
            u = st.text_input("Username").upper().strip()
            p = st.text_input("Password", type="password")
            inv = st.text_input("Invite Key") if mode == "Register" else ""
            
            if st.form_submit_button(f"ENTER VAULT"):
                if mode == "Login":
                    if verify_user(u, p):
                        st.session_state.username = u
                        st.rerun()
                    else: st.error("Access Denied.")
                else:
                    ok, msg = register_user(u, p, inv)
                    if ok: st.success(msg)
                    else: st.error(msg)
    st.stop()

# --- MAIN INTERFACE ---
st.sidebar.markdown(f"### 🛡️ Hero: {st.session_state.username}")
if st.sidebar.button("EXIT ARCHIVE"):
    del st.session_state.username
    st.rerun()

tabs = ["➕ Add", "📦 Bulk", "🔍 Vault"]
if st.session_state.username == ADMIN_USERNAME:
    tabs.append("🎟️ Keys")

t = st.tabs(tabs)

# Tab 1: Single Add
with t[0]:
    with st.container():
        st.subheader("Manual Entry")
        c1, c2, c3 = st.columns([2,2,1])
        cid = c1.text_input("Card ID", placeholder="WTR001")
        f_choice = c2.selectbox("Foil", list(FOIL_MAP.keys()))
        q = c3.number_input("Qty", min_value=1, value=1)
        if st.button("COMMIT TO VAULT", use_container_width=True):
            foil_full = FOIL_MAP.get(f_choice)
            payload = {"print_id": f"{cid.upper()}-{foil_full}", "qty_change": q, "username": st.session_state.username, "updated_at": datetime.now().isoformat()}
            httpx.post(f"{URL}/rest/v1/inventories", headers=headers, json=payload)
            st.toast(f"Synchronized {cid}!")

# Tab 2: Bulk
with t[1]:
    st.markdown("### 📦 Mass Import")
    bulk_text = st.text_area("Format: ID FOIL QTY", height=150, placeholder="WTR001 reg 4\nARC055 r 1")
    if st.button("SYNC BATCH", use_container_width=True):
        if bulk_text:
            with st.status("Writing to Archive..."):
                results = process_bulk_logic(st.session_state.username, bulk_text)
                st.success(f"Archived {len(results)} items.")

# Tab 3: Collection
with t[2]:
    search = st.text_input("Filter by Name/Set ID")
    if st.button("REFRESH COLLECTION", use_container_width=True):
        st.session_state.inv_data = get_inventory_data(st.session_state.username)
    
    if "inv_data" in st.session_state:
        df = pd.DataFrame(st.session_state.inv_data)
        if not df.empty:
            if search:
                df = df[df['Name'].str.contains(search, case=False) | df['Set'].str.contains(search, case=False)]
            # Beautifully Styled Dataframe
            st.dataframe(df, use_container_width=True, hide_index=True, 
                         column_config={
                             "Total": st.column_config.NumberColumn(format="%d 🎴"),
                             "Color": st.column_config.TextColumn(help="Pitch Value Color")
                         })

# Tab 4: Admin
if st.session_state.username == ADMIN_USERNAME:
    with t[3]:
        st.subheader("Invite Management")
        if st.button("FORGE NEW KEY"):
            st.code(generate_new_invite())
        
        url = f"{URL}/rest/v1/invites?is_used=eq.false&select=code"
        invites = httpx.get(url, headers=headers).json()
        if invites:
            st.write("Current Valid Keys:")
            for i in invites: st.text(f"🎟️ {i['code']}")