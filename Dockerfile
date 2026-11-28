FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install ca-certificates and tzdata for TLS validation and timezone support
RUN apk add --no-cache ca-certificates tzdata

# Copy project files (preserving zero-external-pip-dependency architecture)
# Copies daily_news.py and configuration files; falls back to config.example.json if config.json is not present
COPY daily_news.py config*.json ./
RUN if [ ! -f config.json ] && [ -f config.example.json ]; then cp config.example.json config.json; fi

# Ensure digests directory exists
RUN mkdir -p digests

# Expose digest web viewer port (custom non-standard port 58619)
EXPOSE 58619

# Set default entrypoint/command
ENTRYPOINT ["python", "daily_news.py"]
CMD []
