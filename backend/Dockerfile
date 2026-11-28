FROM python:3.11-alpine

WORKDIR /app

# Install ca-certificates and tzdata for TLS validation and timezone support
RUN apk add --no-cache ca-certificates tzdata

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Jakarta

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend application code and configurations
COPY backend /app/backend
COPY config*.json /app/
RUN if [ ! -f /app/config.json ] && [ -f /app/config.example.json ]; then cp /app/config.example.json /app/config.json; fi

# Create directories for persistent SQLite database and markdown digests
RUN mkdir -p /app/data /app/digests

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
