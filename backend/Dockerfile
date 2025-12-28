# Backend Dockerfile - Development with live reload
FROM python:3.13-slim

# Accept version as build arg (will be git hash for local builds)
ARG VERSION=dev

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (will be overridden by mount in dev)
COPY backend/ ./backend/

# Set version as environment variable
ENV APP_VERSION=${VERSION}

# Expose port for FastAPI
EXPOSE 8000

# Copy and set entrypoint
COPY backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Run with reload for development
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

