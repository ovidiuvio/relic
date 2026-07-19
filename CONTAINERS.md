# Container-Based Development Setup

Relic runs entirely in Docker containers for development, making it easy to start, stop, and manage all services.

## Quick Start

```bash
# Start all services (nginx, backend, frontend, database, storage)
make dev-up

# View logs
make dev-logs

# Stop all services
make dev-down
```

## Services

All services run in Docker containers and communicate via a shared network:

| Service | Port | Container Name | Purpose |
|---------|------|-----------------|---------|
| **Nginx** | 80 | Relic-nginx | Reverse proxy & API gateway |
| **Frontend** | 5173 | Relic-frontend | Svelte dev server (internal) |
| **Backend** | 8000 | Relic-backend | FastAPI server (internal) |
| **PostgreSQL** | 5432 | Relic-postgres | Main database |
| **MinIO** | 9000/9001 | Relic-minio | S3-compatible file storage |

## Available Commands

### Quick Start
```bash
make dev-up              # Start all containers
make dev-down            # Stop all containers
make dev-restart         # Restart all containers
```

### Development
```bash
make dev-logs            # View logs from all containers
make dev-logs-backend    # View backend logs only
make dev-logs-frontend   # View frontend logs only
make dev-logs-nginx      # View nginx logs only
make dev-rebuild         # Rebuild images and start fresh
```

### Debugging
```bash
make dev-shell-backend   # Open bash shell in backend container
make dev-shell-frontend  # Open shell in frontend container
make db-init             # Initialize database
make dev-test            # Run tests in backend container
```

### Maintenance
```bash
make dev-build           # Build images without starting
make clean               # Stop and remove all containers/volumes
make backup-now          # Trigger manual database backup
```

## Service URLs

Once running, access services at:

- **Frontend**: http://localhost
- **Backend API**: http://localhost/api
- **API Docs**: http://localhost/api/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## Development Workflow

### 1. Start Development
```bash
make dev-up
make dev-logs  # In another terminal to watch logs
```

### 2. Make Code Changes
- Backend changes in `backend/` are automatically reflected (hot reload)
- Frontend changes in `frontend/src/` are automatically reflected (HMR)
- No need to rebuild or restart containers!

### 3. Stop Development
```bash
make dev-down
```

## Mount Paths

Code directories are mounted into containers for live development:

- `./backend/` → `/app/backend` (Backend source code)
- `./frontend/` → `/app` (Frontend source code)
- `requirements.txt` → `/app/requirements.txt` (Python dependencies, read-only)
- `package-lock.json` → `/app/package-lock.json` (Node dependencies, read-only)
- `minio_data` volume → MinIO storage
- `postgres_data` volume → PostgreSQL data

## Debugging

### View Container Logs
```bash
# All containers
make dev-logs

# Specific service
make dev-logs-backend
make dev-logs-frontend
make dev-logs-nginx

# With docker command
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f frontend
```

### Access Container Shell
```bash
# Backend (Python)
make dev-shell-backend
pytest
exit

# Frontend (Node)
make dev-shell-frontend
npm run build
exit
```

### Connect to Database
```bash
# From host machine (if port exposed)
psql -h localhost -U relic_user -d relic_db

# Or from backend container
docker compose -f docker-compose.dev.yml exec backend psql -h postgres -U relic_user -d relic_db
```

## Troubleshooting

### Port Already in Use
If port 80 is in use, you might need to stop other web servers or change the port mapping in `docker-compose.dev.yml` for the nginx service.

### Database Connection Issues
Wait for PostgreSQL to be healthy before running operations:
```bash
docker compose -f docker-compose.dev.yml logs postgres  # Check if it's ready
make db-init                                             # Initialize database
```

### Container Won't Start
Check the logs and rebuild:
```bash
make dev-logs
make clean          # Remove everything
make dev-rebuild    # Start fresh
```

### Frontend Not Updating
The frontend container uses volumes for live updates. If changes aren't reflected:

1. Check if the file was saved
2. Verify the volume is mounted:
   ```bash
   docker compose -f docker-compose.dev.yml exec frontend mount | grep /app
   ```
3. Restart the frontend:
   ```bash
   docker compose -f docker-compose.dev.yml restart frontend
   ```

## Environment Variables

Environment variables are set in `docker-compose.dev.yml` and `docker-compose.prod.yml`. To customize:

1. Edit the relevant compose file
2. Restart containers: `make dev-restart` or `make down && make up`

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `S3_ENDPOINT_URL`: S3-compatible storage endpoint
- `S3_BUCKET_NAME`: Storage bucket name
- `DEBUG`: Enable debug mode
- `ALLOWED_ORIGINS`: CORS allowed origins
- `BACKUP_ENABLED`: Enable automated backups

## Network Communication

All services communicate via the `Relic` Docker network:

- Nginx routes traffic to `backend:8000` and `frontend:5173`
- Backend connects to: `postgres:5432`, `minio:9000`
- Frontend connects to: Backend via Nginx at `http://localhost/api`
- From host: Use `localhost` (port 80)

## Building for Production

To create production images:

```bash
make up              # Start production services
make build           # Build production images

# Or directly with docker compose
docker compose -f docker-compose.prod.yml up -d --build
```
