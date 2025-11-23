# Relic Setup Guide

This guide will help you set up Relic on your system.

## System Requirements

### Required
- **Python 3.10 or higher**
- **Node.js 18 or higher** (for the frontend)
- **Docker & Docker Compose** (for running MinIO and PostgreSQL)
- **Git** (for cloning the repository)

### Optional
- **PostgreSQL client** (for database management, only needed for production)

## Step-by-Step Setup

### 1. Clone or navigate to the repository

```bash
cd /home/ovidiu/Workspaces/paste
```

### 2. Verify Python installation

```bash
python3 --version
# Should output Python 3.10 or higher
```

### 3. Check if python3-venv is available

On Debian/Ubuntu systems, you might need to install `python3-venv`:

```bash
python3 -m venv --help
```

If this fails, install it with:

```bash
# On Debian/Ubuntu
apt install python3.13-venv

# Or if you have pipx installed
pipx install virtualenv
```

### 4. Run the setup script (Recommended)

```bash
./setup.sh
```

This will:
- ✅ Create a Python virtual environment in `./venv/`
- ✅ Install all Python dependencies from `requirements.txt`
- ✅ Install all Node.js dependencies for the frontend
- ✅ Check for Docker availability
- ✅ Provide next steps

**If the setup script fails**, see the Manual Setup section below.

### 5. Activate the virtual environment

After running `setup.sh`, activate the virtual environment:

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### 6. Start Docker services

```bash
make docker-up
```

This will:
- Start MinIO (S3 storage) on port 9000
- Start MinIO Console on port 9001
- Start PostgreSQL on port 5432

**MinIO Credentials:**
- Username: `minioadmin`
- Password: `minioadmin`

### 7. Run the development server

```bash
make dev
```

This will start:
- **Backend** on http://localhost:8000
- **Frontend** on http://localhost:5173

### 8. Access the application

Open your browser and visit:

- **Frontend**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (if using Docker)

---

## Manual Setup (if setup.sh doesn't work)

### 1. Create virtual environment

```bash
python3 -m venv venv
```

### 2. Activate virtual environment

```bash
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Install Node.js dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Continue from Step 6 above

```bash
make docker-up
make dev
```

---

## Troubleshooting

### Issue: `python3-venv not available`

**Solution:** Install the system package
```bash
apt install python3.13-venv
```

### Issue: `python3 -m venv` fails

**Solution 1:** Use system Python with pip
```bash
# Install virtualenv instead of venv
pip3 install virtualenv
virtualenv venv
source venv/bin/activate
```

**Solution 2:** Use conda (if installed)
```bash
conda create -n Relic python=3.10
conda activate Relic
pip install -r requirements.txt
```

### Issue: `make: command not found`

**Solution:** Install make
```bash
# On Debian/Ubuntu
apt install make

# On macOS
brew install make

# Or use the commands directly:
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install
```

### Issue: `docker-compose: command not found`

**Solution:** Install Docker Compose
```bash
# On macOS
brew install docker-compose

# On Linux
sudo apt install docker-compose

# Or use newer syntax
docker compose up -d
```

### Issue: Port already in use

**Solution:** Kill the process using the port
```bash
# Find process using port 8000 (backend)
lsof -i :8000
# Kill the process
kill -9 <PID>

# Or use docker
docker-compose down
docker-compose up -d
```

### Issue: Database connection errors

**Solution:** Initialize the database
```bash
source venv/bin/activate
make db-init
```

### Issue: Frontend not connecting to backend

**Check:**
1. Backend is running: http://localhost:8000/health
2. CORS settings in `backend/config.py`
3. Browser console for errors (F12)
4. Vite proxy configuration in `frontend/vite.config.js`

### Issue: MinIO bucket not created

**Solution:** MinIO creates the bucket automatically, but if it doesn't:
```bash
# Access MinIO console at http://localhost:9001
# Or use mc (MinIO client)
mc ls minio/pastes
```

---

## Development Workflow

### Activate virtual environment (every session)

```bash
source venv/bin/activate
```

### Start development server

```bash
make dev
```

### Or run services separately

```bash
# Terminal 1: Backend
make backend

# Terminal 2: Frontend
make frontend

# Terminal 3: Docker services (if needed)
make docker-up
```

### Run tests

```bash
make test
```

### Clean up

```bash
make clean
```

### Stop Docker services

```bash
make docker-down
```

---

## Production Setup

For production deployment:

1. Use PostgreSQL instead of SQLite:
   ```env
   DATABASE_URL=postgresql://user:password@host/paste_db
   ```

2. Use AWS S3 or S3-compatible service:
   ```env
   S3_ENDPOINT_URL=https://s3.amazonaws.com
   S3_ACCESS_KEY=your-key
   S3_SECRET_KEY=your-secret
   ```

3. Use production ASGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app
   ```

4. Set up reverse proxy (Nginx)

5. Enable SSL/TLS

See `README.md` for full production deployment guide.

---

## Environment Variables

Configuration can be customized via `.env` file. Copy `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DEBUG=false
DATABASE_URL=sqlite:///./paste.db
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
MAX_UPLOAD_SIZE=104857600
RATE_LIMIT_UPLOAD=10
RATE_LIMIT_READ=100
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8000
```

---

## Getting Help

### Check documentation

- `README.md` - Full project documentation
- `QUICKSTART.md` - Quick start guide
- `CLAUDE.md` - Architecture and development guide
- `PASTE.md` - Feature specification

### API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation.

### View logs

```bash
# Backend logs
# Check the terminal where you ran 'make dev' or 'make backend'

# Docker logs
docker-compose logs minio
docker-compose logs postgres

# Clear all logs
docker-compose logs --tail=0 -f
```

---

## Next Steps

1. ✅ Run `./setup.sh` or follow manual setup
2. ✅ Activate virtual environment: `source venv/bin/activate`
3. ✅ Start Docker services: `make docker-up`
4. ✅ Run development server: `make dev`
5. ✅ Visit http://localhost:5173 and create a paste!
6. 📖 Read the documentation in README.md
7. 🔧 Explore the API at http://localhost:8000/docs

---

## Quick Command Reference

```bash
# Setup
./setup.sh                    # Automated setup
source venv/bin/activate      # Activate venv
make install                  # Install dependencies

# Development
make dev                       # Run everything
make backend                   # Run backend only
make frontend                  # Run frontend only
make docker-up               # Start services
make docker-down             # Stop services

# Testing & Maintenance
make test                      # Run tests
make clean                     # Clean generated files
make db-init                  # Initialize database

# Help
make help                      # Show all commands
./setup.sh                     # Show setup instructions
```

Happy coding! 🚀
