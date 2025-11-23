# Relic - Professional Pastebin Service

A modern, feature-rich pastebin service with immutable pastes, complete version history, and smart content processing. Built with FastAPI (Python), Svelte, and Tailwind CSS.

## Features

- **Immutable Pastes**: Each paste is permanent. Edits create new versions with complete history preserved.
- **Version Lineage**: Track complete history through parent-child relationships and fork support.
- **Universal Content Support**: Text, code, images, PDFs, CSV/Excel, archives, and more.
- **Smart Processing**: Automatic syntax highlighting, thumbnail generation, metadata extraction.
- **Diff Support**: Compare any two pastes with full diff output.
- **Access Control**: Public, unlisted, and private pastes with optional password protection.
- **Expiration**: Set pastes to expire after 1h, 24h, 7d, 30d, or never.
- **Soft Delete**: Deleted pastes are recoverable and don't break version chains.

## Architecture

### Backend
- **FastAPI** for REST API
- **SQLAlchemy** for database ORM
- **MinIO/S3** for blob storage
- **Pygments** for syntax highlighting
- **Pillow** for image processing
- **SQLite** for development, PostgreSQL for production

### Frontend
- **Svelte** for reactive UI
- **Tailwind CSS** for styling
- **Axios** for API calls
- **Vite** for building and dev server

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional, for MinIO and PostgreSQL)

### Setup

1. **Clone and install dependencies**
```bash
make install
```

2. **Start Docker services (MinIO, PostgreSQL)**
```bash
make docker-up
```

3. **Run development server**
```bash
make dev
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (admin/admin)

## API Endpoints

### Paste Operations

**Create Paste**
```bash
curl -X POST http://localhost:8000/api/v1/pastes \
  -F "file=@myfile.txt" \
  -F "name=My File" \
  -F "access_level=public" \
  -F "expires_in=24h"
```

**Get Paste Metadata**
```bash
curl http://localhost:8000/api/v1/pastes/{id}
```

**Get Raw Content**
```bash
curl http://localhost:8000/{id}/raw
```

**Edit Paste (Create New Version)**
```bash
curl -X POST http://localhost:8000/api/v1/pastes/{id}/edit \
  -F "file=@updated.txt" \
  -F "name=Updated Name"
```

**Fork Paste (New Lineage)**
```bash
curl -X POST http://localhost:8000/api/v1/pastes/{id}/fork \
  -F "file=@forked.txt"
```

**Delete Paste**
```bash
curl -X DELETE http://localhost:8000/api/v1/pastes/{id}
```

### Version & Lineage

**Get Version History**
```bash
curl http://localhost:8000/api/v1/pastes/{id}/history
```

**Compare Two Pastes**
```bash
curl "http://localhost:8000/api/v1/diff?from={id1}&to={id2}"
```

**Compare with Parent**
```bash
curl http://localhost:8000/api/v1/pastes/{id}/diff
```

### Listing & Search

**List Recent Pastes**
```bash
curl "http://localhost:8000/api/v1/pastes?limit=50&offset=0"
```

## Data Model

### Paste Entity
- `id`: Unique identifier (base62, 7-8 chars)
- `user_id`: Owner (nullable for anonymous pastes)
- `name`: Display name
- `description`: Optional description
- `content_type`: MIME type
- `language_hint`: Programming language for code
- `size_bytes`: Content size
- `parent_id`: Reference to previous version
- `root_id`: Reference to first paste in chain
- `version_number`: Sequential version (1, 2, 3...)
- `fork_of`: Reference to source paste if forked
- `s3_key`: Storage location in S3
- `access_level`: public/unlisted/private
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp (null = never)
- `deleted_at`: Soft delete timestamp (null = active)
- `access_count`: View counter
- `metadata`: JSON field for processing metadata

### Relationships
- Each paste has 0 or 1 parent
- Each paste has 0 to N children
- Each paste belongs to 0 or 1 user
- Each paste can have 0 to N tags

## Development Commands

```bash
make help          # Show all available commands
make install       # Install dependencies
make dev           # Run backend and frontend
make backend       # Run backend only
make frontend      # Run frontend only
make test          # Run tests
make clean         # Clean up generated files
make docker-up     # Start Docker services
make docker-down   # Stop Docker services
make db-init       # Initialize database
```

## Environment Variables

See `.env` file for configuration:
- `DEBUG`: Enable debug mode
- `DATABASE_URL`: Database connection string
- `S3_ENDPOINT_URL`: MinIO/S3 endpoint
- `S3_ACCESS_KEY`: S3 access key
- `S3_SECRET_KEY`: S3 secret key
- `S3_BUCKET_NAME`: S3 bucket name
- `MAX_UPLOAD_SIZE`: Maximum upload size (bytes)
- `SECRET_KEY`: JWT secret for authentication

## File Processing

Different content types receive smart processing:

### Text Files
- Line count, character count, word count
- Encoding detection

### Code Files
- Syntax highlighting with Pygments
- Language auto-detection
- Line numbers

### Images
- EXIF metadata extraction
- Thumbnail generation (200x200)
- Dimensions and color space

### PDF Documents
- Page count
- First page preview
- Text extraction
- Metadata (author, title, creation date)

### CSV/Excel
- Column detection and types
- Row count
- Data preview (first 10 rows)
- Basic statistics (mean, min, max)

### Videos/Archives
- Metadata extraction (duration, resolution, codecs)
- File preview without extraction

## Version Lineage Example

```
Original:  a3Bk9Zx (v1)
  ├─ Edit: b4Ck2Ty (v2, parent: a3Bk9Zx, root: a3Bk9Zx)
  │   └─ Edit: c5Dm3Uz (v3, parent: b4Ck2Ty, root: a3Bk9Zx)
  └─ Fork: x7Yz8Wx (v1, fork_of: a3Bk9Zx, root: x7Yz8Wx)
      └─ Edit: y8Za9Xy (v2, parent: x7Yz8Wx, root: x7Yz8Wx)
```

All versions remain accessible at their unique URLs. Complete history is preserved.

## Performance Targets

- Upload: <500ms for <1MB files
- Retrieval: <100ms
- Diff: <200ms for 10KB text
- History query: <50ms

## Rate Limiting

- Upload: 10 per minute per IP
- Read: 100 per minute per IP

## Security

- File type validation via MIME detection
- Size limits enforced (100MB default)
- HTML sanitization for display
- Authenticated deletion (owner only)
- Soft delete preserves privacy
- No content indexing for private pastes

## Testing

```bash
make test
```

## Deployment

### Production Database
Replace SQLite with PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/paste_db
```

### Production Storage
Configure S3-compatible storage or AWS S3:

```env
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=your-key
S3_SECRET_KEY=your-secret
S3_BUCKET_NAME=Relic
```

### Docker Deployment
See `docker-compose.yml` for local development. For production, use managed services (RDS for database, S3 for storage, etc.)

## Contributing

See CLAUDE.md for architecture and development guidelines.

## License

MIT
