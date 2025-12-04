# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Relic** is a professional artifact storage service with immutable artifacts. Built with FastAPI (Python), Svelte, and Tailwind CSS.

Key principle: Relics cannot be edited after creation - they are permanent and immutable. To modify content, create a fork which creates an independent copy.

### Tech Stack
- **Infrastructure**: Docker + Nginx (Reverse Proxy)
- **Backend**: FastAPI + SQLAlchemy + MinIO/S3
- **Frontend**: Svelte + Tailwind CSS + Axios
- **Database**: PostgreSQL (prod/dev)
- **Storage**: MinIO (dev), S3 (prod)

## Core Architecture Concepts

### 1. Immutable Relic Model

- Each relic is permanent and cannot be edited after creation
- "Forking" creates an independent copy with `fork_of` reference to the source
- Each relic has a unique URL that serves as the access identifier
- No versioning - each relic stands alone

**Database fields:**
- `id`: 32-character hexadecimal (GitHub Gist-style), primary key
- `fork_of`: Source relic if forked (null for original relics)
- `client_id`: Client identification key (nullable for anonymous)
- `name`: Optional display name
- `description`: Optional description
- `content_type`: MIME type of the stored content
- `language_hint`: Optional language hint for syntax highlighting
- `size_bytes`: Size of the content in bytes
- `s3_key`: Storage location (format: `relics/{id}`)
- `access_level`: public (listed in recents) or private (URL is the access token)
- `password_hash`: Optional password protection
- `created_at`, `expires_at`, `deleted_at`: Timestamps
- `access_count`: Number of times the relic has been accessed

### 2. Universal Content Support

The system handles **any file type** (text, code, images, PDFs, CSVs, archives, etc.):

- **Text/Code**: Displayed with syntax highlighting support via language hints
- **Images**: Displayed as-is with size information
- **PDFs**: Downloaded and can be viewed in browser
- **CSV/Excel**: Downloaded and can be opened in external tools
- **Videos/Archives**: Downloaded and can be processed locally


### 3. Fork Relationships

```
Original:  f47ac10b58cc4372a5670e02b2c3d479
  └─ Fork: a1b2c3d4e5f678901234567890abcdef (fork_of: f47ac...)
      └─ Fork: 1234567890abcdef1234567890abcdef (fork_of: a1b2c...)
```

Key queries:
- Check if fork: look at `fork_of` field (null = original relic)
- Get forks of a relic: query where `fork_of` = relic_id
- Trace fork lineage: follow `fork_of` references backward
- Each fork is independent - changes to original don't affect forks

### 4. Access Control & Expiration

- **Access levels**:
  - **Public**: Listed in recent relics, discoverable via UI
  - **Private**: Not listed in recents, only accessible via direct URL (which serves as the access token with 128 bits of entropy)
- **Optional password protection**: Can be applied to any relic (public or private) for additional security
- **Expiration options**: 1h, 24h, 7d, 30d, never (default: never)
- **Soft delete**: Deleted relics marked with `deleted_at` timestamp (hard delete after 30 days)
- **Anonymous relics**: No client association
- **URL format**: 32-character hexadecimal (GitHub Gist-style), cryptographically secure, practically collision-proof

## Storage Architecture

- **Primary storage**: S3-compatible (MinIO) - one object per relic
- **Database**: Stores metadata (id, client_id, fork_of, content_type, language_hint, size_bytes, s3_key, created_at, expires_at, deleted_at, access_count, tags, etc.)
- **Max upload**: 100MB (configurable)
- **No S3 versioning needed**: Immutable model means each relic is independent

## API Structure

### Key Endpoint Patterns

All API endpoints are prefixed with `/api/v1` and served via Nginx at `http://localhost`.

```
POST   /api/v1/relics                  Create relic
GET    /api/v1/relics/:id              Get relic metadata
GET    /:id/raw                        Get raw content (served from root)
POST   /api/v1/relics/:id/fork         Create fork (independent copy)
DELETE /api/v1/relics/:id              Delete relic (soft delete)

GET    /api/v1/relics/:id/preview      Get type-specific preview
GET    /api/v1/relics/:id/thumbnail    Get thumbnail image
GET    /api/v1/relics                  List recent public relics
```

### Request/Response Pattern

