# RelicBin Feature Specification

## Overview

Modern artifacts service with immutable artifacts, version lineage tracking, and rich file processing. Users can share text, code, images, documents, and any binary content. Each relic is permanent with a unique URL. Edits create new relics linked to the original.

## Core Features

### 1. Immutable Relics

**Concept:**
- Relics cannot be edited after creation
- Each relic has a unique ID and permanent URL
- "Editing" creates a new relic linked to the original
- Complete version history preserved through parent-child relationships

**Example:**
```
Original relic:  f47ac10b58cc4372a5670e02b2c3d479  → /f47ac10b58cc4372a5670e02b2c3d479
User edits:      a1b2c3d4e5f678901234567890abcdef  → /a1b2c3d4e5f678901234567890abcdef  (parent: f47ac...)
User edits:      1234567890abcdef1234567890abcdef  → /1234567890abcdef1234567890abcdef  (parent: a1b2c...)

All three URLs remain accessible
Lineage tracked: f47ac... → a1b2c... → 12345...
```

### 2. Version Lineage Tracking

**Version Chain:**
- Each relic knows its parent (previous version)
- Each relic knows its root (original in chain)
- Sequential version numbers (1, 2, 3...)
- Full history queryable

**Fork Support:**
- Users can fork any relic to start new lineage
- Fork creates independent version chain
- Original lineage preserved
- Attribution tracked via `fork_of` field


### 3. Universal Content Support

**Supported Types:**
- Text files (plain text, logs, configs)
- Source code (500+ languages)
- Images (PNG, JPEG, GIF, WebP, SVG)
- Documents (PDF, Office files)
- Data files (CSV, Excel, JSON, XML)
- Videos (MP4, WebM, AVI)
- Audio (MP3, WAV, OGG)
- Archives (ZIP, TAR, 7Z)
- Binary files (any content type)

**All content types are:**
- Versionable (can be edited → new relic)
- Diffable (text) or comparable (binary)
- Processable (smart previews based on type)

### 4. Smart File Processing

**Images:**
- Automatic thumbnail generation (200x200)
- EXIF metadata extraction
- Dimensions, format, color space
- Image optimization

**PDF Documents:**
- Page count
- First page preview image
- Text extraction
- Metadata (author, title, creation date)

**CSV/Excel Data:**
- Column names and types
- Row count
- Preview: first 10 rows
- Basic statistics (mean, min, max for numeric columns)
- Detect encoding

**Source Code:**
- Syntax highlighting (500+ languages via Pygments)
- Auto-detect language from content
- Line numbers
- Code formatting (optional)
- Complexity analysis (optional)

**Videos:**
- Thumbnail extraction (first frame, middle frame)
- Duration, resolution, codec
- File size, bitrate

**Archives:**
- List all files in archive
- Total size, file count
- Preview without extraction

### 5. Diff & Comparison

**Text Content:**
- Unified diff format
- Line-by-line comparison
- Additions/deletions highlighted
- Syntax-highlighted diffs for code
- Show stats: +N lines, -N lines

**Binary Content:**
- Metadata comparison (size, dimensions)
- Cannot show line-by-line diff
- Visual side-by-side for images (optional)

**Diff Endpoints:**
- Compare any two relics
- Compare relic with its parent
- Compare across version chain

### 6. User Features

**Relic Management:**
- Create relic (upload file or relic text)
- View relic (with processing/preview)
- Edit relic (creates new version)
- Fork relic (creates new lineage)
- Delete relic (soft delete, user must own it)
- Tag relics for organization

**Discovery:**
- List recent relics
- Search by content, tags, type
- Filter by content type
- User's relic history

**Expiration:**
- Optional TTL: 1h, 24h, 7d, 30d, never
- Default: never expires
- Expired relics auto-deleted
- Version chains: if parent expires, children unaffected

**Access Control:**
- Public: anyone can view
- Unlisted: only via direct URL
- Private: only owner can view (requires auth)
- Anonymous relics (no client association)
- Authenticated relics (with client association)

## Data Model

### Relic Entity

