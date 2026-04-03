# Relic - Project Context

## Project Overview

**Relic** is a self-hosted artifact/pastebin storage service designed for developers. It supports immutable relics (permanent artifacts) with fork-based modification, complete version history, and smart content processing for 100+ file types including code, images, PDFs, CSVs, archives, and structured data.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (Python), SQLAlchemy, Pydantic |
| **Frontend** | Svelte 4, Tailwind CSS, Vite, Monaco Editor |
| **Database** | PostgreSQL 16 |
| **Storage** | MinIO (S3-compatible object storage) |
| **Infrastructure** | Docker Compose, Nginx (reverse proxy) |
| **Testing** | pytest, pytest-asyncio, httpx |

### Key Design Principle

**True immutability**: Relics cannot be edited after creation. Each relic is permanent with a unique 32-character hex URL. To modify content, users *fork* a relic, creating an independent copy linked via the `fork_of` field. No version chains — each relic stands alone.

---

## Project Structure

```
relic/
├── backend/                    # Python FastAPI application
│   ├── main.py                 # FastAPI app, lifecycle events, router registration
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic validation schemas
│   ├── database.py             # DB initialization & session management
│   ├── config.py               # Pydantic settings (env vars)
│   ├── storage.py              # S3/MinIO client wrapper
│   ├── utils.py                # ID generation, hashing, expiry parsing
│   ├── scheduler.py            # APScheduler for backups & relic cleanup
│   ├── backup.py               # Database backup logic
│   ├── profiling.py            # Performance profiling middleware
│   ├── dependencies.py         # FastAPI dependency injection helpers
│   ├── migrations/             # Alembic database migrations
│   └── routes/                 # API route handlers
│       ├── relics.py           # Core relic CRUD + fork operations
│       ├── admin.py            # Admin endpoints (all relics, clients, stats)
│       ├── clients.py          # Client registration & management
│       ├── bookmarks.py        # Bookmark operations
│       ├── comments.py         # Line-specific comment threads
│       ├── spaces.py           # Space collections
│       ├── reports.py          # Report/flag relics
│       └── health.py           # Health check endpoint
│
├── frontend/                   # Svelte + Vite application
│   ├── src/
│   │   ├── App.svelte          # Root component, client init, routing
│   │   ├── routes.js           # Route definitions (pattern → component)
│   │   ├── main.js             # Entry point
│   │   ├── components/         # UI components
│   │   │   ├── renderers/      # Content-specific renderers
│   │   │   │   ├── CodeRenderer.svelte
│   │   │   │   ├── ImageRenderer.svelte
│   │   │   │   ├── ArchiveRenderer.svelte
│   │   │   │   ├── CsvRenderer.svelte
│   │   │   │   ├── DiffRenderer.svelte
│   │   │   │   ├── ExcalidrawRenderer.svelte
│   │   │   │   ├── MarkdownRenderer.svelte
│   │   │   │   ├── PdfRenderer.svelte
│   │   │   │   ├── RelicIndexRenderer.svelte
│   │   │   │   └── TreeRenderer.svelte / TreeNode.svelte
│   │   │   ├── RelicForm.svelte
│   │   │   ├── RelicViewer.svelte
│   │   │   ├── RelicHeader.svelte
│   │   │   ├── RelicStatusBar.svelte
│   │   │   ├── RelicTable.svelte
│   │   │   ├── MonacoEditor.svelte
│   │   │   ├── ForkModal.svelte
│   │   │   ├── ForkEditor.svelte
│   │   │   ├── LineageModal.svelte
│   │   │   ├── CommentEditor.svelte
│   │   │   ├── SpacesList.svelte / SpaceViewer.svelte
│   │   │   ├── AdminPanel.svelte
│   │   │   └── ... (modals, toast, etc.)
│   │   ├── services/
│   │   │   ├── api/            # API client modules
│   │   │   ├── processors/     # Content type processors
│   │   │   ├── data/           # File type definitions
│   │   │   ├── utils/          # Helper utilities
│   │   │   └── relicActions.js # Relic action helpers
│   │   └── stores/
│   │       └── toastStore.js   # Global toast notification store
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── cli/                        # CLI tool for terminal uploads
├── sync/                       # S3 sync service (MinIO → S3 backup)
├── deploy/                     # Deployment configurations
├── k8s/                        # Kubernetes manifests
├── scripts/                    # Utility scripts
├── tests/                      # pytest test suite
├── test-data/                  # Test fixtures
│
├── docker-compose.dev.yml      # Development: hot-reload, volume mounts
├── docker-compose.prod.yml     # Production: optimized builds
├── nginx.conf                  # Nginx reverse proxy config (dev)
├── Makefile                    # All build/deploy commands
├── requirements.txt            # Python dependencies
└── pytest.ini                  # pytest configuration
```

