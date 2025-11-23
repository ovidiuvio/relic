.PHONY: help up down logs logs-backend logs-frontend logs-nginx stop restart build rebuild clean test db-init shell-backend shell-frontend

help:
	@echo "Relic Development Commands (Container-based)"
	@echo "=================================================="
	@echo "Quick Start:"
	@echo "  make up            - Start all containers (nginx, backend, frontend, PostgreSQL, MinIO)"
	@echo "  make down          - Stop all containers"
	@echo ""
	@echo "Development:"
	@echo "  make logs          - View logs from all containers"
	@echo "  make logs-backend  - View backend logs only"
	@echo "  make logs-frontend - View frontend logs only"
	@echo "  make logs-nginx    - View nginx logs only"
	@echo "  make restart       - Restart all containers"
	@echo "  make rebuild       - Rebuild images and start containers"
	@echo ""
	@echo "Debugging & Shells:"
	@echo "  make shell-backend - Open shell in backend container"
	@echo "  make shell-frontend - Open shell in frontend container"
	@echo "  make db-init       - Initialize database"
	@echo ""
	@echo "Maintenance:"
	@echo "  make build         - Build images without starting containers"
	@echo "  make clean         - Stop containers and clean up volumes"
	@echo "  make test          - Run tests in backend container"
	@echo ""
	@echo "Service URLs:"
	@echo "  Frontend:  http://localhost"
	@echo "  Backend:   http://localhost/api"
	@echo "  API Docs:  http://localhost/api/docs"
	@echo "  MinIO:     http://localhost:9001"
	@echo "  Database:  localhost:5432"

# Start all containers in development mode
up:
	@echo "Starting Relic services..."
	docker compose up -d
	@echo ""
	@echo "✓ Services started!"
	@echo ""
	@echo "Service URLs:"
	@echo "  Frontend:  http://localhost"
	@echo "  Backend:   http://localhost/api"
	@echo "  API Docs:  http://localhost/api/docs"
	@echo "  MinIO:     http://localhost:9001 (minioadmin/minioadmin)"
	@echo ""
	@echo "View logs with: make logs"

# Stop all containers
down:
	@echo "Stopping Relic services..."
	docker compose down
	@echo "✓ Services stopped"

# View logs from all containers
logs:
	docker compose logs -f

# View backend logs only
logs-backend:
	docker compose logs -f backend

# View frontend logs only
logs-frontend:
	docker compose logs -f frontend

# View nginx logs only
logs-nginx:
	docker compose logs -f nginx

# Restart all containers
restart: down up

# Build images without starting
build:
	@echo "Building Docker images..."
	docker compose build
	@echo "✓ Images built"

# Rebuild images and start containers
rebuild: build up

# Open shell in backend container
shell-backend:
	docker compose exec backend /bin/bash

# Open shell in frontend container
shell-frontend:
	docker compose exec frontend /bin/sh

# Initialize database
db-init:
	@echo "Initializing database..."
	docker compose exec backend python -c "from backend.database import init_db; init_db()"
	@echo "✓ Database initialized"

# Run tests in backend container
test:
	docker compose exec backend pytest -v

# Clean up volumes and stopped containers
clean:
	@echo "Cleaning up..."
	docker compose down -v
	@echo "✓ Containers and volumes removed"
	@echo ""
	@echo "Note: Use 'make up' to start fresh"

# Old commands (kept for backwards compatibility but no longer used)
.PHONY: venv install dev backend frontend docker-up docker-down stop
venv install dev backend frontend docker-up docker-down stop:
	@echo "This command is no longer used in the container-based setup."
	@echo "Use 'make help' for available commands."
