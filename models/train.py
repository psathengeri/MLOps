import mlflow
import mlflow.sklearn
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import os

# Set MLflow tracking and registry URIs
mlflow.set_tracking_uri("http://localhost:5001")
mlflow.set_experiment("default")
mlflow.set_registry_uri("file:/Users/rocketman_1/Developer/MLOPs/MLOps/mlruns")

# Create artifacts directory (optional, for local runs)
os.makedirs("mlruns", exist_ok=True)

def train_model():
    with mlflow.start_run():
        # Generate sample data
        X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        n_estimators = 100
        max_depth = 5
        
        rf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
        rf.fit(X_train, y_train)
        
        # Predictions
        y_pred = rf.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Log parameters and metrics
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_metric("accuracy", accuracy)
        
        # Log model
        mlflow.sklearn.log_model(rf, "model")
        
        print(f"Model trained with accuracy: {accuracy:.4f}")
        print(f"Run ID: {mlflow.active_run().info.run_id}")

if __name__ == "__main__":
    train_model()
