import streamlit as st
import pandas as pd
import datetime
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Trojan Market - Store Management System",
    page_icon="🛡️",
    layout="wide"
)

# --- DATABASE / LOCAL FILE INITIALIZATION (NO GOOGLE DEPENDENCIES) ---
ROSTER_FILE = "roster.csv"
SHIFTS_FILE = "shift_logs.csv"
INVENTORY_FILE = "inventory.csv"
SALES_FILE = "revtrack_sales.csv"

def init_databases():
    # Initialize Student Roster with SHS DECA Officers &amp; Course Data
    if not os.path.exists(ROSTER_FILE):
        roster_data = pd.DataFrame([
            {"student_id": "SIM1001", "first_name": "Caroline", "last_name": "Fair", "course": "1-Entrepreneurship", "track": "DECA President", "req_hours": 20},
            {"student_id": "SIM1002", "first_name": "Elizabeth", "last_name": "Cadoff", "course": "6-Marketing", "track": "VP-School Store", "req_hours": 20},
            {"student_id": "SIM1003", "first_name": "Radha", "last_name": "Bansal", "course": "1-Entrepreneurship", "track": "VP-Marketing", "req_hours": 20},
            {"student_id": "SIM1004", "first_name": "Liam", "last_name": "Ricciardelli", "course": "2-Marketing", "track": "Officer", "req_hours": 10},
            {"student_id": "SIM1005", "first_name": "Julian", "last_name": "Mass", "course": "2-Marketing", "track": "Honors: Store", "req_hours": 10},
            {"student_id": "SIM1006", "first_name": "Henry", "last_name": "Pfeiffer", "course": "6-Marketing", "track": "ICDC", "req_hours": 10},
            {"student_id": "SIM1007", "first_name": "Caleb", "last_name": "Deems", "course": "7-SEM", "track": "Honors: Store", "req_hours": 10},
            {"student_id": "SIM1008", "first_name": "Olivia", "last_name": "Campasano", "course": "Accounting 2", "track": "Store", "req_hours": 10}
        ])
        roster_data.to_csv(ROSTER_FILE, index=False)

    # Initialize Shift Log
    if not os.path.exists(SHIFTS_FILE):
        shifts_data = pd.DataFrame(columns=["student_id", "name", "check_in", "check_out", "hours_logged", "shift_type", "status"])
        shifts_data.to_csv(SHIFTS_FILE, index=False)

    # Initialize Store Inventory
    if not os.path.exists(INVENTORY_FILE):
        inventory_data = pd.DataFrame([
            {"item_id": "SKU-001", "item_name": "Fresh Baked Cookies", "category": "Food", "stock": 48, "unit_price": 1.50},
            {"item_id": "SKU-002", "item_name": "Fresh Popcorn Bag", "category": "Food", "stock": 30, "unit_price": 2.00},
            {"item_id": "SKU-003", "item_name": "Slushy (Full Size)", "category": "Beverage", "stock": 25, "unit_price": 2.50},
            {"item_id": "SKU-004", "item_name": "SHS Trojan Hoodie", "category": "Apparel", "stock": 15, "unit_price": 35.00},
            {"item_id": "SKU-005", "item_name": "Trojan Spirit T-Shirt", "category": "Apparel", "stock": 22, "unit_price": 18.00}
        ])
        inventory_data.to_csv(INVENTORY_FILE, index=False)

    # Initialize RevTrack Sales History
    if not os.path.exists(SALES_FILE):
        sales_data = pd.DataFrame(columns=["transaction_id", "timestamp", "item_id", "quantity", "total_price", "payment_method"])
        sales_data.to_csv(SALES_FILE, index=False)

init_databases()

# --- HEADER &amp; NAVIGATION ---
st.title("🛡️ Trojan Market Management Dashboard")
st.caption("Simsbury High School DECA | Standalone Custom Operations Hub (Non-Google)")

tabs = st.tabs([
    "🕒 ID Scanner &amp; Time Clock", 
    "📋 Custom Sheets Database", 
    "📦 RevTrack POS &amp; Inventory", 
    "📊 Advisor &amp; Honors Analytics",
    "🪪 ID Card Generator"
])

