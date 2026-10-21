import os
import datetime
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Trojan Market - Store Management System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- FILE STORAGE & CONFIGURATION ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ROSTER_FILE = os.path.join(ROOT_DIR, "roster.csv")
SHIFTS_FILE = os.path.join(ROOT_DIR, "shifts.csv")
INVENTORY_FILE = os.path.join(ROOT_DIR, "inventory.csv")
SALES_FILE = os.path.join(ROOT_DIR, "sales.csv")
AUDIT_FILE = os.path.join(ROOT_DIR, "audit_logs.csv")

MAX_SHIFT_HOURS = 4.0

ADMIN_EMAILS = [
    "deca@simsburyschools.net",
    "jstanwood@simsburyschools.net",
    "27cadoffe@simsburyschools.net",
    "30guptaa@simsburyschools.net",
]

# --- STYLING (FORCE-HIDE SIDEBAR ON DESKTOP & MOBILE) ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    section[data-testid="stSidebar"],
    button[aria-label="Toggle sidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0b1120 !important;
        color: #e5e7eb !important;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        background: #0b1120 !important;
        max-width: 100% !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, div, span, label, li, button {
        color: #e5e7eb !important;
    }
    
    .stTabs [role="tablist"] {
        gap: 0.5rem;
        background: transparent;
    }
    
    .stTabs [role="tab"] {
        border-radius: 10px 10px 0 0;
        background: #1f2937;
        border: 1px solid rgba(148, 163, 184, 0.2);
        color: #dbeafe;
        padding: 0.5rem 1rem;
    }
    
    .stTabs [role="tab"][aria-selected="true"] {
        background: #2563eb;
        color: white;
        border-color: #3b82f6;
    }
    
    .stTextInput > div > div, .stSelectbox > div > div, .stNumberInput > div > div,
    .stRadio > div, .stDataFrame, .stDataEditor, .stMarkdownContainer, .stAlert,
    .stButton > button, .stDownloadButton > button {
        background: #111827;
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #e5e7eb;
    }
    
    .stButton > button {
        background: #1d4ed8;
        color: white;
        border: none;
        border-radius: 0.5rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background: #2563eb;
        color: white;
    }
    
    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
    }
    
    [data-testid="stMetricContainer"] {
        background: rgba(17, 24, 39, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 0.75rem;
        padding: 0.75rem;
    }
    
    .stInfo, .stSuccess, .stWarning, .stError {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- TIME FORMATTING HELPER ---
def format_hours_mins(hours_val: float) -> str:
    """Formats decimal hours into clean hours and minutes (e.g. '2 mins' or '1 hr 15 mins')."""
    total_minutes = int(round(float(hours_val) * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    
    if h > 0 and m > 0:
        return f"{h} hr{'s' if h > 1 else ''} {m} min{'s' if m > 1 else ''}"
    elif h > 0:
        return f"{h} hr{'s' if h > 1 else ''}"
    else:
        return f"{m} min{'s' if m != 1 else ''}"


# --- AUDIT LOGGING ENGINE ---
def log_audit_event(action: str, details: str):
    user_email = st.session_state.get("user_email", "system")
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_log = {
        "timestamp": now_str,
        "user_email": user_email,
        "action": action,
        "details": details
    }
    
    audit_df = st.session_state.get("audit_df", load_or_create_df(AUDIT_FILE, get_default_audit()))
    audit_df = pd.concat([audit_df, pd.DataFrame([new_log])], ignore_index=True)
    save_df(AUDIT_FILE, audit_df)
    st.session_state["audit_df"] = audit_df


# --- BARCODE KEYCARD RENDERER ---
def render_barcode_keycard(student_id: str, barcode_val: str, student_name: str, track: str, photo_url: str = ""):
    avatar_html = f'<img src="{photo_url}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #3b82f6; margin-bottom: 8px; object-fit: cover;" />' if photo_url else '<div style="font-size: 32px; margin-bottom: 4px;">👤</div>'
    
    html_code = f"""
    <div style="
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #3b82f6;
        border-radius: 16px;
        padding: 16px;
        width: 320px;
        text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        color: #ffffff;
        margin: auto;
    ">
        <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 2px; color: #93c5fd; font-weight: 700;">
            SIMSBURY HIGH SCHOOL
        </div>
        <div style="font-size: 16px; font-weight: 800; color: #f8fafc; margin-bottom: 8px;">
            🛡️ TROJAN MARKET PASS
        </div>
        
        {avatar_html}

        <div style="font-size: 15px; font-weight: 700; color: #ffffff;">
            {student_name}
        </div>
        <div style="font-size: 11px; color: #60a5fa; margin-bottom: 8px;">
            ID: {student_id} • {track}
        </div>
        
        <div style="background: #ffffff; padding: 8px 6px 2px 6px; border-radius: 10px; display: inline-block;">
            <svg id="barcode_{student_id}"></svg>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
    <script>
        JsBarcode("#barcode_{student_id}", "{barcode_val}", {{
            format: "CODE128",
            width: 2,
            height: 44,
            displayValue: true,
            fontSize: 12,
            marginTop: 0,
            marginBottom: 0
        }});
    </script>
    """
    components.html(html_code, height=270)


# --- DATA HELPERS ---
def normalize_dataframe(df: pd.DataFrame, numeric_columns=None, text_columns=None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    numeric_columns = numeric_columns or []
    text_columns = text_columns or []

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: "" if pd.isna(v) else str(v))

    return df


def load_or_create_df(file_path: str, default_df: pd.DataFrame) -> pd.DataFrame:
    if not os.path.exists(file_path):
        default_df.to_csv(file_path, index=False)
        return default_df.copy()
    try:
        df = pd.read_csv(file_path)
    except Exception:
        default_df.to_csv(file_path, index=False)
        return default_df.copy()

    for col in default_df.columns:
        if col not in df.columns:
            df[col] = default_df[col].iloc[0] if len(default_df) > 0 and col in default_df else ""

    return df


def save_df(file_path: str, df: pd.DataFrame) -> None:
    df.to_csv(file_path, index=False)


# Default Datasets
def get_default_roster() -> pd.DataFrame:
    return pd.DataFrame([
        {"student_id": "SIM1001", "barcode_id": "BC-1001", "first_name": "Caroline", "last_name": "Fair", "course": "1-Entrepreneurship", "track": "DECA President", "req_hours": 20, "photo_url": ""},
        {"student_id": "SIM1002", "barcode_id": "BC-1002", "first_name": "Elizabeth", "last_name": "Cadoff", "course": "6-Marketing", "track": "VP-School Store", "req_hours": 20, "photo_url": ""},
        {"student_id": "SIM1003", "barcode_id": "BC-1003", "first_name": "Radha", "last_name": "Bansal", "course": "1-Entrepreneurship", "track": "VP-Marketing", "req_hours": 20, "photo_url": ""},
        {"student_id": "SIM1004", "barcode_id": "BC-1004", "first_name": "Liam", "last_name": "Ricciardelli", "course": "2-Marketing", "track": "Officer", "req_hours": 10, "photo_url": ""},
        {"student_id": "SIM1005", "barcode_id": "BC-1005", "first_name": "Julian", "last_name": "Mass", "course": "2-Marketing", "track": "Honors: Store", "req_hours": 10, "photo_url": ""},
        {"student_id": "SIM1006", "barcode_id": "BC-1006", "first_name": "Henry", "last_name": "Pfeiffer", "course": "6-Marketing", "track": "ICDC", "req_hours": 10, "photo_url": ""},
        {"student_id": "SIM1007", "barcode_id": "BC-1007", "first_name": "Caleb", "last_name": "Deems", "course": "7-SEM", "track": "Honors: Store", "req_hours": 10, "photo_url": ""},
        {"student_id": "SIM1008", "barcode_id": "BC-1008", "first_name": "Olivia", "last_name": "Campasano", "course": "Accounting 2", "track": "Store", "req_hours": 10, "photo_url": ""},
        {"student_id": "SIM1009", "barcode_id": "13753", "first_name": "Anay", "last_name": "Gupta", "course": "Accounting 2", "track": "Store", "req_hours": 10, "photo_url": ""},
    ])


def get_default_shifts() -> pd.DataFrame:
    return pd.DataFrame(columns=["student_id", "name", "check_in", "check_out", "hours_logged", "shift_type", "status", "flagged"])


def get_default_inventory() -> pd.DataFrame:
    return pd.DataFrame([
        {"item_id": "SKU-001", "revtrak_sku": "RT-COOK-01", "item_name": "Fresh Baked Cookies", "category": "Food", "stock": 48, "unit_price": 1.50},
        {"item_id": "SKU-002", "revtrak_sku": "RT-POPC-01", "item_name": "Fresh Popcorn Bag", "category": "Food", "stock": 30, "unit_price": 2.00},
        {"item_id": "SKU-003", "revtrak_sku": "RT-SLUS-01", "item_name": "Slushy (Full Size)", "category": "Beverage", "stock": 25, "unit_price": 2.50},
        {"item_id": "SKU-004", "revtrak_sku": "RT-HOOD-01", "item_name": "SHS Trojan Hoodie", "category": "Apparel", "stock": 15, "unit_price": 35.00},
        {"item_id": "SKU-005", "revtrak_sku": "RT-TSHI-01", "item_name": "Trojan Spirit T-Shirt", "category": "Apparel", "stock": 22, "unit_price": 18.00},
    ])


def get_default_sales() -> pd.DataFrame:
    return pd.DataFrame(columns=["transaction_id", "timestamp", "item_id", "quantity", "total_price", "payment_method"])


def get_default_audit() -> pd.DataFrame:
    return pd.DataFrame(columns=["timestamp", "user_email", "action", "details"])


def reload_all_data():
    rost_raw = load_or_create_df(ROSTER_FILE, get_default_roster())
    if "barcode_id" not in rost_raw.columns:
        rost_raw["barcode_id"] = rost_raw["student_id"]
    if "photo_url" not in rost_raw.columns:
        rost_raw["photo_url"] = ""

    st.session_state["roster_df"] = normalize_dataframe(
        rost_raw, numeric_columns=["req_hours"], text_columns=["student_id", "barcode_id", "first_name", "last_name", "photo_url"]
    )
    
    shifts_raw = load_or_create_df(SHIFTS_FILE, get_default_shifts())
    if "flagged" not in shifts_raw.columns:
        shifts_raw["flagged"] = "NO"
    
    st.session_state["shifts_df"] = normalize_dataframe(
        shifts_raw,
        numeric_columns=["hours_logged"],
        text_columns=["student_id", "name", "check_in", "check_out", "shift_type", "status", "flagged"],
    )
    
    inv_raw = load_or_create_df(INVENTORY_FILE, get_default_inventory())
    if "revtrak_sku" not in inv_raw.columns:
        inv_raw["revtrak_sku"] = "RT-NONE"
        
    st.session_state["inventory_df"] = normalize_dataframe(
        inv_raw, numeric_columns=["stock", "unit_price"]
    )
    st.session_state["sales_df"] = normalize_dataframe(
        load_or_create_df(SALES_FILE, get_default_sales()),
        numeric_columns=["quantity", "total_price"],
        text_columns=["transaction_id", "timestamp", "item_id", "payment_method"],
    )
    st.session_state["audit_df"] = normalize_dataframe(
        load_or_create_df(AUDIT_FILE, get_default_audit()),
        text_columns=["timestamp", "user_email", "action", "details"]
    )


# --- AUTOMATED REVTRAK SYNC ENGINE ---
def sync_revtrak_orders(silent=False):
    if "revtrak" not in st.secrets:
        if not silent:
            st.error("RevTrak secrets not configured. Please set up `.streamlit/secrets.toml`.")
        return

    api_url = st.secrets["revtrak"].get("api_url", "")
    api_key = st.secrets["revtrak"].get("api_key", "")

    if not api_url or not api_key:
        if not silent:
            st.error("Missing RevTrak API credentials in secrets configuration.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(f"{api_url}/orders/recent", headers=headers, timeout=3)
        if response.status_code != 200:
            if not silent:
                st.error(f"RevTrak API call failed (HTTP {response.status_code}): {response.text}")
            return

        orders = response.json().get("orders", [])
        inv_df = st.session_state.get("inventory_df", load_or_create_df(INVENTORY_FILE, get_default_inventory()))
        sls_df = st.session_state.get("sales_df", load_or_create_df(SALES_FILE, get_default_sales()))
        updated = False

        for order in orders:
            order_id = order.get("order_id")
            if not sls_df.empty and order_id in sls_df["transaction_id"].values:
                continue

            for item in order.get("items", []):
                rt_sku = item.get("sku")
                qty = int(item.get("quantity", 1))

                match = inv_df[inv_df["revtrak_sku"] == rt_sku]
                if not match.empty:
                    idx = match.index[0]
                    current_stock = int(inv_df.at[idx, "stock"])
                    inv_df.at[idx, "stock"] = max(0, current_stock - qty)

                    new_sale = {
                        "transaction_id": order_id,
                        "timestamp": order.get("created_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        "item_id": inv_df.at[idx, "item_id"],
                        "quantity": qty,
                        "total_price": float(item.get("price", 0.0)) * qty,
                        "payment_method": "RevTrak Online",
                    }
                    sls_df = pd.concat([sls_df, pd.DataFrame([new_sale])], ignore_index=True)
                    updated = True

        if updated:
            save_df(INVENTORY_FILE, inv_df)
            save_df(SALES_FILE, sls_df)
            st.session_state["inventory_df"] = inv_df
            st.session_state["sales_df"] = sls_df
            log_audit_event("REVTRAK_SYNC", f"Imported new orders from RevTrak endpoint.")
            st.toast("⚡ RevTrak Auto-Sync: New online sales imported & inventory updated!")
            st.rerun()
        else:
            if not silent:
                st.info("Inventory is already up to date with RevTrak.")

    except Exception as e:
        if not silent:
            st.error(f"RevTrak sync error: {e}")


def fetch_revtrak_item_details(rt_sku: str) -> dict | None:
    if "revtrak" not in st.secrets:
        return None

    api_url = st.secrets["revtrak"].get("api_url", "")
    api_key = st.secrets["revtrak"].get("api_key", "")

    if not api_url or not api_key:
        return None

    try:
        res = requests.get(
            f"{api_url}/catalog/items/{rt_sku}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=3,
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


# Load state data
if "roster_df" not in st.session_state:
    reload_all_data()

sync_revtrak_orders(silent=True)

roster_df = st.session_state["roster_df"]
shifts_df = st.session_state["shifts_df"]
inventory_df = st.session_state["inventory_df"]
sales_df = st.session_state["sales_df"]


def student_lookup_by_code(query_val: str) -> pd.Series | None:
    """Matches either Student ID or linked Barcode ID."""
    clean_val = str(query_val).strip().upper()
    match = roster_df[
        (roster_df["student_id"].astype(str).str.upper() == clean_val) | 
        (roster_df["barcode_id"].astype(str).str.upper() == clean_val)
    ]
    return None if match.empty else match.iloc[0]


# ----------------------------------------------------
# AUTHENTICATION & LOGIN SCREEN
# ----------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = ""
    st.session_state["is_admin"] = False

if not st.session_state["logged_in"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    l_col1, l_col2, l_col3 = st.columns([1, 1.5, 1])
    
    with l_col2:
        st.markdown(
            """
            <div style="background: #111827; border: 2px solid #2563eb; padding: 2rem; border-radius: 1rem; text-align: center;">
                <h1 style="margin-bottom: 0;">🛡️ Trojan Market</h1>
                <p style="color: #93c5fd; margin-top: 4px;">Simsbury High School DECA Store Portal</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write("")
        with st.form(key="login_form"):
            email_input = st.text_input("Enter School Email Address:", placeholder="user@simsburyschools.net or signin.org").strip().lower()
            pass_input = st.text_input("Password (Optional for Kiosk):", type="password")
            login_btn = st.form_submit_button("🔑 Sign In to Terminal")
            
        if login_btn:
            if not email_input:
                st.error("Please enter an email address to sign in.")
            else:
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email_input
                
                if email_input in ADMIN_EMAILS:
                    st.session_state["is_admin"] = True
                    log_audit_event("ADMIN_LOGIN", f"Admin signed in: {email_input}")
                else:
                    st.session_state["is_admin"] = False
                    log_audit_event("KIOSK_LOGIN", f"Terminal kiosk signed in: {email_input}")
                    
                st.rerun()
    st.stop()


# --- HEADER & NAVIGATION CONTROL ---
h_col1, h_col2 = st.columns([3, 1])
with h_col1:
    st.title("Trojan Market")
    role_badge = "👑 Admin Portal" if st.session_state["is_admin"] else "📱 Kiosk Clock Terminal"
    st.caption(f"Simsbury High School DECA • Logged in as: **{st.session_state['user_email']}** ({role_badge})")
with h_col2:
    st.write("")
    if st.button("🚪 Sign Out"):
        log_audit_event("LOGOUT", f"User signed out: {st.session_state['user_email']}")
        st.session_state["logged_in"] = False
        st.session_state["user_email"] = ""
        st.session_state["is_admin"] = False
        st.rerun()

st.write("")

# ----------------------------------------------------
# SHARED VIEW: ID & TIME CLOCK FUNCTION
# ----------------------------------------------------
def render_time_clock_view():
    st.header("Student Keytag Scanner & Shift Clock")
    st.caption("Scan keytag barcode using the terminal USB scanner or manually enter ID.")

    col_scan, col_info = st.columns([1.2, 1])

    with col_scan:
        with st.form(key="scanner_form", clear_on_submit=True):
            scanned_barcode = st.text_input("⚡ Barcode Terminal Feed (Scan Keytag Here):", key="barcode_field")
            shift_type = st.selectbox(
                "Select Shift Type:",
                ["Prep Shift (Period 5-8)", "School Day Shift", "After School Shift", "Open House / Event"],
            )
            submit_scan = st.form_submit_button("Process Scan")

        if submit_scan and scanned_barcode:
            global shifts_df
            student = student_lookup_by_code(scanned_barcode)
            if student is None:
                st.error(f"❌ Barcode/ID '{scanned_barcode}' is not registered in the database.")
            else:
                student_name = f"{student['first_name']} {student['last_name']}"
                st.session_state["active_pass_sid"] = str(student["student_id"])
                
                active_shifts = shifts_df[(shifts_df["student_id"].astype(str) == str(student["student_id"])) & (shifts_df["status"] == "ACTIVE")]

                if active_shifts.empty:
                    # Clock IN
                    now = datetime.datetime.now()
                    new_shift = {
                        "student_id": student["student_id"],
                        "name": student_name,
                        "check_in": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "check_out": "",
                        "hours_logged": 0.0,
                        "shift_type": shift_type,
                        "status": "ACTIVE",
                        "flagged": "NO",
                    }
                    shifts_df = pd.concat([shifts_df, pd.DataFrame([new_shift])], ignore_index=True)
                    shifts_df = normalize_dataframe(shifts_df, numeric_columns=["hours_logged"])
                    save_df(SHIFTS_FILE, shifts_df)
                    st.session_state["shifts_df"] = shifts_df
                    log_audit_event("CLOCK_IN", f"{student_name} ({student['student_id']}) clocked in for {shift_type}")
                    st.success(f"✅ Clocked IN: {student_name} ({student['track']}) at {now.strftime('%H:%M:%S')}")
                    st.rerun()
                else:
                    # Clock OUT
                    idx = active_shifts.index[0]
                    checked_in = datetime.datetime.strptime(active_shifts.iloc[0]["check_in"], "%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.now()
                    raw_hours = (now - checked_in).total_seconds() / 3600.0

                    flagged = "NO"
                    if raw_hours > MAX_SHIFT_HOURS:
                        duration_hours = MAX_SHIFT_HOURS
                        flagged = "YES (Exceeded Max Hours)"
                        st.warning(f"Shift exceeded limit ({MAX_SHIFT_HOURS}h). Duration capped and flagged for review.")
                    else:
                        duration_hours = round(raw_hours, 4)

                    shifts_df.at[idx, "check_out"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    shifts_df.at[idx, "hours_logged"] = duration_hours
                    shifts_df.at[idx, "status"] = "COMPLETED"
                    shifts_df.at[idx, "flagged"] = flagged

                    shifts_df = normalize_dataframe(shifts_df, numeric_columns=["hours_logged"])
                    save_df(SHIFTS_FILE, shifts_df)
                    st.session_state["shifts_df"] = shifts_df
                    
                    logged_str = format_hours_mins(duration_hours)
                    log_audit_event("CLOCK_OUT", f"{student_name} ({student['student_id']}) clocked out. Logged {logged_str}")
                    st.success(f"🛑 Clocked OUT: {student_name}. Logged {logged_str}!")
                    st.rerun()

    with col_info:
        st.subheader("Currently Clocked In")
        active_now = shifts_df[shifts_df["status"] == "ACTIVE"] if "status" in shifts_df.columns else pd.DataFrame()
        if active_now.empty:
            st.info("No students are currently clocked in.")
        else:
            st.dataframe(
                active_now[["student_id", "name", "check_in", "shift_type"]],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("---")
    st.subheader("📱 Digital Barcode Keytag Pass & Profile View")
    if roster_df.empty:
        st.info("No students enrolled in roster.")
    else:
        student_opts = {f"{row['first_name']} {row['last_name']} (ID: {row['student_id']})": str(row['student_id']) for _, row in roster_df.iterrows()}
        student_labels = list(student_opts.keys())
        student_ids = list(student_opts.values())

        active_sid = st.session_state.get("active_pass_sid", student_ids[0])
        default_index = student_ids.index(active_sid) if active_sid in student_ids else 0

        selected_pass_label = st.selectbox("Select Student Profile:", student_labels, index=default_index)
        pass_sid = student_opts[selected_pass_label]
        pass_student = student_lookup_by_code(pass_sid)

        k_col1, k_col2 = st.columns([1, 1.5])
        with k_col1:
            render_barcode_keycard(
                student_id=str(pass_student["student_id"]),
                barcode_val=str(pass_student["barcode_id"]),
                student_name=f"{pass_student['first_name']} {pass_student['last_name']}",
                track=f"{pass_student['track']} • {pass_student['course']}",
                photo_url=str(pass_student.get("photo_url", ""))
            )
        with k_col2:
            st.markdown(f"### Profile: **{pass_student['first_name']} {pass_student['last_name']}**")
            st.write(f"• **Student ID#:** `{pass_student['student_id']}`")
            st.write(f"• **Assigned Keytag Barcode:** `{pass_student['barcode_id']}`")
            st.write(f"• **Enrolled Course:** {pass_student['course']}")
            st.write(f"• **DECA Role / Track:** {pass_student['track']}")
            st.write(f"• **Target Hours:** {pass_student['req_hours']} hrs")


# ----------------------------------------------------
# ROUTING: KIOSK MODE (NO TABS) vs ADMIN MODE (FULL TABS)
# ----------------------------------------------------
if not st.session_state["is_admin"]:
    # --- KIOSK MODE ---
    render_time_clock_view()

else:
    # --- ADMIN MODE (FULL ACCESS) ---
    with st.expander("⚙️ Store Controls & System Settings"):
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.5, 1, 1])
        with ctrl_col1:
            low_stock_limit = st.slider("Low stock warning threshold:", min_value=1, max_value=20, value=5)
        with ctrl_col2:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh Local Data"):
                reload_all_data()
                st.rerun()
        with ctrl_col3:
            st.write("")
            st.write("")
            if st.button("🌐 Force Manual RevTrak Sync"):
                sync_revtrak_orders(silent=False)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Enrolled Students", len(roster_df))
    m2.metric("Active Shifts", int((shifts_df["status"] == "ACTIVE").sum()) if "status" in shifts_df.columns else 0)
    low_stock_count = int((inventory_df["stock"] <= low_stock_limit).sum())
    m3.metric("Total Items Stocked", int(inventory_df["stock"].sum()), delta=f"{low_stock_count} low" if low_stock_count else "Stock OK", delta_color="inverse" if low_stock_count else "normal")
    m4.metric("Sales Recorded", len(sales_df))

    st.write("")

    tabs = st.tabs([
        "🛡️ ID & Time Clock",
        "💳 RevTrak POS & Inventory",
        "📈 Advisor Dashboard",
        "📊 Sheet Manager",
        "📜 System Audit Logs"
    ])

    # TAB 1: TIME CLOCK
    with tabs[0]:
        render_time_clock_view()

    # TAB 2: REVTRAK POS & LIVE INVENTORY OVERRIDE
    with tabs[1]:
        st.header("RevTrak Automated POS & Live Inventory")
        st.caption("Sales auto-sync directly from RevTrak. Use admin overrides below for manual stock adjustments.")

        st.subheader("Live Inventory Levels")
        def highlight_low_stock(val):
            try:
                val_num = float(val)
                if val_num == 0:
                    return "background-color: #7f1d1d; color: white;"
                elif val_num <= low_stock_limit:
                    return "background-color: #78350f; color: white;"
            except Exception:
                pass
            return ""

        styler = inventory_df[["item_id", "revtrak_sku", "item_name", "category", "stock", "unit_price"]].style
        if hasattr(styler, "map"):
            styled_inventory = styler.map(highlight_low_stock, subset=["stock"])
        else:
            styled_inventory = styler.applymap(highlight_low_stock, subset=["stock"])

        st.dataframe(styled_inventory, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⚙️ Admin Inventory Override & Catalog Tools")

        t_override, t_add = st.tabs(["🛠️ Manual Stock Override", "📦 Add New Product"])

        with t_override:
            if not inventory_df.empty:
                override_item_name = st.selectbox("Select Item to Override:", inventory_df["item_name"].tolist())
                r_idx = inventory_df.index[inventory_df["item_name"] == override_item_name][0]
                current_qty = int(inventory_df.at[r_idx, "stock"])
                
                new_qty = st.number_input(f"New Exact Stock Quantity for '{override_item_name}':", min_value=0, value=current_qty)
                override_reason = st.text_input("Reason for Override (Audit Logged):", placeholder="Damaged items, physical recount, promo giveaway...")

                if st.button("⚠️ Force Update Inventory Stock"):
                    inventory_df.at[r_idx, "stock"] = new_qty
                    save_df(INVENTORY_FILE, inventory_df)
                    st.session_state["inventory_df"] = inventory_df
                    
                    log_audit_event(
                        "STOCK_OVERRIDE", 
                        f"Overrode '{override_item_name}' stock from {current_qty} to {new_qty}. Reason: {override_reason if override_reason else 'None provided'}"
                    )
                    st.success(f"Stock for '{override_item_name}' overridden to {new_qty} units.")
                    st.rerun()

        with t_add:
            if "auto_name" not in st.session_state:
                st.session_state["auto_name"] = ""
            if "auto_price" not in st.session_state:
                st.session_state["auto_price"] = 2.00
            if "auto_cat" not in st.session_state:
                st.session_state["auto_cat"] = "Food"

            c1, c2, c_pull = st.columns([1, 1.5, 1])
            new_sku = c1.text_input("SKU ID:", value=f"SKU-00{len(inventory_df)+1}")
            new_rsku = c2.text_input("RevTrak SKU:", value=f"RT-ITEM-0{len(inventory_df)+1}")
            
            with c_pull:
                st.write("")
                st.write("")
                if st.button("⚡ Auto-Pull Details from RevTrak"):
                    fetched = fetch_revtrak_item_details(new_rsku)
                    if fetched:
                        st.session_state["auto_name"] = fetched.get("title", fetched.get("name", ""))
                        st.session_state["auto_price"] = float(fetched.get("price", 2.00))
                        st.session_state["auto_cat"] = fetched.get("category", "Food")
                        st.success(f"Pulled '{st.session_state['auto_name']}' from RevTrak!")
                        st.rerun()
                    else:
                        st.info("No matching RevTrak catalog item found for that SKU. Enter details manually.")

            c3, c4, c5, c6 = st.columns([1.8, 1.2, 1, 1])
            new_name = c3.text_input("Item Name:", value=st.session_state["auto_name"])
            cat_options = ["Food", "Beverage", "Apparel", "Merchandise", "Supplies"]
            cat_idx = cat_options.index(st.session_state["auto_cat"]) if st.session_state["auto_cat"] in cat_options else 0
            new_cat = c4.selectbox("Category:", cat_options, index=cat_idx)
            new_stock = c5.number_input("Initial Stock:", min_value=0, value=20)
            new_price = c6.number_input("Price ($):", min_value=0.0, value=st.session_state["auto_price"], step=0.25)

            if st.button("➕ Add Item to Catalog"):
                if new_name.strip() == "":
                    st.error("Please enter an item name.")
                else:
                    new_item = {
                        "item_id": new_sku,
                        "revtrak_sku": new_rsku,
                        "item_name": new_name,
                        "category": new_cat,
                        "stock": new_stock,
                        "unit_price": new_price,
                    }
                    inventory_df = pd.concat([inventory_df, pd.DataFrame([new_item])], ignore_index=True)
                    inventory_df = normalize_dataframe(inventory_df, numeric_columns=["stock", "unit_price"])
                    save_df(INVENTORY_FILE, inventory_df)
                    st.session_state["inventory_df"] = inventory_df
                    
                    log_audit_event("ADD_PRODUCT", f"Added new product '{new_name}' ({new_sku}) with stock {new_stock}")
                    st.success(f"Added item '{new_name}' ({new_sku})!")
                    st.rerun()

    # TAB 3: ADVISOR DASHBOARD
    with tabs[2]:
        st.header("DECA Advisor & Student Progress Dashboard")
        st.caption("Tracks required shift hours, links keytag barcodes and photos to student profiles.")

        completed_shifts = shifts_df[shifts_df["status"] == "COMPLETED"].copy() if "status" in shifts_df.columns else pd.DataFrame()
        if not completed_shifts.empty:
            completed_shifts["hours_logged"] = pd.to_numeric(completed_shifts["hours_logged"], errors="coerce").fillna(0)
            hours_by_student = completed_shifts.groupby("student_id")["hours_logged"].sum().reset_index()
            summary_df = roster_df.merge(hours_by_student, on="student_id", how="left").fillna({"hours_logged": 0.0})
            summary_df["progress_%"] = ((summary_df["hours_logged"] / summary_df["req_hours"]) * 100).round(1)
        else:
            summary_df = roster_df.copy()
            summary_df["hours_logged"] = 0.0
            summary_df["progress_%"] = 0.0

        a1, a2, a3 = st.columns(3)
        a1.metric("Enrolled Students", len(summary_df))
        total_hours_sum = summary_df['hours_logged'].sum()
        a2.metric("Total Time Completed", format_hours_mins(total_hours_sum))
        a3.metric("Average Course Completion", f"{summary_df['progress_%'].mean():.1f}%")

        st.subheader("Student Hours Progress Roster")
        for idx, row in summary_df.iterrows():
            c_name, c_course, c_hours, c_bar = st.columns([1.5, 1.2, 1.2, 1.8])
            c_name.markdown(f"**{row['first_name']} {row['last_name']}** (`ID: {row['student_id']}` | `BC: {row['barcode_id']}`)")
            c_course.caption(f"{row['course']} • {row['track']}")
            logged_text = format_hours_mins(row['hours_logged'])
            c_hours.markdown(f"**{logged_text}** / {row['req_hours']} hrs")
            pct = min(max(float(row["progress_%"]) / 100.0, 0.0), 1.0)
            c_bar.progress(pct, text=f"{row['progress_%']}%")

        st.markdown("---")
        st.subheader("⚡ Rapid Barcode Keytag Pairing Terminal")
        st.caption("Click into the barcode field below and scan the physical keytag with your USB scanner.")

        if roster_df.empty:
            st.warning("No students in roster to link.")
        else:
            r_opts = {f"{row['first_name']} {row['last_name']} (ID: {row['student_id']})": row['student_id'] for _, row in roster_df.iterrows()}
            
            with st.form(key="rapid_pair_form", clear_on_submit=False):
                selected_student_key = st.selectbox("1. Select Student Profile:", list(r_opts.keys()))
                target_sid = r_opts[selected_student_key]
                current_st = student_lookup_by_code(target_sid)
                
                scanned_pair_barcode = st.text_input(
                    "2. Click Here & Zap Physical Keytag with USB Scanner:", 
                    value=str(current_st["barcode_id"]),
                    help="Pull the trigger on your hardware scanner. It will auto-fill this input box."
                )
                save_pair_btn = st.form_submit_button("🔗 Link Barcode to Student Profile")

            if save_pair_btn:
                r_idx = roster_df.index[roster_df["student_id"].astype(str) == str(target_sid)][0]
                roster_df.at[r_idx, "barcode_id"] = scanned_pair_barcode.strip()
                save_df(ROSTER_FILE, roster_df)
                st.session_state["roster_df"] = roster_df
                
                log_audit_event("LINK_BARCODE", f"Linked barcode '{scanned_pair_barcode.strip()}' to student {current_st['first_name']} {current_st['last_name']} ({target_sid})")
                st.success(f"✅ Keytag Barcode '{scanned_pair_barcode.strip()}' successfully linked to {current_st['first_name']} {current_st['last_name']}!")
                st.rerun()

        st.markdown("---")
        with st.expander("👤 Register New Student to Roster"):
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            st_id = col_s1.text_input("Student ID#:", value=f"SIM100{len(roster_df)+1}")
            st_bc = col_s2.text_input("Scan/Type Keytag Barcode:", value=f"BC-100{len(roster_df)+1}")
            st_fn = col_s3.text_input("First Name:")
            st_ln = col_s4.text_input("Last Name:")

            col_s5, col_s6, col_s7 = st.columns(3)
            st_course = col_s5.selectbox("Enrolled Course:", ["1-Entrepreneurship", "2-Marketing", "6-Marketing", "7-SEM", "Accounting 2", "Store Management"])
            st_track = col_s6.text_input("DECA Role / Track:", value="Store Officer")
            st_req = col_s7.number_input("Required Hours:", min_value=1, max_value=100, value=10)

            if st.button("➕ Register Student to Roster"):
                if st_fn.strip() == "" or st_ln.strip() == "":
                    st.error("Please enter student first and last name.")
                else:
                    new_student = {
                        "student_id": st_id,
                        "barcode_id": st_bc,
                        "first_name": st_fn,
                        "last_name": st_ln,
                        "course": st_course,
                        "track": st_track,
                        "req_hours": st_req,
                        "photo_url": "",
                    }
                    roster_df = pd.concat([roster_df, pd.DataFrame([new_student])], ignore_index=True)
                    roster_df = normalize_dataframe(roster_df, numeric_columns=["req_hours"])
                    save_df(ROSTER_FILE, roster_df)
                    st.session_state["roster_df"] = roster_df
                    
                    log_audit_event("REGISTER_STUDENT", f"Registered new student {st_fn} {st_ln} ({st_id})")
                    st.success(f"Registered {st_fn} {st_ln} ({st_id})!")
                    st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Remove / Unenroll Student from Roster"):
            if roster_df.empty:
                st.warning("No students in roster to remove.")
            else:
                rem_opts = {f"{row['first_name']} {row['last_name']} (ID: {row['student_id']})": str(row['student_id']) for _, row in roster_df.iterrows()}
                student_to_rem_key = st.selectbox("Select Student to Remove:", list(rem_opts.keys()), key="rem_student_select")
                rem_sid = rem_opts[student_to_rem_key]
                rem_st = student_lookup_by_code(rem_sid)

                if st.button("❌ Permanently Delete Student Profile"):
                    roster_df = roster_df[roster_df["student_id"].astype(str) != str(rem_sid)]
                    save_df(ROSTER_FILE, roster_df)
                    st.session_state["roster_df"] = roster_df
                    
                    log_audit_event("DELETE_STUDENT", f"Deleted student {rem_st['first_name']} {rem_st['last_name']} ({rem_sid})")
                    st.success(f"Removed {rem_st['first_name']} {rem_st['last_name']} ({rem_sid}) from roster.")
                    st.rerun()

    # TAB 4: SHEET MANAGER
    with tabs[3]:
        st.header("Custom Database Manager")
        st.caption("Directly inspect and update store CSV data files.")

        sheet_option = st.radio(
            "Select Sheet to Edit:",
            ["Student Roster", "Shift Logs", "Master Inventory", "Sales Ledger"],
            horizontal=True,
        )

        if sheet_option == "Student Roster":
            target_df = roster_df.copy()
        elif sheet_option == "Shift Logs":
            target_df = shifts_df.copy()
        elif sheet_option == "Master Inventory":
            target_df = inventory_df.copy()
        else:
            target_df = sales_df.copy()

        edited_df = st.data_editor(target_df, num_rows="dynamic", use_container_width=True)

        if st.button("💾 Save Sheet Changes"):
            if sheet_option == "Student Roster":
                st.session_state["roster_df"] = normalize_dataframe(edited_df, numeric_columns=["req_hours"])
                save_df(ROSTER_FILE, st.session_state["roster_df"])
            elif sheet_option == "Shift Logs":
                st.session_state["shifts_df"] = normalize_dataframe(edited_df, numeric_columns=["hours_logged"])
                save_df(SHIFTS_FILE, st.session_state["shifts_df"])
            elif sheet_option == "Master Inventory":
                st.session_state["inventory_df"] = normalize_dataframe(edited_df, numeric_columns=["stock", "unit_price"])
                save_df(INVENTORY_FILE, st.session_state["inventory_df"])
            else:
                st.session_state["sales_df"] = normalize_dataframe(edited_df, numeric_columns=["quantity", "total_price"])
                save_df(SALES_FILE, st.session_state["sales_df"])

            log_audit_event("SHEET_EDITOR_SAVE", f"Manually edited and saved {sheet_option} database file.")
            st.success("Changes saved successfully to disk.")
            st.rerun()

    # TAB 5: SYSTEM AUDIT LOGS
    with tabs[4]:
        st.header("📜 System Audit & Security Logs")
        st.caption("Live timeline of all admin actions, time clock events, overrides, and user sign-ins.")

        audit_df = st.session_state.get("audit_df", load_or_create_df(AUDIT_FILE, get_default_audit()))
        if audit_df.empty:
            st.info("No audit logs recorded yet.")
        else:
            st.dataframe(
                audit_df.sort_values(by="timestamp", ascending=False),
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("🗑️ Clear Audit History"):
                empty_audit = get_default_audit()
                save_df(AUDIT_FILE, empty_audit)
                st.session_state["audit_df"] = empty_audit
                st.success("Audit logs cleared.")
                st.rerun()
