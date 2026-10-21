import os
import datetime
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Trojan Market - Store Management System",
    page_icon="🛡️",
    layout="wide",
)

# --- FILE STORAGE & CONFIGURATION ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ROSTER_FILE = os.path.join(ROOT_DIR, "roster.csv")
SHIFTS_FILE = os.path.join(ROOT_DIR, "shifts.csv")
INVENTORY_FILE = os.path.join(ROOT_DIR, "inventory.csv")
SALES_FILE = os.path.join(ROOT_DIR, "sales.csv")

MAX_SHIFT_HOURS = 4.0

# --- STYLING ---
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0b1120 !important;
        color: #e5e7eb !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%) !important;
        border-right: 1px solid rgba(148, 163, 184, 0.2);
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        background: #0b1120;
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
    return df


def save_df(file_path: str, df: pd.DataFrame) -> None:
    df.to_csv(file_path, index=False)


# Default datasets[cite: 1]
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
        {"item_id": "SKU-001", "item_name": "Fresh Baked Cookies", "category": "Food", "stock": 48, "unit_price": 1.50},
        {"item_id": "SKU-002", "item_name": "Fresh Popcorn Bag", "category": "Food", "stock": 30, "unit_price": 2.00},
        {"item_id": "SKU-003", "item_name": "Slushy (Full Size)", "category": "Beverage", "stock": 25, "unit_price": 2.50},
        {"item_id": "SKU-004", "item_name": "SHS Trojan Hoodie", "category": "Apparel", "stock": 15, "unit_price": 35.00},
        {"item_id": "SKU-005", "item_name": "Trojan Spirit T-Shirt", "category": "Apparel", "stock": 22, "unit_price": 18.00},
    ])


def get_default_sales() -> pd.DataFrame:
    return pd.DataFrame(columns=["transaction_id", "timestamp", "item_id", "quantity", "total_price", "payment_method"])


def reload_all_data():
    st.session_state["roster_df"] = normalize_dataframe(
        load_or_create_df(ROSTER_FILE, get_default_roster()), numeric_columns=["req_hours"]
    )
    st.session_state["shifts_df"] = normalize_dataframe(
        load_or_create_df(SHIFTS_FILE, get_default_shifts()),
        numeric_columns=["hours_logged"],
        text_columns=["student_id", "name", "check_in", "check_out", "shift_type", "status", "flagged"],
    )
    st.session_state["inventory_df"] = normalize_dataframe(
        load_or_create_df(INVENTORY_FILE, get_default_inventory()), numeric_columns=["stock", "unit_price"]
    )
    st.session_state["sales_df"] = normalize_dataframe(
        load_or_create_df(SALES_FILE, get_default_sales()),
        numeric_columns=["quantity", "total_price"],
        text_columns=["transaction_id", "timestamp", "item_id", "payment_method"],
    )


# Load session state
if "roster_df" not in st.session_state:
    reload_all_data()

roster_df = st.session_state["roster_df"]
shifts_df = st.session_state["shifts_df"]
inventory_df = st.session_state["inventory_df"]
sales_df = st.session_state["sales_df"]


def student_lookup(student_id: str) -> pd.Series | None:
    match = roster_df[roster_df["student_id"].str.upper() == student_id.strip().upper()]
    return None if match.empty else match.iloc[0]


# --- SIDEBAR & HEADER ---
st.title("Trojan Market")
st.caption("Simsbury High School DECA • Operations & Hours Dashboard")

with st.sidebar:
    st.markdown("### Store Controls")
    st.info("Central management system for student time tracking, POS, and DECA course progress[cite: 1].")

    if st.button("🔄 Refresh Data"):
        reload_all_data()
        st.rerun()

    st.markdown("---")
    low_stock_limit = st.slider("Low stock warning threshold:", min_value=1, max_value=20, value=5)


# Metric Bar
m1, m2, m3, m4 = st.columns(4)
m1.metric("Enrolled Students", len(roster_df))
m2.metric("Active Shifts", int((shifts_df["status"] == "ACTIVE").sum()))
low_stock_count = int((inventory_df["stock"] <= low_stock_limit).sum())
m3.metric("Total Items Stocked", int(inventory_df["stock"].sum()), delta=f"{low_stock_count} low" if low_stock_count else "Stock OK", delta_color="inverse" if low_stock_count else "normal")
m4.metric("Sales Recorded", len(sales_df))

st.write("")

# --- TABS ---
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
        active_now = shifts_df[shifts_df["status"] == "ACTIVE"]
        if active_now.empty:
            st.info("No students are currently clocked in.")
        else:
            st.dataframe(
                active_now[["student_id", "name", "check_in", "shift_type"]],
                use_container_width=True,
                hide_index=True,
            )

# ----------------------------------------------------
# TAB 2: POS & INVENTORY
# ----------------------------------------------------
with tabs[1]:
    st.header("Point of Sale & Live Inventory")
    st.caption("Record purchases and automatically adjust store inventory levels[cite: 1].")

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

            payment_method = st.selectbox("Payment Method:", ["Cash Box", "Tap-to-Pay (RevTrak Ready)", "School Account"])
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

        # Backward/Forward compatible Pandas Styler (.map vs .applymap)
        styler = inventory_df[["item_id", "item_name", "category", "stock", "unit_price"]].style
        if hasattr(styler, "map"):
            styled_inventory = styler.map(highlight_low_stock, subset=["stock"])
        else:
            styled_inventory = styler.applymap(highlight_low_stock, subset=["subset" if "subset" in dir() else "stock"])

        st.dataframe(styled_inventory, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# TAB 3: ADVISOR DASHBOARD
# ----------------------------------------------------
with tabs[2]:
    st.header("DECA Advisor & Student Progress Dashboard")
    st.caption("Tracks required shift hours and monitors student progress[cite: 1].")

    completed_shifts = shifts_df[shifts_df["status"] == "COMPLETED"].copy()
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

    flagged_shifts = shifts_df[shifts_df["flagged"].str.startswith("YES", na=False)]
    if not flagged_shifts.empty:
        st.markdown("---")
        st.subheader("⚠️ Shifts Flagged for Review")
        st.dataframe(flagged_shifts[["student_id", "name", "check_in", "check_out", "hours_logged", "flagged"]], use_container_width=True, hide_index=True)

# ----------------------------------------------------
# TAB 4: SHEET MANAGER
# ----------------------------------------------------
with tabs[3]:
    st.header("Custom Database Manager")
    st.caption("Directly inspect and update store CSV data files[cite: 1].")

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