- **Create**: Returns `{id, url, fork_of?, created_at}`
- **Get**: Returns full metadata including `content_type`, `size`, `created_at`, etc.
- **Fork**: Returns `{id, url, fork_of, created_at}`
- **Preview**: Type-specific (images: metadata+thumbnail_url, CSV: rows+columns+preview+stats, etc.)

## Project Structure

```
relic/
├── backend/
│   ├── main.py              # FastAPI application and routes
│   ├── models.py            # SQLAlchemy ORM models (Relic, User, Tag)
│   ├── schemas.py           # Pydantic validation schemas
│   ├── database.py          # Database initialization and session management
│   ├── config.py            # Configuration (settings, env vars)
│   ├── storage.py           # S3/MinIO client wrapper
│   ├── utils.py             # Utilities (ID generation, hashing, expiry parsing)
│   ├── backup.py            # Database backup logic
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── App.svelte       # Main app component
│   │   ├── main.js          # Entry point
│   │   ├── app.css          # Tailwind styles
│   │   ├── components/
│   │   │   ├── Navigation.svelte
│   │   │   ├── RelicForm.svelte
│   │   │   ├── RelicViewer.svelte
│   │   │   ├── ForkModal.svelte
│   │   │   ├── MonacoEditor.svelte
│   │   │   ├── MyBookmarks.svelte
│   │   │   ├── MyRelics.svelte
│   │   │   ├── RecentRelics.svelte
│   │   │   ├── RelicTable.svelte
│   │   │   ├── ApiDocs.svelte
│   │   │   └── Toast.svelte
│   │   ├── stores/
│   │   │   └── toastStore.js
│   │   └── services/
│   │       └── api.js
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── sync/                    # S3 Sync service
│   └── Dockerfile
├── requirements.txt         # Python dependencies
├── Makefile                 # Development commands
├── docker-compose.yml       # Docker services (Nginx, Backend, Frontend, DB, MinIO)
├── nginx.conf               # Nginx configuration
├── .env                     # Environment variables
├── .gitignore
├── RELIC.md                 # Feature specification
├── CLAUDE.md                # This file
└── README.md                # User documentation
```

## Common Development Tasks
### Handling Fork Relationships

For queries across fork relationships:
- **Check if fork**: Look at `fork_of` field (null = original)
- **Get forks**: Query where `fork_of = :relic_id`
- **Trace lineage**: Follow `fork_of` references backward
- **Independent copies**: Each fork is completely independent

Example:
```python
# Get all forks of a relic
db.query(Relic).filter(Relic.fork_of == relic_id).order_by(Relic.created_at.desc())

# Check if relic is a fork
relic.fork_of  # None if original, otherwise contains source relic ID

# Get original relic from a fork
if relic.fork_of:
    original = db.query(Relic).filter(Relic.id == relic.fork_of).first()
```


### Search & Filtering

Not yet implemented. Plan:
- **By content**: Full-text search (SQLite `MATCH`, PostgreSQL `tsvector`, or external index)
- **By tags**: Many-to-many via `relic_tags` table
- **By type**: Simple filter on `content_type` field
- **By client**: Filter on `client_id` field
- **Pagination**: Use `offset` and `limit` parameters

### Frontend Routing

Frontend uses simple section-based routing (not a full router). To add new pages:
1. Create component in `frontend/src/components/`
2. Add navigation button in `Navigation.svelte`
3. Add section handling in `App.svelte`
4. Emit 'navigate' event from Navigation

## Performance Targets

- **Upload**: <500ms for <1MB files
- **Retrieval**: <100ms
- **Fork creation**: <300ms for <1MB files
- **Forks query**: <50ms

## Security

- **File type validation**: MIME detection (not just extension)
- **Size limits**: 100MB max
- **HTML sanitization**: Required for display
- **Authenticated deletion**: Only owner can delete
- **Expiration cleanup**: Hourly job to hard-delete expired relics

## Key Implementation Decisions

1. **True immutability**: Each relic is permanent and cannot be modified after creation
2. **Fork-based modification**: To modify content, create an independent fork
3. **Soft delete**: Allows recovery and maintains referential integrity
4. **S3 storage**: Scales to millions of relics, supports any file type
5. **Cryptographic IDs**: 32-character hexadecimal IDs (GitHub Gist-style) for security and collision resistance
6. **Simple and focused**: Clean, straightforward implementation without unnecessary complexity
