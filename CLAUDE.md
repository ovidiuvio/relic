# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CloudPaste** is a professional pastebin service with immutable pastes, complete version history tracking, and smart content processing. Built with FastAPI (Python), Svelte, and Tailwind CSS.

Key principle: Pastes cannot be edited - edits create new versions linked to the original, preserving complete history.

### Tech Stack
- **Backend**: FastAPI + SQLAlchemy + MinIO/S3
- **Frontend**: Svelte + Tailwind CSS + Axios
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Storage**: MinIO (dev), S3 (prod)

## Core Architecture Concepts

### 1. Immutable Paste Model

- Each paste is permanent and cannot be edited after creation
- "Editing" creates a **new paste** with `parent_id` pointing to the original
- "Forking" creates an independent lineage with `fork_of` reference
- All versions accessible at unique URLs and via history API

**Database fields:**
- `id`: Base62 ID (7-8 chars), primary key
- `parent_id`: Link to previous version (null if original)
- `root_id`: First paste in version chain (for efficient history lookup)
- `version_number`: Sequential counter (1, 2, 3...)
- `fork_of`: Source paste if forked (creates new root_id)
- `user_id`: Owner (nullable for anonymous)
- `s3_key`: Storage location (format: `pastes/{id}`)
- `access_level`: public/unlisted/private
- `created_at`, `expires_at`, `deleted_at`: Timestamps

### 2. Universal Content Support

The system handles **any file type** (text, code, images, PDFs, CSVs, archives, etc.) with smart processing:

- **Text/Code**: Syntax highlighting, line numbers, diff support
- **Images**: EXIF extraction, thumbnail generation (200x200)
- **PDFs**: Page count, first page preview, text extraction, metadata
- **CSV/Excel**: Column detection, row count, statistics, data preview
- **Videos/Archives**: Metadata extraction, preview without extraction

All content types are versionable, diffable, and processable.

### 3. Version Lineage & Relationships

```
Original:  a3Bk9Zx (v1)
  ├─ Edit: b4Ck2Ty (v2, parent: a3Bk9Zx, root: a3Bk9Zx)
  │   └─ Edit: c5Dm3Uz (v3, parent: b4Ck2Ty, root: a3Bk9Zx)
  └─ Fork: x7Yz8Wx (v1, fork_of: a3Bk9Zx, root: x7Yz8Wx)
      └─ Edit: y8Za9Xy (v2, parent: x7Yz8Wx, root: x7Yz8Wx)
```

Key queries:
- Get full history: traverse using `parent_id` or query by `root_id`
- Get children: query all pastes with this `id` as `parent_id`
- Check if fork: look at `fork_of` field
- Find root: use `root_id` field directly

### 4. Access Control & Expiration

- **Access levels**: Public, Unlisted (direct URL only), Private (owner only)
- **Expiration options**: 1h, 24h, 7d, 30d, never (default: never)
- **Authentication**: Required for private pastes and deletion
- **Soft delete**: Deleted pastes marked with `deleted_at` timestamp (hard delete after 30 days)
- **Anonymous pastes**: `user_id` is null

## Storage Architecture

- **Primary storage**: S3-compatible (MinIO) - one object per paste
- **Database**: Stores metadata (id, user_id, parent_id, root_id, version_number, fork_of, content_type, language_hint, size_bytes, s3_key, created_at, expires_at, deleted_at, access_count, tags, etc.)
- **Max upload**: 100MB (configurable)
- **No S3 versioning needed**: Immutable model means each paste is independent

## API Structure

### Key Endpoint Patterns

```
POST   /api/pastes                    Create paste
GET    /api/pastes/:id                Get paste metadata
GET    /:id/raw                       Get raw content
POST   /api/pastes/:id/edit           Create new version
POST   /api/pastes/:id/fork           Create fork (new lineage)
DELETE /api/pastes/:id                Delete paste (soft delete)

GET    /api/pastes/:id/history        Get full version history
GET    /api/pastes/:id/parent         Get parent paste
GET    /api/pastes/:id/children       Get child pastes
GET    /api/diff?from=:id1&to=:id2    Compare any two pastes
GET    /api/pastes/:id/diff           Compare with parent

GET    /api/pastes/:id/preview        Get type-specific preview
GET    /api/pastes/:id/thumbnail      Get thumbnail image
GET    /api/pastes/search             Search by content/tags/type
GET    /api/pastes                    List recent pastes
```

### Request/Response Pattern

