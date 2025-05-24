FROM python:3.9-slim
WORKDIR /app
RUN pip install fastapi uvicorn mlflow psycopg2-binary pandas
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
