# Pastebin Feature Specification

## Overview

Modern pastebin service with immutable pastes, version lineage tracking, and rich file processing. Users can share text, code, images, documents, and any binary content. Each paste is permanent with a unique URL. Edits create new pastes linked to the original.

## Core Features

### 1. Immutable Pastes

**Concept:**
- Pastes cannot be edited after creation
- Each paste has a unique ID and permanent URL
- "Editing" creates a new paste linked to the original
- Complete version history preserved through parent-child relationships

**Example:**
```
Original paste:  a3Bk9Zx  → /a3Bk9Zx
User edits:      b4Ck2Ty  → /b4Ck2Ty  (parent: a3Bk9Zx)
User edits:      c5Dm3Uz  → /c5Dm3Uz  (parent: b4Ck2Ty)

All three URLs remain accessible
Lineage tracked: a3Bk9Zx → b4Ck2Ty → c5Dm3Uz
```

### 2. Version Lineage Tracking

**Version Chain:**
- Each paste knows its parent (previous version)
- Each paste knows its root (original in chain)
- Sequential version numbers (1, 2, 3...)
- Full history queryable

**Fork Support:**
- Users can fork any paste to start new lineage
- Fork creates independent version chain
- Original lineage preserved
- Attribution tracked via `fork_of` field

**Relationships:**
```
Original:  a3Bk9Zx (v1)
  ├─ Edit: b4Ck2Ty (v2)
  │   └─ Edit: c5Dm3Uz (v3)
  └─ Fork: x7Yz8Wx (v1, new lineage)
      └─ Edit: y8Za9Xy (v2)
```

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
- Versionable (can be edited → new paste)
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
- Compare any two pastes
- Compare paste with its parent
- Compare across version chain

### 6. User Features

**Paste Management:**
- Create paste (upload file or paste text)
- View paste (with processing/preview)
- Edit paste (creates new version)
- Fork paste (creates new lineage)
- Delete paste (soft delete, user must own it)
- Tag pastes for organization

**Discovery:**
- List recent pastes
- Search by content, tags, type
- Filter by content type
- User's paste history

**Expiration:**
- Optional TTL: 1h, 24h, 7d, 30d, never
- Default: never expires
- Expired pastes auto-deleted
- Version chains: if parent expires, children unaffected

**Access Control:**
- Public: anyone can view
- Unlisted: only via direct URL
- Private: only owner can view (requires auth)
- Anonymous pastes (no user_id)
- Authenticated pastes (with user_id)

## Data Model

### Paste Entity

```
id              Unique identifier (base62, 7-8 chars)
user_id         Owner (null for anonymous)
name            Optional display name
description     Optional description

parent_id       Previous version (null if original)
root_id         First paste in version chain
version_number  Sequential position (1, 2, 3...)
fork_of         Source paste if forked

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

- Each paste has 0 or 1 parent
- Each paste has 0 to N children
- Each paste belongs to 0 or 1 user
- Each paste can have 0 to N tags

## API Endpoints

### Paste Operations

**Create Paste**
```
POST /api/pastes
Body: {content, name?, type?, language?, expires?, tags?}
Returns: {id, url, parent_id, version}
```

**Get Paste**
```
GET /api/pastes/:id
Returns: {id, name, content_type, size, parent_id, root_id, version, ...}
```

**Get Raw Content**
```
GET /:id/raw
Returns: raw file content with appropriate Content-Type
```

**Edit Paste (Create New Version)**
```
POST /api/pastes/:id/edit
Body: {content, name?}
Returns: {id: new_id, url, parent_id: old_id, version}
```

**Fork Paste (New Lineage)**
```
POST /api/pastes/:id/fork
Body: {content?, name?}
Returns: {id: new_id, url, fork_of: old_id, version: 1}
```

**Delete Paste**
```
DELETE /api/pastes/:id
Requires: Authentication (must own paste)
Returns: 204 No Content
```

### Version Operations

**Get Version History**
```
GET /api/pastes/:id/history
Returns: {root_id, current, versions: [{id, version, created_at, size}, ...]}
```

**Get Parent**
```
GET /api/pastes/:id/parent
Returns: {id, name, content_type, ...}
```

**Get Children**
```
GET /api/pastes/:id/children
Returns: {children: [{id, version, created_at}, ...]}
```

**Diff Two Pastes**
```
GET /api/diff?from=:id1&to=:id2
Returns: {from_id, to_id, diff, additions, deletions}
```

**Diff With Parent**
```
GET /api/pastes/:id/diff
Returns: {from_id: parent, to_id: id, diff, additions, deletions}
```

### Processing Operations

**Get Preview**
```
GET /api/pastes/:id/preview
Returns: Type-specific preview:
  - Images: {metadata, thumbnail_url}
  - CSV: {rows, columns, preview[], stats}
  - Code: {language, highlighted_html, lines}
  - PDF: {pages, preview_image_url}
