FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY test_vercel_relay.py .
CMD ["python", "test_vercel_relay.py"]
