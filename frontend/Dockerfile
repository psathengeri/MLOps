FROM python:3.9-slim
WORKDIR /app
RUN pip install streamlit requests pandas plotly
COPY . .
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
