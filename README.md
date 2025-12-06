# Relic - Artifact Storage Service

A modern, feature-rich artifact service with immutable relics, complete version history, and smart content processing. Built with FastAPI (Python), Svelte, and Tailwind CSS.

## Features

- **Immutable Artifacts**: Each relic is permanent. Edits create new versions via forking with complete history preserved.
- **Version Lineage**: Track complete history through parent-child relationships (forks).
- **Universal Content Support**: Text, code, images, PDFs, CSV/Excel, archives, and more.
- **Smart Processing**: Automatic syntax highlighting, thumbnail generation, metadata extraction.

- **Access Control**: Public, unlisted, and private relics with optional password protection.
- **Expiration**: Set relics to expire after 1h, 24h, 7d, 30d, or never.
- **Database Backups**: Automated and manual database backups with retention policies.

## Architecture

### Infrastructure
- **Docker**: All services run in containers
- **Nginx**: Reverse proxy handling routing and SSL (optional)
- **PostgreSQL**: Production-grade database
- **MinIO**: S3-compatible object storage

### Backend
- **FastAPI** for REST API
- **SQLAlchemy** for database ORM
- **Pygments** for syntax highlighting
- **Pillow** for image processing

### Frontend
- **Svelte** for reactive UI
- **Tailwind CSS** for styling
- **Axios** for API calls
- **Vite** for building and dev server

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Make (optional, for convenience commands)

### Setup

1. **Start all services**
```bash
make up
```

2. **Access the application**
- Frontend: http://localhost
- API Docs: http://localhost/api/docs
- MinIO Console: http://localhost:9001 (admin/admin)

3. **Stop services**
```bash
make down
```

## API Endpoints

All API endpoints are prefixed with `/api/v1` and served via Nginx at `http://localhost`.

### Relic Operations

**Create Relic**
```bash
curl -X POST http://localhost/api/v1/relics \
  -F "file=@myfile.txt" \
  -F "name=My File" \
  -F "access_level=public" \
  -F "expires_in=24h"
```

**Get Relic Metadata**
```bash
curl http://localhost/api/v1/relics/{id}
```

**Get Raw Content**
```bash
curl http://localhost/{id}/raw
```

**Fork Relic (Create Independent Copy)**
```bash
curl -X POST http://localhost/api/v1/relics/{id}/fork \
  -F "file=@new.txt" \
  -F "name=Forked Relic"
```

**Delete Relic**
```bash
curl -X DELETE http://localhost/api/v1/relics/{id}
```

### Listing & Search

**List Recent Relics**
```bash
curl "http://localhost/api/v1/relics?limit=50"
```

## Data Model

### Relic Entity
- `id`: Unique identifier (32-char hex string, e.g., `f47ac10b58cc4372a5670e02b2c3d479`)
- `client_id`: Client identification key (nullable for anonymous relics)
- `name`: Display name
- `description`: Optional description
- `content_type`: MIME type
- `language_hint`: Programming language for code
- `size_bytes`: Content size
- `fork_of`: Source relic if forked (null for original relics)
- `s3_key`: Storage location in S3
- `access_level`: public/private
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp (null = never)
- `access_count`: View counter

## Development Commands

```bash
make help          # Show all available commands
make up            # Start all containers
make down          # Stop all containers
make logs          # View logs from all containers
make restart       # Restart all containers
make rebuild       # Rebuild images and start fresh
make shell-backend # Open shell in backend container
make shell-frontend # Open shell in frontend container
make test          # Run tests
```

## Database Backups

The system includes a built-in backup service for PostgreSQL.

```bash
make backup-now     # Trigger manual backup
make backup-list    # List available backups
make backup-status  # Show backup system status
```

## Environment Variables

See `.env` file (or `docker-compose.yml`) for configuration:
- `DATABASE_URL`: Database connection string
- `MINIO_ENDPOINT`: MinIO/S3 endpoint
- `BACKUP_ENABLED`: Enable/disable automated backups
- `BACKUP_TIMES`: Schedule for daily backups (UTC)

## Contributing

See CLAUDE.md for architecture and development guidelines.

## License

MIT
