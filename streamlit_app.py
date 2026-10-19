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

# --- FILE STORAGE ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ROSTER_FILE = os.path.join(ROOT_DIR, "roster.csv")
SHIFTS_FILE = os.path.join(ROOT_DIR, "shifts.csv")
INVENTORY_FILE = os.path.join(ROOT_DIR, "inventory.csv")
SALES_FILE = os.path.join(ROOT_DIR, "sales.csv")


def normalize_dataframe(df: pd.DataFrame, numeric_columns=None, text_columns=None) -> pd.DataFrame:
    """Normalize columns so pandas doesn't crash when assigning strings into blank numeric columns."""
    if df is None:
        return df

    numeric_columns = numeric_columns or []
    text_columns = text_columns or []

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(lambda value: "" if pd.isna(value) else str(value))

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


# --- SAMPLE DATA ---
def get_default_roster() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "student_id": "SIM1001",
                "first_name": "Caroline",
                "last_name": "Fair",
                "course": "1-Entrepreneurship",
                "track": "DECA President",
                "req_hours": 20,
            },
            {
                "student_id": "SIM1002",
                "first_name": "Elizabeth",
                "last_name": "Cadoff",
                "course": "6-Marketing",
                "track": "VP-School Store",
                "req_hours": 20,
            },
            {
                "student_id": "SIM1003",
                "first_name": "Radha",
                "last_name": "Bansal",
                "course": "1-Entrepreneurship",
                "track": "VP-Marketing",
                "req_hours": 20,
            },
            {
                "student_id": "SIM1004",
                "first_name": "Liam",
                "last_name": "Ricciardelli",
                "course": "2-Marketing",
                "track": "Officer",
                "req_hours": 10,
            },
            {
                "student_id": "SIM1005",
                "first_name": "Julian",
                "last_name": "Mass",
                "course": "2-Marketing",
                "track": "Honors: Store",
                "req_hours": 10,
            },
            {
                "student_id": "SIM1006",
                "first_name": "Henry",
                "last_name": "Pfeiffer",
                "course": "6-Marketing",
                "track": "ICDC",
                "req_hours": 10,
            },
            {
                "student_id": "SIM1007",
                "first_name": "Caleb",
                "last_name": "Deems",
                "course": "7-SEM",
                "track": "Honors: Store",
                "req_hours": 10,
            },
            {
                "student_id": "SIM1008",
                "first_name": "Olivia",
                "last_name": "Campasano",
                "course": "Accounting 2",
                "track": "Store",
                "req_hours": 10,
            },
        ]
    )


def get_default_shifts() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "student_id",
            "name",
            "check_in",
            "check_out",
            "hours_logged",
            "shift_type",
            "status",
        ]
    )


def get_default_inventory() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"item_id": "SKU-001", "item_name": "Fresh Baked Cookies", "category": "Food", "stock": 48, "unit_price": 1.50},
            {"item_id": "SKU-002", "item_name": "Fresh Popcorn Bag", "category": "Food", "stock": 30, "unit_price": 2.00},
            {"item_id": "SKU-003", "item_name": "Slushy (Full Size)", "category": "Beverage", "stock": 25, "unit_price": 2.50},
            {"item_id": "SKU-004", "item_name": "SHS Trojan Hoodie", "category": "Apparel", "stock": 15, "unit_price": 35.00},
            {"item_id": "SKU-005", "item_name": "Trojan Spirit T-Shirt", "category": "Apparel", "stock": 22, "unit_price": 18.00},
        ]
    )


def get_default_sales() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["transaction_id", "timestamp", "item_id", "quantity", "total_price", "payment_method"]
    )


# Normalize on load so blank CSV values don't create bad float dtypes.
roster_df = normalize_dataframe(
    load_or_create_df(ROSTER_FILE, get_default_roster()),
    numeric_columns=["req_hours"],
)
shifts_df = normalize_dataframe(
    load_or_create_df(SHIFTS_FILE, get_default_shifts()),
    numeric_columns=["hours_logged"],
    text_columns=["student_id", "name", "check_in", "check_out", "shift_type", "status"],
)
inventory_df = normalize_dataframe(
    load_or_create_df(INVENTORY_FILE, get_default_inventory()),
    numeric_columns=["stock", "unit_price"],
)
sales_df = normalize_dataframe(
    load_or_create_df(SALES_FILE, get_default_sales()),
    numeric_columns=["quantity", "total_price"],
    text_columns=["transaction_id", "timestamp", "item_id", "payment_method"],
)

# --- UI HELPERS ---

def student_lookup(student_id: str) -> pd.Series | None:
    match = roster_df[roster_df["student_id"].str.upper() == student_id.strip().upper()]
    if match.empty:
        return None
    return match.iloc[0]


st.title("Trojan Market Management Dashboard")
st.caption("Simsbury High School DECA | Standalone Customs Hub (Non-Google)")


