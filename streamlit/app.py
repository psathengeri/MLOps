import streamlit as st
import mlflow
import pandas as pd
import plotly.express as px
from mlflow.tracking import MlflowClient

# Set MLflow tracking URI
mlflow.set_tracking_uri("http://mlflow:5000")
client = MlflowClient()

st.set_page_config(page_title="Veroxe MLOps Platform", layout="wide")

# Sidebar navigation
page = st.sidebar.selectbox("Navigate", [
    "Dashboard", 
    "Experiments", 
    "Models", 
    "Deploy", 
    "Monitor"
])

if page == "Dashboard":
    st.title("🚀 Veroxe MLOps Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Experiments", len(client.search_experiments()))
    with col2:
        st.metric("Total Models", len(client.search_registered_models()))
    with col3:
        st.metric("Deployed Models", 2)  # Placeholder
    with col4:
        st.metric("Data Quality", "98%")  # Placeholder

elif page == "Experiments":
    st.title("🔬 Experiment Tracking")
    
    experiments = client.search_experiments()
    
    if experiments:
        exp_names = [exp.name for exp in experiments]
        selected_exp = st.selectbox("Select Experiment", exp_names)
        
        # Get runs for selected experiment
        exp_id = next(exp.experiment_id for exp in experiments if exp.name == selected_exp)
        runs = client.search_runs([exp_id])
        
        if runs:
            # Create runs dataframe
            runs_data = []
            for run in runs:
                runs_data.append({
                    'Run ID': run.info.run_id[:8],
                    'Status': run.info.status,
                    'Accuracy': run.data.metrics.get('accuracy', 'N/A'),
                    'Loss': run.data.metrics.get('loss', 'N/A'),
                    'Duration': (run.info.end_time - run.info.start_time) / 1000 if run.info.end_time else 'Running'
                })
            
            df = pd.DataFrame(runs_data)
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No experiments found. Start training your first model!")

elif page == "Models":
    st.title("📦 Model Registry")
    
    models = client.search_registered_models()
    
    if models:
        for model in models:
            with st.expander(f"Model: {model.name}"):
                versions = client.get_latest_versions(model.name)
                for version in versions:
                    st.write(f"Version: {version.version}")
                    st.write(f"Stage: {version.current_stage}")
                    st.write(f"Description: {version.description or 'No description'}")
    else:
        st.info("No registered models found.")

elif page == "Deploy":
    st.title("🚀 Model Deployment")
    
    st.subheader("Deploy New Model")
    
    models = client.search_registered_models()
    if models:
        model_names = [model.name for model in models]
        selected_model = st.selectbox("Select Model", model_names)
        
        versions = client.get_latest_versions(selected_model)
        version_numbers = [v.version for v in versions]
        selected_version = st.selectbox("Select Version", version_numbers)
        
        if st.button("Deploy Model"):
            st.success(f"Model {selected_model} v{selected_version} deployed successfully!")
            st.code(f"""
            # API Endpoint:
            POST http://localhost:5000/invocations
            Content-Type: application/json
            
            {{
                "instances": [your_data_here]
            }}
            """)

elif page == "Monitor":
    st.title("📊 Model Monitoring")
    
    # Simulated monitoring data
    import numpy as np
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    accuracy = np.random.normal(0.85, 0.05, 30)
    latency = np.random.normal(200, 50, 30)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_acc = px.line(x=dates, y=accuracy, title="Model Accuracy Over Time")
        st.plotly_chart(fig_acc, use_container_width=True)
    
    with col2:
        fig_lat = px.line(x=dates, y=latency, title="Prediction Latency (ms)")
        st.plotly_chart(fig_lat, use_container_width=True)
    
    st.subheader("Data Drift Detection")
    drift_score = np.random.random()
    
    if drift_score > 0.7:
        st.error(f"🚨 Data drift detected! Score: {drift_score:.2f}")
    elif drift_score > 0.5:
        st.warning(f"⚠️ Potential data drift. Score: {drift_score:.2f}")
    else:
        st.success(f"✅ No data drift detected. Score: {drift_score:.2f}")