```
id              Unique identifier (32-char hex string)
client_id       Client identification (null for anonymous)
name            Optional display name
description     Optional description

parent_id       Previous version (null if original)
root_id         First relic in version chain
version_number  Sequential position (1, 2, 3...)
fork_of         Source relic if forked

content_type    MIME type
language_hint   Programming language (for code)
size_bytes      Content size

s3_key          Storage location
created_at      Creation timestamp
expires_at      Expiration timestamp (null = never)
deleted_at      Soft delete timestamp (null = active)
access_count    View counter
```

### Relationships

- Each relic has 0 or 1 parent
- Each relic has 0 to N children
- Each relic belongs to 0 or 1 user
- Each relic can have 0 to N tags

## API Endpoints

### Relic Operations

**Create Relic**
```
POST /api/v1/relics
Body: {content, name?, type?, language?, expires?, tags?}
Returns: {id, url, parent_id, version}
```

**Get Relic**
```
GET /api/v1/relics/:id
Returns: {id, name, content_type, size, parent_id, root_id, version, ...}
```

**Get Raw Content**
```
GET /:id/raw
Returns: raw file content with appropriate Content-Type
```

**Edit Relic (Create New Version)**
```
POST /api/v1/relics/:id/edit
Body: {content, name?}
Returns: {id: new_id, url, parent_id: old_id, version}
```

**Fork Relic (New Lineage)**
```
POST /api/v1/relics/:id/fork
Body: {content?, name?}
Returns: {id: new_id, url, fork_of: old_id, version: 1}
```

**Delete Relic**
```
DELETE /api/v1/relics/:id
Requires: Authentication (must own relic)
Returns: 204 No Content
```

### Version Operations

**Get Version History**
```
GET /api/relics/:id/history
Returns: {root_id, current, versions: [{id, version, created_at, size}, ...]}
```

**Get Parent**
```
GET /api/relics/:id/parent
Returns: {id, name, content_type, ...}
```

**Get Children**
```
GET /api/relics/:id/children
Returns: {children: [{id, version, created_at}, ...]}
```

**Diff Two Relics**
```
GET /api/diff?from=:id1&to=:id2
Returns: {from_id, to_id, diff, additions, deletions}
```

**Diff With Parent**
```
GET /api/relics/:id/diff
Returns: {from_id: parent, to_id: id, diff, additions, deletions}
```

### Processing Operations

**Get Preview**
```
GET /api/relics/:id/preview
Returns: Type-specific preview:
  - Images: {metadata, thumbnail_url}
  - CSV: {rows, columns, preview[], stats}
  - Code: {language, highlighted_html, lines}
  - PDF: {pages, preview_image_url}
```

**Get Thumbnail**
```
GET /api/relics/:id/thumbnail
Returns: Generated thumbnail image (for images/PDFs)
```

**Search Relics**
```
GET /api/relics/search?q=query&type=code&tag=python&user=me
Returns: {relics: [...], total, page}
```

**List Recent Relic**
```
GET /api/relics?limit=50&offset=0&sort=created_at
Returns: {relics: [...], total}
```

## User Workflows

### Workflow 1: Create and Edit

```
1. User uploads file
   POST /api/relics {content: "hello"}
   → Relic a3Bk9Zx created

2. View relic
   GET /a3Bk9Zx
   → Shows content with syntax highlighting

3. User wants to fix typo
   POST /api/relics/a3Bk9Zx/edit {content: "hello world"}
   → New relic b4Ck2Ty created (parent: a3Bk9Zx)

4. Both URLs still work
   GET /a3Bk9Zx → original version
   GET /b4Ck2Ty → edited version

5. View history
   GET /api/relics/b4Ck2Ty/history
   → Shows: a3Bk9Zx (v1), b4Ck2Ty (v2)

6. Compare versions
   GET /api/diff?from=a3Bk9Zx&to=b4Ck2Ty
   → Shows: +world
```

### Workflow 2: Fork and Diverge

