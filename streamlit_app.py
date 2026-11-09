import os
import datetime
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Trojan Market - Punch Clock Terminal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_SHIFT_HOURS = 4.0
ADMIN_USERS = ["admin.admin"]
KIOSK_USERS = ["kiosk.org", "signin.org"]

# Passwords (Defaults or fetched from .streamlit/secrets.toml)
DEFAULT_ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", st.secrets.get("postgres", {}).get("ADMIN_PASSWORD", "DECA2026!"))
DEFAULT_KIOSK_PASSWORD = st.secrets.get("KIOSK_PASSWORD", st.secrets.get("postgres", {}).get("KIOSK_PASSWORD", "LOGINDECA2026!"))

# --- DATA SANITIZER & DATE HELPERS ---
def clean_str(val, default="") -> str:
    """Converts NaN, None, floats ending in .0, or messy values into clean strings."""
    if pd.isna(val) or val is None:
        return default
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.lower() in ["nan", "none", "<na>", "null"]:
        return default
    return s

def get_current_et_naive() -> datetime.datetime:
    """Returns current US/Eastern time as naive datetime for reliable calculations."""
    try:
        return datetime.datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
    except Exception:
        return datetime.datetime.now().replace(tzinfo=None)

def parse_datetime_safe(dt_str: str) -> datetime.datetime:
    """Safely parses timestamp strings in multiple standard formats."""
    clean_ts = clean_str(dt_str)
    if not clean_ts:
        return get_current_et_naive()
    
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(clean_ts, fmt)
        except ValueError:
            continue
    return get_current_et_naive()

# --- NEON DATABASE ENGINE ---
@st.cache_resource
def get_db_engine():
    if "postgres" not in st.secrets or "url" not in st.secrets["postgres"]:
        st.error("❌ Missing Neon PostgreSQL connection string in `.streamlit/secrets.toml`!")
        st.stop()
    return create_engine(st.secrets["postgres"]["url"], pool_pre_ping=True)

engine = get_db_engine()

# --- DATABASE SCHEMAS & INITIALIZATION ---
def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS roster (
                student_id VARCHAR(50) PRIMARY KEY,
                barcode_id VARCHAR(50),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                course VARCHAR(100),
                track VARCHAR(100),
                req_hours FLOAT DEFAULT 10.0,
                photo_url TEXT,
                privacy_opt_out VARCHAR(10) DEFAULT 'NO'
            );
        """))
        # Ensure column exists if table was initialized previously
        conn.execute(text("ALTER TABLE roster ADD COLUMN IF NOT EXISTS privacy_opt_out VARCHAR(10) DEFAULT 'NO';"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shifts (
                id SERIAL PRIMARY KEY,
                student_id VARCHAR(50),
                name VARCHAR(200),
                check_in VARCHAR(50),
                check_out VARCHAR(50),
                hours_logged FLOAT DEFAULT 0.0,
                shift_type VARCHAR(100),
                status VARCHAR(20),
                flagged VARCHAR(100)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                item_id VARCHAR(50) PRIMARY KEY,
                revtrak_sku VARCHAR(100),
                item_name VARCHAR(200),
                category VARCHAR(100),
                stock INT DEFAULT 0,
                unit_price FLOAT DEFAULT 0.0
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sales (
                transaction_id VARCHAR(100) PRIMARY KEY,
                timestamp VARCHAR(50),
                item_id VARCHAR(50),
                quantity INT,
                total_price FLOAT,
                payment_method VARCHAR(50)
            );
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                timestamp VARCHAR(50),
                user_email VARCHAR(100),
                action VARCHAR(100),
                details TEXT
            );
        """))

init_db()

