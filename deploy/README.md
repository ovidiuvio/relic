# Relic Production Deployment

This directory contains the files needed to deploy the Relic application in a production environment using Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Setup

**Quick start (from the repo root):**

```bash
make deploy-up
```

The first run generates `deploy/.env` automatically with random secrets
(PostgreSQL/MinIO passwords and the ops-agent token) — no manual edits needed —
then pulls the pinned images and starts the stack.

**Manual setup (from this directory):**

1.  **Configure Environment Variables:**
    -   Copy the `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```
    -   Open the `.env` file in a text editor and customize the settings for your environment. At a minimum, you should change the default passwords for PostgreSQL and MinIO.
    -   Generate the ops-agent shared secret (enables service logs and UI-driven deployments in the admin panel):
        ```bash
        openssl rand -hex 32   # paste the result into OPS_AGENT_TOKEN in .env
        ```

2.  **Pull the Latest Images:**
    -   To ensure you have the latest versions of the application images, run the following command:
        ```bash
        docker compose pull
        ```

3.  **Start the Application:**
    -   To start the application in detached mode, run:
        ```bash
        docker compose up -d
        ```

4.  **Accessing the Application:**
    -   **Relic UI:** Open your web browser and navigate to `http://localhost`.
    -   **MinIO Console:** The MinIO object storage console is available at `http://localhost:9001`.
    -   **PostgreSQL:** The database is exposed on port `5432`.

## Managing the Application

-   **Stopping the application:**
    ```bash
    docker compose down
    ```
-   **Viewing logs:**
    ```bash
    docker compose logs -f
    ```
-   **Updating to a new version:**
    ```bash
    docker compose pull
    docker compose up -d
    ```

## Managed Deployments (Admin Panel)

The stack includes an **ops-agent** sidecar that holds the docker socket and lets
admins operate the deployment from the web UI (Admin → Services / Deploy / Monitor):

-   **Services**: container states, uptime, restart counts, per-service log viewer
    (with follow mode), and one-click service restarts.
-   **Deploy**: check GitHub for new releases, deploy any released version, or roll
    back to an older one. The agent pins `RELIC_VERSION` in this directory's `.env`
    and runs `docker compose pull && up -d` for the app services (`backend`,
    `frontend`, `s3-sync`). Postgres, MinIO, and the agent itself are never touched.
    Deployment history is kept in the `ops_data` volume.
-   **Monitor**: realtime API metrics (requests/sec, latencies, DB times, slow queries).

Notes:

-   The agent is only reachable on the internal compose network and requires the
    `OPS_AGENT_TOKEN` shared secret; it is never exposed through nginx.
-   The compose project name must be `deploy` (the default when running
    `docker compose` from this directory). If you use `-p <name>`, set
    `COMPOSE_PROJECT_NAME=<name>` in `.env` so the agent can find the containers.
-   To update the ops-agent itself: `docker compose pull ops-agent && docker compose up -d ops-agent`.
