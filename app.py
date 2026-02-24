import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. MOCK DATABASE & USERS ---
# We are creating fake accounts to test the Role & Department-based access [cite: 15]
USERS = {
    "staff": {"password": "123", "role": "User"},
    "supervisor": {"password": "123", "role": "Supervisor"},
    "engineer": {"password": "123", "role": "Engineer"}
}

# Temporary database to hold tickets while the app is running
if 'tickets' not in st.session_state:
    st.session_state.tickets = pd.DataFrame(columns=[
        "Ticket ID", "Raised by", "Ward", "Help Department", 
        "Issue Type", "Description", "Priority", "Status", "Assigned To", "Timestamp"
    ])

# --- 2. LOGIN MODULE [cite: 13] ---
def login():
    st.title("Hospital Ticketing Service Portal")
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username in USERS and USERS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = USERS[username]["role"]
                st.rerun()
            else:
                st.error("Invalid username or password.")

# --- 3. USER (HOSPITAL STAFF) DASHBOARD ---
def user_dashboard():
    st.header(f"Welcome, {st.session_state.username} (Staff)")
    st.subheader("Raise a New Ticket [cite: 20]")
    
    with st.form("ticket_form"):
        ward = st.text_input("Requesting Department (Ward) [cite: 26]")
        dept = st.selectbox("Help Department (IT or Maintenance) [cite: 27]", ["IT", "Maintenance"])
        
        # Sample Issue Categories [cite: 32]
        if dept == "IT":
            issue = st.selectbox("Issue Type [cite: 28]", ["PC not working [cite: 41]", "Printer not working [cite: 42]", "Network issue [cite: 44]", "Other"])
        else:
            issue = st.selectbox("Issue Type [cite: 28]", ["AC not working [cite: 34]", "Tap leakage [cite: 37]", "Light not working [cite: 36]", "Other"])
            
        desc = st.text_area("Issue Description [cite: 29]")
        priority = st.selectbox("Priority [cite: 30]", ["Low", "Medium", "High"])
        
        if st.form_submit_button("Submit Ticket"):
            if ward and desc:
                # Ticket ID (auto-generated) [cite: 24]
                ticket_id = f"TKT-{datetime.now().strftime('%H%M%S')}"
                new_data = pd.DataFrame([{
                    "Ticket ID": ticket_id, "Raised by": st.session_state.username,
                    "Ward": ward, "Help Department": dept, "Issue Type": issue,
                    "Description": desc, "Priority": priority, "Status": "Open",
                    "Assigned To": "Unassigned", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                st.session_state.tickets = pd.concat([st.session_state.tickets, new_data], ignore_index=True)
                st.success(f"Ticket {ticket_id} raised successfully!")
            else:
                st.error("Please fill in all fields.")

    st.subheader("My Tickets")
    my_tickets = st.session_state.tickets[st.session_state.tickets["Raised by"] == st.session_state.username]
    st.dataframe(my_tickets)

# --- 4. SUPERVISOR DASHBOARD ---
def supervisor_dashboard():
    st.header("Supervisor Dashboard")
    st.write("View unassigned tickets and Assign tickets to available engineers [cite: 50, 51]")
    
    st.dataframe(st.session_state.tickets)
    
    st.subheader("Assign a Ticket")
    with st.form("assign_form"):
        # Select from available ticket IDs
        ticket_to_assign = st.selectbox("Select Ticket ID", st.session_state.tickets["Ticket ID"].tolist())
        engineer_name = st.text_input("Engineer Username (e.g., 'engineer')")
        
        if st.form_submit_button("Assign"):
            if ticket_to_assign and engineer_name:
                # Update the database
                st.session_state.tickets.loc[st.session_state.tickets["Ticket ID"] == ticket_to_assign, "Assigned To"] = engineer_name
                st.session_state.tickets.loc[st.session_state.tickets["Ticket ID"] == ticket_to_assign, "Status"] = "Assigned"
                st.success(f"Ticket assigned to {engineer_name}.")
                st.rerun()

# --- 5. ENGINEER DASHBOARD ---
def engineer_dashboard():
    st.header(f"Engineer Dashboard: {st.session_state.username}")
    st.write("View assigned tickets [cite: 58]")
    
    # Filter tickets assigned to this engineer
    my_tasks = st.session_state.tickets[st.session_state.tickets["Assigned To"] == st.session_state.username]
    st.dataframe(my_tasks)
    
    st.subheader("Update Ticket Status")
    with st.form("update_form"):
        task_to_update = st.selectbox("Select Ticket ID", my_tasks["Ticket ID"].tolist() if not my_tasks.empty else ["No tickets"])
        # Change status to: Resolved , In Progress , or On Hold 
        new_status = st.selectbox("New Status", ["In Progress", "On Hold", "Resolved"])
        notes = st.text_area("Add notes (e.g. diagnosis, steps taken) [cite: 59]")
        
        if st.form_submit_button("Update Status"):
            if task_to_update != "No tickets":
                st.session_state.tickets.loc[st.session_state.tickets["Ticket ID"] == task_to_update, "Status"] = new_status
                st.success(f"Ticket {task_to_update} marked as {new_status}.")
                st.rerun()

# --- 6. MAIN APP CONTROLLER ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    # Route to the correct dashboard based on role
    if st.session_state.role == "User":
        user_dashboard()
    elif st.session_state.role == "Supervisor":
        supervisor_dashboard()
    elif st.session_state.role == "Engineer":
        engineer_dashboard()
