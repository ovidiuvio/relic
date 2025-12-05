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
