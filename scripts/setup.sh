#!/bin/bash

echo "🚀 Setting up Veroxe MLOps Platform..."

# Create directories
mkdir -p mlflow_data notebooks data

# Create MLflow Dockerfile
cat > mlflow/Dockerfile << EOF
FROM python:3.9-slim
RUN pip install mlflow psutil
WORKDIR /mlflow
EOF

# Create Streamlit Dockerfile
cat > streamlit/Dockerfile << EOF
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
WORKDIR /app
EOF

# Create Streamlit requirements
cat > streamlit/requirements.txt << EOF
streamlit
mlflow
pandas
plotly
numpy
EOF

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

echo "✅ Setup complete!"
echo "📊 MLflow UI: http://localhost:5000"
echo "🎯 Streamlit Dashboard: http://localhost:8501"
echo "📓 Jupyter: http://localhost:8888"
echo ""
echo "🚀 Train your first model:"
echo "python models/train.py"