# ==========================================
# TAB 1: ID SCANNER &amp; TIME LOGGING
# ==========================================
with tabs:
    st.header("Student ID Barcode Time Clock")
    st.info("Scan student ID card barcode (e.g. SIM1001) using a USB barcode scanner or type manually.")

    roster_df = pd.read_csv(ROSTER_FILE)
    shifts_df = pd.read_csv(SHIFTS_FILE)

    col1, col2 = st.columns([1, 2])
    
    with col1:
        scanned_barcode = st.text_input("⚡ Barcode Input Feed (Scan Card Here):", key="barcode_input")
        shift_type = st.selectbox("Select Shift Type:", ["Prep Shift (Period 5-8)", "School Day Shift", "After School Shift", "Open House / Event"])
        
        if scanned_barcode:
            scanned_barcode = scanned_barcode.strip().upper()
            student_match = roster_df[roster_df["student_id"] == scanned_barcode]

            if not student_match.empty:
                student_name = f"{student_match.iloc['first_name']} {student_match.iloc['last_name']}"
                st.success(f"ID Verified: **{student_name}** ({student_match.iloc['track']})")

                # Check if currently active shift exists
                active_shifts = shifts_df[(shifts_df["student_id"] == scanned_barcode) &amp (shifts_df["status"] == "ACTIVE")]

                if active_shifts.empty:
                    # CHECK IN
                    if st.button(f"🔴 Clock IN for {student_name}"):
                        new_shift = {
                            "student_id": scanned_barcode,
                            "name": student_name,
                            "check_in": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "check_out": "",
                            "hours_logged": 0.0,
                            "shift_type": shift_type,
                            "status": "ACTIVE"
                        }
                        shifts_df = pd.concat([shifts_df, pd.DataFrame([new_shift])], ignore_index=True)
                        shifts_df.to_csv(SHIFTS_FILE, index=False)
                        st.balloons()
                        st.success(f"Clocked IN successfully at {datetime.datetime.now().strftime('%H:%M:%S')}!")
                        st.rerun()
                else:
                    # CHECK OUT
                    check_in_time_str = active_shifts.iloc["check_in"]
                    check_in_dt = datetime.datetime.strptime(check_in_time_str, "%Y-%m-%d %H:%M:%S")
                    now_dt = datetime.datetime.now()
                    duration_hrs = round((now_dt - check_in_dt).total_seconds() / 3600.0, 2)

                    st.warning(f"Currently Clocked IN since: {check_in_time_str}")
                    if st.button(f"🟢 Clock OUT for {student_name} ({duration_hrs} hrs)"):
                        idx = active_shifts.index
                        shifts_df.at[idx, "check_out"] = now_dt.strftime("%Y-%m-%d %H:%M:%S")
                        shifts_df.at[idx, "hours_logged"] = max(duration_hrs, 1.0) # Default minimum 1-hr shift credit
                        shifts_df.at[idx, "status"] = "COMPLETED"
                        shifts_df.to_csv(SHIFTS_FILE, index=False)
                        st.success(f"Clocked OUT! Logged {max(duration_hrs, 1.0)} shift hours.")
                        st.rerun()
            else:
                st.error("Student ID barcode not found in roster database.")

    with col2:
        st.subheader("Currently Clocked In")
        active_now = shifts_df[shifts_df["status"] == "ACTIVE"]
        if not active_now.empty:
            st.dataframe(active_now[["name", "shift_type", "check_in"]], use_container_width=True)
        else:
            st.caption("No students currently clocked in.")

# ==========================================
# TAB 2: CUSTOM SHEETS DATABASE
# ==========================================
with tabs[2]:
    st.header("Custom Sheets Datastore Manager")
    st.caption("Direct spreadsheet viewer and editor operating independently of Google Sheets.")

    sheet_option = st.radio("Select Sheet to Manage:", ["Student Roster", "Shift Logs", "Master Inventory"], horizontal=True)

    if sheet_option == "Student Roster":
        df = pd.read_csv(ROSTER_FILE)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Roster Changes"):
            edited_df.to_csv(ROSTER_FILE, index=False)
            st.success("Roster updated successfully!")

    elif sheet_option == "Shift Logs":
        df = pd.read_csv(SHIFTS_FILE)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Shift Log Changes"):
            edited_df.to_csv(SHIFTS_FILE, index=False)
            st.success("Shift records updated successfully!")

    elif sheet_option == "Master Inventory":
        df = pd.read_csv(INVENTORY_FILE)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Inventory Changes"):
            edited_df.to_csv(INVENTORY_FILE, index=False)
            st.success("Inventory records updated successfully!")

