from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import mlflow
from mlflow.tracking import MlflowClient
import os
import hashlib
from typing import Optional
import json

app = FastAPI(title="Multi-Tenant MLOps Gateway")
security = HTTPBearer()

# Simple tenant storage (use proper DB in production)
TENANTS_FILE = "/app/tenants_data/tenants.json"

class TenantManager:
    def __init__(self):
        self.load_tenants()
    
    def load_tenants(self):
        try:
            with open(TENANTS_FILE, 'r') as f:
                self.tenants = json.load(f)
        except FileNotFoundError:
            self.tenants = {}
            self.save_tenants()
    
    def save_tenants(self):
        os.makedirs(os.path.dirname(TENANTS_FILE), exist_ok=True)
        with open(TENANTS_FILE, 'w') as f:
            json.dump(self.tenants, f)
    
    def create_tenant(self, tenant_id: str, tenant_name: str):
        if tenant_id in self.tenants:
            raise HTTPException(status_code=400, detail="Tenant already exists")
        
        # Create tenant entry
        self.tenants[tenant_id] = {
            "name": tenant_name,
            "created_at": str(pd.Timestamp.now()),
            "mlflow_uri": f"postgresql://mlflow:mlflow123@postgres:5432/mlflow_multitenant?options=-csearch_path={tenant_id}",
            "artifact_root": f"/mlflow/tenants_data/{tenant_id}/artifacts"
        }
        
        # Create database schema
        self.create_tenant_schema(tenant_id)
        
        # Create artifact directory
        os.makedirs(f"/app/tenants_data/{tenant_id}/artifacts", exist_ok=True)
        
        self.save_tenants()
        return self.tenants[tenant_id]
    
    def create_tenant_schema(self, tenant_id: str):
        import psycopg2
        conn = psycopg2.connect(
            host="postgres",
            database="mlflow_multitenant", 
            user="mlflow",
            password="mlflow123"
        )
        cur = conn.cursor()
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant_id}")
        conn.commit()
        cur.close()
        conn.close()
    
    def get_tenant(self, tenant_id: str):
        if tenant_id not in self.tenants:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return self.tenants[tenant_id]
    
    def list_tenants(self):
        return list(self.tenants.keys())

tenant_manager = TenantManager()

def get_tenant_id(x_tenant_id: str = Header(...)):
    """Extract tenant ID from header"""
    return x_tenant_id

def get_mlflow_client(tenant_id: str = Depends(get_tenant_id)):
    """Get MLflow client for specific tenant"""
    tenant = tenant_manager.get_tenant(tenant_id)
    mlflow.set_tracking_uri(tenant["mlflow_uri"])
    return MlflowClient(tracking_uri=tenant["mlflow_uri"])

# Tenant Management Endpoints
@app.post("/tenants")
async def create_tenant(tenant_id: str, tenant_name: str):
    """Create a new tenant"""
    return tenant_manager.create_tenant(tenant_id, tenant_name)

@app.get("/tenants")
async def list_tenants():
    """List all tenants"""
    return tenant_manager.list_tenants()

@app.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get tenant details"""
    return tenant_manager.get_tenant(tenant_id)

# Tenant-Scoped MLflow Endpoints
@app.get("/experiments")
async def list_experiments(client: MlflowClient = Depends(get_mlflow_client)):
    """List experiments for tenant"""
    experiments = client.search_experiments()
    return [{"id": exp.experiment_id, "name": exp.name} for exp in experiments]

@app.get("/experiments/{experiment_id}/runs")
async def list_runs(experiment_id: str, client: MlflowClient = Depends(get_mlflow_client)):
    """List runs for experiment"""
    runs = client.search_runs([experiment_id])
    return [{"id": run.info.run_id, "status": run.info.status} for run in runs]

@app.get("/models")
async def list_models(client: MlflowClient = Depends(get_mlflow_client)):
    """List registered models for tenant"""
    models = client.search_registered_models()
    return [{"name": model.name, "description": model.description} for model in models]

# Training endpoint (tenant-scoped)
@app.post("/train")
async def train_model(
    model_type: str = "sklearn",
    tenant_id: str = Depends(get_tenant_id)
):
    """Train a model for specific tenant"""
    tenant = tenant_manager.get_tenant(tenant_id)
    mlflow.set_tracking_uri(tenant["mlflow_uri"])
    
    with mlflow.start_run():
        # Sample training (replace with actual training logic)
        if model_type == "sklearn":
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.datasets import make_classification
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            
            X, y = make_classification(n_samples=1000, n_features=20, n_classes=2)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
            
            model = RandomForestClassifier(n_estimators=100)
            model.fit(X_train, y_train)
            
            accuracy = accuracy_score(y_test, model.predict(X_test))
            
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("tenant_id", tenant_id)
            mlflow.log_metric("accuracy", accuracy)
            mlflow.sklearn.log_model(model, "model")
            
            return {"run_id": mlflow.active_run().info.run_id, "accuracy": accuracy}