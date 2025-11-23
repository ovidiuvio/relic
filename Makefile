.PHONY: help install dev backend frontend test clean docker-up docker-down

help:
	@echo "CloudPaste Development Commands"
	@echo "==============================="
	@echo "  make install       - Install dependencies"
	@echo "  make dev           - Run backend and frontend in development"
	@echo "  make backend       - Run backend only"
	@echo "  make frontend      - Run frontend only"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Clean up generated files"
	@echo "  make docker-up     - Start Docker services (MinIO, etc)"
	@echo "  make docker-down   - Stop Docker services"

install:
	pip install -r requirements.txt
	cd frontend && npm install

dev: docker-up
	@echo "Starting backend and frontend..."
	@echo "Backend will run on http://localhost:8000"
	@echo "Frontend will run on http://localhost:5173"
	@echo "API docs available at http://localhost:8000/docs"
	@(trap 'kill 0' EXIT; cd frontend && npm run dev & python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000)

backend: docker-up
	python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info .pytest_cache
	cd frontend && rm -rf node_modules dist

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

db-init:
	python -c "from backend.database import init_db; init_db()"
