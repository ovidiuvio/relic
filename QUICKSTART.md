# Relic Quick Start Guide

Get Relic running in 5 minutes.

## Prerequisites

- **Python 3.10+** (required)
- **Node.js 18+** (required for frontend)
- **Docker & Docker Compose** (required for local development)

## Installation

### Option 1: Using setup script (Recommended)

```bash
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all Python dependencies
- Install all Node.js dependencies
- Check for Docker and other requirements

Then activate the virtual environment:
```bash
source venv/bin/activate
```

### Option 2: Manual installation

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
make install
```

### 3. Start Docker services
```bash
make docker-up
```

This starts:
- **MinIO** (S3 storage) on port 9000
- **MinIO Console** on port 9001 (credentials: minioadmin/minioadmin)
- **PostgreSQL** database on port 5432

### 4. Run the application
```bash
make dev
```

This starts both the backend and frontend in development mode:
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Documentation: http://localhost:8000/docs

## First Steps

### 1. Create a Paste via UI
1. Go to http://localhost:5173
2. Fill in the "Create New Paste" form
3. Click "Create Paste"
4. Your paste URL will be copied to clipboard

### 2. Create a Paste via curl
```bash
# Create a simple paste
curl -X POST http://localhost:8000/api/v1/pastes \
  -F "file=@/path/to/file.txt" \
  -F "name=My File"

# With options
curl -X POST http://localhost:8000/api/v1/pastes \
  -F "file=@code.py" \
  -F "name=Python Code" \
  -F "language_hint=python" \
  -F "access_level=public" \
  -F "expires_in=24h"
```

### 3. View Your Paste
Visit the URL returned by the API:
```
http://localhost:8000/{paste_id}
```

Or get raw content:
```bash
curl http://localhost:8000/{paste_id}/raw
```

### 4. Edit Your Paste (Create New Version)
```bash
curl -X POST http://localhost:8000/api/v1/pastes/{paste_id}/edit \
  -F "file=@updated_file.txt"
```

### 5. View Version History
```bash
curl http://localhost:8000/api/v1/pastes/{paste_id}/history
```

### 6. Fork a Paste
```bash
curl -X POST http://localhost:8000/api/v1/pastes/{paste_id}/fork \
  -F "file=@my_version.txt"
```

### 7. Compare Two Pastes
```bash
curl "http://localhost:8000/api/v1/diff?from={id1}&to={id2}"
```

## Development Commands

```bash
make help              # Show all commands
make dev              # Run backend + frontend together
make backend          # Run backend only
make frontend         # Run frontend only
make test             # Run tests
make clean            # Clean generated files
make docker-down      # Stop Docker services
```

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation with Swagger UI.

## Project Structure

- `backend/` - FastAPI application
  - `main.py` - API routes and endpoints
  - `models.py` - Database models
  - `processors.py` - File type processors
  - `storage.py` - S3/MinIO client

- `frontend/` - Svelte + Tailwind application
  - `src/components/` - Svelte components
  - `src/services/api.js` - API client

- `PASTE.md` - Feature specification
- `CLAUDE.md` - Development guide
- `README.md` - Full documentation

## Troubleshooting

### MinIO not starting
```bash
docker-compose logs minio
docker-compose restart minio
```

### API errors
Check the logs:
```bash
# In the make dev output or
python -m uvicorn backend.main:app --reload --log-level debug
```

### Frontend not connecting to backend
- Ensure backend is running on 8000
- Check CORS settings in `backend/config.py`
- Check browser console for errors

### Port already in use
- Backend: `lsof -i :8000` and kill the process
- Frontend: `lsof -i :5173` and kill the process
- MinIO: `lsof -i :9000` and kill the process

## Next Steps

- [ ] Read `README.md` for full documentation
- [ ] Check `CLAUDE.md` for architecture details
- [ ] Explore the API with Swagger UI at /docs
- [ ] Build a custom integration with the API
- [ ] Set up PostgreSQL for production (see README.md)
- [ ] Deploy to production (cloud provider of choice)

## Support

For issues or questions:
1. Check the `README.md` documentation
2. Check the `CLAUDE.md` development guide
3. Review the API documentation at `/docs`
4. Check `PASTE.md` for feature specifications

Happy pasting! 🚀