# ==========================================
# TAB 3: REVTRACK POS &amp; REAL-TIME INVENTORY
# ==========================================
with tabs[1]:
    st.header("RevTrack POS Terminal &amp; Auto-Deduction")
    st.caption("Simulates sales transactions executed on store iPads/tap-to-pay devices.")

    inventory_df = pd.read_csv(INVENTORY_FILE)
    sales_df = pd.read_csv(SALES_FILE)

    c1, c2 = st.columns([2])

    with c1:
        st.subheader("Process New Sale")
        item_selected = st.selectbox("Select Purchased Item:", inventory_df["item_name"].tolist())
        qty_sold = st.number_input("Quantity Sold:", min_value=1, max_value=50, value=1)
        pay_method = st.selectbox("Payment Method:", ["RevTrack Tap-to-Pay (iPad)", "Cash Box"])

        item_row = inventory_df[inventory_df["item_name"] == item_selected].iloc
        total_cost = qty_sold * item_row["unit_price"]

        st.markdown(f"**Total Transaction Price:** `${total_cost:.2f}`")

        if st.button("💳 Confirm RevTrack Sale"):
            if item_row["stock"] &gt= qty_sold:
                # Deduct Inventory Stock
                idx = inventory_df[inventory_df["item_name"] == item_selected].index
                inventory_df.at[idx, "stock"] -= qty_sold
                inventory_df.to_csv(INVENTORY_FILE, index=False)

                # Log Transaction
                new_sale = {
                    "transaction_id": f"REV-{datetime.datetime.now().strftime('%M%S')}",
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "item_id": item_row["item_id"],
                    "quantity": qty_sold,
                    "total_price": total_cost,
                    "payment_method": pay_method
                }
                sales_df = pd.concat([sales_df, pd.DataFrame([new_sale])], ignore_index=True)
                sales_df.to_csv(SALES_FILE, index=False)

                st.success(f"Sale Processed! Stock for '{item_selected}' auto-updated to {inventory_df.at[idx, 'stock']}.")
                st.rerun()
            else:
                st.error("Insufficient stock to process transaction!")

    with c2:
        st.subheader("Live Inventory Levels")
        st.dataframe(inventory_df[["item_id", "item_name", "stock", "unit_price"]], use_container_width=True)
        
        # Low Stock Warnings
        low_stock = inventory_df[inventory_df["stock"] &lt; 10]
        if not low_stock.empty:
            st.warning(f"⚠️ Low Stock Alert for: {', '.join(low_stock['item_name'].tolist())}")

# ==========================================
# TAB 4: ADVISOR &amp; HONORS TRACK ANALYTICS
# ==========================================
with tabs[7]:
    st.header("DECA Advisor &amp; Course Progress Dashboard")
    st.caption("Tracks required honors and course shift hours (10/20 Hours Target) for Mr. Stanwood.")

    roster_df = pd.read_csv(ROSTER_FILE)
    shifts_df = pd.read_csv(SHIFTS_FILE)

    # Calculate Total Hours Completed Per Student
    completed_shifts = shifts_df[shifts_df["status"] == "COMPLETED"]
    hours_by_student = completed_shifts.groupby("student_id")["hours_logged"].sum().reset_index()

    summary_df = pd.merge(roster_df, hours_by_student, on="student_id", how="left").fillna(0)
    summary_df["progress_%"] = ((summary_df["hours_logged"] / summary_df["req_hours"]) * 100).round(1)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Students Enrolled", len(summary_df))
    m2.metric("Total Shift Hours Completed", summary_df["hours_logged"].sum())
    m3.metric("Avg Completion Rate", f"{summary_df['progress_%'].mean():.1f}%")

    st.subheader("Student Hours Breakdown")
    st.dataframe(summary_df[["student_id", "first_name", "last_name", "course", "track", "hours_logged", "req_hours", "progress_%"]], use_container_width=True)

# ==========================================
# TAB 5: ID CARD GENERATOR
# ==========================================
with tabs[8]:
    st.header("Custom Student ID Card Template")
    st.caption("Generates ID templates containing student photos, barcode numbers, and CT emergency contacts.")

    roster_df = pd.read_csv(ROSTER_FILE)
    selected_id = st.selectbox("Select Student for ID Card Generation:", roster_df["student_id"].tolist())

    student = roster_df[roster_df["student_id"] == selected_id].iloc

    st.markdown("---")
    st.subheader("🪪 Generated ID Card Preview")

    card_col1, card_col2 = st.columns(2)

    with card_col1:
        st.markdown("### **FRONT OF CARD**")
        st.markdown(f"""
        <div>
            <h3>SIMSBURY HIGH SCHOOL</h3>
            <p>Trojan Market / DECA Staff ID</p>
            <hr />
            <h4><b>Name:</b> {student['first_name']} {student['last_name']}</h4>
            <p><b>Course/Role:</b> {student['course']} ({student['track']})</p>
            <p><b>Student ID:</b> {student['student_id']}</p>
            <div>
                |||| | ||||| ||| || ||||||<br />{student['student_id']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with card_col2:
        st.markdown("### **BACK OF CARD (CT Law Mandate)**")
        st.markdown("""
        <div>
            <h5>EMERGENCY &amp; CRISIS CONTACTS</h5>
            <hr />
            <ul>
                <li><b>Suicide &amp; Crisis Lifeline:</b> Call or Text 988</li>
                <li><b>Police / Fire / Ambulance:</b> 911</li>
                <li><b>Mobile Mental Health &amp; Community Resources:</b> 211</li>
                <li><b>Westport/Simsbury Together Info:</b> QR / Online Portal</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
