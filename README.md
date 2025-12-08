# Relic - Artifact Storage Service

A modern, feature-rich artifact service with immutable relics, complete version history, and smart content processing. Built with FastAPI (Python), Svelte, and Tailwind CSS.

![Relic Overview](assets/newrelic.png)

## Overview

Relic is a self-hosted pastebin and artifact storage system designed for developers. It goes beyond simple text storage by supporting binary files, archives, images, and providing rich previews for various content types. With a focus on immutability and versioning, Relic ensures your shared snippets and files are safe, trackable, and easy to manage.

## Key Features

- **Immutable Artifacts**: Each relic is permanent. Edits create new versions via forking with complete history preserved.
- **Universal Content Support**: 
  - **Code**: Syntax highlighting for 100+ languages.
  - **Images**: Preview and zoom support.
  - **Archives**: Browse ZIP/TAR contents directly in the browser.
  - **Documents**: PDF rendering, CSV/Excel tables, and Markdown rendering.
  - **Diagrams**: Integrated Excalidraw support.
- **CLI Tool**: Powerful command-line interface for quick uploads from terminal.
- **Relic Indexes**: Create curated collections of relics (`.rix` files).
- **Access Control**: Public, unlisted, and private relics.
- **Expiration**: Set relics to expire after 1h, 24h, 7d, 30d, or never.
- **Admin Panel**: Manage users, view system stats, and moderate content.

## Visual Tour

### Create Relics
Upload files via drag-and-drop, paste text directly, or use the CLI.
![Create Relic](assets/newrelic.png)

### Rich Code Viewing
Syntax highlighting with line numbers, copy-to-clipboard, and raw view options.
![Source View](assets/source-view.png)

### Image Previews
Direct image rendering with zoom capabilities.
![Image View](assets/relicimg.png)

### Archive Explorer
Browse the contents of ZIP and TAR files without downloading them.
![Archive View](assets/archive.png)

### Recent Relics & Management
View recently created public relics or manage your own.
![Recent Relics](assets/recent.png)

### Comments & Collaboration
Discuss code snippets and artifacts directly on the relic page.
![Comments](assets/comments.png)

### Admin Dashboard
Monitor system usage, storage, and manage relics.
![Admin Panel](assets/admin.png)

## CLI Tool

Relic comes with a powerful CLI tool for terminal-based workflows.

### Quick Install
```bash
curl -sSL https://your-domain.com/install.sh | bash
```

### Usage
```bash
# Upload from stdin
echo "Hello World" | relic

# Upload a file
relic myfile.txt

# Upload with options
relic --name "My Script" --private --expires 24h script.py
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Make (optional)

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

## Relic Indexes

Relic indexes (`.rix` files) allow you to create curated collections of relics.

```yaml
title: My Project Documentation
description: A collection of documentation files.
relics:
  - id: f47ac10b58cc4372a5670e02b2c3d479
    title: API Reference
  - id: a1b2c3d4e5f678901234567890abcdef
```

## API Endpoints

All API endpoints are prefixed with `/api/v1`.

**Create Relic**
```bash
curl -X POST http://localhost/api/v1/relics \
  -F "file=@myfile.txt" \
  -F "name=My File"
```

**Get Relic**
```bash
curl http://localhost/api/v1/relics/{id}
```

**Fork Relic**
```bash
curl -X POST http://localhost/api/v1/relics/{id}/fork \
  -F "file=@new.txt"
```

## Architecture

- **Frontend**: Svelte, Tailwind CSS, Vite
- **Backend**: FastAPI, SQLAlchemy, Pygments
- **Storage**: PostgreSQL (Metadata), MinIO (Content)
- **Infrastructure**: Docker, Nginx

## License

MIT