---

## Building and Running

### Prerequisites
- Docker & Docker Compose
- Make (recommended)

### Production (default)
```bash
make up              # Start production services
make logs            # Tail logs
make down            # Stop services
make build           # Build images only
make rebuild         # Build + restart
make clean           # Remove all data (WARNING prompt)
```

### Development (hot-reload)
```bash
make dev-up          # Start dev services with hot-reload
make dev-logs        # Tail all dev logs
make dev-logs-backend   # Backend logs only
make dev-logs-frontend  # Frontend logs only
make dev-down        # Stop dev services
make dev-restart     # Restart dev services
make dev-test        # Run pytest in backend container
make dev-shell-backend  # Bash in backend container
make dev-shell-frontend # Shell in frontend container
```

### Database
```bash
make db-init         # Initialize database (run migrations)
make db-revision     # Create new Alembic migration
make db-migrate      # Apply pending migrations
```

### Backups
```bash
make backup-now      # Manual database backup
make backup-list     # List all backups
make backup-cleanup  # Run retention cleanup
make backup-status   # Show backup system status
```

### Service URLs
| Service | URL | Credentials |
|---------|-----|-------------|
| Application | http://localhost | — |
| API Docs | http://localhost/api/docs | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| PostgreSQL | localhost:5432 | relic_user / relic_password |

---

## Architecture

### Backend (FastAPI)

**Entry point**: `backend/main.py`

The FastAPI app registers route modules in a specific order — the `relics` router **must be last** because it contains catch-all `/{relic_id}` routes.

**Lifecycle events**:
- **Startup**: Init DB → Init storage → Ensure bucket → Start scheduler → Optional startup backup
- **Shutdown**: Optional shutdown backup → Stop scheduler → Dispose connections

**Key modules**:
- `storage.py`: `storage_service` — async S3 client wrapper (aiobotocore). Handles upload/download, bucket provisioning.
- `scheduler.py`: APScheduler for automated backups and expired relic cleanup.
- `config.py`: Pydantic `Settings` class loaded from env vars. All config goes here.

**API route patterns**:
- All API routes are prefixed with `/api/v1`
- Relic raw content served at `/{id}/raw`
- Relic viewing (browser) at `/{id}`

### Frontend (Svelte)

**Routing**: Custom section-based routing in `frontend/src/routes.js` (not a full router). Pattern matching against `window.location.pathname`.

**Routing flow**:
1. `App.svelte` calls `matchRoute(path, urlParams)` on navigation
2. Returns component + props + section identifier
3. Section drives active nav state
4. `sectionToPath(section)` converts section back to URL for navigation

**Content processing pipeline**:
1. Content fetched → content type detected (`typeUtils.js`)
2. Processor runs (`processors/`) → returns structured data
3. Viewer routes to appropriate renderer component

**API client**: Modular API services under `services/api/` (axios-based).

### Nginx (Reverse Proxy)

Routes traffic:
- `/api/*` → Backend (`backend:8000`)
- `/{id}/raw` → Backend (for CLI tools like wget/curl)
- `/{id}` with wget/curl UA → Backend
- Everything else → Frontend (`frontend:5173` in dev, static files in prod)
- WebSocket upgrade support for Vite HMR

---

## Data Model

### Core Models (`backend/models.py`)

**Relic**: 32-char hex ID, content metadata, `fork_of` reference, access level, expiration, tags, spaces.

**ClientKey**: 32-char hex ID (auth secret), 16-char `public_id` (safe to share), display name, relic count.

**Space**: Groups relics into curated collections. Public or private with access lists (viewer/editor roles).

**Comment**: Line-specific comments with threaded replies (`parent_id` self-reference).

**Tag**: Many-to-many with relics via `relic_tags` association table.

**RelicAccess** / **SpaceAccess**: ACL entries tracking per-client access with roles.

**ClientBookmark**: Many-to-many bookmark tracking.