```

**Get Thumbnail**
```
GET /api/pastes/:id/thumbnail
Returns: Generated thumbnail image (for images/PDFs)
```

**Search Pastes**
```
GET /api/pastes/search?q=query&type=code&tag=python&user=me
Returns: {pastes: [...], total, page}
```

**List Recent Pastes**
```
GET /api/pastes?limit=50&offset=0&sort=created_at
Returns: {pastes: [...], total}
```

## User Workflows

### Workflow 1: Create and Edit

```
1. User uploads file
   POST /api/pastes {content: "hello"}
   → Paste a3Bk9Zx created

2. View paste
   GET /a3Bk9Zx
   → Shows content with syntax highlighting

3. User wants to fix typo
   POST /api/pastes/a3Bk9Zx/edit {content: "hello world"}
   → New paste b4Ck2Ty created (parent: a3Bk9Zx)

4. Both URLs still work
   GET /a3Bk9Zx → original version
   GET /b4Ck2Ty → edited version

5. View history
   GET /api/pastes/b4Ck2Ty/history
   → Shows: a3Bk9Zx (v1), b4Ck2Ty (v2)

6. Compare versions
   GET /api/diff?from=a3Bk9Zx&to=b4Ck2Ty
   → Shows: +world
```

### Workflow 2: Fork and Diverge

```
1. User A creates paste
   POST /api/pastes {content: "function foo() {}"}
   → Paste a3Bk9Zx

2. User B finds it and wants to modify
   POST /api/pastes/a3Bk9Zx/fork {content: "function foo() { return 42; }"}
   → Paste x7Yz8Wx (fork_of: a3Bk9Zx)

3. User B continues editing their fork
   POST /api/pastes/x7Yz8Wx/edit {content: "function foo(x) { return x * 2; }"}
   → Paste y8Za9Xy (parent: x7Yz8Wx)

4. Two separate lineages exist:
   Original: a3Bk9Zx
   Fork: x7Yz8Wx → y8Za9Xy
```

### Workflow 3: Image Upload & Preview

```
1. User uploads screenshot
   POST /api/pastes {content: screenshot.png, type: image/png}
   → Paste c5Dm3Uz

2. Backend processes image:
   - Extract EXIF data
   - Generate thumbnail
   - Get dimensions

3. View paste
   GET /c5Dm3Uz
   → Shows image viewer with metadata

4. Get thumbnail for listing
   GET /api/pastes/c5Dm3Uz/thumbnail
   → Returns 200x200 thumbnail

5. User uploads updated screenshot
   POST /api/pastes/c5Dm3Uz/edit {content: screenshot_v2.png}
   → Paste d6En4Va (parent: c5Dm3Uz)

6. Compare images
   GET /api/diff?from=c5Dm3Uz&to=d6En4Va
   → Shows metadata comparison (size changed, dimensions same)
```

### Workflow 4: Data File Analysis

```
1. User uploads CSV
   POST /api/pastes {content: data.csv, type: text/csv}
   → Paste e7Fp5Wb

2. Backend processes CSV:
   - Parse columns
   - Count rows
   - Calculate statistics
   - Generate preview

3. View preview
   GET /api/pastes/e7Fp5Wb/preview
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
   POST /api/pastes {content: "def hello():\n  print('hi')", language: python}
   → Paste f8Gq6Xc

2. Colleague reviews and improves
   POST /api/pastes/f8Gq6Xc/edit {content: "def hello(name):\n  print(f'Hello {name}')" }
   → Paste g9Hr7Yd

3. View diff with syntax highlighting
   GET /api/diff?from=f8Gq6Xc&to=g9Hr7Yd
   → Shows colorized diff with Python syntax

4. Original developer sees history
   GET /api/pastes/g9Hr7Yd/history
   → f8Gq6Xc (v1) → g9Hr7Yd (v2)
```

## Technical Constraints

### Storage
- Max upload size: 100MB (configurable)
- Supported: Any file type
- Storage: S3-compatible (MinIO)
- Each paste = one S3 object
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
- Auto-cleanup of expired pastes (hourly job)
- Soft-deleted pastes: hard delete after 30 days

## Non-Functional Requirements

### Scalability
- Support for millions of pastes
- Horizontal scaling (multiple API servers)
- Distributed storage (MinIO multi-node)

### Reliability
- Immutable storage (no data loss from edits)
- Soft delete (accidental deletion recovery)
- Complete audit trail via version lineage

### Usability
- Clean URLs: /a3Bk9Zx not /paste?id=123
- Fast previews via background processing
- Smart content detection
- Intuitive version history navigation

### Privacy
- Anonymous uploads supported
- User-owned pastes (with auth)
- Soft delete preserves privacy
- No content indexing for private pastes
