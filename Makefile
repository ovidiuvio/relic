.PHONY: help up down logs build rebuild clean dev-up dev-down dev-logs dev-logs-backend dev-logs-frontend dev-logs-nginx dev-restart dev-build dev-rebuild dev-shell-backend dev-shell-frontend dev-test db-init backup-now backup-list backup-cleanup backup-status k8s-bootstrap k8s-deploy k8s-deploy-seeded k8s-demo k8s-list-demos k8s-teardown k8s-teardown-clean k8s-teardown-all-demos k8s-status k8s-shell k8s-logs k8s-test k8s-seed k8s-cluster-delete

# Docker Compose files
COMPOSE_DEV := docker-compose.dev.yml
COMPOSE_PROD := docker-compose.prod.yml

# Kubernetes / k3d settings
K8S_DIR     := k8s
K8S_ENV     ?= demo-$(shell cat /dev/urandom | tr -dc 'a-z0-9' | head -c 6)
K8S_VERSION ?= latest
K8S_SEED    ?= demo

# Read domain from cluster secrets if not explicitly set
_CF_SECRETS := $(K8S_DIR)/.cluster-secrets.env
K8S_DOMAIN  ?= $(shell [ -f $(_CF_SECRETS) ] && grep '^DOMAIN=' $(_CF_SECRETS) | cut -d= -f2 || echo relic.example.com)

help:
	@echo "Relic Commands"
	@echo "=============================================="
	@echo "Kubernetes / k3d:"
	@echo "  make k8s-bootstrap              - Create cluster and install shared infra"
	@echo "  make k8s-deploy K8S_ENV=testing - Deploy (or update) a static environment"
	@echo "  make k8s-demo K8S_ENV=demo-acme - Create on-demand demo (seeded, auto DNS)"
	@echo "  make k8s-list-demos             - List all running demo environments"
	@echo "  make k8s-teardown K8S_ENV=...   - Remove a static environment (keep data)"
	@echo "  make k8s-teardown-clean K8S_ENV=... - Remove any environment + destroy data"
	@echo "  make k8s-teardown-all-demos     - Remove all dynamic environments + data"
	@echo "  make k8s-status                 - Show all running environments"
	@echo "  make k8s-logs K8S_ENV=testing   - Stream backend logs"
	@echo "  make k8s-shell K8S_ENV=testing  - Open shell in backend pod"
	@echo "  make k8s-test K8S_ENV=testing   - Run integration tests against env"
	@echo "  make k8s-seed K8S_ENV=demo-acme K8S_SEED=demo  - Re-seed an environment"
	@echo "  make k8s-cluster-delete         - Destroy the entire cluster (DESTRUCTIVE)"
	@echo ""
	@echo "  Options: K8S_DOMAIN, K8S_VERSION, K8S_ENV, K8S_SEED"
	@echo "  Demo examples:"
	@echo "    make k8s-demo K8S_ENV=demo-acme"
	@echo "    make k8s-demo K8S_ENV=demo-acme K8S_VERSION=v1.2.3 K8S_SEED=demo"
	@echo "    make k8s-teardown-clean K8S_ENV=demo-acme"
	@echo ""
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

# ===== Kubernetes / k3d Commands =====

# Bootstrap the k3d cluster and shared infrastructure (one-time, idempotent)
# Usage: make k8s-bootstrap CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_ZONE_ID=... GITHUB_RUNNER_TOKEN=ghp_... K8S_DOMAIN=relic.example.com
k8s-bootstrap:
	@echo "Bootstrapping k3d cluster..."
	@$(K8S_DIR)/scripts/bootstrap.sh \
	  --domain $(K8S_DOMAIN) \
	  $(if $(CLOUDFLARE_API_TOKEN),--cloudflare-token $(CLOUDFLARE_API_TOKEN),) \
	  $(if $(CLOUDFLARE_ACCOUNT_ID),--cloudflare-account-id $(CLOUDFLARE_ACCOUNT_ID),) \
	  $(if $(CLOUDFLARE_ZONE_ID),--cloudflare-zone-id $(CLOUDFLARE_ZONE_ID),) \
	  $(if $(GITHUB_RUNNER_TOKEN),--github-token $(GITHUB_RUNNER_TOKEN),)

# Deploy or update a named environment
# Usage: make k8s-deploy K8S_ENV=testing K8S_VERSION=latest K8S_DOMAIN=relic.example.com
k8s-deploy:
	@echo "Deploying environment '$(K8S_ENV)' version '$(K8S_VERSION)'..."
	@$(K8S_DIR)/scripts/provision-env.sh \
	  --env $(K8S_ENV) \
	  --version $(K8S_VERSION) \
	  --domain $(K8S_DOMAIN)

# Deploy with seed data
# Usage: make k8s-deploy-seeded K8S_ENV=demo K8S_SEED=demo
k8s-deploy-seeded:
	@$(K8S_DIR)/scripts/provision-env.sh \
	  --env $(K8S_ENV) \
	  --version $(K8S_VERSION) \
	  --domain $(K8S_DOMAIN) \
	  --seed $(K8S_SEED)

