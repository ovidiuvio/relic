# ✅ CloudPaste Setup Complete!

Your development environment is ready. Here's what you need to do next:

## 🚀 Next Steps

### 1. Activate the virtual environment

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### 2. Start Docker services

```bash
make docker-up
```

This will start:
- **MinIO** (S3 storage) on port 9000
- **MinIO Console** on port 9001 (credentials: minioadmin/minioadmin)
- **PostgreSQL** on port 5432

Wait 10-15 seconds for services to start.

### 3. Run the development server

```bash
make dev
```

This will start both the backend and frontend automatically. You'll see output like:

```
Backend will run on http://localhost:8000
Frontend will run on http://localhost:5173
API docs available at http://localhost:8000/docs
```

**Keep this terminal open** - it shows the server logs.

### 4. Open in your browser

Visit these URLs:

| URL | Description |
|-----|-------------|
| http://localhost:5173 | **Frontend** - Create and manage pastes |
| http://localhost:8000/docs | **API Documentation** - Interactive Swagger UI |
| http://localhost:9001 | **MinIO Console** - Manage storage (minioadmin/minioadmin) |

## ✅ What's Installed

- ✅ Python 3.13 virtual environment in `./venv/`
- ✅ All Python backend dependencies (FastAPI, SQLAlchemy, Pydantic, etc.)
- ✅ All frontend dependencies (Svelte, Tailwind CSS, Axios, Vite)
- ✅ Ready for development

## 📖 Documentation

- **README.md** - Complete project documentation
- **QUICKSTART.md** - Quick reference guide
- **CLAUDE.md** - Architecture and development guide
- **SETUP.md** - Detailed setup instructions
- **PASTE.md** - Feature specification

## 🐛 Troubleshooting

### If ports are already in use

```bash
# Kill existing processes
make docker-down
pkill -f uvicorn
pkill -f vite

# Try again
make docker-up
make dev
```

### If frontend doesn't connect to backend

1. Check backend is running: http://localhost:8000/health
2. Check browser console (F12) for errors
3. Make sure both services are started

### If MinIO isn't working

```bash
docker-compose logs minio
docker-compose restart minio
```

### How to stop everything

1. Press `Ctrl+C` in the terminal running `make dev`
2. Run `make docker-down` to stop services

## 💡 Tips

**Always activate the virtual environment first:**
```bash
source venv/bin/activate
```

**Run commands with `make`:**
- `make dev` - Run everything
- `make backend` - Backend only
- `make frontend` - Frontend only
- `make test` - Run tests
- `make help` - Show all commands

**View logs:**
- Backend logs are in the `make dev` terminal
- Docker logs: `docker-compose logs -f`

## 🎉 You're ready!

Run `make dev` and start creating pastes!

If you have any issues, check SETUP.md or README.md for help.

Happy coding! 🚀
