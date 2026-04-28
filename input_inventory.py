import streamlit as st
import httpx
from datetime import datetime
import pandas as pd
import secrets
import string

# --- CONFIG & CONSTANTS ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

# Change this to whatever username you want to be the "Boss"
ADMIN_USERNAME = "ADMIN" 

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

FOIL_MAP = {"r": "Rainbow Foil", "c": "Cold Foil", "reg": "Regular", "f": "Full Art", "g": "Gold Cold Foil"}
PITCH_MAP = {1: "Red", 2: "Yellow", 3: "Blue"}

# --- DB FUNCTIONS ---
def verify_user(username, password):
    try:
        url = f"{URL}/rest/v1/users?username=eq.{username}&password=eq.{password}"
        resp = httpx.get(url, headers=headers)
        return len(resp.json()) > 0
    except: return False

def register_user(username, password, invite_code):
    try:
        # 1. Check if the code exists and hasn't been used yet
        invite_url = f"{URL}/rest/v1/invites?code=eq.{invite_code}&is_used=eq.false"
        invite_resp = httpx.get(invite_url, headers=headers).json()
        
        if not invite_resp:
            return False, "❌ Invalid or already used Invite Key!"

        # 2. Check if username is taken
        user_check = httpx.get(f"{URL}/rest/v1/users?username=eq.{username}", headers=headers).json()
        if user_check: 
            return False, "⚠️ Username already taken!"
        
        # 3. Create the user
        httpx.post(f"{URL}/rest/v1/users", headers=headers, 
                   json={"username": username, "password": password})
        
        # 4. Burn the invite key
        httpx.patch(f"{URL}/rest/v1/invites?code=eq.{invite_code}", 
                    headers=headers, json={"is_used": True})
        
        return True, "✅ Success! You can now log in."
    except: 
        return False, "🛑 System error during registration."

def create_new_invite():
    # Generates a random 6-character code like "FAB-X8K9P2"
    random_str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    code = f"FAB-{random_str}"
    try:
        httpx.post(f"{URL}/rest/v1/invites", headers=headers, json={"code": code})
        return code
    except: return None

def get_all_invites():
    try:
        url = f"{URL}/rest/v1/invites?select=code,is_used,created_at&order=created_at.desc"
        return httpx.get(url, headers=headers).json()
    except: return []

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

# --- UI LAYOUT ---
st.set_page_config(page_title="FaB Inventory 0.0.1", layout="centered")

# Visual Header
st.code("""
╔═════════════════════════════════════════╗
║        FaB_Inventory_Tool_0.0.1         ║
╚═════════════════════════════════════════╝
""", language="text")

# --- AUTHENTICATION SCREEN ---
if "username" not in st.session_state:
    mode = st.radio("Choose Mode", ["Login", "Register"], horizontal=True)
    
    with st.form("auth_form"):
        u = st.text_input("Username").upper().strip()
        p = st.text_input("Password", type="password")
        inv = ""
        if mode == "Register":
            inv = st.text_input("Invite Key")
            
        if st.form_submit_button(mode):
            if mode == "Login":
                if verify_user(u, p):
                    st.session_state.username = u
                    st.rerun()
                else: 
                    st.error("Invalid credentials.")
            else:
                if u and p and inv:
                    ok, msg = register_user(u, p, inv)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else:
                    st.warning("Please fill in all fields.")
    st.stop()

# --- MAIN APP (AFTER LOGIN) ---
username = st.session_state.username
st.sidebar.title(f"👤 {username}")
if st.sidebar.button("Logout"):
    del st.session_state.username
    st.rerun()

# Determine which tabs to show
tabs_list = ["📑 Single Add", "📦 Bulk Paste", "🔍 My Collection"]
if username == ADMIN_USERNAME:
    tabs_list.append("🔑 Admin Controls")

tabs = st.tabs(tabs_list)

# Tab 1: Single Add
with tabs[0]:
    with st.form("single_add"):
        c1, c2, c3 = st.columns([2,2,1])
        cid = c1.text_input("Card ID (e.g. PEN001)")
        f_choice = c2.selectbox("Foil", ["reg", "r", "c", "f", "g"])
        q = c3.number_input("Qty", min_value=1, value=1)
        if st.form_submit_button("Add Card"):
            foil_full = FOIL_MAP.get(f_choice)
            payload = {"print_id": f"{cid.upper()}-{foil_full}", "qty_change": q, "username": username, "updated_at": datetime.now().isoformat()}
            httpx.post(f"{URL}/rest/v1/inventories", headers=headers, json=payload)
            st.toast(f"Added {cid}!")

# Tab 2: Bulk Paste
with tabs[1]:
    st.info("Format: `ID FOIL QTY` (One per line)\nExample:\n`PEN001 reg 4`\n`WTR002 r 1`")
    bulk_text = st.text_area("Paste List Here", height=200)
    if st.button("Process Bulk Upload"):
        if bulk_text:
            with st.spinner("Uploading..."):
                results = process_bulk_logic(username, bulk_text)
                st.success(f"Processed {len(results)} lines.")
                with st.expander("View Logs"):
                    for r in results: st.write(r)

# Tab 3: View Collection
with tabs[2]:
    col_a, col_b = st.columns([3,1])
    search = col_a.text_input("Filter by Name/Set")
    if col_b.button("🔄 Refresh"):
        st.session_state.inv_data = get_inventory_data(username)
    
    if "inv_data" in st.session_state:
        df = pd.DataFrame(st.session_state.inv_data)
        if not df.empty:
            if search:
                df = df[df['Name'].str.contains(search, case=False) | df['Set'].str.contains(search, case=False)]
            st.dataframe(df, use_container_width=True, hide_index=True)

# Tab 4: Admin Controls (Hidden from non-admins)
if username == ADMIN_USERNAME:
    with tabs[3]:
        st.subheader("Generate New Invite Key")
        if st.button("✨ Create One-Time Key"):
            new_code = create_new_invite()
            if new_code:
                st.success(f"Code Created! Copy this: `{new_code}`")
            else:
                st.error("Failed to generate code.")
        
        st.divider()
        st.subheader("Existing Keys Status")
        
        raw_invites = get_all_invites()
        if raw_invites:
            # Convert to DataFrame for easy reading
            inv_df = pd.DataFrame(raw_invites)
            inv_df['is_used'] = inv_df['is_used'].apply(lambda x: "🔴 Used" if x else "🟢 Active")
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
        else:
            st.info("No keys generated yet.")