import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection

# --- TIMEZONE SETUP ---
IST = timezone(timedelta(hours=5, minutes=30))

# --- 1. SETUP DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(worksheet="Tickets", ttl=0)

def add_data(new_row_df):
    try:
        current_data = get_data()
        updated_data = pd.concat([current_data, new_row_df], ignore_index=True)
        conn.update(worksheet="Tickets", data=updated_data)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

def update_ticket_status(ticket_id, col_name, new_value):
    df = get_data()
    mask = df["Ticket ID"] == ticket_id
    if mask.any():
        df.loc[mask, col_name] = new_value
        conn.update(worksheet="Tickets", data=df)
        st.cache_data.clear()
        return True
    return False

# --- 2. USERS (Updated for dual supervisors) ---
USERS = {
    "staff": {"password": "123", "role": "User"},
    "it_super": {"password": "123", "role": "Supervisor", "dept": "IT"},
    "maint_super": {"password": "123", "role": "Supervisor", "dept": "Maintenance"},
    "admin": {"password": "123", "role": "Admin"}  
}

# --- 3. LOGIN MODULE ---
def login():
    st.title("🏥 Hospital Ticketing Portal (Live DB)")
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            safe_username = username.lower()
            df = get_data()
            
            # Find all names that have tickets assigned to them in the database
            if not df.empty and "Assigned To" in df.columns:
                assigned_engineers = df["Assigned To"].str.lower().unique().tolist()
            else:
                assigned_engineers = []
            
            # 1. Check if it's a hardcoded main user (Staff, Admin, Supervisors)
            if safe_username in USERS and USERS[safe_username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = safe_username
                st.session_state.role = USERS[safe_username]["role"]
                # Save their department if they are a supervisor
                if "dept" in USERS[safe_username]:
                    st.session_state.dept = USERS[safe_username]["dept"]
                st.rerun()
                
            # 2. DYNAMIC ENGINEER LOGIN: Check if they are an assigned engineer!
            elif safe_username in assigned_engineers and safe_username != "unassigned" and password == "123":
                st.session_state.logged_in = True
                st.session_state.username = safe_username
                st.session_state.role = "Engineer"
                st.rerun()
                
            else:
                st.error("Invalid credentials. (Engineers: Ensure your supervisor assigned you a ticket and use password '123')")

# --- 4. DASHBOARDS ---

def user_dashboard():
    st.header(f"Welcome, {st.session_state.username}")
    st.subheader("Raise a New Ticket")
    
    ward = st.text_input("Ward / Department")
    dept = st.selectbox("Help Department", ["IT", "Maintenance"])
    
    if dept == "Maintenance":
        issue = st.selectbox("Issue Type", [
            "Air condition", "Plumbing", "Electrical", "Paint", "Other maintenance related issue"
        ]) 
    elif dept == "IT":
        issue = st.selectbox("Issue Type", [
            "PC not working", "Printer not working", "Network issue", "Other IT related issue"
        ]) 
        
    desc = st.text_area("Description")
    priority = st.selectbox("Priority", ["Low", "Medium", "High"])
    
    if st.button("Submit Ticket"):
        if ward and desc:
            ticket_id = f"TKT-{datetime.now(IST).strftime('%d%H%M%S')}"
            new_ticket = pd.DataFrame([{
                "Ticket ID": ticket_id, "Raised By": st.session_state.username,
                "Ward": ward, "Help Department": dept, "Issue Type": issue,
                "Description": desc, "Priority": priority, "Status": "Open",
                "Assigned To": "Unassigned", "Timestamp": datetime.now(IST).strftime("%Y-%m-%d %I:%M %p") 
            }])
            
            if add_data(new_ticket):
                st.success(f"Ticket {ticket_id} Saved to Database!")
        else:
            st.warning("Please fill all fields")

    st.write("---")
    st.subheader("My Past Tickets")
    df = get_data()
    if not df.empty and "Raised By" in df.columns:
        my_tickets = df[df["Raised By"] == st.session_state.username]
        st.dataframe(my_tickets)

def supervisor_dashboard():
    # Only show the department name for this specific supervisor
    my_dept = st.session_state.dept
    st.header(f"Supervisor Dashboard ({my_dept} Department)")
    
    df = get_data()
    
    # Filter the entire database so this supervisor ONLY sees their department's tickets
    if not df.empty:
        df_filtered = df[df["Help Department"] == my_dept]
    else:
        df_filtered = pd.DataFrame()
        
    st.dataframe(df_filtered)
    
    st.subheader("Assign Ticket")
    with st.form("assign"):
        if not df_filtered.empty and "Assigned To" in df_filtered.columns:
            # Only show UNASSIGNED tickets for THEIR department
            open_tickets = df_filtered[df_filtered["Assigned To"] == "Unassigned"]["Ticket ID"].tolist()
        else:
            open_tickets = []
            
        t_id = st.selectbox("Select Ticket", open_tickets) if open_tickets else None
        eng_name = st.text_input("Assign to Engineer (e.g., 'hello1')")
        
        if st.form_submit_button("Assign"):
            if t_id and eng_name:
                safe_eng_name = eng_name.lower().strip()
                update_ticket_status(t_id, "Assigned To", safe_eng_name)
                update_ticket_status(t_id, "Status", "Assigned")
                st.success(f"Ticket assigned! {safe_eng_name} can now log in using password '123'.")
                st.rerun()

def admin_dashboard():
    st.header("👑 Admin & Analytics Dashboard")
    st.write("System oversight and reporting.")
    
    df = get_data()
    
    if df.empty:
        st.warning("No tickets in the database yet.")
        return

    st.subheader("System Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    total_tickets = len(df)
    open_tickets = len(df[df["Status"] == "Open"])
    assigned_tickets = len(df[df["Status"] == "Assigned"])
    resolved_tickets = len(df[df["Status"] == "Resolved"])

    col1.metric("Total Tickets", total_tickets)
    col2.metric("Pending (Open)", open_tickets)
    col3.metric("Assigned", assigned_tickets)
    col4.metric("Resolved", resolved_tickets)

    st.write("---")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Department Breakdown") 
        dept_counts = df["Help Department"].value_counts()
        st.bar_chart(dept_counts)

    with col_chart2:
        st.subheader("Engineer Workload") 
        assigned_df = df[df["Assigned To"] != "Unassigned"]
        if not assigned_df.empty:
            eng_counts = assigned_df["Assigned To"].value_counts()
            st.bar_chart(eng_counts)
        else:
            st.info("No tickets assigned to engineers yet.")

    st.write("---")
    st.subheader("Export System Data")
    
    csv = df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Download Full Report as CSV (Excel)",
        data=csv,
        file_name=f"hospital_tickets_report_{datetime.now(IST).strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
    
    st.write("Raw Data View:")
    st.dataframe(df)

def engineer_dashboard():
    st.header(f"Engineer: {st.session_state.username}")
    df = get_data()
    
    # Filter the database so the engineer ONLY sees tickets assigned to them
    if not df.empty and "Status" in df.columns:
        # We make sure the assignment name matches their username perfectly
        my_tasks = df[(df["Status"].isin(["Assigned", "In Progress"])) & (df["Assigned To"].str.lower() == st.session_state.username)]
    else:
        my_tasks = pd.DataFrame()
        
    st.dataframe(my_tasks)
    
    st.subheader("Update Status")
    with st.form("update"):
        t_id = st.selectbox("Select Ticket", my_tasks["Ticket ID"].tolist()) if not my_tasks.empty else None
        status = st.selectbox("New Status", ["In Progress", "Resolved"])
        
        if st.form_submit_button("Update"):
            if t_id:
                update_ticket_status(t_id, "Status", status)
                st.success("Updated!")
                st.rerun()

# --- 5. MAIN APP ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    if st.session_state.role == "User":
        user_dashboard()
    elif st.session_state.role == "Supervisor":
        supervisor_dashboard()
    elif st.session_state.role == "Engineer":
        engineer_dashboard()
    elif st.session_state.role == "Admin":      
        admin_dashboard()