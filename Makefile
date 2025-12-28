.PHONY: help up down logs build rebuild clean dev-up dev-down dev-logs dev-logs-backend dev-logs-frontend dev-logs-nginx dev-restart dev-build dev-rebuild dev-shell-backend dev-shell-frontend dev-test db-init backup-now backup-list backup-cleanup backup-status

# Docker Compose files
COMPOSE_DEV := docker-compose.dev.yml
COMPOSE_PROD := docker-compose.prod.yml

help:
	@echo "Relic Commands"
	@echo "=============================================="
	@echo "Production (Default):"
	@echo "  make up            - Start production services"
	@echo "  make down          - Stop production services"
	@echo "  make logs          - View production logs"
	@echo "  make build         - Build production images"
	@echo "  make rebuild       - Rebuild and restart production"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up        - Start dev services (with hot-reload)"
	@echo "  make dev-down      - Stop dev services"
	@echo "  make dev-logs      - View dev logs"
	@echo "  make dev-logs-backend   - View backend logs only"
	@echo "  make dev-logs-frontend  - View frontend logs only"
	@echo "  make dev-logs-nginx     - View nginx logs only"
	@echo "  make dev-restart        - Restart dev services"
	@echo "  make dev-build          - Build dev images"
	@echo "  make dev-rebuild        - Rebuild and restart dev"
	@echo "  make dev-shell-backend  - Open shell in backend container"
	@echo "  make dev-shell-frontend - Open shell in frontend container"
	@echo "  make dev-test           - Run tests in backend container"
	@echo ""
	@echo "Database & Maintenance:"
	@echo "  make db-init            - Initialize database"
	@echo "  make clean              - Clean production environment"
	@echo "  make backup-now         - Trigger manual database backup"
	@echo "  make backup-list        - List all database backups"
	@echo "  make backup-cleanup     - Run retention policy cleanup"
	@echo "  make backup-status      - Show backup system status"
	@echo ""
	@echo "Service URLs:"
	@echo "  Application: http://localhost"
	@echo "  MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"

# ===== Production Commands (Default) =====

# Start production services
up:
	@echo "Starting Relic services in production mode..."
	@echo "⚠️  Make sure you have reviewed environment variables in docker-compose.prod.yml"
	docker compose -f $(COMPOSE_PROD) up -d --build
	@echo ""
	@echo "✓ Production services started!"
	@echo ""
	@echo "Service URLs:"
	@echo "  Application: http://localhost"
	@echo "  MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
	@echo ""
	@echo "View logs with: make logs"

# Stop production services
down:
	@echo "Stopping production services..."
	docker compose -f $(COMPOSE_PROD) down
	@echo "✓ Production services stopped"

# View production logs
logs:
	docker compose -f $(COMPOSE_PROD) logs -f

# Build production images
build:
	@echo "Building production Docker images..."
	docker compose -f $(COMPOSE_PROD) build
	@echo "✓ Production images built"

# Rebuild and restart production
rebuild: build up

# Clean production environment (WARNING: removes data)
clean:
	@echo "⚠️  WARNING: This will remove all production data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f $(COMPOSE_PROD) down -v; \
		echo "✓ Production containers and volumes removed"; \
	else \
		echo "Cancelled"; \
	fi

# ===== Development Commands =====

# Start development services
dev-up:
	@echo "Starting Relic services in development mode..."
	GIT_HASH=$$(git rev-parse --short HEAD 2>/dev/null || echo "dev") docker compose -f $(COMPOSE_DEV) up -d --build
	@echo ""
	@echo "✓ Development services started!"
	@echo ""
	@echo "Service URLs:"
	@echo "  Frontend:  http://localhost (with hot-reload)"
	@echo "  Backend:   http://localhost/api (with auto-reload)"
	@echo "  API Docs:  http://localhost/api/docs"
	@echo "  MinIO:     http://localhost:9001 (minioadmin/minioadmin)"
	@echo ""
	@echo "View logs with: make dev-logs"

# Stop development services
dev-down:
	@echo "Stopping development services..."
	docker compose -f $(COMPOSE_DEV) down
	@echo "✓ Development services stopped"

# View development logs
dev-logs:
	docker compose -f $(COMPOSE_DEV) logs -f

# View backend logs only
dev-logs-backend:
	docker compose -f $(COMPOSE_DEV) logs -f backend

# View frontend logs only
dev-logs-frontend:
	docker compose -f $(COMPOSE_DEV) logs -f frontend

# View nginx logs only
dev-logs-nginx:
	docker compose -f $(COMPOSE_DEV) logs -f nginx

# Restart development services
dev-restart: dev-down dev-up

# Build development images
dev-build:
	@echo "Building development Docker images..."
	GIT_HASH=$$(git rev-parse --short HEAD 2>/dev/null || echo "dev") docker compose -f $(COMPOSE_DEV) build
	@echo "✓ Development images built"

# Rebuild and restart development
dev-rebuild: dev-build dev-up

# Open shell in backend container
dev-shell-backend:
	docker compose -f $(COMPOSE_DEV) exec backend /bin/bash

# Open shell in frontend container
dev-shell-frontend:
	docker compose -f $(COMPOSE_DEV) exec frontend /bin/sh

