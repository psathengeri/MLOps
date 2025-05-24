import streamlit as st
import requests
import json
import mlflow
from mlflow.exceptions import MlflowException
from typing import Dict, Any
import os
from datetime import datetime
import logging
import pathlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TENANTS_FILE = "tenants_data/tenants.json"
GATEWAY_URL = "http://gateway:8000"

@st.cache_resource
def load_tenants() -> Dict[str, Any]:
    """Load tenants data from JSON file with improved error handling and debugging."""
    # Get absolute path for debugging
    abs_path = os.path.abspath(TENANTS_FILE)
    
    # Debug information
    st.sidebar.markdown("### Debug Information")
    st.sidebar.code(f"Tenants file path: {abs_path}")
    st.sidebar.code(f"File exists: {os.path.exists(abs_path)}")
    
    if os.path.exists(abs_path):
        st.sidebar.code(f"File permissions: {oct(os.stat(abs_path).st_mode)[-3:]}")
    
    try:
        # Check if file exists
        if not os.path.exists(abs_path):
            error_msg = f"Tenants file not found at: {abs_path}"
            logger.error(error_msg)
            st.error(error_msg)
            st.warning("Please ensure the tenants.json file is properly mounted in the Docker container.")
            return {}
        
        # Check if file is readable
        if not os.access(abs_path, os.R_OK):
            error_msg = f"Tenants file exists but is not readable: {abs_path}"
            logger.error(error_msg)
            st.error(error_msg)
            st.warning("Please check file permissions in the Docker container.")
            return {}
        
        # Try to read and parse the file
        with open(abs_path, 'r') as f:
            try:
                tenants_data = json.load(f)
                if not tenants_data:
                    st.warning("Tenants file is empty. No tenants configured.")
                    return {}
                return tenants_data
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in tenants file: {str(e)}"
                logger.error(error_msg)
                st.error(error_msg)
                return {}
                
    except Exception as e:
        error_msg = f"Error loading tenants data: {str(e)}"
        logger.error(error_msg)
        st.error(error_msg)
        st.warning("""
        Common issues:
        1. File not mounted in Docker container
        2. Incorrect file permissions
        3. Invalid JSON format
        
        Please check the Docker volume mounts and file permissions.
        """)
        return {}

def initialize_session_state():
    """Initialize session state variables."""
    if "tenant_id" not in st.session_state:
        st.session_state.tenant_id = None
    if "experiment_type" not in st.session_state:
        st.session_state.experiment_type = None
    if 'current_tenant' not in st.session_state:
        st.session_state.current_tenant = None
    if 'tenants_data' not in st.session_state:
        st.session_state.tenants_data = load_tenants()

def get_tenant_from_query_params() -> str:
    """Get tenant from URL query parameters."""
    return st.query_params.get('tenant', None)

def set_tenant(tenant_id: str):
    """Set the current tenant in session state."""
    if tenant_id in st.session_state.tenants_data:
        st.session_state.current_tenant = tenant_id
        # Update URL query parameter
        st.query_params['tenant'] = tenant_id
        st.session_state.tenant_id = tenant_id
        st.session_state.experiment_type = None
    else:
        st.error(f"Invalid tenant: {tenant_id}")

def clear_tenant():
    """Clear the current tenant and return to tenant selection."""
    st.session_state.current_tenant = None
    st.session_state.tenant_id = None
    st.session_state.experiment_type = None
    # Clear the tenant from URL query parameters
    if 'tenant' in st.query_params:
        del st.query_params['tenant']

def get_experiments(tenant_id: str) -> list:
    """Fetch experiments for the current tenant from the gateway."""
    try:
        response = requests.get(
            f"{GATEWAY_URL}/experiments",
            params={"tenant": tenant_id}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching experiments: {e}")
        return []

def display_tenant_selector():
    """Display tenant selector dropdown."""
    tenant_id = st.selectbox(
        "Select Tenant",
        options=list(st.session_state.tenants_data.keys()),
        index=0 if st.session_state.current_tenant is None else 
              list(st.session_state.tenants_data.keys()).index(st.session_state.current_tenant)
    )
    if tenant_id != st.session_state.current_tenant:
        set_tenant(tenant_id)

def display_dashboard():
    """Display tenant-specific dashboard."""
    tenant_id = st.session_state.current_tenant
    tenant_data = st.session_state.tenants_data[tenant_id]
    
    # Add back button at the top
    if st.button("← Back to Tenant Selection"):
        clear_tenant()
        st.rerun()
    
    st.title(f"MLOps Dashboard - {tenant_data['name']}")
    
    # Display tenant info
    st.sidebar.header("Tenant Information")
    st.sidebar.write(f"**Name:** {tenant_data['name']}")
    st.sidebar.write(f"**Created:** {tenant_data['created_at']}")
    
    # Fetch and display experiments
    experiments = get_experiments(tenant_id)
    
    if experiments:
        st.header("Experiments")
        for exp in experiments:
            with st.expander(f"Experiment: {exp.get('name', 'Unnamed')}"):
                st.write(f"**ID:** {exp.get('experiment_id', 'N/A')}")
                st.write(f"**Created:** {exp.get('creation_time', 'N/A')}")
                st.write(f"**Last Updated:** {exp.get('last_update_time', 'N/A')}")
    else:
        st.info("No experiments found for this tenant.")

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="MLOps Platform",
        page_icon="🔬",
        layout="wide"
    )
    
    initialize_session_state()
    
    # Check for tenant in URL query params
    tenant_from_url = get_tenant_from_query_params()
    if tenant_from_url and tenant_from_url != st.session_state.current_tenant:
        set_tenant(tenant_from_url)
    
    # If no tenant is selected, show selector
    if st.session_state.current_tenant is None:
        st.title("Welcome to MLOps Platform")
        display_tenant_selector()
    else:
        display_dashboard()

if __name__ == "__main__":
    main()