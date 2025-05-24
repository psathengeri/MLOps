import streamlit as st
import requests
import json
import mlflow
from mlflow.exceptions import MlflowException

st.set_page_config(page_title="Multi-Tenant MLOps", layout="wide")

# Initialize session state variables if they don't exist
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "experiment_type" not in st.session_state:
    st.session_state.experiment_type = None

# Tenant Selection
st.sidebar.title("🏢 Tenant Selection")

# Load or create tenant list
if 'tenants' not in st.session_state:
    try:
        response = requests.get("http://gateway:8000/tenants", headers={"X-Tenant-ID": "system"})
        st.session_state.tenants = response.json() if response.status_code == 200 else []
    except:
        st.session_state.tenants = []

# Tenant selector
tenant_options = ["Create New Tenant"] + st.session_state.tenants
selected_tenant = st.sidebar.selectbox("Select Tenant", tenant_options)

# Experiment type selector
experiment_types = ["Default", "AutoML", "Notebook", "BatchPipeline"]
selected_experiment_type = st.sidebar.selectbox("Select Experiment Type", experiment_types)

# Update session state when selections change
if selected_tenant != "Create New Tenant":
    st.session_state.tenant_id = selected_tenant
    st.session_state.experiment_type = selected_experiment_type

# Create new tenant
if selected_tenant == "Create New Tenant":
    st.sidebar.subheader("Create New Tenant")
    new_tenant_id = st.sidebar.text_input("Tenant ID")
    new_tenant_name = st.sidebar.text_input("Tenant Name")
    
    if st.sidebar.button("Create Tenant"):
        if new_tenant_id and new_tenant_name:
            try:
                response = requests.post(
                    "http://gateway:8000/tenants",
                    headers={"X-Tenant-ID": "system"},
                    json={
                        "tenant_id": new_tenant_id,
                        "tenant_name": new_tenant_name
                    }
                )
                if response.status_code == 200:
                    st.sidebar.success("Tenant created successfully!")
                    st.session_state.tenants.append(new_tenant_id)
                    st.rerun()
                else:
                    error_msg = response.json().get("detail", "Failed to create tenant")
                    st.sidebar.error(f"Error: {error_msg}")
            except requests.exceptions.RequestException as e:
                st.sidebar.error(f"Connection error: {str(e)}")
            except Exception as e:
                st.sidebar.error(f"Unexpected error: {str(e)}")
        else:
            st.sidebar.warning("Please provide both Tenant ID and Tenant Name")

# Display status message if both selections are made
if st.session_state.tenant_id and st.session_state.experiment_type:
    st.info(f"You are working in tenant: `{st.session_state.tenant_id}` | Experiment: `{st.session_state.experiment_type}`")
    
    # Configure MLflow
    try:
        tracking_uri = f"http://mlflow:5000/{st.session_state.tenant_id}"
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(st.session_state.experiment_type)
        st.sidebar.success("MLflow tracking configured successfully!")
    except MlflowException as e:
        st.error(f"Failed to configure MLflow: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error configuring MLflow: {str(e)}")

# Main interface (if tenant selected)
if selected_tenant != "Create New Tenant":
    st.title(f"🚀 MLOps Dashboard - Tenant: {selected_tenant}")
    
    # Headers for API calls
    headers = {"X-Tenant-ID": selected_tenant}
    
    tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Experiments", "Models", "Train"])
    
    with tab1:
        st.subheader("📊 Dashboard")
        
        col1, col2, col3 = st.columns(3)
        
        try:
            # Get tenant stats
            experiments_resp = requests.get("http://gateway:8000/experiments", headers=headers)
            models_resp = requests.get("http://gateway:8000/models", headers=headers)
            
            with col1:
                exp_count = len(experiments_resp.json()) if experiments_resp.status_code == 200 else 0
                st.metric("Experiments", exp_count)
            
            with col2:
                model_count = len(models_resp.json()) if models_resp.status_code == 200 else 0
                st.metric("Models", model_count)
            
            with col3:
                st.metric("Tenant", selected_tenant)
                
        except Exception as e:
            st.error(f"Failed to load dashboard: {str(e)}")
    
    with tab2:
        st.subheader("🔬 Experiments")
        
        try:
            response = requests.get("http://gateway:8000/experiments", headers=headers)
            if response.status_code == 200:
                experiments = response.json()
                if experiments:
                    for exp in experiments:
                        st.write(f"**{exp['name']}** (ID: {exp['id']})")
                else:
                    st.info("No experiments found for this tenant.")
            else:
                st.error("Failed to load experiments")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with tab3:
        st.subheader("📦 Models")
        
        try:
            response = requests.get("http://gateway:8000/models", headers=headers)
            if response.status_code == 200:
                models = response.json()
                if models:
                    for model in models:
                        st.write(f"**{model['name']}**")
                        if model['description']:
                            st.write(f"Description: {model['description']}")
                else:
                    st.info("No models found for this tenant.")
            else:
                st.error("Failed to load models")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with tab4:
        st.subheader("🏋️ Train Model")
        
        model_type = st.selectbox("Model Type", ["sklearn", "tensorflow", "pytorch"])
        
        if st.button("Start Training"):
            try:
                with st.spinner("Training model..."):
                    response = requests.post(
                        f"http://gateway:8000/train?model_type={model_type}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"Training completed!")
                        st.json(result)
                    else:
                        st.error("Training failed")
            except Exception as e:
                st.error(f"Error: {str(e)}")

else:
    st.title("🏢 Multi-Tenant MLOps Platform")
    st.info("Please select or create a tenant to continue.")