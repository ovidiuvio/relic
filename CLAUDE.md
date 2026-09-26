# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Relic** is a professional artifact storage service with immutable artifacts. Built with FastAPI (Python) and Svelte 5, styled with the Relic design system.

Key principle: Relics cannot be edited after creation - they are permanent and immutable. To modify content, create a fork which creates an independent copy.

### Tech Stack
- **Infrastructure**: Docker + Nginx (Reverse Proxy)
- **Backend**: FastAPI + SQLAlchemy + MinIO/S3
- **Frontend**: Svelte 5 + Vite + Axios, styled with the Relic design system (tokens and component classes); Tailwind remains for base styles and older markup
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
- `user_id`: User identification key (nullable for anonymous)
- `name`: Optional display name
- `description`: Optional description
- `content_type`: MIME type of the stored content
- `language_hint`: Optional language hint for syntax highlighting
- `size_bytes`: Size of the content in bytes
- `s3_key`: Storage location (format: `relics/{id}`)
- `access_level`: public (listed in recents) or private (URL is the access token)
- `password_hash`: Optional password protection
- `created_at`, `expires_at`: Timestamps
- `access_count`: Number of times the relic has been accessed

### 2. Universal Content Support

The system handles **any file type** (text, code, images, PDFs, CSVs, archives, relic indexes, etc.):

- **Text/Code**: Displayed with syntax highlighting support via language hints
- **Images**: Displayed as-is with size information
- **PDFs**: Downloaded and can be viewed in browser
- **CSV/Excel**: Downloaded and can be opened in external tools
- **Videos/Archives**: Downloaded and can be processed locally
- **Relic Indexes (.rix)**: Collections of relics with custom metadata and progressive loading


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
- **Anonymous relics**: No user association
- **URL format**: 32-character hexadecimal (GitHub Gist-style), cryptographically secure, practically collision-proof

## Storage Architecture

- **Primary storage**: S3-compatible (MinIO) - one object per relic
- **Database**: Stores metadata (id, user_id, fork_of, content_type, language_hint, size_bytes, s3_key, created_at, expires_at, access_count, tags, etc.)
- **Max upload**: 100MB (configurable)
- **No S3 versioning needed**: Immutable model means each relic is independent

## API Structure

### Key Endpoint Patterns

All API endpoints are prefixed with `/api/v1` and served via Nginx at `http://localhost`.

```
POST   /api/v1/relics                  Create relic
GET    /api/v1/relics/:id              Get relic metadata
PUT    /api/v1/relics/:id              Update relic metadata
GET    /:id/raw                        Get raw content (served from root)
POST   /api/v1/relics/:id/fork         Create fork (independent copy)
DELETE /api/v1/relics/:id              Delete relic (owner OR admin)

GET    /api/v1/relics                  List recent public relics
```

### Admin Endpoints

Admin endpoints require the `X-User-Key` header of an admin: a super admin listed in the `ADMIN_USER_IDS` env var, or a user granted admin at runtime (`User.is_admin`).

```
GET    /api/v1/admin/check                   Check admin status (no auth required)
GET    /api/v1/admin/stats                   System statistics
GET    /api/v1/admin/relics                  All relics, including private (same list params as below)
GET    /api/v1/admin/users                   All users
DELETE /api/v1/admin/users/:id               Delete a user (?delete_relics=true to delete their relics too)
GET    /api/v1/admin/admins                  Effective admins (super and runtime)
POST   /api/v1/admin/admins                  Grant admin by public ID
POST   /api/v1/admin/users/:id/admin         Grant admin
DELETE /api/v1/admin/users/:id/admin         Revoke admin (not for super admins)
GET    /api/v1/admin/config                  Server configuration
GET    /api/v1/admin/reports                 Reported relics
DELETE /api/v1/admin/reports/:id             Dismiss a report
GET    /api/v1/admin/backups                 Database backups
POST   /api/v1/admin/backups                 Back up now
GET    /api/v1/admin/backups/:file/download  Download a backup
POST   /api/v1/admin/backups/:file/restore   Restore from a stored backup
POST   /api/v1/admin/backups/restore-upload  Restore from an uploaded .sql.gz
GET    /api/v1/admin/jobs                    Scheduled jobs and their run history
POST   /api/v1/admin/jobs/:id/run|pause|resume
```

Admins see everything by design (keys, private relics, full config); don't add redaction inside the admin area.

**Admin Privileges:**
- Delete any relic (not just their own)
- View all relics including private ones via admin endpoints
- View all registered users
- Delete users (and optionally their relics)
- View system statistics