# Tear down environment (keeps database and bucket)
# Usage: make k8s-teardown K8S_ENV=testing
k8s-teardown:
	@$(K8S_DIR)/scripts/teardown-env.sh \
	  --env $(K8S_ENV) \
	  --domain $(K8S_DOMAIN)

# Tear down environment and destroy all data
# Usage: make k8s-teardown-clean K8S_ENV=pr-42
k8s-teardown-clean:
	@$(K8S_DIR)/scripts/teardown-env.sh \
	  --env $(K8S_ENV) \
	  --domain $(K8S_DOMAIN) \
	  --destroy-data

# Show status of all running environments
k8s-status:
	@echo "k3d cluster:"
	@k3d cluster list 2>/dev/null || echo "  (no cluster)"
	@echo ""
	@echo "Shared services (namespace: shared):"
	@kubectl get pods -n shared --no-headers 2>/dev/null | awk '{printf "  %-45s %s\n", $$1, $$3}' || echo "  (cluster not running)"
	@echo ""
	@echo "Environments:"
	@for ns in $$(kubectl get ns -o name 2>/dev/null | grep "^namespace/relic-" | sed 's|namespace/||'); do \
	  echo "  $$ns:"; \
	  kubectl get pods -n $$ns --no-headers 2>/dev/null | awk '{printf "    %-40s %s\n", $$1, $$3}'; \
	done

# Stream backend logs for an environment
# Usage: make k8s-logs K8S_ENV=testing
k8s-logs:
	kubectl logs -n relic-$(K8S_ENV) -l app=backend -f --max-log-requests 5

# Open shell in backend pod
# Usage: make k8s-shell K8S_ENV=testing
k8s-shell:
	kubectl exec -it -n relic-$(K8S_ENV) \
	  $$(kubectl get pod -n relic-$(K8S_ENV) -l app=backend -o name | head -1) \
	  -- /bin/bash

# Run integration tests against a k8s environment
# Usage: make k8s-test K8S_ENV=testing
k8s-test:
	@echo "Running integration tests against https://$(K8S_ENV).$(K8S_DOMAIN)"
	RELIC_BASE_URL=https://$(K8S_ENV).$(K8S_DOMAIN) \
	  python -m pytest tests/ --ignore=tests/test_utils.py -v

# Create an on-demand demo environment with seed data
# Usage: make k8s-demo K8S_ENV=demo-acme
#        make k8s-demo K8S_ENV=demo-acme K8S_VERSION=v1.2.3 K8S_SEED=demo
k8s-demo:
	@$(K8S_DIR)/scripts/provision-env.sh \
	  --env $(K8S_ENV) \
	  --version $(K8S_VERSION) \
	  --domain $(K8S_DOMAIN) \
	  --seed $(K8S_SEED)

# Delete all dynamic (non-static) environments and their data
k8s-teardown-all-demos:
	@kubectl get ns -o name 2>/dev/null \
	  | grep "^namespace/relic-" \
	  | sed 's|namespace/relic-||' \
	  | grep -v "^testing$$\|^dev$$\|^demo$$" \
	  | while read env; do \
	      echo "Tearing down $$env..."; \
	      $(K8S_DIR)/scripts/teardown-env.sh --env "$$env" --domain $(K8S_DOMAIN) --destroy-data; \
	    done

# List all running demo environments
k8s-list-demos:
	@echo "Running demo environments:"
	@kubectl get ns -o name 2>/dev/null \
	  | grep "^namespace/relic-" \
	  | sed 's|namespace/relic-||' \
	  | grep -v "^testing$$\|^dev$$\|^demo$$" \
	  | while read env; do \
	      age=$$(kubectl get ns "relic-$$env" -o jsonpath='{.metadata.creationTimestamp}' 2>/dev/null); \
	      pods=$$(kubectl get pods -n "relic-$$env" --no-headers 2>/dev/null | awk '{print $$1" "$$3}' | tr '\n' '  '); \
	      printf "  %-30s created: %s\n    pods: %s\n" "$$env.$(K8S_DOMAIN)" "$$age" "$$pods"; \
	    done \
	  || echo "  (none)"

# Seed an environment with data
# Usage: make k8s-seed K8S_ENV=demo K8S_SEED=demo
k8s-seed:
	@$(K8S_DIR)/scripts/provision-env.sh \
	  --env $(K8S_ENV) \
	  --domain $(K8S_DOMAIN) \
	  --seed $(K8S_SEED) \
	  --seed-only

# Destroy the entire k3d cluster (IRREVERSIBLE — loses all data)
k8s-cluster-delete:
	@echo "WARNING: This destroys the entire k3d cluster and ALL environment data."
	@read -p "Type 'yes' to confirm: " confirm; \
	[ "$$confirm" = "yes" ] && k3d cluster delete relic || echo "Aborted."

