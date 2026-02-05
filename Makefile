.PHONY: help build up down logs test clean restart dev prod

# Capture git info for build metadata
export GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "local")
export GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
export BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

help: ## Show this help message
	@echo "Notetime Docker Commands"
	@echo ""
	@echo "Build info: $(GIT_BRANCH) @ $(GIT_COMMIT)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	@echo "Building with: $(GIT_BRANCH) @ $(GIT_COMMIT)"
	docker-compose build

up: ## Start services in detached mode
	docker-compose up -d

down: ## Stop and remove services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

test: ## Run Docker build tests
	./test-docker.sh

clean: ## Remove all containers, volumes, and images
	docker-compose down -v
	docker rmi notetime:latest 2>/dev/null || true
	docker rmi notetime:test 2>/dev/null || true

restart: down up ## Restart services

dev: ## Start services in development mode
	docker-compose up --build

prod: ## Start services in production mode
	docker-compose -f docker-compose.prod.yml up -d --build

db-shell: ## Access PostgreSQL shell
	docker-compose exec db psql -U notetime -d notetime

db-backup: ## Backup database to backup.sql
	docker-compose exec db pg_dump -U notetime notetime > backup.sql
	@echo "Database backed up to backup.sql"

db-restore: ## Restore database from backup.sql
	@if [ ! -f backup.sql ]; then echo "backup.sql not found"; exit 1; fi
	docker-compose exec -T db psql -U notetime notetime < backup.sql
	@echo "Database restored from backup.sql"

stats: ## Show container resource usage
	docker stats notetime-app notetime-db

shell: ## Access application container shell
	docker-compose exec web /bin/bash

lint-docker: ## Lint Dockerfile with hadolint
	docker run --rm -i hadolint/hadolint < Dockerfile
