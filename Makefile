.PHONY: help build run stop clean test

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

ps: ## list containers
	docker compose ps

logs: ## View logs
	docker compose logs -f api

logs-db: ## View database logs
	docker compose logs -f postgres

restart: ## Restart API service
	docker compose restart api

clean: ## Remove containers and volumes
	docker compose down -v

psql: ## Connect to PostgreSQL
	docker compose exec postgres psql -U postgres_user -d pg_db

db-seed:
	psql -U postgres -d pg_db -f migrations/002_seed_data.sql

test: ## Run tests
	go test -v ./...

.DEFAULT_GOAL := help
