import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SETUP DATABASE CONNECTION ---
# This establishes a live connection to your Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# Function to fetch latest data
def get_data():
    # ttl=0 means "don't cache, always get fresh data"
    return conn.read(worksheet="Tickets", ttl=0)

# Function to save data
def add_data(new_row_df):
    try:
        current_data = get_data()
        updated_data = pd.concat([current_data, new_row_df], ignore_index=True)
        conn.update(worksheet="Tickets", data=updated_data)
        st.cache_data.clear() # Clear cache to force reload next time
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

# Function to update a specific ticket (for Supervisors/Engineers)
def update_ticket_status(ticket_id, col_name, new_value):
    df = get_data()
    # Find the row index
    mask = df["Ticket ID"] == ticket_id
    if mask.any():
        df.loc[mask, col_name] = new_value
        conn.update(worksheet="Tickets", data=df)
        st.cache_data.clear()
        return True
    return False

# --- 2. USERS (Still Hardcoded for Safety) ---
USERS = {
    "staff": {"password": "123", "role": "User"},
    "supervisor": {"password": "123", "role": "Supervisor"},
    "engineer": {"password": "123", "role": "Engineer"}
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
            # Convert whatever they typed into lowercase right away
            safe_username = username.lower()
            
            # Check the lowercase version against our database
            if safe_username in USERS and USERS[safe_username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = safe_username
                st.session_state.role = USERS[safe_username]["role"]
                st.rerun()
            else:
                st.error("Invalid credentials")

# --- 4. DASHBOARDS ---

def user_dashboard():
    st.header(f"Welcome, {st.session_state.username}")
    
    # Form to raise ticket
    with st.form("ticket_form"):
        ward = st.text_input("Ward / Department")
        dept = st.selectbox("Help Department", ["IT", "Maintenance"])
        
        if dept == "IT":
            issue = st.selectbox("Issue", ["PC Issue", "Printer", "Network", "Software", "Other"])
        else:
            issue = st.selectbox("Issue", ["AC", "Lights", "Plumbing", "Furniture", "Other"])
            
        desc = st.text_area("Description")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        
        if st.form_submit_button("Submit Ticket"):
            if ward and desc:
                ticket_id = f"TKT-{datetime.now().strftime('%d%H%M%S')}"
                new_ticket = pd.DataFrame([{
                    "Ticket ID": ticket_id, "Raised By": st.session_state.username,
                    "Ward": ward, "Help Department": dept, "Issue Type": issue,
                    "Description": desc, "Priority": priority, "Status": "Open",
                    "Assigned To": "Unassigned", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                
                if add_data(new_ticket):
                    st.success(f"Ticket {ticket_id} Saved to Database!")
            else:
                st.warning("Please fill all fields")

    # View My Tickets
    st.subheader("My Past Tickets")
    df = get_data()
    # Filter for current user. Note: Check column names match Sheet exactly!
    if not df.empty and "Raised By" in df.columns:
        my_tickets = df[df["Raised By"] == st.session_state.username]
        st.dataframe(my_tickets)

def supervisor_dashboard():
    st.header("Supervisor Dashboard")
    df = get_data()
    st.dataframe(df)
    
    st.subheader("Assign Ticket")
    with st.form("assign"):
        if not df.empty and "Assigned To" in df.columns:
            open_tickets = df[df["Assigned To"] == "Unassigned"]["Ticket ID"].tolist()
        else:
            open_tickets = []
            
        t_id = st.selectbox("Select Ticket", open_tickets) if open_tickets else None
        eng_name = st.text_input("Assign to Engineer (Name)")
        
        if st.form_submit_button("Assign"):
            if t_id and eng_name:
                update_ticket_status(t_id, "Assigned To", eng_name)
                update_ticket_status(t_id, "Status", "Assigned")
                st.success("Assigned!")
                st.rerun()

def engineer_dashboard():
    st.header(f"Engineer: {st.session_state.username}")
    df = get_data()
    
    if not df.empty and "Status" in df.columns:
        my_tasks = df[df["Status"] == "Assigned"] 
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