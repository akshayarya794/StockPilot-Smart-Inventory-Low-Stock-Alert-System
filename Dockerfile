# ==============================================================================
# StockPilot — Production Container Definition (Section 7.1)
# ==============================================================================
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Set non-buffering and container database path
ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/app/data/stockpilot.db \
    PORT=5000 \
    IS_DOCKER=true

# Create persistent storage mount directory for SQLite volume
RUN mkdir -p /app/data

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY app/ ./app/
COPY scripts/ ./scripts/

# Expose internal ASGI server port
EXPOSE 5000

# Native Docker Healthcheck (polling /health endpoint every 10s)
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()" || exit 1

# Production ASGI server entry point
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
