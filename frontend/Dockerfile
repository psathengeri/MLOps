FROM python:3.9-slim
WORKDIR /app

# Install system dependencies required for bcrypt and MLflow
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
