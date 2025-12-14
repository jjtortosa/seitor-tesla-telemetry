FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_telemetry.py .

ENTRYPOINT ["python", "mock_telemetry.py"]
CMD ["--scenario", "driving", "--continuous"]
