import bcrypt
import json
import os
from typing import Optional, Dict, Any, Tuple
import streamlit as st
import logging
import fcntl
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
USERS_FILE = "tenants_data/tenants_users.json"
BACKUP_FILE = "tenants_data/tenants_users.json.bak"

def safe_read_json(file_path: str) -> Dict[str, Any]:
    """Safely read JSON file with error handling and backup."""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File {file_path} does not exist")
            return {}
        
        with open(file_path, 'r') as f:
            # Add file lock for reading
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                data = json.load(f)
                logger.info(f"Successfully read data from {file_path}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {file_path}: {str(e)}")
                # Try to restore from backup if available
                if os.path.exists(BACKUP_FILE):
                    logger.info("Attempting to restore from backup")
                    return safe_read_json(BACKUP_FILE)
                return {}
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

def safe_write_json(file_path: str, data: Dict[str, Any]):
    """Safely write JSON file with backup and file locking."""
    try:
        # Create backup of existing file
        if os.path.exists(file_path):
            with open(file_path, 'r') as src, open(BACKUP_FILE, 'w') as dst:
                fcntl.flock(src.fileno(), fcntl.LOCK_SH)
                fcntl.flock(dst.fileno(), fcntl.LOCK_EX)
                try:
                    dst.write(src.read())
                finally:
                    fcntl.flock(src.fileno(), fcntl.LOCK_UN)
                    fcntl.flock(dst.fileno(), fcntl.LOCK_UN)
        
        # Write new data
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2)
                logger.info(f"Successfully wrote data to {file_path}")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def load_tenant_users() -> Dict[str, Any]:
    """Load tenant and user data from JSON file."""
    data = safe_read_json(USERS_FILE)
    logger.info(f"Loaded tenant data: {json.dumps(data, indent=2)}")
    return data

def save_tenant_users(data: Dict[str, Any]):
    """Save tenant and user data to JSON file."""
    try:
        safe_write_json(USERS_FILE, data)
        logger.info(f"Saved tenant data: {json.dumps(data, indent=2)}")
    except Exception as e:
        logger.error(f"Failed to save tenant data: {str(e)}")
        raise

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        logger.info("Successfully hashed password")
        return hashed
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        raise

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        result = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        logger.info(f"Password verification {'succeeded' if result else 'failed'}")
        return result
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def create_tenant(tenant_id: str, tenant_name: str, mlflow_uri: str, artifact_root: str, admin_username: str = "admin", admin_password: str = "admin123") -> bool:
    """Create a new tenant with initial admin user."""
    try:
        data = load_tenant_users()
        logger.info(f"Creating tenant: {tenant_id}")
        
        if tenant_id in data:
            logger.warning(f"Tenant {tenant_id} already exists")
            return False
        
        # Create initial admin user with provided credentials
        hashed_password = hash_password(admin_password)
        
        data[tenant_id] = {
            "name": tenant_name,
            "users": {
                admin_username: {
                    "hashed_password": hashed_password,
                    "role": "admin",
                    "created_at": str(datetime.now())
                }
            },
            "mlflow_uri": mlflow_uri,
            "artifact_root": artifact_root,
            "created_at": str(datetime.now())
        }
        
        save_tenant_users(data)
        logger.info(f"Created tenant {tenant_id} with initial admin user {admin_username}")
        return True
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def add_user(tenant_id: str, username: str, password: str, role: str) -> Tuple[bool, str]:
    """Add a new user to a tenant."""
    try:
        data = load_tenant_users()
        logger.info(f"Adding user {username} to tenant {tenant_id}")
        
        if tenant_id not in data:
            logger.warning(f"Tenant {tenant_id} not found")
            return False, "Tenant not found"
        
        if username in data[tenant_id]["users"]:
            logger.warning(f"Username {username} already exists in tenant {tenant_id}")
            return False, "Username already exists"
        
        if role not in ["admin", "viewer"]:
            logger.warning(f"Invalid role: {role}")
            return False, "Invalid role"
        
        hashed_password = hash_password(password)
        data[tenant_id]["users"][username] = {
            "hashed_password": hashed_password,
            "role": role,
            "created_at": str(datetime.now())
        }
        
        save_tenant_users(data)
        logger.info(f"Added user {username} to tenant {tenant_id}")
        return True, "User added successfully"
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error adding user: {str(e)}"

def authenticate_user(tenant_id: str, username: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """
    Authenticate a user.
    Returns (success, message, role) tuple.
    """
    try:
        data = load_tenant_users()
        logger.info(f"Authenticating user {username} for tenant {tenant_id}")
        
        if tenant_id not in data:
            logger.warning(f"Tenant {tenant_id} not found")
            return False, "Tenant not found", None
        
        if username not in data[tenant_id]["users"]:
            logger.warning(f"User {username} not found in tenant {tenant_id}")
            return False, "User not found", None
        
        user_data = data[tenant_id]["users"][username]
        if verify_password(password, user_data["hashed_password"]):
            logger.info(f"User {username} authenticated successfully")
            return True, "Authentication successful", user_data["role"]
        
        logger.warning(f"Invalid password for user {username}")
        return False, "Invalid password", None
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        logger.error(traceback.format_exc())
        return False, f"Error authenticating: {str(e)}", None

def get_tenant_users(tenant_id: str) -> Dict[str, Any]:
    """Get all users for a tenant."""
    data = load_tenant_users()
    users = data.get(tenant_id, {}).get("users", {})
    logger.info(f"Retrieved users for tenant {tenant_id}: {json.dumps(users, indent=2)}")
    return users

def get_tenant_info(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get tenant information."""
    data = load_tenant_users()
    info = data.get(tenant_id)
    logger.info(f"Retrieved info for tenant {tenant_id}: {json.dumps(info, indent=2) if info else 'None'}")
    return info

def initialize_user_state():
    """Initialize user-related session state variables."""
    if "authenticated_user" not in st.session_state:
        st.session_state.authenticated_user = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "current_tenant" not in st.session_state:
        st.session_state.current_tenant = None 