# Run tests in backend container
dev-test:
	docker compose -f $(COMPOSE_DEV) exec backend pytest -v

# ===== Database Commands =====

# Initialize database (works with both dev and prod)
db-init:
	@echo "Initializing database..."
	@if docker compose -f $(COMPOSE_PROD) ps | grep -q Relic-backend; then \
		docker compose -f $(COMPOSE_PROD) exec backend python -c "from backend.database import init_db; init_db()"; \
	elif docker compose -f $(COMPOSE_DEV) ps | grep -q Relic-backend; then \
		docker compose -f $(COMPOSE_DEV) exec backend python -c "from backend.database import init_db; init_db()"; \
	else \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi
	@echo "✓ Database initialized"

# Generate a new database migration revision
db-revision:
	@read -p "Enter migration message: " message; \
	COMPOSE_FILE=$$(if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; else echo ""; fi); \
	if [ -z "$$COMPOSE_FILE" ]; then \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi; \
	docker compose -f $$COMPOSE_FILE exec backend bash -c "export PYTHONPATH=/app && alembic -c backend/alembic.ini revision --autogenerate -m \"$$message\""

# Apply database migrations to current head
db-migrate:
	@COMPOSE_FILE=$$(if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; else echo ""; fi); \
	if [ -z "$$COMPOSE_FILE" ]; then \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi; \
	docker compose -f $$COMPOSE_FILE exec backend bash -c "export PYTHONPATH=/app && alembic -c backend/alembic.ini upgrade head"

# ===== Database Backup Commands =====

# Helper to get compose file for running backend
define get_backend_compose
$(shell if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; fi)
endef

# Trigger manual database backup
backup-now:
	@echo "Triggering manual database backup..."
	@COMPOSE_FILE=$$(if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; else echo ""; fi); \
	if [ -z "$$COMPOSE_FILE" ]; then \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi; \
	docker compose -f $$COMPOSE_FILE exec backend python -c "import asyncio; from backend.backup import perform_backup; asyncio.run(perform_backup(backup_type='manual'))"
	@echo "✓ Backup completed"

# List all database backups
backup-list:
	@echo "Listing all database backups..."
	@echo ""
	@COMPOSE_FILE=$$(if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; else echo ""; fi); \
	if [ -z "$$COMPOSE_FILE" ]; then \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi; \
	docker compose -f $$COMPOSE_FILE exec backend python -c "import asyncio; from backend.backup import list_all_backups; backups = asyncio.run(list_all_backups()); sorted_backups = sorted(backups, key=lambda x: x['timestamp'], reverse=True); print(f'Total backups: {len(sorted_backups)}'); print(f'Total size: {sum(b[\"size\"] for b in sorted_backups) / 1024 / 1024:.2f} MB'); print(''); print('Recent backups:'); print('-' * 80); [print(f'{b[\"timestamp\"].strftime(\"%Y-%m-%d %H:%M:%S UTC\"):<25} {b[\"size\"]/1024/1024:>10.2f} MB  {b[\"key\"]}') for b in sorted_backups[:20]]"

# Run backup retention cleanup
backup-cleanup:
	@echo "Running backup retention cleanup..."
	@COMPOSE_FILE=$$(if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; else echo ""; fi); \
	if [ -z "$$COMPOSE_FILE" ]; then \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi; \
	docker compose -f $$COMPOSE_FILE exec backend python -c "import asyncio; from backend.backup import cleanup_old_backups; asyncio.run(cleanup_old_backups())"
	@echo "✓ Cleanup completed"

# Show backup system status
backup-status:
	@echo "Database Backup System Status"
	@echo "=============================="
	@COMPOSE_FILE=$$(if docker compose -f $(COMPOSE_PROD) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_PROD)"; elif docker compose -f $(COMPOSE_DEV) ps 2>/dev/null | grep -q Relic-backend; then echo "$(COMPOSE_DEV)"; else echo ""; fi); \
	if [ -z "$$COMPOSE_FILE" ]; then \
		echo "Error: No backend container running. Start services with 'make up' or 'make dev-up'"; \
		exit 1; \
	fi; \
	docker compose -f $$COMPOSE_FILE exec backend python -c "import asyncio; from backend.backup import list_all_backups; from backend.config import settings; backups = asyncio.run(list_all_backups()); sorted_backups = sorted(backups, key=lambda x: x['timestamp'], reverse=True); print(f'Enabled: {settings.BACKUP_ENABLED}'); print(f'Backup times: {settings.BACKUP_TIMES} ({settings.BACKUP_TIMEZONE})'); print(f'Startup backup: {settings.BACKUP_ON_STARTUP}'); print(f'Shutdown backup: {settings.BACKUP_ON_SHUTDOWN}'); print(f'Retention: {settings.BACKUP_RETENTION_DAYS}d daily, {settings.BACKUP_RETENTION_WEEKS}d weekly, monthly forever'); print(''); print(f'Total backups: {len(sorted_backups)}'); print(f'Total size: {sum(b[\"size\"] for b in sorted_backups) / 1024 / 1024:.2f} MB'); print(f'Last backup: {sorted_backups[0][\"timestamp\"].strftime(\"%Y-%m-%d %H:%M:%S UTC\")} ({sorted_backups[0][\"size\"]/1024/1024:.2f} MB)') if sorted_backups else None"

