# Docker Configuration for Telbooru Discord Bot

This directory contains Docker configuration for running the Telbooru Discord bot in containerized environments.

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your Discord token
nano .env
```

### 2. Basic Usage

```bash
# Build and run the bot
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f telbooru-bot

# Stop services
docker-compose down
```

### 3. Development Mode

```bash
# Run with live code reloading
docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

# Run in background
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

## Services

### telbooru-bot
- **Description**: Main Discord bot service
- **Image**: Custom Python 3.11 image
- **Environment**: Uses `.env` file
- **Volumes**: 
  - `./data:/app/data` - Persistent data
  - `./logs:/app/logs` - Log files
- **Depends on**: Redis

### redis
- **Description**: In-memory data store for caching
- **Image**: redis:7-alpine
- **Volumes**: `redis_data:/data` - Persistent Redis data
- **Ports**: Internal only (6379)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Your Discord bot token | **Required** |
| `BOORU_API_KEY` | Optional Booru API key | - |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_SEARCH_RESULTS` | Max images per search | `10` |
| `RATING_FILTER` | Default rating filter | `safe` |

### Volume Mounts

- `./data`: Bot data (settings, cache)
- `./logs`: Application logs
- `./.env`: Environment configuration

## Commands

### Basic Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f telbooru-bot

# View all logs
docker-compose logs -f
```

### Development Commands

```bash
# Build with no cache
docker-compose build --no-cache

# Run specific service
docker-compose run --rm telbooru-bot bash

# Execute commands in running container
docker-compose exec telbooru-bot python -c "print('Hello from container')"
```

### Maintenance Commands

```bash
# Clean up containers
docker-compose down -v --remove-orphans

# Clean up images
docker image prune -f

# View container stats
docker stats

# Access Redis CLI
docker-compose exec redis redis-cli
```

## Production Deployment

### Using Docker Compose in Production

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x docker-entrypoint.sh
   ```

2. **Build Failures**
   ```bash
   # Clear build cache
   docker builder prune -f
   docker-compose build --no-cache
   ```

3. **Redis Connection Issues**
   ```bash
   # Check Redis status
   docker-compose exec redis redis-cli ping
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up --build

# Interactive debugging
docker-compose run --rm telbooru-bot bash
```

## Monitoring

### Log Aggregation

```bash
# View all logs
docker-compose logs -f

# Filter by service
docker-compose logs -f telbooru-bot

# Search logs
docker-compose logs telbooru-bot | grep "search_query"
```

## Security Best Practices

1. **Never commit `.env` file**
2. **Use non-root user in containers**
3. **Regular security updates**
4. **Use secrets management for production**

## Backup and Recovery

### Data Backup

```bash
# Backup Redis data
docker run --rm -v telbooru_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz /data

# Backup application data
docker run --rm -v $(pwd)/data:/data -v $(pwd):/backup alpine tar czf /backup/data_backup.tar.gz /data
```

### Recovery

```bash
# Restore Redis data
docker run --rm -v telbooru_redis_data:/data -v $(pwd):/backup alpine tar xzf /backup/redis_backup.tar.gz -C /

# Restore application data
docker run --rm -v $(pwd)/data:/data -v $(pwd):/backup alpine tar xzf /backup/data_backup.tar.gz -C /
```