# --- STYLING (POOF TOP HEADER BAR & SIDEBAR) ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    section[data-testid="stSidebar"],
    button[aria-label="Toggle sidebar"],
    header,
    [data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0b1120 !important;
        color: #e5e7eb !important;
        overflow-x: hidden;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
        background: #0b1120 !important;
        max-width: 98% !important;
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
        padding: 0.4rem 0.8rem;
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
        font-size: 1.5rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-size: 0.85rem !important;
    }
    
    [data-testid="stMetricContainer"] {
        background: rgba(17, 24, 39, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    
    .stInfo, .stSuccess, .stWarning, .stError {
        background: rgba(30, 41, 59, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 0.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- TIME & SHIFT HELPERS ---
def format_hours_mins(hours_val: float) -> str:
    total_minutes = int(round(max(0.0, float(hours_val)) * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    
    if h > 0 and m > 0:
        return f"{h} hr{'s' if h > 1 else ''} {m} min{'s' if m > 1 else ''}"
    elif h > 0:
        return f"{h} hr{'s' if h > 1 else ''}"
    else:
        return f"{m} min{'s' if m != 1 else ''}"

def get_auto_shift_type() -> str:
    """Auto-detect shift type based on US Eastern Time (CT Local Time)."""
    now_et = get_current_et_naive().time()
    if now_et < datetime.time(14, 10):
        return "Prep Shift (Period 5-8)"
    else:
        return "After School Shift"

# --- DB DATA LOAD & SAVE FUNCTIONS ---
def load_table(table_name: str) -> pd.DataFrame:
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(clean_str)
        return df
    except Exception:
        return pd.DataFrame()

def save_table(table_name: str, df: pd.DataFrame):
    df.to_sql(table_name, engine, if_exists="replace", index=False)

def log_audit_event(action: str, details: str):
    user_email = st.session_state.get("user_email", "system")
    now_str = get_current_et_naive().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO audit_logs (timestamp, user_email, action, details) VALUES (:t, :u, :a, :d)"),
            {"t": now_str, "u": user_email, "a": action, "d": details}
        )
    st.session_state["audit_df"] = load_table("audit_logs")

# --- BARCODE KEYCARD RENDERER ---
def render_barcode_keycard(student_id: str, barcode_val: str, student_name: str, track: str, photo_url: str = ""):
    clean_id = clean_str(student_id)
    clean_bc = clean_str(barcode_val, default=clean_id)
    clean_name = clean_str(student_name, default="Student")
    clean_tr = clean_str(track, default="DECA Member")
    clean_photo = clean_str(photo_url)

    avatar_html = f'<img src="{clean_photo}" style="width: 48px; height: 48px; border-radius: 50%; border: 2px solid #3b82f6; margin-bottom: 4px; object-fit: cover;" />' if clean_photo else '<div style="font-size: 24px; margin-bottom: 2px;">👤</div>'
    
    html_code = f"""
    <div style="
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 10px;
        width: 280px;
        text-align: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4);
        color: #ffffff;
        margin: auto;
    ">
        <div style="font-size: 9px; text-transform: uppercase; letter-spacing: 1px; color: #93c5fd; font-weight: 700;">
            SIMSBURY HIGH SCHOOL
        </div>
        <div style="font-size: 13px; font-weight: 800; color: #f8fafc; margin-bottom: 4px;">
            🛡️ TROJAN MARKET PASS
        </div>
        
        {avatar_html}

        <div style="font-size: 13px; font-weight: 700; color: #ffffff;">
            {clean_name}
        </div>
        <div style="font-size: 10px; color: #60a5fa; margin-bottom: 6px;">
            ID: {clean_id} • {clean_tr}
        </div>
        
        <div style="background: #ffffff; padding: 4px 4px 1px 4px; border-radius: 6px; display: inline-block;">
            <svg id="barcode_{clean_id}"></svg>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
    <script>
        JsBarcode("#barcode_{clean_id}", "{clean_bc}", {{
            format: "CODE128",
            width: 1.8,
            height: 36,
            displayValue: true,
            fontSize: 10,
            marginTop: 0,
            marginBottom: 0
        }});
    </script>
    """
    components.html(html_code, height=210)

# --- AUTOMATED REVTRAK SYNC ENGINE ---
def sync_revtrak_orders(silent=False):
    if "revtrak" not in st.secrets:
        if not silent:
            st.error("RevTrak secrets not configured in `.streamlit/secrets.toml`.")
        return

    api_url = st.secrets["revtrak"].get("api_url", "")
    api_key = st.secrets["revtrak"].get("api_key", "")

    if not api_url or not api_key:
        if not silent:
            st.error("Missing RevTrak API credentials.")
        return

    try:
        res = requests.get(f"{api_url}/orders/recent", headers={"Authorization": f"Bearer {api_key}"}, timeout=3)
        if res.status_code != 200:
            if not silent:
                st.error(f"RevTrak API error ({res.status_code}): {res.text}")
            return

        orders = res.json().get("orders", [])
        sls_df = load_table("sales")
        inv_df = load_table("inventory")
        updated = False

        with engine.begin() as conn:
            for order in orders:
                order_id = clean_str(order.get("order_id"))
                if not sls_df.empty and order_id in sls_df["transaction_id"].values:
                    continue

                for item in order.get("items", []):
                    rt_sku = clean_str(item.get("sku"))
                    qty = int(item.get("quantity", 1))

                    match = inv_df[inv_df["revtrak_sku"] == rt_sku]
                    if not match.empty:
                        item_id = match.iloc[0]["item_id"]
                        price = float(item.get("price", 0.0)) * qty
                        now_str = order.get("created_at", get_current_et_naive().strftime("%Y-%m-%d %H:%M:%S"))

                        conn.execute(
                            text("INSERT INTO sales (transaction_id, timestamp, item_id, quantity, total_price, payment_method) VALUES (:t_id, :ts, :i_id, :q, :p, 'RevTrak Online')"),
                            {"t_id": order_id, "ts": now_str, "i_id": item_id, "q": qty, "p": price}
                        )
                        conn.execute(
                            text("UPDATE inventory SET stock = GREATEST(0, stock - :q) WHERE revtrak_sku = :sku"),
                            {"q": qty, "sku": rt_sku}
                        )
                        updated = True

        if updated:
            st.session_state["inventory_df"] = load_table("inventory")
            st.session_state["sales_df"] = load_table("sales")
            log_audit_event("REVTRAK_SYNC", "Imported new online orders from RevTrak to Neon DB.")
            st.toast("⚡ RevTrak Auto-Sync: New sales saved to database!")
            st.rerun()
        else:
            if not silent:
                st.info("Inventory is up to date with RevTrak.")

    except Exception as e:
        if not silent:
            st.error(f"RevTrak sync exception: {e}")

# Load Initial Data Frame States from Neon DB
if "roster_df" not in st.session_state:
    st.session_state["roster_df"] = load_table("roster")
    st.session_state["shifts_df"] = load_table("shifts")
    st.session_state["inventory_df"] = load_table("inventory")
    st.session_state["sales_df"] = load_table("sales")
    st.session_state["audit_df"] = load_table("audit_logs")

sync_revtrak_orders(silent=True)

roster_df = st.session_state["roster_df"]
shifts_df = st.session_state["shifts_df"]
inventory_df = st.session_state["inventory_df"]
sales_df = st.session_state["sales_df"]

def student_lookup_by_code(query_val: str) -> pd.Series | None:
    if roster_df.empty:
        return None
    clean_val = clean_str(query_val).upper()
    if not clean_val:
        return None
        
    match = roster_df[
        (roster_df["student_id"].apply(lambda x: clean_str(x).upper()) == clean_val) | 
        (roster_df["barcode_id"].apply(lambda x: clean_str(x).upper()) == clean_val)
    ]
    return None if match.empty else match.iloc[0]

def get_logged_hours(student_id: str, barcode_id: str = "") -> float:
    """Calculates completed shift hours strictly avoiding empty string matches."""
    clean_sid = clean_str(student_id).upper()
    clean_bc = clean_str(barcode_id).upper()
    
    conditions = []
    params = {}
    if clean_sid:
        conditions.append("LOWER(TRIM(student_id)) = LOWER(TRIM(:sid))")
        params["sid"] = clean_sid
    if clean_bc:
        conditions.append("LOWER(TRIM(student_id)) = LOWER(TRIM(:bc))")
        params["bc"] = clean_bc
        
    if not conditions:
        return 0.0
        
    where_clause = " OR ".join(conditions)
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text(f"SELECT SUM(hours_logged) FROM shifts WHERE ({where_clause}) AND LOWER(TRIM(status)) = 'completed'"),
                params
            ).scalar()
            return max(0.0, float(res)) if res is not None else 0.0
    except Exception:
        return 0.0

def get_active_shift_direct_from_db(student_id: str, barcode_id: str = "", scanned_code: str = "") -> pd.DataFrame:
    """Queries Neon DB directly for ACTIVE shifts strictly matching non-empty IDs."""
    clean_sid = clean_str(student_id).upper()
    clean_bc = clean_str(barcode_id).upper()
    clean_code = clean_str(scanned_code).upper()

    conditions = []
    params = {}
    if clean_sid:
        conditions.append("LOWER(TRIM(student_id)) = LOWER(TRIM(:sid))")
        params["sid"] = clean_sid
    if clean_bc:
        conditions.append("LOWER(TRIM(student_id)) = LOWER(TRIM(:bc))")
        params["bc"] = clean_bc
    if clean_code:
        conditions.append("LOWER(TRIM(student_id)) = LOWER(TRIM(:code))")
        params["code"] = clean_code

    if not conditions:
        return pd.DataFrame()

    where_clause = " OR ".join(conditions)
    try:
        query = text(f"SELECT * FROM shifts WHERE ({where_clause}) AND LOWER(TRIM(status)) = 'active' ORDER BY id DESC")
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params=params)
    except Exception:
        return pd.DataFrame()

# ----------------------------------------------------
# AUTHENTICATION & LOGIN SCREEN
# ----------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = ""
    st.session_state["is_admin"] = False

if not st.session_state["logged_in"]:
    st.markdown("<br>", unsafe_allow_html=True)
    l_col1, l_col2, l_col3 = st.columns([1, 1.4, 1])
    
    with l_col2:
        st.markdown(
            """
            <div style="background: #111827; border: 2px solid #2563eb; padding: 1.5rem; border-radius: 1rem; text-align: center;">
                <h2 style="margin-bottom: 0;">🛡️ Trojan Market</h2>
                <p style="color: #93c5fd; margin-top: 2px; font-size: 0.9rem;">Simsbury High School DECA Store Portal</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write("")
        with st.form(key="login_form"):
            email_input = st.text_input("Username / Email:", placeholder="admin.admin or kiosk.org").strip().lower()
            pass_input = st.text_input("Password:", type="password")
            login_btn = st.form_submit_button("🔑 Sign In")
            
        if login_btn:
            clean_user = email_input.strip().lower()
            
            if not clean_user:
                st.error("Please enter a username or email address to sign in.")
            elif clean_user in ADMIN_USERS:
                if not pass_input:
                    st.error("❌ Password is required for admin.admin sign-in.")
                    log_audit_event("FAILED_LOGIN", f"Missing password attempt for admin: {clean_user}")
                elif pass_input != DEFAULT_ADMIN_PASSWORD:
                    st.error("❌ Incorrect password for admin.admin.")
                    log_audit_event("FAILED_LOGIN", f"Invalid password attempt for admin: {clean_user}")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = clean_user
                    st.session_state["is_admin"] = True
                    log_audit_event("ADMIN_LOGIN", f"Admin signed in as: {clean_user}")
                    st.rerun()
            elif clean_user in KIOSK_USERS or clean_user.endswith("@simsburyschools.net"):
                if not pass_input:
                    st.error("❌ Password is required for Kiosk mode sign-in.")
                    log_audit_event("FAILED_LOGIN", f"Missing password attempt for kiosk: {clean_user}")
                elif pass_input != DEFAULT_KIOSK_PASSWORD:
                    st.error("❌ Incorrect password for Kiosk mode.")
                    log_audit_event("FAILED_LOGIN", f"Invalid password attempt for kiosk: {clean_user}")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = clean_user
                    st.session_state["is_admin"] = False
                    log_audit_event("KIOSK_LOGIN", f"Terminal kiosk signed in: {clean_user}")
                    st.rerun()
            else:
                st.error("❌ Access denied. Enter 'admin.admin' for admin access or 'kiosk.org' for terminal mode.")
                log_audit_event("REJECTED_LOGIN", f"Attempted sign-in with unrecognized user: {clean_user}")

    st.stop()

# --- COMPACT HEADER ---
h_col1, h_col2 = st.columns([4, 1])
with h_col1:
    role_badge = "👑 Admin Portal" if st.session_state["is_admin"] else "📱 Kiosk Clock Terminal"
    st.markdown(f"<h3 style='margin:0;'>🛡️ Trojan Market <span style='font-size: 14px; color: #93c5fd; font-weight: normal;'>({role_badge})</span></h3>", unsafe_allow_html=True)
with h_col2:
    if st.button("🚪 Sign Out"):
        log_audit_event("LOGOUT", f"User signed out: {st.session_state['user_email']}")
        st.session_state["logged_in"] = False
        st.session_state["user_email"] = ""
        st.session_state["is_admin"] = False
        st.rerun()

st.markdown("<hr style='margin: 0.2rem 0 0.8rem 0; border-color: rgba(148,163,184,0.2);'>", unsafe_allow_html=True)

# ----------------------------------------------------
# SHARED VIEW: SINGLE-PAGE PUNCH CLOCK TERMINAL
# ----------------------------------------------------
def render_time_clock_view():
    components.html(
        """
        <script>
        const autoFocusScanField = () => {
            const mainDoc = window.parent.document;
            const textInputs = mainDoc.querySelectorAll('input[type="text"]');
            for (let input of textInputs) {
                if (input.placeholder && input.placeholder.includes("Scan Barcode Here")) {
                    input.focus();
                    break;
                }
            }
        };
        setTimeout(autoFocusScanField, 100);
        setTimeout(autoFocusScanField, 300);
        </script>
        """,
        height=0,
    )

    col_punch, col_status, col_profile = st.columns([1.1, 1, 1.1])

    with col_punch:
        st.markdown("<h4 style='margin-bottom:2px;'>⏱️ Job Punch Clock</h4>", unsafe_allow_html=True)
        auto_shift = get_auto_shift_type()
        shift_options = ["Prep Shift (Period 5-8)", "After School Shift", "Open House / Event"]
        auto_index = shift_options.index(auto_shift) if auto_shift in shift_options else 0

        with st.form(key="scanner_form", clear_on_submit=True):
            shift_type = st.selectbox(
                "Shift Type (Auto-Selected by Schedule):",
                shift_options,
                index=auto_index,
                help="Automatically selects Prep Shift or After School Shift based on time."
            )
            scanned_barcode = st.text_input(
                "⚡ Scan Keytag / SHS ID Card:", 
                key="barcode_field",
                placeholder="Scan Barcode Here..."
            )
            submit_scan = st.form_submit_button("⚡ Process Punch Scan")

        if submit_scan and scanned_barcode:
            clean_code = clean_str(scanned_barcode)
            student = student_lookup_by_code(clean_code)
            if student is None:
                st.error(f"❌ Barcode / ID '{clean_code}' not found in roster.")
            else:
                student_sid = clean_str(student["student_id"])
                student_bc = clean_str(student.get("barcode_id"))
                student_name = f"{clean_str(student['first_name'])} {clean_str(student['last_name'])}".strip()
                st.session_state["active_pass_sid"] = student_sid
                
                # Force update profile dropdown state so card updates on scan
                if not roster_df.empty:
                    target_label = f"{clean_str(student['first_name'])} {clean_str(student['last_name'])} ({student_sid})"
                    st.session_state["kiosk_profile_select"] = target_label

                # Query database directly for ANY active shift matching ID, barcode, or scanned code
                active_shifts = get_active_shift_direct_from_db(student_sid, student_bc, clean_code)

                if active_shifts.empty:
                    # PUNCH IN
                    now_dt = get_current_et_naive()
                    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO shifts (student_id, name, check_in, check_out, hours_logged, shift_type, status, flagged) VALUES (:s_id, :n, :ci, '', 0.0, :st, 'ACTIVE', 'NO')"),
                            {"s_id": student_sid, "n": student_name, "ci": now_str, "st": shift_type}
                        )
                    st.session_state["shifts_df"] = load_table("shifts")
                    log_audit_event("CLOCK_IN", f"{student_name} ({student_sid}) clocked in for {shift_type}")
                    st.success(f"✅ PUNCH IN: {student_name} at {now_dt.strftime('%H:%M:%S')}")
                    st.rerun()
                else:
                    # PUNCH OUT
                    primary_shift = active_shifts.iloc[0]
                    primary_shift_id = int(primary_shift["id"])
                    checked_in_dt = parse_datetime_safe(clean_str(primary_shift["check_in"]))
                    now_dt = get_current_et_naive()
                    
                    raw_hours = max(0.0, (now_dt - checked_in_dt).total_seconds() / 3600.0)

                    flagged = "NO"
                    if raw_hours > MAX_SHIFT_HOURS:
                        duration_hours = MAX_SHIFT_HOURS
                        flagged = "YES (Exceeded Max Hours)"
                        st.warning(f"Shift exceeded limit ({MAX_SHIFT_HOURS}h). Duration capped.")
                    else:
                        duration_hours = round(raw_hours, 4)

                    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                    with engine.begin() as conn:
                        # Complete primary active shift
                        conn.execute(
                            text("UPDATE shifts SET check_out = :co, hours_logged = :hl, status = 'COMPLETED', flagged = :fl WHERE id = :sid"),
                            {"co": now_str, "hl": duration_hours, "fl": flagged, "sid": primary_shift_id}
                        )
                        # Automatically close out any lingering duplicate active shifts for this student
                        conn.execute(
                            text("""
                                UPDATE shifts 
                                SET check_out = :co, hours_logged = 0.0, status = 'COMPLETED', flagged = 'CLEANUP' 
                                WHERE (
                                    (LOWER(TRIM(student_id)) = LOWER(TRIM(:sid)) AND :sid != '')
                                    OR (LOWER(TRIM(student_id)) = LOWER(TRIM(:bc)) AND :bc != '')
                                    OR (LOWER(TRIM(student_id)) = LOWER(TRIM(:code)) AND :code != '')
                                ) 
                                AND LOWER(TRIM(status)) = 'active'
                            """),
                            {"co": now_str, "sid": student_sid, "bc": student_bc, "code": clean_code}
                        )

                    st.session_state["shifts_df"] = load_table("shifts")
                    logged_str = format_hours_mins(duration_hours)
                    log_audit_event("CLOCK_OUT", f"{student_name} ({student_sid}) clocked out. Logged {logged_str}")
                    st.success(f"🛑 PUNCH OUT: {student_name}. Logged {logged_str}!")
                    st.rerun()

    with col_status:
        st.markdown("<h4 style='margin-bottom:2px;'>📋 Currently On Shift</h4>", unsafe_allow_html=True)
        active_now = load_table("shifts")
        if not active_now.empty and "status" in active_now.columns:
            active_now = active_now[active_now["status"].apply(lambda x: clean_str(x).upper()) == "ACTIVE"]
        
        if active_now.empty:
            st.info("No students currently clocked in.")
        else:
            st.dataframe(
                active_now[["student_id", "name", "check_in", "shift_type"]],
                use_container_width=True,
                hide_index=True,
                height=180
            )

    with col_profile:
        st.markdown("<h4 style='margin-bottom:2px;'>⏳ Student Hours Tally</h4>", unsafe_allow_html=True)
        if roster_df.empty:
            st.info("No students in database roster.")
        else:
            student_opts = {f"{clean_str(row['first_name'])} {clean_str(row['last_name'])} ({clean_str(row['student_id'])})": clean_str(row['student_id']) for _, row in roster_df.iterrows()}
            student_labels = list(student_opts.keys())
            student_ids = list(student_opts.values())

            active_sid = st.session_state.get("active_pass_sid", student_ids[0] if student_ids else "")
            
            if "kiosk_profile_select" not in st.session_state or st.session_state["kiosk_profile_select"] not in student_labels:
                matched_labels = [lbl for lbl, sid in student_opts.items() if sid == active_sid]
                st.session_state["kiosk_profile_select"] = matched_labels[0] if matched_labels else student_labels[0]

            selected_pass_label = st.selectbox("Active Profile View:", student_labels, key="kiosk_profile_select", label_visibility="collapsed")
            pass_sid = student_opts[selected_pass_label]
            pass_student = student_lookup_by_code(pass_sid)

            if pass_student is not None:
                req_h = float(pass_student["req_hours"]) if "req_hours" in pass_student and pd.notna(pass_student["req_hours"]) else 10.0
                req_h = max(0.1, req_h)
                logged_h = get_logged_hours(clean_str(pass_student["student_id"]), clean_str(pass_student.get("barcode_id")))
                rem_h = max(0.0, req_h - logged_h)

                render_barcode_keycard(
                    student_id=clean_str(pass_student["student_id"]),
                    barcode_val=clean_str(pass_student.get("barcode_id"), default=clean_str(pass_student["student_id"])),
                    student_name=f"{clean_str(pass_student['first_name'])} {clean_str(pass_student['last_name'])}",
                    track=clean_str(pass_student.get('track')),
                    photo_url=clean_str(pass_student.get("photo_url"))
                )

                # Privacy Opt-In / Opt-Out Tally Display
                is_private = (clean_str(pass_student.get("privacy_opt_out", "NO")).upper() == "YES")
                if is_private:
                    p1, p2 = st.columns(2)
                    p1.metric("Completed", "🔒 Private Mode")
                    p2.metric("Remaining", "🔒 Private Mode")
                else:
                    p1, p2 = st.columns(2)
                    p1.metric("Completed", format_hours_mins(logged_h))
                    p2.metric("Remaining", "Done! 🎉" if rem_h == 0 else format_hours_mins(rem_h))

                # Privacy Toggle Button
                toggle_btn_text = "👁️ Show Hours Publicly" if is_private else "🔒 Hide My Hours (Private Mode)"
                if st.button(toggle_btn_text, key=f"priv_btn_{clean_str(pass_student['student_id'])}"):
                    new_val = "NO" if is_private else "YES"
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE roster SET privacy_opt_out = :p WHERE LOWER(TRIM(student_id)) = LOWER(TRIM(:sid))"),
                            {"p": new_val, "sid": clean_str(pass_student['student_id'])}
                        )
                    st.session_state["roster_df"] = load_table("roster")
                    st.toast("Privacy setting saved!")
                    st.rerun()
            else:
                st.info("Select a student to view details.")

# ----------------------------------------------------
# ROUTING: KIOSK MODE (NO TABS) vs ADMIN MODE (FULL TABS)
# ----------------------------------------------------
if not st.session_state["is_admin"]:
    render_time_clock_view()

else:
    with st.expander("⚙️ Store Controls & Reset Tools"):
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.5, 1, 1])
        with ctrl_col1:
            low_stock_limit = st.slider("Low stock warning threshold:", min_value=1, max_value=20, value=5)
        with ctrl_col2:
            st.write("")
            st.write("")
            if st.button("🔄 Reload DB Data"):
                st.session_state["roster_df"] = load_table("roster")
                st.session_state["shifts_df"] = load_table("shifts")
                st.session_state["inventory_df"] = load_table("inventory")
                st.session_state["sales_df"] = load_table("sales")
                st.session_state["audit_df"] = load_table("audit_logs")
                st.rerun()
        with ctrl_col3:
            st.write("")
            st.write("")
            with st.popover("⚠️ Reset Active Shifts / Fix Clocks"):
                st.write("Force-close all stuck active shifts without logging hours.")
                if st.button("Confirm Reset Active Shifts"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE shifts SET status = 'CANCELLED', check_out = :co WHERE LOWER(TRIM(status)) = 'active'"),
                            {"co": get_current_et_naive().strftime("%Y-%m-%d %H:%M:%S")}
                        )
                    st.session_state["shifts_df"] = load_table("shifts")
                    log_audit_event("RESET_ACTIVE_SHIFTS", "Admin reset all stuck active shifts.")
                    st.toast("🧹 Active shifts reset!")
                    st.rerun()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Enrolled Students", len(roster_df))
    m2.metric("Active Shifts", int((shifts_df["status"].apply(lambda x: clean_str(x).upper()) == "ACTIVE").sum()) if not shifts_df.empty and "status" in shifts_df.columns else 0)
    low_stock_count = int((pd.to_numeric(inventory_df["stock"], errors="coerce").fillna(0) <= low_stock_limit).sum()) if not inventory_df.empty else 0
    m3.metric("Total Items Stocked", int(pd.to_numeric(inventory_df["stock"], errors="coerce").fillna(0).sum()) if not inventory_df.empty else 0, delta=f"{low_stock_count} low" if low_stock_count else "Stock OK", delta_color="inverse" if low_stock_count else "normal")
    m4.metric("Sales Recorded", len(sales_df))

    st.write("")

    tabs = st.tabs([
        "🛡️ ID & Time Clock",
        "💳 RevTrak POS & Inventory",
        "📈 Advisor Dashboard",
        "📊 Database Manager",
        "📜 System Audit Logs"
    ])

    # TAB 1: TIME CLOCK
    with tabs[0]:
        render_time_clock_view()

    # TAB 2: REVTRAK POS & LIVE INVENTORY OVERRIDE
    with tabs[1]:
        st.header("RevTrak Automated POS & Live Inventory")
        st.caption("Sales auto-sync directly from RevTrak. Use admin overrides below for manual stock adjustments.")

        if inventory_df.empty:
            st.info("No catalog items in database.")
        else:
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
                current_qty = int(pd.to_numeric(inventory_df.at[r_idx, "stock"], errors="coerce") or 0)
                
                new_qty = st.number_input(f"New Exact Stock Quantity for '{override_item_name}':", min_value=0, value=current_qty)
                override_reason = st.text_input("Reason for Override (Audit Logged):", placeholder="Damaged items, physical recount, promo giveaway...")

                if st.button("⚠️ Force Update Inventory Stock"):
                    item_id_val = clean_str(inventory_df.at[r_idx, "item_id"])
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE inventory SET stock = :st WHERE item_id = :iid"),
                            {"st": new_qty, "iid": item_id_val}
                        )
                    st.session_state["inventory_df"] = load_table("inventory")
                    log_audit_event("STOCK_OVERRIDE", f"Overrode '{override_item_name}' stock from {current_qty} to {new_qty}. Reason: {override_reason if override_reason else 'None provided'}")
                    st.success(f"Stock for '{override_item_name}' overridden to {new_qty} units in Neon DB.")
                    st.rerun()

        with t_add:
            c1, c2 = st.columns(2)
            new_sku = c1.text_input("SKU ID:", value=f"SKU-00{len(inventory_df)+1}")
            new_rsku = c2.text_input("RevTrak SKU:", value=f"RT-ITEM-0{len(inventory_df)+1}")
            
            c3, c4, c5, c6 = st.columns([1.8, 1.2, 1, 1])
            new_name = c3.text_input("Item Name:")
            new_cat = c4.selectbox("Category:", ["Food", "Beverage", "Apparel", "Merchandise", "Supplies"])
            new_stock = c5.number_input("Initial Stock:", min_value=0, value=20)
            new_price = c6.number_input("Price ($):", min_value=0.0, value=2.00, step=0.25)

            if st.button("➕ Add Item to Catalog"):
                if new_name.strip() == "":
                    st.error("Please enter an item name.")
                else:
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO inventory (item_id, revtrak_sku, item_name, category, stock, unit_price) VALUES (:iid, :rsku, :name, :cat, :st, :pr)"),
                            {"iid": clean_str(new_sku), "rsku": clean_str(new_rsku), "name": clean_str(new_name), "cat": clean_str(new_cat), "st": new_stock, "pr": new_price}
                        )
                    st.session_state["inventory_df"] = load_table("inventory")
                    log_audit_event("ADD_PRODUCT", f"Added product '{new_name}' ({new_sku}) to Neon DB.")
                    st.success(f"Added item '{new_name}' ({new_sku})!")
                    st.rerun()

    # TAB 3: ADVISOR DASHBOARD
    with tabs[2]:
        st.header("DECA Advisor & Student Progress Dashboard")
        st.caption("Tracks required shift hours, countdown tallies, links SHS ID / keytag barcodes to student profiles.")

        if roster_df.empty:
            st.info("No enrolled students in the database.")
        else:
            summary_df = roster_df.copy()
            summary_df["req_hours"] = pd.to_numeric(summary_df["req_hours"], errors="coerce").fillna(10.0).apply(lambda x: max(0.1, float(x)))
            summary_df["hours_logged"] = summary_df.apply(lambda r: get_logged_hours(clean_str(r["student_id"]), clean_str(r.get("barcode_id"))), axis=1)
            
            summary_df["progress_%"] = summary_df.apply(
                lambda r: round(min(100.0, max(0.0, (r["hours_logged"] / r["req_hours"]) * 100)), 1),
                axis=1
            )

            a1, a2, a3 = st.columns(3)
            a1.metric("Enrolled Students", len(summary_df))
            total_hours_sum = summary_df['hours_logged'].sum()
            a2.metric("Total Time Completed", format_hours_mins(total_hours_sum))
            a3.metric("Average Course Completion", f"{summary_df['progress_%'].mean():.1f}%")

            st.subheader("Student Hours Progress & Countdown Tally Roster")
            for idx, row in summary_df.iterrows():
                req_h = float(row['req_hours'])
                log_h = float(row['hours_logged'])
                rem_h = max(0.0, req_h - log_h)
                is_priv = (clean_str(row.get("privacy_opt_out", "NO")).upper() == "YES")
                
                c_name, c_course, c_hours, c_bar = st.columns([1.5, 1.2, 1.4, 1.6])
                priv_tag = " 🔒" if is_priv else ""
                c_name.markdown(f"**{clean_str(row['first_name'])} {clean_str(row['last_name'])}**{priv_tag} (`ID: {clean_str(row['student_id'])}` | `BC: {clean_str(row['barcode_id'], default=clean_str(row['student_id']))}`) ")
                c_course.caption(f"{clean_str(row['course'])} • {clean_str(row['track'])}")
                
                rem_text = "Completed! 🎉" if rem_h == 0 else f"Rem: {format_hours_mins(rem_h)}"
                c_hours.markdown(f"**{format_hours_mins(log_h)}** / {req_h} hrs  \n<span style='font-size: 12px; color: #93c5fd;'>{rem_text}</span>", unsafe_allow_html=True)
                
                pct = min(max(float(row["progress_%"]) / 100.0, 0.0), 1.0)
                c_bar.progress(pct, text=f"{row['progress_%']}%")

        st.markdown("---")
        st.subheader("⚡ Rapid Barcode Keytag / SHS ID Pairing Terminal")
        if roster_df.empty:
            st.warning("No students in roster to link.")
        else:
            r_opts = {f"{clean_str(row['first_name'])} {clean_str(row['last_name'])} (ID: {clean_str(row['student_id'])})": clean_str(row['student_id']) for _, row in roster_df.iterrows()}
            
            with st.form(key="rapid_pair_form", clear_on_submit=False):
                selected_student_key = st.selectbox("1. Select Student Profile:", list(r_opts.keys()))
                target_sid = r_opts[selected_student_key]
                current_st = student_lookup_by_code(target_sid)
                
                current_barcode = clean_str(current_st["barcode_id"]) if current_st is not None else clean_str(target_sid)
                scanned_pair_barcode = st.text_input(
                    "2. Click Here & Zap Physical Keytag or SHS Student ID with USB Scanner:", 
                    value=current_barcode,
                    help="Pull the trigger on your hardware scanner. It will auto-fill this input box."
                )
                save_pair_btn = st.form_submit_button("🔗 Link Barcode / SHS ID to Profile")

            if save_pair_btn:
                clean_bc_input = clean_str(scanned_pair_barcode)
                clean_target_sid = clean_str(target_sid)
                with engine.begin() as conn:
                    conn.execute(
                        text("UPDATE roster SET barcode_id = :bc WHERE LOWER(TRIM(student_id)) = LOWER(TRIM(:sid))"),
                        {"bc": clean_bc_input, "sid": clean_target_sid}
                    )
                st.session_state["roster_df"] = load_table("roster")
                st.session_state["active_pass_sid"] = clean_target_sid
                log_audit_event("LINK_BARCODE", f"Linked barcode '{clean_bc_input}' to student ID {clean_target_sid}")
                st.success(f"✅ Barcode / SHS ID '{clean_bc_input}' linked to profile {clean_target_sid} in Neon DB!")
                st.rerun()

        st.markdown("---")
        with st.expander("👤 Register New Student to Database Roster"):
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            st_id = col_s1.text_input("SHS Student ID#:", value=f"SIM100{len(roster_df)+1}")
            st_bc = col_s2.text_input("Scan/Type Keytag Barcode (Default: SHS ID):", value=f"SIM100{len(roster_df)+1}")
            st_fn = col_s3.text_input("First Name:")
            st_ln = col_s4.text_input("Last Name:")

            col_s5, col_s6, col_s7 = st.columns(3)
            st_course = col_s5.selectbox("Enrolled Course:", ["1-Entrepreneurship", "2-Marketing", "6-Marketing", "7-SEM", "Accounting 2", "Store Management"])
            st_track = col_s6.text_input("DECA Role / Track:", value="Store Officer")
            st_req = col_s7.number_input("Required Hours:", min_value=1, max_value=100, value=10)

            if st.button("➕ Register Student to Database"):
                if st_fn.strip() == "" or st_ln.strip() == "":
                    st.error("Please enter student first and last name.")
                else:
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO roster (student_id, barcode_id, first_name, last_name, course, track, req_hours, photo_url, privacy_opt_out) VALUES (:sid, :bc, :fn, :ln, :crs, :trk, :req, '', 'NO')"),
                            {"sid": clean_str(st_id), "bc": clean_str(st_bc), "fn": clean_str(st_fn), "ln": clean_str(st_ln), "crs": clean_str(st_course), "trk": clean_str(st_track), "req": float(st_req)}
                        )
                    st.session_state["roster_df"] = load_table("roster")
                    log_audit_event("REGISTER_STUDENT", f"Registered student {st_fn} {st_ln} ({st_id}) into Neon DB.")
                    st.success(f"Registered {st_fn} {st_ln} ({st_id})!")
                    st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Remove Student from Database Roster"):
            if roster_df.empty:
                st.warning("No students in database to remove.")
            else:
                rem_opts = {f"{clean_str(row['first_name'])} {clean_str(row['last_name'])} (ID: {clean_str(row['student_id'])})": clean_str(row['student_id']) for _, row in roster_df.iterrows()}
                student_to_rem_key = st.selectbox("Select Student to Remove:", list(rem_opts.keys()), key="rem_student_select")
                rem_sid = rem_opts[student_to_rem_key]

                if st.button("❌ Permanently Delete Student Profile"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM roster WHERE LOWER(TRIM(student_id)) = LOWER(TRIM(:sid))"), {"sid": clean_str(rem_sid)})
                    st.session_state["roster_df"] = load_table("roster")
                    log_audit_event("DELETE_STUDENT", f"Deleted student ({rem_sid}) from Neon DB.")
                    st.success(f"Removed student profile ({rem_sid}) from Neon DB.")
                    st.rerun()

    # TAB 4: DATABASE MANAGER & HARD RESET
    with tabs[3]:
        st.header("Neon Cloud Database Manager")
        st.caption("Directly inspect and update Neon PostgreSQL database tables.")

        sheet_option = st.radio(
            "Select Table to Edit:",
            ["roster", "shifts", "inventory", "sales"],
            horizontal=True,
        )

        target_df = load_table(sheet_option)
        edited_df = st.data_editor(target_df, num_rows="dynamic", use_container_width=True)

        if st.button("💾 Save Database Changes"):
            save_table(sheet_option, edited_df)
            st.session_state[f"{sheet_option}_df"] = load_table(sheet_option)
            log_audit_event("DB_EDITOR_SAVE", f"Manually updated Neon DB table '{sheet_option}'.")
            st.success(f"Table '{sheet_option}' successfully updated in Neon PostgreSQL!")
            st.rerun()

        st.markdown("---")
        with st.expander("🚨 Nuclear Option: Hard Reset Complete Database", expanded=False):
            st.error("⚠️ WARNING: This will permanently erase ALL students, shifts, inventory, sales, and audit logs!")
            wipe_confirm_text = st.text_input(
                "To confirm complete database wipe, type 'WIPE-ALL-DATA-PERMANENTLY' below:",
                key="wipe_confirm_input"
            )
            if wipe_confirm_text.strip() == "WIPE-ALL-DATA-PERMANENTLY":
                if st.button("🔥 PERMANENTLY ERASE ALL DATABASE DATA", type="primary"):
                    with engine.begin() as conn:
                        conn.execute(text("DROP TABLE IF EXISTS roster, shifts, inventory, sales, audit_logs CASCADE;"))
                    init_db()
                    st.session_state.clear()
                    st.success("💥 Database wiped clean! Initialized fresh tables.")
                    st.rerun()
            else:
                st.info("Type the exact confirmation phrase above to unlock the hard reset button.")

    # TAB 5: SYSTEM AUDIT LOGS
    with tabs[4]:
        st.header("📜 System Audit & Security Logs")
        st.caption("Live timeline of all admin actions, time clock events, overrides, and user sign-ins stored in Neon DB.")

        audit_df = load_table("audit_logs")
        if audit_df.empty:
            st.info("No audit logs recorded yet.")
        else:
            st.dataframe(
                audit_df.sort_values(by="id", ascending=False),
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("🗑️ Clear Audit History"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM audit_logs"))
                st.session_state["audit_df"] = load_table("audit_logs")
                st.success("Audit history cleared from database.")
                st.rerun()
