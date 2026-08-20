FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY test_beaman_auth.py .

CMD ["python", "test_beaman_auth.py"]