```
1. User A creates relic
   POST /api/relics {content: "function foo() {}"}
   → Relic a3Bk9Zx

2. User B finds it and wants to modify
   POST /api/relics/a3Bk9Zx/fork {content: "function foo() { return 42; }"}
   → Relic x7Yz8Wx (fork_of: a3Bk9Zx)

3. User B continues editing their fork
   POST /api/relics/x7Yz8Wx/edit {content: "function foo(x) { return x * 2; }"}
   → Relic y8Za9Xy (parent: x7Yz8Wx)

4. Two separate lineages exist:
   Original: a3Bk9Zx
   Fork: x7Yz8Wx → y8Za9Xy
```

### Workflow 3: Image Upload & Preview

```
1. User uploads screenshot
   POST /api/relics {content: screenshot.png, type: image/png}
   → Relic c5Dm3Uz

2. Backend processes image:
   - Extract EXIF data
   - Generate thumbnail
   - Get dimensions

3. View relic
   GET /c5Dm3Uz
   → Shows image viewer with metadata

4. Get thumbnail for listing
   GET /api/relics/c5Dm3Uz/thumbnail
   → Returns 200x200 thumbnail

5. User uploads updated screenshot
   POST /api/relics/c5Dm3Uz/edit {content: screenshot_v2.png}
   → Relic d6En4Va (parent: c5Dm3Uz)

6. Compare images
   GET /api/diff?from=c5Dm3Uz&to=d6En4Va
   → Shows metadata comparison (size changed, dimensions same)
```

### Workflow 4: Data File Analysis

```
1. User uploads CSV
   POST /api/relics {content: data.csv, type: text/csv}
   → Relic e7Fp5Wb

2. Backend processes CSV:
   - Parse columns
   - Count rows
   - Calculate statistics
   - Generate preview

3. View preview
   GET /api/relics/e7Fp5Wb/preview
   → Returns: {
       rows: 1500,
       columns: ["id", "name", "value"],
       preview: [{id: 1, name: "foo", value: 100}, ...],
       stats: {value: {mean: 150, min: 10, max: 500}}
     }
```

### Workflow 5: Code Collaboration

```
1. Developer shares code
   POST /api/relics {content: "def hello():\n  print('hi')", language: python}
   → Relic f8Gq6Xc

2. Colleague reviews and improves
   POST /api/relics/f8Gq6Xc/edit {content: "def hello(name):\n  print(f'Hello {name}')" }
   → Relic g9Hr7Yd

3. View diff with syntax highlighting
   GET /api/diff?from=f8Gq6Xc&to=g9Hr7Yd
   → Shows colorized diff with Python syntax

4. Original developer sees history
   GET /api/relics/g9Hr7Yd/history
   → f8Gq6Xc (v1) → g9Hr7Yd (v2)
```

## Technical Constraints

### Storage
- Max upload size: 100MB (configurable)
- Supported: Any file type
- Storage: S3-compatible (MinIO)
- Each relic = one S3 object
- No S3 versioning needed (immutable model)

### Performance
- Upload: <500ms for <1MB files
- Retrieval: <100ms
- Diff: <200ms for 10KB text
- History query: <50ms

### Security
- Rate limiting: 10 uploads/min, 100 reads/min per IP
- File type validation via MIME detection
- Size limits enforced
- HTML sanitization for display
- Authenticated deletion only

### Expiration
- Options: 1h, 24h, 7d, 30d, never
- Default: never
- Auto-cleanup of expired relics (hourly job)
- Soft-deleted relics: hard delete after 30 days

## Non-Functional Requirements

### Scalability
- Support for millions of relics
- Horizontal scaling (multiple API servers)
- Distributed storage (MinIO multi-node)

### Reliability
- Immutable storage (no data loss from edits)
- Soft delete (accidental deletion recovery)
- Complete audit trail via version lineage

### Usability
- Clean URLs: /a3Bk9Zx not /relic?id=123
- Fast previews via background processing
- Smart content detection
- Intuitive version history navigation

### Privacy
- Anonymous uploads supported
- User-owned relics (with auth)
- Soft delete preserves privacy
- No content indexing for private relics