**Setting Up Admin Users:**
1. Get the user's key: it is shown once, in the banner on the first visit (copy or download it then). The key lives in a service-worker vault (`public/vault-sw.js`), not in `localStorage`; an existing admin can also reveal it in Admin · Users.
2. Add it to `ADMIN_USER_IDS` in `docker-compose.prod.yml` (comma-separated for multiple admins)
3. Restart services with `make down && make up`
4. Admin appears in the navbar and opens the admin area at `/admin`. More admins can then be granted there by public ID (Admin · Config), without a restart.

### Request/Response Pattern

- **Create**: Returns `{id, url, fork_of?, created_at}`
- **Get**: Returns full metadata including `id`, `name`, `description`, `content_type`, `language_hint`, `size_bytes`, `fork_of`, `access_level`, `created_at`, `expires_at`, `access_count`, `bookmark_count`, `can_edit`, `tags`.
- **Fork**: Returns `{id, url, fork_of, created_at}`


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
│   ├── dependencies.py      # FastAPI dependencies
│   ├── profiling.py         # Profiling utilities
│   ├── scheduler.py         # Background task scheduler
│   ├── tasks.py             # Background tasks
│   ├── entrypoint.sh        # Docker entrypoint
│   ├── routes/              # API route handlers
│   │   ├── admin.py
│   │   ├── bookmarks.py
│   │   ├── comments.py
│   │   ├── health.py
│   │   ├── relics.py
│   │   ├── reports.py
│   │   ├── spaces.py
│   │   └── users.py
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── App.svelte       # Shell: navbar, sidebar, key banner, route outlet
│   │   ├── main.js          # Entry point
│   │   ├── routes.js        # Path patterns → lazy-loaded pages
│   │   ├── app.css          # Global styles; imports tokens, components and inspector CSS
│   │   ├── design-system/   # Relic design system: tokens.json/.css, components.css (r-* classes), icons.json
│   │   ├── styles/          # tailwind-base.css, inspector.css
│   │   ├── pages/           # One component per route
│   │   │   ├── NewRelic.svelte, Fork.svelte
│   │   │   ├── Recent.svelte, MyRelics.svelte, Bookmarks.svelte
│   │   │   ├── Spaces.svelte, Space.svelte
│   │   │   ├── RelicView.svelte
│   │   │   └── Admin.svelte
│   │   ├── lib/
│   │   │   ├── shell/       # Frame: NavBar, NavSearch, Sidebar, BottomTabs, PageBar, Workbench,
│   │   │   │                #   inspectorPanel, layout tiers, KeyBanner, ProfileMenu
│   │   │   ├── ui/          # Icon, DataList (generic list), Combobox, Toasts, RelicMark
│   │   │   ├── data/        # PagedFeed (paged, search/sort-aware list loading, facets)
│   │   │   ├── relics/      # RelicList, RelicWorkbench, TypeFacets, TagPicker, format, filters
│   │   │   │   ├── inspector/  # RelicInspector and its sections (details, lineage, comments…)
│   │   │   │   └── fields/     # Visibility, expiry, tags and space fields
│   │   │   ├── viewer/      # ContentView, ViewerStatusBar, FilterStrip, RelicIndexView,
│   │   │   │                #   listContext (previous/next), viewerPrefs
│   │   │   ├── compose/     # New relic: drafts, uploads, create, ComposeInspector
│   │   │   ├── spaces/      # SpaceList, SpaceInspector, SpaceForm, PeopleSection
│   │   │   └── admin/       # Admin sections (overview, relics, users, reports, backups, jobs,
│   │   │                    #   config), their inspectors, AdminNav, shared admin state
│   │   ├── components/      # Editors and renderers kept from the old UI
│   │   │   ├── MonacoEditor.svelte, ForkEditor.svelte, CommentEditor.svelte, PDFViewer.svelte
│   │   │   └── renderers/   # Archive, Code, Csv, Diff, Excalidraw, Html, Image, Markdown, Tree
│   │   ├── stores/          # session, pageTitle, toastStore, userStore
│   │   ├── services/
│   │   │   ├── api.js, api/ # Axios client (core.js), one module per resource
│   │   │   ├── processors/  # Content processing per type (incl. relicIndexProcessor.js)
│   │   │   ├── relicActions.js, typeUtils.js
│   │   │   ├── data/, utils/
│   │   └── utils/           # navigation, lineNumbers
│   ├── public/              # vault-sw.js (key vault service worker), fonts, favicon
│   ├── scripts/             # build-tokens.mjs (tokens.json → tokens.css)
│   ├── index.html
│   ├── vite.config.mjs
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── cli/client/              # Go CLI client
│   ├── cmd/
│   ├── internal/
│   └── pkg/
├── sync/                    # S3 Sync service
│   └── Dockerfile
├── requirements.in          # Direct Python dependencies (edit this)
├── requirements.txt         # Pinned lock generated by `make deps-lock`
├── Makefile                 # Build and deployment commands
├── docker-compose.dev.yml   # Development: hot-reload, volume mounts
├── docker-compose.prod.yml  # Production: optimized builds, restart policies
├── nginx.conf               # Nginx configuration (dev only)
├── .env                     # Environment variables
├── .gitignore
├── RELIC.md                 # Feature specification
├── CLAUDE.md                # This file
└── README.md                # User documentation
```

## Docker Compose Setup

The project uses two separate Docker Compose configurations:

### Production (`docker-compose.prod.yml`) - Default
- **Purpose**: Production/release deployments
- **Frontend**: Built static files served via Nginx (`frontend/Dockerfile.prod`)
- **Backend**: Production build (`backend/Dockerfile.prod`)
- **Features**: Optimized builds, restart policies, no volume mounts
- **Commands**: `make up`, `make down`, `make logs`, `make build`

### Development (`docker-compose.dev.yml`)
- **Purpose**: Local development with hot-reload
- **Frontend**: Vite dev server with volume mounts for live updates
- **Backend**: Uvicorn with `--reload` flag and volume mounts
- **Features**: Hot-reload, code volumes, separate Nginx container
- **Commands**: `make dev-up`, `make dev-down`, `make dev-logs`, `make dev-build`

**Important**: By default, `make up` starts **production** services. Use `make dev-up` for development.

## Common Development Tasks

### Handling Relic Indexes

Relic indexes are processed entirely on the frontend:

**File Type Detection** (`typeUtils.js`):
- Extension: `.rix`
- MIME type: `application/x-relic-index`
- Category: `relicindex`

**Content Processing** (`services/processors/relicIndexProcessor.js`):
- `isRelicIndex(content, contentType)`: Auto-detect if content is a relic index
  - Check for MIME type `application/x-relic-index`
  - Check for structured format signature (`relics:` and `- id:`)
  - Heuristic: >50% of lines match ID pattern `[a-f0-9]{32}`
- `processRelicIndex(content)`: Parse the .rix file
  - Detect format (structured YAML vs simple list)
  - Extract metadata (title, description)
  - Parse relic array with overrides (title, description, tags)
  - Return `{type: 'relicindex', relics: [...], meta: {...}}`

**Rendering** (`lib/viewer/RelicIndexView.svelte`):
- Progressive loading in batches of 5
- Fetch each relic via `getRelic(id)`
- Apply metadata overrides from index
- Display in the standard `RelicList`, with filter, tag and sort done in the page
- Handle errors gracefully (show placeholder for failed relics)

**Integration**:
- `ContentView.svelte` shows `RelicIndexView` when `processed.type === 'relicindex'`
- Selecting a listed relic shows it in the viewer's inspector (with a "Back to …" strip); phones open it instead
- All standard relic actions available (share, copy, fork, download)

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

The relic lists (`GET /api/v1/relics`, `/api/v1/user/relics`, `/api/v1/bookmarks`, `/api/v1/spaces/:id/relics`, `/api/v1/admin/relics`, `/api/v1/search`) share these parameters, built from helpers in `backend/utils.py`:
- `search`: every word must match the name, ID, description or a tag name, case-insensitively and in any order; `"quoted phrases"` match whole (`search_terms`, `apply_relic_search`)
- `tag`: one tag name
- `types`: comma-separated content types; parameters like `; charset=` are ignored on both sides (`parse_types`, `apply_type_filter`)
- `owner`: a public ID, or a display name (case-insensitive; may match several people) (`apply_owner_filter`)
- `access_level`: public, private or restricted (`apply_visibility_filter`; the user list validates it itself)
- `created_after` / `created_before`: ISO datetimes (after inclusive, before exclusive); `min_size` / `max_size`: bytes, inclusive (`apply_range_filters`)
- `facets=true`: adds `facets: {types: {content_type: count}, tags: [{name, count}]}`; type counts ignore the type filter so each type facet shows what it would give, tag counts apply it (`relic_facets`)
- `sort_by` / `sort_order`: `created_at`, `name`, `owner`, `size`, `access_count`, `bookmark_count`, `comments_count`, `forks_count`, and `relevance` (best name matches for `search` first; not on the admin list); ties break by newest then ID so offset paging is stable (`relic_sort_order`)
- `limit` / `offset`: pagination (`clamp_limit`)

`GET /api/v1/search` (`backend/routes/search.py`) is universal search: every relic the requester may see (public, their own, bookmarked, restricted ones shared with them, in spaces they own or belong to; never another user's private relic, even by ID; admins get the same view). It adds `source=public|yours|bookmarked|shared|spaces`, `facets.sources` counts, and per relic `sources` and `spaces` (why it's visible). `GET /api/v1/tags?search=` finds tags among the same entitled relics, with counts.

In the UI, list filters live in the URL: `?search=`, `?type=` (a family such as `code` or `image`, mapped to MIME types in `lib/relics/typeFacets.js`, or one exact content type), `?tag=`, `?owner=` (a public ID), `?after=` / `?before=` / `?size=` (as typed: `7d`, `2026-09-01`, `>1mb`; turned into API parameters at request time in the viewer's timezone by `lib/search/ranges.js`, so saved searches stay relative) and `?sort=` (`size-desc`; omitted for newest first). The navbar search (`lib/shell/NavSearch.svelte`) holds the whole query as text, free words plus tokens `type:` `tag:` `by:` `is:` `from:` `in:` `after:` `before:` `size:` (parsed in `lib/search/query.js`; `from:` implies Everywhere), shows whatever the list is filtered by, and applies it all on Enter; the page bar shows the same filters as chips and facets. While it has focus, a panel (`lib/search/SearchPanel.svelte`) lists the filters, completes the token being typed, and shows your searches: recent ones in this browser and pinned ones on the server (`GET/POST/PATCH/DELETE /api/v1/user/searches`, table `saved_search`). On a list page the list filters live as you type while the panel shows what the query finds Everywhere (the `/search` page, `pages/Search.svelte`); on other pages the panel searches the scope, Everywhere by default. Matches come in relevance order with a preview and a reason chip. Ctrl+K starts in Everywhere, Backspace at the start of the bar widens to it, Ctrl+Enter shows all.

### Frontend Routing

`routes.js` matches the path against a list of patterns and lazy-loads the page (no router library); `utils/navigation.js` pushes history and App re-routes on `popstate`. Query parameters (`search`, `tag`, `type`, …) become page props. To add a page:
1. Create it in `frontend/src/pages/`
2. Add a route in `routes.js` (and its first path segment to the relic route's `reserved` list, or it will be read as a relic ID)
3. Add a default title to `SECTION_TITLES` in `App.svelte`
4. If it belongs in the navigation, add it to `lib/shell/navItems.js` (navbar and phone tab bar)

### Frontend UI Conventions

- **Layout**: list pages use `Workbench` (page bar, list, inspector, status bar). The inspector docks beside the list from 1280px, is a drawer below that; on phones selecting opens the item, or a drawer on pages that set `phoneDrawer`. `]` toggles it.
- **No modals or dialogs.** Details, editing, confirmations and forms live in the inspector (`InsSection` sections) or inline (`r-confirm`, `r-banner-*`); the first-visit key is a banner (`KeyBanner`).
- **Design system**: use the tokens (`--ink`, `--surface`, `--line`, `--accent`, `--type-*`, …) and `r-*` component classes from `src/design-system/`; `Icon` takes names from `icons.json`. Don't hand-edit `tokens.css`; update `tokens.json` and run `node scripts/build-tokens.mjs`.
- **Lists**: relic lists use `RelicWorkbench` + `RelicList` with a `PagedFeed`; other lists (admin) use `DataList`. Column layout follows the list's own width (container queries), not the window's.
- **Svelte**: new code uses Svelte 5 runes (`$state`, `$derived`, `$props`, snippets); `$state.raw` for API data. The renderers in `components/renderers/` still use `export let` and events.
- **Times**: the API sends naive UTC datetimes; `services/api/core.js` marks them UTC on the way in, so format them as local time without further conversion.
- **Checking a change**: `npx vite build` in `frontend/`. The images install with node 20 / npm 10 `npm ci`; don't regenerate `package-lock.json` with a newer npm.

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
3. **S3 storage**: Scales to millions of relics, supports any file type
5. **Cryptographic IDs**: 32-character hexadecimal IDs (GitHub Gist-style) for security and collision resistance
6. **Simple and focused**: Clean, straightforward implementation without unnecessary complexity
