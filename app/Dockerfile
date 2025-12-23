FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8501

CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --reload & streamlit run /app/streamlit_app.py --server.address 0.0.0.0 --server.port 8501"]