**RelicReport**: User reports for moderation.

### Key Relationships
```
ClientKey ──1:N──> Relic (owner)
Relic ──N:M──> Tag (via relic_tags)
Relic ──N:M──> Space (via space_relics)
Relic ──1:N──> RelicAccess
Space ──1:N──> SpaceAccess
ClientKey ──1:N──> ClientBookmark
Relic ──1:N──> Comment (with self-referencing replies)
Relic ──1:N──> RelicReport
```

---

## API Endpoints

All prefixed with `/api/v1`.

### Relics
| Method | Path | Description |
|--------|------|-------------|
| POST | `/relics` | Create relic |
| GET | `/relics` | List recent public relics |
| GET | `/relics/:id` | Get relic metadata |
| PUT | `/relics/:id` | Update relic metadata |
| POST | `/relics/:id/fork` | Create fork (independent copy) |
| DELETE | `/relics/:id` | Delete relic (owner or admin) |
| GET | `/:id/raw` | Get raw content |

### Admin (requires admin client ID in `X-Client-Key` header)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/check` | Check admin status |
| GET | `/admin/relics` | List all relics (incl. private) |
| GET | `/admin/clients` | List all clients |
| GET | `/admin/stats` | System statistics |
| DELETE | `/admin/clients/:id` | Delete client |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/clients/*` | Client registration & management |
| GET/POST | `/bookmarks/*` | Bookmark operations |
| GET/POST | `/comments/*` | Comment CRUD |
| GET/POST | `/spaces/*` | Space collections |
| POST | `/reports` | Flag a relic |
| GET | `/health` | Health check |

---

## Testing

Tests live in `tests/` and use pytest with async support.

```bash
make dev-test              # Run via Docker
# Or directly:
pytest -v                  # All tests
pytest -v -m unit          # Unit tests only
pytest -v -m integration   # Integration tests only
pytest tests/test_api.py   # Specific test file
```

**Test files**:
- `test_api.py` — Core relic API operations
- `test_admin.py` — Admin endpoints
- `test_bookmarks.py` — Bookmark functionality
- `test_clients.py` — Client management
- `test_comments.py` — Comment system
- `test_spaces.py` — Space collections
- `test_reports.py` — Reporting
- `test_raw_route.py` — Raw content routes
- `test_update_relic.py` — Relic metadata updates
- `test_utils.py` — Utility functions
- `conftest.py` — Shared fixtures

---

## Development Conventions

### Backend
- **Async-first**: Uses async engines where possible, asyncpg for PostgreSQL
- **Pydantic v2**: Settings and schemas use Pydantic v2 patterns
- **SQLAlchemy 2.0**: Declarative base with `lazy="raise"` (no implicit lazy loading)
- **Dependency injection**: FastAPI's `Depends()` pattern via `backend/dependencies.py`
- **Route ordering matters**: Catch-all routes must be registered last

### Frontend
- **Svelte 4**: Uses Svelte stores for global state (`toastStore`)
- **Tailwind CSS**: Utility-first styling with typography and forms plugins
- **Monaco Editor**: Full IDE-like code editor for code viewing/forking
- **Content processors**: Pluggable processor pattern for different file types
- **No full router**: Section-based routing in `routes.js` mapped to components

### Testing
- **Markers**: `unit`, `integration`, `slow`
- **Async mode**: `asyncio_mode = auto` in pytest.ini
- **Fixtures**: Shared in `conftest.py`

---

## Configuration

Environment variables (see `docker-compose.dev.yml` / `docker-compose.prod.yml`):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `MINIO_ENDPOINT` | MinIO/S3 endpoint |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | S3 credentials |
| `MINIO_BUCKET` | S3 bucket name |
| `ADMIN_CLIENT_IDS` | Comma-separated admin client IDs |
| `ALLOWED_ORIGINS` | CORS allowed origins |
| `DEBUG` | Debug mode |
| `BACKUP_*` | Backup scheduling configuration |

---

## Admin Setup

1. Get client ID from browser console: `localStorage.getItem('relic_client_key')`
2. Add to `ADMIN_CLIENT_IDS` in the relevant docker-compose file (comma-separated for multiple admins)
3. Restart services (`make down && make up` or `make dev-down && make dev-up`)

Admin privileges: delete any relic, view all relics (incl. private), manage clients, view system stats.
