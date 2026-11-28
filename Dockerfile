FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install ca-certificates and tzdata for TLS validation and timezone support
RUN apk add --no-cache ca-certificates tzdata

# Copy project files (preserving zero-external-pip-dependency architecture)
COPY daily_news.py config.json ./

# Ensure digests directory exists
RUN mkdir -p digests

# Set default entrypoint/command
ENTRYPOINT ["python", "daily_news.py"]
CMD []
