# Telbooru Discord Bot Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Production stage
FROM base as production
USER app
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "main_refactored.py"]

# Development stage
FROM base as development
USER app
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "main_refactored.py"]