- **Create**: Returns `{id, url, parent_id, version, fork_of?}`
- **Get**: Returns full metadata plus `content_type`, `size`, `created_at`, etc.
- **Diff**: Returns `{from_id, to_id, diff, additions, deletions}`
- **Preview**: Type-specific (images: metadata+thumbnail_url, CSV: rows+columns+preview+stats, etc.)

## Project Structure

```
paste/
├── backend/
│   ├── main.py              # FastAPI application and routes
│   ├── models.py            # SQLAlchemy ORM models (Paste, User, Tag)
│   ├── schemas.py           # Pydantic validation schemas
│   ├── database.py          # Database initialization and session management
│   ├── config.py            # Configuration (settings, env vars)
│   ├── storage.py           # S3/MinIO client wrapper
│   ├── processors.py        # File processors (text, code, images, PDFs, CSV, etc)
│   ├── utils.py             # Utilities (ID generation, hashing, expiry parsing)
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── App.svelte       # Main app component
│   │   ├── main.js          # Entry point
│   │   ├── app.css          # Tailwind styles
│   │   ├── components/
│   │   │   ├── Navigation.svelte
│   │   │   ├── HeroSection.svelte
│   │   │   ├── PasteForm.svelte
│   │   │   ├── PasteViewer.svelte
│   │   │   ├── PasteItem.svelte
│   │   │   ├── RecentPastes.svelte
│   │   │   ├── MyPastes.svelte
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
├── requirements.txt         # Python dependencies
├── Makefile                 # Development commands
├── docker-compose.yml       # MinIO and PostgreSQL services
├── .env                     # Environment variables
├── .gitignore
├── PASTE.md                 # Feature specification
├── CLAUDE.md                # This file
└── README.md                # User documentation
```

## Common Development Tasks

### Adding File Type Processing

File processors are in `backend/processors.py`. Each processor extends `ProcessorBase`:

1. Create a new processor class (e.g., `VideoProcessor`)
2. Implement `extract_metadata()` to parse file and return dict
3. Implement `generate_preview()` to return preview-specific data
4. Update `get_processor()` to route content types to your processor
5. Update `process_content()` if special handling needed

Example:
```python
class MyTypeProcessor(ProcessorBase):
    @staticmethod
    async def extract_metadata(content, content_type):
        return {"key": "value"}

    @staticmethod
    async def generate_preview(content, content_type):
        return {"type": "mytype", "preview": {...}}
```

### Handling Version Chains

For queries across version chains:
- **Get history**: Query with `root_id` and sort by `created_at`
- **Walk backward**: Follow `parent_id` pointers
- **Find children**: Query where `parent_id = :id`
- **Check if fork**: Look at `fork_of` field
- **Efficient lookup**: Always use `root_id` for chain operations, not recursive parent lookups

Example:
```python
# Get all versions in chain
db.query(Paste).filter(Paste.root_id == original_root_id).order_by(Paste.created_at)

# Get children
db.query(Paste).filter(Paste.parent_id == paste_id)
```

### Diff Implementation

In `backend/main.py`, diff endpoints:
- **Text/Code**: Use `difflib.unified_diff()` for line-by-line comparison
- **Binary**: Compare metadata only (size, dimensions, EXIF)
- **Syntax highlighting**: Apply Pygments to diff output (not yet implemented)

### Search & Filtering

Not yet implemented. Plan:
- **By content**: Full-text search (SQLite `MATCH`, PostgreSQL `tsvector`, or external index)
- **By tags**: Many-to-many via `paste_tags` table
- **By type**: Simple filter on `content_type` field
- **By user**: Filter on `user_id` field
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
- **Diff**: <200ms for 10KB text
- **History query**: <50ms

## Rate Limiting & Security

- **Upload**: 10 uploads/min per IP
- **Read**: 100 reads/min per IP
- **File type validation**: MIME detection (not just extension)
- **Size limits**: 100MB max
- **HTML sanitization**: Required for display
- **Authenticated deletion**: Only owner can delete
- **Expiration cleanup**: Hourly job to hard-delete expired pastes

## Key Implementation Decisions

1. **Immutability over editability**: This is the core philosophy - edits create new versions
2. **Soft delete**: Allows recovery and maintains referential integrity (children stay linked)
3. **S3 storage**: Scales to millions of pastes, supports any file type
4. **Base62 IDs**: URL-friendly, shorter than UUIDs
5. **Version chains**: Preserve complete history without manual tracking
6. **Smart processing**: Different previews for different types (syntax highlighting vs. image thumbnails vs. stats)
