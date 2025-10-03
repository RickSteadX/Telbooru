.PHONY: help build up down logs clean dev prod shell

help: ## Show this help
	@echo "Telbooru Docker Commands"
	@echo "======================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start services in background
	docker-compose up -d

down: ## Stop services
	docker-compose down

restart: ## Restart services
	docker-compose restart

logs: ## View logs
	docker-compose logs -f

clean: ## Clean up containers and images
	docker-compose down -v --remove-orphans
	docker system prune -f

dev: ## Run in development mode
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

prod: ## Run in production mode
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

shell: ## Open shell in bot container
	docker-compose exec telbooru-bot bash

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

status: ## Show service status
	docker-compose ps

test: ## Run tests in container
	docker-compose run --rm telbooru-bot python -m pytest

lint: ## Run linting
	docker-compose run --rm telbooru-bot black --check .
	docker-compose run --rm telbooru-bot flake8 .

format: ## Format code
	docker-compose run --rm telbooru-bot black .