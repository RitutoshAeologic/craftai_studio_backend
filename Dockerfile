FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for OpenCV, Rembg, ONNX Runtime, and media handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure storage directories exist for local media persistence
RUN mkdir -p storage/generations

# Environment variables
ENV PYTHONPATH=.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# WebSocket generation streaming ping intervals (300s) to keep long inference connections alive
CMD ["sh", "-c", "WORKERS=${WEB_WORKERS:-1}; PORT=${PORT:-8000}; uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers $WORKERS --ws-ping-interval 300 --ws-ping-timeout 300"]
