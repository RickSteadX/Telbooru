#!/bin/bash
set -e

# Wait for Redis to be ready
if [ "$WAIT_FOR_REDIS" = "true" ]; then
    echo "Waiting for Redis..."
    while ! nc -z redis 6379; do
      sleep 0.1
    done
    echo "Redis is ready!"
fi

# Create necessary directories
mkdir -p /app/data /app/logs

# Run the application
exec "$@"