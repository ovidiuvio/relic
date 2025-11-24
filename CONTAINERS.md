# Container-Based Development Setup

Relic now runs entirely in Docker containers for development, making it easy to start, stop, and manage all services.

## Quick Start

```bash
# Start all services (backend, frontend, database, storage)
make up

# View logs
make logs

# Stop all services
make down
```

## Services

All services run in Docker containers and communicate via a shared network:

| Service | Port | Container Name | Purpose |
|---------|------|-----------------|---------|
| **Frontend** | 5173 | Relic-frontend | Svelte dev server with HMR |
| **Backend** | 8000 | Relic-backend | FastAPI with auto-reload |
| **PostgreSQL** | 5432 | Relic-postgres | Main database |
| **MinIO** | 9000/9001 | Relic-minio | S3-compatible file storage |

## Available Commands

### Quick Start
```bash
make up              # Start all containers
make down            # Stop all containers
make restart         # Restart all containers
```

### Development
```bash
make logs            # View logs from all containers
make logs-backend    # View backend logs only
make logs-frontend   # View frontend logs only
make rebuild         # Rebuild images and start fresh
```

### Debugging
```bash
make shell-backend   # Open bash shell in backend container
make shell-frontend  # Open shell in frontend container
make db-init         # Initialize database
make test            # Run tests in backend container
```

### Maintenance
```bash
make build           # Build images without starting
make clean           # Stop and remove all containers/volumes
```

## Service URLs

Once running, access services at:

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Database**: localhost:5432

## Development Workflow

### 1. Start Development
```bash
make up
make logs  # In another terminal to watch logs
```

### 2. Make Code Changes
- Backend changes in `backend/` are automatically reflected (hot reload)
- Frontend changes in `frontend/src/` are automatically reflected (HMR)
- No need to rebuild or restart containers!

### 3. Stop Development
```bash
make down
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
make logs

# Specific service
make logs-backend
make logs-frontend

# With docker command
docker compose logs -f backend
docker compose logs -f frontend
```

### Access Container Shell
```bash
# Backend (Python)
make shell-backend
python -m pytest
exit

# Frontend (Node)
make shell-frontend
npm run build
exit
```

### Connect to Database
```bash
# From host machine
psql -h localhost -U relic_user -d relic_db

# Or from backend container
docker compose exec backend psql -h postgres -U relic_user -d relic_db
```

## Troubleshooting

### Port Already in Use
If a port is already in use (e.g., port 5173), you can:

1. Stop the conflicting service:
   ```bash
   lsof -i :5173  # Find what's using port 5173
   kill -9 <PID>
   ```

2. Or change the port in `docker-compose.yml`

### Database Connection Issues
Wait for PostgreSQL to be healthy before running operations:
```bash
docker compose logs postgres  # Check if it's ready
make db-init                  # Initialize database
```

### Container Won't Start
Check the logs and rebuild:
```bash
make logs
make clean    # Remove everything
make rebuild  # Start fresh
```

### Frontend Not Updating
The frontend container uses volumes for live updates. If changes aren't reflected:

1. Check if the file was saved
2. Verify the volume is mounted:
   ```bash
   docker compose exec frontend mount | grep /app
   ```
3. Restart the frontend:
   ```bash
   docker compose restart frontend
   ```

## Environment Variables

Environment variables are set in `docker-compose.yml`. To customize:

1. Edit `docker-compose.yml`
2. Restart containers: `make restart`

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `MINIO_ENDPOINT`: MinIO endpoint
- `DEBUG`: Enable debug mode
- `ALLOWED_ORIGINS`: CORS allowed origins

## Performance Notes

- First build takes ~2-3 minutes (downloading base images)
- Subsequent starts are instant
- Hot reload works for both backend and frontend
- File I/O in containers may be slower on some systems (Docker Desktop on Mac/Windows)

## Network Communication

All services communicate via the `Relic` Docker network:

- Backend connects to: `postgres:5432`, `minio:9000`
- Frontend connects to: Backend at `http://localhost:8000` (from browser)
- From host: Use `localhost:<port>`
- Container-to-container: Use service names (e.g., `postgres`)

## Building for Production

To create production images:

```bash
# Build without development dependencies
docker build -f backend/Dockerfile.prod -t Relic-backend:latest backend/
docker build -f frontend/Dockerfile.prod -t Relic-frontend:latest frontend/

# Or use production docker-compose file
docker compose -f docker-compose.prod.yml up
```

See `docker-compose.prod.yml` (when created) for production configuration.
