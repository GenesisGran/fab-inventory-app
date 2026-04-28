import streamlit as st
import httpx
from datetime import datetime
import pandas as pd

# --- CONSTANTS ---
FOIL_MAP = {"Regular": "Regular", "Rainbow Foil": "Rainbow Foil", "Cold Foil": "Cold Foil", "Full Art": "Full Art", "Gold Cold Foil": "Gold Cold Foil"}
PITCH_MAP = {1: "Red", 2: "Yellow", 3: "Blue"}

# --- DATABASE CONFIG ---
# We use st.secrets for security. Never hardcode keys in the script!
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

# --- FUNCTIONS ---
def check_user_exists(username):
    try:
        url = f"{URL}/rest/v1/users?username=eq.{username}"
        resp = httpx.get(url, headers=headers)
        return len(resp.json()) > 0
    except: return False

def register_user(username):
    try:
        httpx.post(f"{URL}/rest/v1/users", headers=headers, json={"username": username})
        return True
    except: return False

def get_inventory_data(username):
    query = "qty_change,print_id,card_prints(cards(name,pitch))"
    url = f"{URL}/rest/v1/inventories?username=eq.{username}&select={query}"
    resp = httpx.get(url, headers=headers)
    data = resp.json()
    
    if not data or isinstance(data, dict): return []

    vault = {}
    for entry in data:
        pid = entry.get('print_id') or ""
        qty = entry.get('qty_change', 0)
        p_data = entry.get('card_prints') or {}
        c_data = p_data.get('cards') or {}
        
        parts = pid.split('-', 1)
        set_id = parts[0]
        foil = parts[1] if len(parts) > 1 else "Regular"
        
        if pid not in vault:
            vault[pid] = {
                "Name": c_data.get('name', 'Unknown'),
                "Set": set_id,
                "Foil": foil,
                "Color": PITCH_MAP.get(c_data.get('pitch'), "N/A"),
                "Total": 0
            }
        vault[pid]["Total"] += qty
    
    # Filter out zeros and return as list
    return [v for v in vault.values() if v["Total"] > 0]

def add_card(username, card_id, foil, qty):
    print_id = f"{card_id.upper()}-{foil}"
    payload = {
        "print_id": print_id, 
        "qty_change": qty, 
        "username": username, 
        "updated_at": datetime.now().isoformat()
    }
    resp = httpx.post(f"{URL}/rest/v1/inventories", headers=headers, json=payload)
    return resp.status_code in [200, 201]

# --- UI LAYOUT ---
st.set_page_config(page_title="FaB Inventory 0.0.1", page_icon="🛡️")

# Custom CSS to make it look better on mobile
st.markdown("""<style> .stTabs [data-baseweb="tab-list"] { gap: 10px; } 
            .stTabs [data-baseweb="tab"] { padding: 10px 20px; border-radius: 4px; } </style>""", unsafe_allow_html=True)

st.title("🛡️ FaB Inventory Tool")

# --- LOGIN LOGIC ---
if "username" not in st.session_state:
    with st.container():
        st.subheader("Login to your Vault")
        user_in = st.text_input("Username").strip().upper()
        col1, col2 = st.columns(2)
        
        if col1.button("Login", use_container_width=True):
            if check_user_exists(user_in):
                st.session_state.username = user_in
                st.rerun()
            else:
                st.error("User not found.")
                
        if col2.button("Register New", use_container_width=True):
            if user_in and register_user(user_in):
                st.success(f"Registered {user_in}!")
            else:
                st.error("Invalid username.")
    st.stop()

# --- MAIN APP (AFTER LOGIN) ---
username = st.session_state.username
st.sidebar.caption(f"Logged in as: **{username}**")
if st.sidebar.button("Logout"):
    del st.session_state.username
    st.rerun()

tab_add, tab_view = st.tabs(["➕ Add Cards", "🔍 My Collection"])

with tab_add:
    st.subheader("Quick Add")
    c_id = st.text_input("Card ID", placeholder="e.g., PEN001").upper()
    c_foil = st.selectbox("Foiling", list(FOIL_MAP.keys()))
    c_qty = st.number_input("Quantity", min_value=1, value=1)
    
    if st.button("Save to Vault", use_container_width=True):
        if c_id:
            with st.spinner("Syncing..."):
                if add_card(username, c_id, c_foil, c_qty):
                    st.success(f"Added {c_qty}x {c_id}!")
                else:
                    st.error("Card ID not found in database.")
        else:
            st.warning("Please enter a Card ID.")

with tab_view:
    search = st.text_input("Filter by Name or Set", placeholder="e.g., WTR or Scar")
    
    if st.button("Refresh Collection", use_container_width=True):
        st.session_state.data = get_inventory_data(username)

    if "data" in st.session_state:
        df = pd.DataFrame(st.session_state.data)
        if not df.empty:
            if search:
                df = df[df['Name'].str.contains(search, case=False) | df['Set'].str.contains(search, case=False)]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Your vault is empty.")