import bcrypt
import json
import os
from typing import Optional, Tuple
import streamlit as st

# Constants
CREDENTIALS_FILE = "tenants_data/tenant_credentials.json"

def load_credentials() -> dict:
    """Load tenant credentials from JSON file."""
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_credentials(credentials: dict):
    """Save tenant credentials to JSON file."""
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f)

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_tenant_credentials(tenant_id: str) -> Optional[str]:
    """Get hashed password for a tenant if it exists."""
    credentials = load_credentials()
    return credentials.get(tenant_id)

def set_tenant_password(tenant_id: str, password: str):
    """Set a new password for a tenant."""
    credentials = load_credentials()
    credentials[tenant_id] = hash_password(password)
    save_credentials(credentials)

def authenticate_tenant(tenant_id: str, password: str) -> Tuple[bool, str]:
    """
    Authenticate a tenant with their password.
    Returns (success, message) tuple.
    """
    hashed_password = get_tenant_credentials(tenant_id)
    
    if not hashed_password:
        return False, "No password set for this tenant"
    
    if verify_password(password, hashed_password):
        return True, "Authentication successful"
    return False, "Invalid password"

def initialize_auth_state():
    """Initialize authentication-related session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "auth_error" not in st.session_state:
        st.session_state.auth_error = None 