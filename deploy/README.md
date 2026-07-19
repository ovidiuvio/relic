# Relic Production Deployment

This directory contains the files needed to deploy the Relic application in a production environment using Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Setup

1.  **Configure Environment Variables:**
    -   Copy the `.env.example` file to a new file named `.env`:
        ```bash
        cp .env.example .env
        ```
    -   Open the `.env` file in a text editor and customize the settings for your environment. At a minimum, you should change the default passwords for PostgreSQL and MinIO.
    -   To pin a specific release instead of always tracking `latest`, set `RELIC_VERSION` (e.g. `RELIC_VERSION=v0.6.1`). See [releases](https://github.com/ovidiuvio/relic/releases) for available versions.

2.  **Pull the Images:**
    -   To fetch the images referenced by your `.env` (`latest` or a pinned version), run:
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
    -   Tracking `latest`:
        ```bash
        docker compose pull
        docker compose up -d
        ```
    -   Pinned to a release: update `RELIC_VERSION` in `.env`, then run the same two commands.

## S3 Bucket Sync (Optional)

By default the `s3-sync` service is **not** started. To enable periodic backups of your MinIO bucket to an external S3-compatible destination, fill in the `S3_SYNC_*` variables in `.env` and add the extra compose file when running commands:

```bash
docker compose -f docker-compose.yml -f docker-compose.s3-sync.yml up -d
```
