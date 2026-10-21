import os
import datetime
import requests
import pandas as pd
import streamlit as st

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

MAX_SHIFT_HOURS = 4.0

# --- STYLING (FORCE-HIDE SIDEBAR ON DESKTOP & MOBILE) ---
st.markdown(
    """
    <style>
    /* Completely hide sidebar drawer, nav, and collapse controls */
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
            df[col] = default_df[col].iloc[0] if len(default_df) > 0 and col in default_df else "NO"

    return df


def save_df(file_path: str, df: pd.DataFrame) -> None:
    df.to_csv(file_path, index=False)


# Default Datasets
def get_default_roster() -> pd.DataFrame:
    return pd.DataFrame([
        {"student_id": "SIM1001", "first_name": "Caroline", "last_name": "Fair", "course": "1-Entrepreneurship", "track": "DECA President", "req_hours": 20},
        {"student_id": "SIM1002", "first_name": "Elizabeth", "last_name": "Cadoff", "course": "6-Marketing", "track": "VP-School Store", "req_hours": 20},
        {"student_id": "SIM1003", "first_name": "Radha", "last_name": "Bansal", "course": "1-Entrepreneurship", "track": "VP-Marketing", "req_hours": 20},
        {"student_id": "SIM1004", "first_name": "Liam", "last_name": "Ricciardelli", "course": "2-Marketing", "track": "Officer", "req_hours": 10},
        {"student_id": "SIM1005", "first_name": "Julian", "last_name": "Mass", "course": "2-Marketing", "track": "Honors: Store", "req_hours": 10},
        {"student_id": "SIM1006", "first_name": "Henry", "last_name": "Pfeiffer", "course": "6-Marketing", "track": "ICDC", "req_hours": 10},
        {"student_id": "SIM1007", "first_name": "Caleb", "last_name": "Deems", "course": "7-SEM", "track": "Honors: Store", "req_hours": 10},
        {"student_id": "SIM1008", "first_name": "Olivia", "last_name": "Campasano", "course": "Accounting 2", "track": "Store", "req_hours": 10},
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


def reload_all_data():
    st.session_state["roster_df"] = normalize_dataframe(
        load_or_create_df(ROSTER_FILE, get_default_roster()), numeric_columns=["req_hours"]
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


# --- AUTOMATED REVTRAK SYNC ENGINE ---
def sync_revtrak_orders(silent=False):
    """Fetches recent online orders from RevTrak API and deducts stock automatically."""
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
            st.toast("⚡ RevTrak Auto-Sync: New online sales imported & inventory updated!")
            st.rerun()
        else:
            if not silent:
                st.info("Inventory is already up to date with RevTrak.")

    except Exception as e:
        if not silent:
            st.error(f"RevTrak sync error: {e}")


# Initialize session state data
if "roster_df" not in st.session_state:
    reload_all_data()

# AUTOMATED SILENT SYNC ON PAGE LOAD
sync_revtrak_orders(silent=True)

roster_df = st.session_state["roster_df"]
shifts_df = st.session_state["shifts_df"]
inventory_df = st.session_state["inventory_df"]
sales_df = st.session_state["sales_df"]


def student_lookup(student_id: str) -> pd.Series | None:
    match = roster_df[roster_df["student_id"].str.upper() == student_id.strip().upper()]
    return None if match.empty else match.iloc[0]


# --- HEADER & TOP CONTROLS (MOVED OUT OF SIDEBAR) ---
st.title("Trojan Market")
st.caption("Simsbury High School DECA • Operations & Hours Dashboard")

# System Controls Expander
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

# Metric Bar
m1, m2, m3, m4 = st.columns(4)
m1.metric("Enrolled Students", len(roster_df))
m2.metric("Active Shifts", int((shifts_df["status"] == "ACTIVE").sum()) if "status" in shifts_df.columns else 0)
low_stock_count = int((inventory_df["stock"] <= low_stock_limit).sum())
m3.metric("Total Items Stocked", int(inventory_df["stock"].sum()), delta=f"{low_stock_count} low" if low_stock_count else "Stock OK", delta_color="inverse" if low_stock_count else "normal")
m4.metric("Sales Recorded", len(sales_df))

st.write("")

# --- MAIN WORKFLOW TABS ---
tabs = st.tabs([
    "🛡️ ID & Time Clock",
    "💸 POS & Inventory",
    "📈 Advisor Dashboard",
    "📊 Sheet Manager",
])

# ----------------------------------------------------
# TAB 1: ID & TIME CLOCK
# ----------------------------------------------------
with tabs[0]:
    st.header("Student ID Scanner & Shift Clock")
    st.caption("Scan student ID card barcode or manually type student ID.")

    col_scan, col_info = st.columns([1, 1])

    with col_scan:
        with st.form(key="scanner_form", clear_on_submit=True):
            scanned_barcode = st.text_input("Barcode Input Feed (Scan Card Here):", key="barcode_field")
            shift_type = st.selectbox(
                "Select Shift Type:",
                ["Prep Shift (Period 5-8)", "School Day Shift", "After School Shift", "Open House / Event"],
            )
            submit_scan = st.form_submit_button("Process Card Scan")

        if submit_scan and scanned_barcode:
            student = student_lookup(scanned_barcode)
            if student is None:
                st.error(f"Student ID '{scanned_barcode}' not found in roster database.")
            else:
                student_name = f"{student['first_name']} {student['last_name']}"
                active_shifts = shifts_df[(shifts_df["student_id"] == student["student_id"]) & (shifts_df["status"] == "ACTIVE")]

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
                        duration_hours = max(round(raw_hours, 2), 0.25)

                    shifts_df.at[idx, "check_out"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    shifts_df.at[idx, "hours_logged"] = duration_hours
                    shifts_df.at[idx, "status"] = "COMPLETED"
                    shifts_df.at[idx, "flagged"] = flagged

                    shifts_df = normalize_dataframe(shifts_df, numeric_columns=["hours_logged"])
                    save_df(SHIFTS_FILE, shifts_df)
                    st.session_state["shifts_df"] = shifts_df
                    st.success(f"🛑 Clocked OUT: {student_name}. Logged {duration_hours:.2f} hours.")
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
    with st.expander("🛠️ Advisor Tool: Add / Override Manual Shift Entry"):
        if roster_df.empty:
            st.warning("Please add students to roster first.")
        else:
            student_list = [f"{row['student_id']} - {row['first_name']} {row['last_name']}" for _, row in roster_df.iterrows()]
            selected_student_str = st.selectbox("Select Student for Manual Shift Entry:", student_list)
            target_sid = selected_student_str.split(" - ")[0]
            target_student = student_lookup(target_sid)
            
            col_m1, col_m2, col_m3 = st.columns(3)
            manual_hours = col_m1.number_input("Hours to Log:", min_value=0.25, max_value=12.0, value=1.0, step=0.25)
            manual_shift_type = col_m2.selectbox("Shift Category:", ["Prep Shift (Period 5-8)", "School Day Shift", "After School Shift", "Open House / Event"], key="manual_shift_cat")
            manual_date = col_m3.date_input("Shift Date:", value=datetime.date.today())

            if st.button("➕ Log Manual Shift Hours"):
                st_name = f"{target_student['first_name']} {target_student['last_name']}"
                dt_stamp = manual_date.strftime("%Y-%m-%d 12:00:00")
                manual_record = {
                    "student_id": target_sid,
                    "name": st_name,
                    "check_in": dt_stamp,
                    "check_out": dt_stamp,
                    "hours_logged": manual_hours,
                    "shift_type": manual_shift_type,
                    "status": "COMPLETED",
                    "flagged": "NO (Manual Override)",
                }
                shifts_df = pd.concat([shifts_df, pd.DataFrame([manual_record])], ignore_index=True)
                shifts_df = normalize_dataframe(shifts_df, numeric_columns=["hours_logged"])
                save_df(SHIFTS_FILE, shifts_df)
                st.session_state["shifts_df"] = shifts_df
                st.success(f"Added {manual_hours} hrs manually for {st_name}!")
                st.rerun()

# ----------------------------------------------------
# TAB 2: POS & INVENTORY
# ----------------------------------------------------
with tabs[1]:
    st.header("Point of Sale & Live Inventory")
    st.caption("Record purchases and automatically adjust store inventory levels.")

    pos_col, inv_col = st.columns([1, 1.2])

    with pos_col:
        st.subheader("Checkout Register")
        
        if inventory_df.empty:
            st.warning("No inventory items found.")
        else:
            inventory_options = {
                f"{row['item_name']} (${float(row['unit_price']):.2f}) - Stock: {int(row['stock'])}": row['item_id']
                for _, row in inventory_df.iterrows()
            }
            
            selected_label = st.selectbox("Select Purchased Item:", list(inventory_options.keys()))
            selected_item_id = inventory_options[selected_label]
            item_row = inventory_df[inventory_df["item_id"] == selected_item_id].iloc[0]

            available_stock = int(item_row["stock"])
            
            if available_stock == 0:
                st.error("⚠️ Item is OUT OF STOCK.")
                quantity_sold = 0
            else:
                quantity_sold = st.number_input(
                    "Quantity Sold:",
                    min_value=1,
                    max_value=max(available_stock, 1),
                    value=1
                )

            payment_method = st.selectbox("Payment Method:", ["Cash Box", "Tap-to-Pay (RevTrak)", "School Account"])
            total_cost = quantity_sold * float(item_row["unit_price"])
            
            st.markdown(f"### Total Price: **${total_cost:.2f}**")

            if st.button("🛒 Complete Sale", disabled=(available_stock == 0)):
                idx = inventory_df.index[inventory_df["item_id"] == selected_item_id][0]
                inventory_df.at[idx, "stock"] = available_stock - quantity_sold
                save_df(INVENTORY_FILE, inventory_df)
                st.session_state["inventory_df"] = inventory_df

                new_sale = {
                    "transaction_id": f"SALE-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "item_id": item_row["item_id"],
                    "quantity": quantity_sold,
                    "total_price": total_cost,
                    "payment_method": payment_method,
                }
                sales_df = pd.concat([sales_df, pd.DataFrame([new_sale])], ignore_index=True)
                sales_df = normalize_dataframe(sales_df, numeric_columns=["quantity", "total_price"])
                save_df(SALES_FILE, sales_df)
                st.session_state["sales_df"] = sales_df

                st.success(f"Transaction recorded! Deducted {quantity_sold} x '{item_row['item_name']}'.")
                st.rerun()

    with inv_col:
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
    st.subheader("Inventory Editing Tools")
    
    t_add, t_restock = st.tabs(["📦 Add New Product", "🔄 Restock Existing Item"])
    
    with t_add:
        c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1.8, 1.2, 1, 1])
        new_sku = c1.text_input("SKU ID:", value=f"SKU-00{len(inventory_df)+1}")
        new_rsku = c2.text_input("RevTrak SKU:", value=f"RT-ITEM-0{len(inventory_df)+1}")
        new_name = c3.text_input("Item Name:")
        new_cat = c4.selectbox("Category:", ["Food", "Beverage", "Apparel", "Merchandise", "Supplies"])
        new_stock = c5.number_input("Initial Stock:", min_value=0, value=20)
        new_price = c6.number_input("Price ($):", min_value=0.0, value=2.00, step=0.25)

        if st.button("➕ Add Item to Store Catalog"):
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
                st.success(f"Added item '{new_name}' ({new_sku})!")
                st.rerun()

    with t_restock:
        if not inventory_df.empty:
            item_to_restock = st.selectbox("Select Item to Restock:", inventory_df["item_name"].tolist())
            restock_amt = st.number_input("Quantity Added to Stock:", min_value=1, value=10)
            
            if st.button("📈 Confirm Stock Addition"):
                r_idx = inventory_df.index[inventory_df["item_name"] == item_to_restock][0]
                inventory_df.at[r_idx, "stock"] = int(inventory_df.at[r_idx, "stock"]) + restock_amt
                save_df(INVENTORY_FILE, inventory_df)
                st.session_state["inventory_df"] = inventory_df
                st.success(f"Added +{restock_amt} units to {item_to_restock}!")
                st.rerun()

# ----------------------------------------------------
# TAB 3: ADVISOR DASHBOARD
# ----------------------------------------------------
with tabs[2]:
    st.header("DECA Advisor & Student Progress Dashboard")
    st.caption("Tracks required shift hours and monitors student progress.")

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
    a2.metric("Total Hours Completed", f"{summary_df['hours_logged'].sum():.1f} hrs")
    a3.metric("Average Course Completion", f"{summary_df['progress_%'].mean():.1f}%")

    st.subheader("Student Hours Progress Roster")
    for idx, row in summary_df.iterrows():
        c_name, c_course, c_hours, c_bar = st.columns([1.5, 1.2, 1, 2])
        c_name.markdown(f"**{row['first_name']} {row['last_name']}** (`{row['student_id']}`)")
        c_course.caption(f"{row['course']} • {row['track']}")
        c_hours.markdown(f"**{row['hours_logged']:.1f}** / {row['req_hours']} hrs")
        pct = min(max(float(row["progress_%"]) / 100.0, 0.0), 1.0)
        c_bar.progress(pct, text=f"{row['progress_%']}%")

    if "flagged" in shifts_df.columns:
        flagged_shifts = shifts_df[shifts_df["flagged"].astype(str).str.startswith("YES", na=False)]
        if not flagged_shifts.empty:
            st.markdown("---")
            st.subheader("⚠️ Shifts Flagged for Review")
            st.dataframe(flagged_shifts[["student_id", "name", "check_in", "check_out", "hours_logged", "flagged"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    with st.expander("👤 DECA Student Roster Management"):
        col_s1, col_s2, col_s3 = st.columns(3)
        st_id = col_s1.text_input("Student ID Number:", value=f"SIM100{len(roster_df)+1}")
        st_fn = col_s2.text_input("First Name:")
        st_ln = col_s3.text_input("Last Name:")

        col_s4, col_s5, col_s6 = st.columns(3)
        st_course = col_s4.selectbox("Enrolled Course:", ["1-Entrepreneurship", "2-Marketing", "6-Marketing", "7-SEM", "Accounting 2", "Store Management"])
        st_track = col_s5.text_input("DECA Role / Track:", value="Store Officer")
        st_req = col_s6.number_input("Required Hours:", min_value=1, max_value=100, value=10)

        if st.button("➕ Register Student to Roster"):
            if st_fn.strip() == "" or st_ln.strip() == "":
                st.error("Please enter student first and last name.")
            else:
                new_student = {
                    "student_id": st_id,
                    "first_name": st_fn,
                    "last_name": st_ln,
                    "course": st_course,
                    "track": st_track,
                    "req_hours": st_req,
                }
                roster_df = pd.concat([roster_df, pd.DataFrame([new_student])], ignore_index=True)
                roster_df = normalize_dataframe(roster_df, numeric_columns=["req_hours"])
                save_df(ROSTER_FILE, roster_df)
                st.session_state["roster_df"] = roster_df
                st.success(f"Registered {st_fn} {st_ln} ({st_id})!")
                st.rerun()

# ----------------------------------------------------
# TAB 4: SHEET MANAGER
# ----------------------------------------------------
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

        st.success("Changes saved successfully to disk.")
        st.rerun()
