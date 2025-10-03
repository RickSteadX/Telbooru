#!/bin/bash
set -e

# Create necessary directories with proper permissions
echo "Creating data and logs directories..."
mkdir -p /app/data /app/logs /app/user_data
chown -R app:app /app/data /app/logs /app/user_data

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis is ready!"

# Run the application
echo "Starting Telbooru Telegram Bot..."
exec "$@"