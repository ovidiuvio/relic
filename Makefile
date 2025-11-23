.PHONY: help venv install dev backend frontend test clean docker-up docker-down

help:
	@echo "CloudPaste Development Commands"
	@echo "==============================="
	@echo "  make venv          - Create virtual environment"
	@echo "  make install       - Install dependencies (creates venv if needed)"
	@echo "  make dev           - Run backend and frontend in development"
	@echo "  make backend       - Run backend only"
	@echo "  make frontend      - Run frontend only"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Clean up generated files"
	@echo "  make docker-up     - Start Docker services (MinIO, etc)"
	@echo "  make docker-down   - Stop Docker services"

venv:
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv || (echo "Error: python3-venv not installed. Try: apt install python3.13-venv" && exit 1); \
		echo "Virtual environment created!"; \
	else \
		echo "Virtual environment already exists"; \
	fi

install: venv
	./venv/bin/pip install --upgrade pip setuptools wheel
	./venv/bin/pip install -r requirements.txt
	cd frontend && npm install
	@echo "✓ Dependencies installed successfully!"
	@echo "Next steps:"
	@echo "  1. Activate virtual environment: source venv/bin/activate"
	@echo "  2. Start Docker services: make docker-up"
	@echo "  3. Run development server: make dev"

dev: docker-up
	@echo "Starting backend and frontend..."
	@echo "Backend will run on http://localhost:8000"
	@echo "Frontend will run on http://localhost:5173"
	@echo "API docs available at http://localhost:8000/docs"
	@. venv/bin/activate && (trap 'kill 0' EXIT; cd frontend && npm run dev & python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000)

backend: docker-up
	@. venv/bin/activate && python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	@. venv/bin/activate && pytest -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info .pytest_cache
	cd frontend && rm -rf node_modules dist
	@echo "✓ Cleaned up generated files"

docker-up:
	@echo "Starting Docker services (MinIO, PostgreSQL)..."
	docker-compose up -d
	@echo "✓ Services started"
	@echo "  MinIO: http://localhost:9000 (credentials: minioadmin/minioadmin)"
	@echo "  MinIO Console: http://localhost:9001"
	@echo "  PostgreSQL: localhost:5432"

docker-down:
	docker-compose down
	@echo "✓ Services stopped"

db-init:
	@. venv/bin/activate && python -c "from backend.database import init_db; init_db()"
	@echo "✓ Database initialized"
