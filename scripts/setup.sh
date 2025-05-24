#!/bin/bash

echo "🏢 Setting up Multi-Tenant MLOps Platform..."

# Create directories
mkdir -p tenants_data database gateway frontend mlflow

# Create database init script
cat > database/init.sql << 'EOF'
-- Initialize multi-tenant database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a function to initialize tenant schema
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', tenant_name);
    -- Add any tenant-specific tables here
END;
$$ LANGUAGE plpgsql;
EOF

# # Create Dockerfiles 
# cat > gateway/Dockerfile << 'EOF'
# FROM python:3.9-slim
# WORKDIR /app
# RUN pip install fastapi uvicorn mlflow psycopg2-binary pandas
# COPY . .
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# EOF

# cat > frontend/Dockerfile << 'EOF'
# FROM python:3.9-slim
# WORKDIR /app
# RUN pip install streamlit requests pandas plotly
# COPY . .
# CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
# EOF

# cat > mlflow/Dockerfile << 'EOF'
# FROM python:3.9-slim
# RUN pip install mlflow psycopg2-binary
# WORKDIR /mlflow
# CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
# EOF 

echo "🐳 Starting services..."
docker compose up -d

echo "⏳ Waiting for services to start..."
sleep 30

echo "✅ Multi-Tenant MLOps Platform is ready!"
echo ""
echo "🌐 Frontend: http://localhost:8501"
echo "🔧 Gateway API: http://localhost:8000"
echo "📊 MLflow UI: http://localhost:5000"
echo ""
echo "🏢 Create your first tenant in the frontend!"