tabs = st.tabs([
    "🛡️ ID & Time Clock",
    "📊 Custom Sheets Database",
    "💸 RevTrack POS & Inventory",
    "📈 DECA Advisor Dashboard",
    "🪪 ID Card Generator",
])

with tabs[0]:
    st.header("Student ID Barcode Time Clock")
    st.info("Scan student ID card barcode (e.g. SIM1001) using a USB barcode scanner or type manually.")

    scanned_barcode = st.text_input("Barcode Input Feed (Scan Card Here):", key="barcode_input")
    shift_type = st.selectbox(
        "Select Shift Type:",
        ["Prep Shift (Period 5-8)", "School Day Shift", "After School Shift", "Open House / Event"],
    )

    if scanned_barcode:
        student = student_lookup(scanned_barcode)
        if student is None:
            st.error("Student ID barcode not found in roster database.")
        else:
            student_name = f"{student['first_name']} {student['last_name']}"
            st.success(f"ID Verified: {student_name} ({student['track']})")

            active_shifts = shifts_df[
                (shifts_df["student_id"] == student["student_id"]) & (shifts_df["status"] == "ACTIVE")
            ]

            if active_shifts.empty:
                if st.button(f"Clock IN for {student_name}"):
                    now = datetime.datetime.now()
                    new_shift = {
                        "student_id": student["student_id"],
                        "name": student_name,
                        "check_in": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "check_out": "",
                        "hours_logged": 0.0,
                        "shift_type": shift_type,
                        "status": "ACTIVE",
                    }
                    shifts_df = pd.concat([shifts_df, pd.DataFrame([new_shift])], ignore_index=True)
                    shifts_df = normalize_dataframe(
                        shifts_df,
                        numeric_columns=["hours_logged"],
                        text_columns=["student_id", "name", "check_in", "check_out", "shift_type", "status"],
                    )
                    save_df(SHIFTS_FILE, shifts_df)
                    st.success(f"Clocked IN successfully at {now.strftime('%H:%M:%S')}!")
                    st.rerun()
            else:
                check_in_time = active_shifts.iloc[0]["check_in"]
                if st.button(f"Clock OUT for {student_name}"):
                    idx = active_shifts.index[0]
                    checked_in = datetime.datetime.strptime(check_in_time, "%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.now()
                    duration_hours = max((now - checked_in).total_seconds() / 3600, 1.0)
                    shifts_df.at[idx, "check_out"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    shifts_df.at[idx, "hours_logged"] = round(duration_hours, 2)
                    shifts_df.at[idx, "status"] = "COMPLETED"
                    shifts_df = normalize_dataframe(
                        shifts_df,
                        numeric_columns=["hours_logged"],
                        text_columns=["student_id", "name", "check_in", "check_out", "shift_type", "status"],
                    )
                    save_df(SHIFTS_FILE, shifts_df)
                    st.success(f"Clocked OUT! Logged {duration_hours:.1f} hours.")
                    st.rerun()

    st.subheader("Currently Clocked In")
    active_now = shifts_df[shifts_df["status"] == "ACTIVE"]
    if active_now.empty:
        st.caption("No students currently clocked in.")
    else:
        st.dataframe(active_now[["student_id", "name", "check_in", "shift_type"]], use_container_width=True)

with tabs[1]:
    st.header("Custom Sheets Database Manager")
    st.caption("Direct spreadsheet viewer and editor operating independently of Google Sheets.")

    sheet_option = st.radio(
        "Select Sheet to Manage:",
        ["Student Roster", "Shift Logs", "Master Inventory"],
        horizontal=True,
    )

    if sheet_option == "Student Roster":
        df = roster_df.copy()
    elif sheet_option == "Shift Logs":
        df = shifts_df.copy()
    else:
        df = inventory_df.copy()

    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("Save Changes"):
        if sheet_option == "Student Roster":
            roster_df = normalize_dataframe(edited_df.copy(), numeric_columns=["req_hours"])
            save_df(ROSTER_FILE, roster_df)
        elif sheet_option == "Shift Logs":
            shifts_df = normalize_dataframe(
                edited_df.copy(),
                numeric_columns=["hours_logged"],
                text_columns=["student_id", "name", "check_in", "check_out", "shift_type", "status"],
            )
            save_df(SHIFTS_FILE, shifts_df)
        else:
            inventory_df = normalize_dataframe(edited_df.copy(), numeric_columns=["stock", "unit_price"])
            save_df(INVENTORY_FILE, inventory_df)
        st.success("Changes saved successfully.")

with tabs[2]:
    st.header("RevTrack POS & Real-Time Inventory")
    st.caption("Simulate sales transactions executed on store iPads and tap-to-pay devices.")

    inventory_df = normalize_dataframe(
        load_or_create_df(INVENTORY_FILE, get_default_inventory()),
        numeric_columns=["stock", "unit_price"],
    )
    sales_df = normalize_dataframe(
        load_or_create_df(SALES_FILE, get_default_sales()),
        numeric_columns=["quantity", "total_price"],
        text_columns=["transaction_id", "timestamp", "item_id", "payment_method"],
    )

    item_options = inventory_df["item_name"].tolist()
    selected_item = st.selectbox("Select Purchased Item:", item_options)
    quantity_sold = st.number_input("Quantity Sold:", min_value=1, max_value=50, value=1)
    payment_method = st.selectbox("Payment Method:", ["RevTrack Tap-to-Pay (iPad)", "Cash Box"])

    item_row = inventory_df[inventory_df["item_name"] == selected_item].iloc[0]
    total_cost = quantity_sold * float(item_row["unit_price"])
    st.markdown(f"**Total Transaction Price:** ${total_cost:.2f}")

    if st.button("Confirm RevTrack Sale"):
        if int(item_row["stock"]) >= quantity_sold:
            idx = inventory_df.index[inventory_df["item_name"] == selected_item][0]
            inventory_df.at[idx, "stock"] = int(item_row["stock"]) - quantity_sold
            save_df(INVENTORY_FILE, inventory_df)

            new_sale = {
                "transaction_id": f"REV-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "item_id": item_row["item_id"],
                "quantity": quantity_sold,
                "total_price": total_cost,
                "payment_method": payment_method,
            }
            sales_df = pd.concat([sales_df, pd.DataFrame([new_sale])], ignore_index=True)
            sales_df = normalize_dataframe(
                sales_df,
                numeric_columns=["quantity", "total_price"],
                text_columns=["transaction_id", "timestamp", "item_id", "payment_method"],
            )
            save_df(SALES_FILE, sales_df)
            st.success(f"Sale processed! Stock for '{selected_item}' auto-updated.")
        else:
            st.error("Insufficient stock to process transaction!")

    st.subheader("Live Inventory Levels")
    st.dataframe(
        inventory_df[["item_id", "item_name", "stock", "unit_price"]],
        use_container_width=True,
    )

with tabs[3]:
    st.header("DECA Advisor & Course Progress Dashboard")
    st.caption("Tracks required hours and completion progress across student participation.")

    completed_shifts = shifts_df[shifts_df["status"] == "COMPLETED"].copy()
    if not completed_shifts.empty:
        completed_shifts["hours_logged"] = pd.to_numeric(completed_shifts["hours_logged"], errors="coerce").fillna(0)
        hours_by_student = completed_shifts.groupby("student_id")["hours_logged"].sum().reset_index()
        summary_df = roster_df.merge(hours_by_student, on="student_id", how="left").fillna({"hours_logged": 0})
        summary_df["progress_%"] = ((summary_df["hours_logged"] / summary_df["req_hours"]) * 100).round(1)
    else:
        summary_df = roster_df.copy()
        summary_df["hours_logged"] = 0.0
        summary_df["progress_%"] = 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Students Enrolled", len(summary_df))
    col2.metric("Total Shift Hours Completed", int(summary_df["hours_logged"].sum()))
    col3.metric("Avg Completion Rate", f"{summary_df['progress_%'].mean():.1f}%")

    st.subheader("Student Hours Breakdown")
    st.dataframe(
        summary_df[["student_id", "first_name", "last_name", "course", "track", "hours_logged", "req_hours", "progress_%"]],
        use_container_width=True,
    )

with tabs[4]:
    st.header("Custom Student ID Card Template")
    st.caption("Generates ID templates containing student photos, barcode numbers, and emergency contacts.")

    selected_student_id = st.selectbox("Select Student for ID Card Generation:", roster_df["student_id"].tolist())
    selected_student = roster_df[roster_df["student_id"] == selected_student_id].iloc[0]
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background:#f4f4f4; border:2px solid #d9d9d9; border-radius:12px; padding:20px; max-width:650px;">
            <h3 style="margin:0;">SIMSBURY HIGH SCHOOL</h3>
            <p style="margin:0;">Trojan Market / DECA Staff ID</p>
            <hr>
            <h4 style="margin:0;">Name: {selected_student['first_name']} {selected_student['last_name']}</h4>
            <p><b>Course/Role:</b> {selected_student['course']} ({selected_student['track']})</p>
            <p><b>Student ID:</b> {selected_student['student_id']}</p>
            <div style="border:1px solid #111; padding:12px; border-radius:8px; background:white;">BARCODE: {selected_student['student_id']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Emergency Contact Info")
    st.markdown(
        """
        <ul>
            <li><b>Suicide & Crisis Lifeline:</b> Call or Text 988</li>
            <li><b>Police / Fire / Ambulance:</b> 911</li>
            <li><b>Mobile Mental Health & Community Resources:</b> 211</li>
            <li><b>Westport / Simsbury Together Info:</b> QR / Online Portal</li>
        </ul>
        """,
        unsafe_allow_html=True,
    )

st.write("")
