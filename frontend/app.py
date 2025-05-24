import streamlit as st
import requests
import json
import mlflow
from mlflow.exceptions import MlflowException
from typing import Dict, Any, List
import os
from datetime import datetime
import logging
import pathlib
from user_management import (
    initialize_user_state,
    authenticate_user,
    create_tenant,
    add_user,
    get_tenant_users,
    get_tenant_info
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
GATEWAY_URL = "http://gateway:8000"

def initialize_session_state():
    """Initialize session state variables."""
    initialize_user_state()
    if "experiment_type" not in st.session_state:
        st.session_state.experiment_type = None
    if "show_user_management" not in st.session_state:
        st.session_state.show_user_management = False

def get_mlflow_experiments(tenant_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get MLflow experiments for the current tenant."""
    try:
        # Set the tracking URI for this tenant
        mlflow.set_tracking_uri(tenant_info["mlflow_uri"])
        
        # Search for experiments
        experiments = mlflow.search_experiments()
        
        # Format experiment data
        experiment_data = []
        for exp in experiments:
            runs = mlflow.search_runs(exp.experiment_id)
            experiment_data.append({
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "creation_time": exp.creation_time,
                "last_update_time": exp.last_update_time,
                "runs": [
                    {
                        "run_id": run.info.run_id,
                        "status": run.info.status,
                        "start_time": run.info.start_time,
                        "end_time": run.info.end_time,
                        "metrics": run.data.metrics,
                        "params": run.data.params
                    }
                    for run in runs.itertuples()
                ]
            })
        
        return experiment_data
    except Exception as e:
        logger.error(f"Error fetching MLflow experiments: {str(e)}")
        return []

def display_login_form():
    """Display the login form."""
    st.title("MLOps Platform Login")
    
    # Debug information
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.write("### Debug Information")
        st.sidebar.write(f"Session State: {st.session_state}")
    
    # Create tabs for Login and Sign Up
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    
    # Initialize active tab if not set
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Login"
    
    # Switch to the active tab
    if st.session_state.active_tab == "Login":
        st.session_state.active_tab = "Login"
    else:
        st.session_state.active_tab = "Sign Up"
    
    with login_tab:
        st.subheader("Login to Existing Tenant")
        col1, col2 = st.columns(2)
        
        with col1:
            # Pre-fill tenant ID if available
            initial_tenant = st.session_state.get("prefill_tenant", "")
            tenant_id = st.text_input("Tenant ID", value=initial_tenant, key="login_tenant_id")
            if tenant_id:
                st.write(f"Selected tenant: {tenant_id}")
        
        if tenant_id:
            with col2:
                # Pre-fill username if available
                initial_username = st.session_state.get("prefill_username", "")
                username = st.text_input("Username", value=initial_username, key="login_username")
                if username:
                    st.write(f"Entered username: {username}")
            
            if username:
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Login"):
                    st.write("Attempting login...")
                    success, message, role = authenticate_user(tenant_id, username, password)
                    if success:
                        st.session_state.authenticated_user = username
                        st.session_state.user_role = role
                        st.session_state.current_tenant = tenant_id
                        # Clear prefill values
                        if "prefill_tenant" in st.session_state:
                            del st.session_state.prefill_tenant
                        if "prefill_username" in st.session_state:
                            del st.session_state.prefill_username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(message)
    
    with signup_tab:
        st.subheader("Create New Tenant")
        with st.form("create_tenant_form"):
            tenant_id = st.text_input("Tenant ID", key="signup_tenant_id")
            tenant_name = st.text_input("Company/Organization Name", key="signup_tenant_name")
            mlflow_uri = st.text_input("MLflow URI", value="postgresql://mlflow:mlflow123@postgres:5432/mlflow_multitenant", key="signup_mlflow_uri")
            artifact_root = st.text_input("Artifact Root", value=f"/mlflow/tenants_data/{tenant_id}/artifacts", key="signup_artifact_root")
            
            # Add password fields for admin user
            st.subheader("Admin User Credentials")
            admin_username = st.text_input("Admin Username", value="admin", key="signup_admin_username")
            admin_password = st.text_input("Admin Password", type="password", key="signup_admin_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
            
            if st.form_submit_button("Create Tenant"):
                if not tenant_id or not tenant_name:
                    st.error("Tenant ID and Company Name are required")
                elif not admin_password or not confirm_password:
                    st.error("Admin password and confirmation are required")
                elif admin_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    st.write("Creating tenant...")
                    if create_tenant(tenant_id, tenant_name, mlflow_uri, artifact_root, admin_username, admin_password):
                        st.success(f"Tenant {tenant_name} created successfully!")
                        st.info("Initial admin user created with:")
                        st.info(f"Username: {admin_username}")
                        st.info("Password: [hidden]")
                        # Switch to login tab and pre-fill the form
                        st.session_state.active_tab = "Login"
                        st.session_state.prefill_tenant = tenant_id
                        st.session_state.prefill_username = admin_username
                        st.rerun()
                    else:
                        st.error("Failed to create tenant. Tenant ID might already exist.")

def display_tenant_management():
    """Display tenant management interface for admins."""
    st.title("Tenant Management")
    
    # Debug information
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.write("### Debug Information")
        st.sidebar.write(f"Session State: {st.session_state}")
    
    # Create new tenant
    with st.expander("Create New Tenant", expanded=True):
        with st.form("create_tenant_form"):
            tenant_id = st.text_input("Tenant ID")
            tenant_name = st.text_input("Tenant Name")
            mlflow_uri = st.text_input("MLflow URI", value="postgresql://mlflow:mlflow123@postgres:5432/mlflow_multitenant")
            artifact_root = st.text_input("Artifact Root", value=f"/mlflow/tenants_data/{tenant_id}/artifacts")
            
            if st.form_submit_button("Create Tenant"):
                st.write("Creating tenant...")
                if not tenant_id or not tenant_name:
                    st.error("Tenant ID and Name are required")
                else:
                    if create_tenant(tenant_id, tenant_name, mlflow_uri, artifact_root):
                        st.success(f"Tenant {tenant_name} created successfully!")
                        st.info(f"Initial admin user created with username: admin, password: admin123")
                        st.rerun()
                    else:
                        st.error("Failed to create tenant. Tenant ID might already exist.")

def display_user_management():
    """Display user management interface for tenant admins."""
    st.title("User Management")
    
    # Debug information
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.write("### Debug Information")
        st.sidebar.write(f"Session State: {st.session_state}")
        st.sidebar.write(f"Current Tenant: {st.session_state.current_tenant}")
    
    # Add new user
    with st.expander("Add New User", expanded=True):
        with st.form("add_user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["admin", "viewer"])
            
            if st.form_submit_button("Add User"):
                st.write("Adding user...")
                success, message = add_user(
                    st.session_state.current_tenant,
                    username,
                    password,
                    role
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    # List existing users
    st.subheader("Existing Users")
    users = get_tenant_users(st.session_state.current_tenant)
    if users:
        for username, user_data in users.items():
            st.write(f"**{username}** - Role: {user_data['role']} (Created: {user_data.get('created_at', 'N/A')})")
    else:
        st.info("No users found for this tenant.")

def display_dashboard():
    """Display tenant-specific dashboard."""
    tenant_id = st.session_state.current_tenant
    tenant_info = get_tenant_info(tenant_id)
    
    if not tenant_info:
        st.error("Tenant information not found")
        return
    
    # Debug information
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.write("### Debug Information")
        st.sidebar.write(f"Session State: {st.session_state}")
        st.sidebar.write(f"Tenant Info: {tenant_info}")
    
    # Sidebar with tenant info and controls
    st.sidebar.header("Tenant Information")
    st.sidebar.write(f"**Name:** {tenant_info['name']}")
    st.sidebar.write(f"**Logged in as:** {st.session_state.authenticated_user}")
    st.sidebar.write(f"**Role:** {st.session_state.user_role}")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated_user = None
        st.session_state.user_role = None
        st.session_state.current_tenant = None
        st.rerun()
    
    # Admin features
    if st.session_state.user_role == "admin":
        if st.sidebar.button("Manage Users"):
            st.session_state.show_user_management = True
    
    # Main dashboard content
    st.title(f"MLOps Dashboard - {tenant_info['name']}")
    
    if st.session_state.get("show_user_management", False):
        display_user_management()
        if st.button("Back to Dashboard"):
            st.session_state.show_user_management = False
            st.rerun()
    else:
        # Display MLflow experiments
        st.header("MLflow Experiments")
        
        try:
            experiments = get_mlflow_experiments(tenant_info)
            
            if experiments:
                for exp in experiments:
                    with st.expander(f"Experiment: {exp['name']}"):
                        st.write(f"**ID:** {exp['experiment_id']}")
                        st.write(f"**Created:** {exp['creation_time']}")
                        st.write(f"**Last Updated:** {exp['last_update_time']}")
                        
                        # Display runs
                        if exp['runs']:
                            st.subheader("Runs")
                            for run in exp['runs']:
                                with st.expander(f"Run: {run['run_id']}"):
                                    st.write(f"**Status:** {run['status']}")
                                    st.write(f"**Start Time:** {run['start_time']}")
                                    if run['end_time']:
                                        st.write(f"**End Time:** {run['end_time']}")
                                    
                                    # Display metrics
                                    if run['metrics']:
                                        st.write("**Metrics:**")
                                        for metric, value in run['metrics'].items():
                                            st.write(f"- {metric}: {value}")
                                    
                                    # Display parameters
                                    if run['params']:
                                        st.write("**Parameters:**")
                                        for param, value in run['params'].items():
                                            st.write(f"- {param}: {value}")
                        else:
                            st.info("No runs found for this experiment")
            else:
                st.info("No experiments found for this tenant")
        except Exception as e:
            st.error(f"Error loading experiments: {str(e)}")
            logger.error(f"Error loading experiments: {str(e)}")

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="MLOps Platform",
        page_icon="🔬",
        layout="wide"
    )
    
    initialize_session_state()
    
    # If not authenticated, show login form
    if not st.session_state.authenticated_user:
        display_login_form()
    # If authenticated and tenant selected, show dashboard
    elif st.session_state.current_tenant:
        display_dashboard()
    else:
        st.error("Invalid state. Please log in again.")
        st.session_state.authenticated_user = None
        st.session_state.user_role = None
        st.session_state.current_tenant = None
        st.rerun()

if __name__ == "__main__":
    main()