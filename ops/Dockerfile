# Relic Ops Agent
FROM python:3.12-slim

ARG VERSION=dev

WORKDIR /app

# Docker CLI + compose plugin (needed to pull images and recreate services)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV APP_VERSION=${VERSION}

EXPOSE 9100

# Runs as root: needs the mounted docker socket
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9100"]
