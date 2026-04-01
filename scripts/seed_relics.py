#!/usr/bin/env python3
"""
Seed script: creates a test space and populates it with N sample relics.
Optimized version using asyncio and httpx for higher throughput.

Usage:
    python3 scripts/seed_relics.py --client-key YOUR_KEY [--count 500] [--url http://localhost] [--space-id EXISTING_ID]
"""
import argparse
import random
import sys
import uuid
import time
import asyncio
import httpx
from datetime import datetime

# ---------------------------------------------------------------------------
# Content generators
# ---------------------------------------------------------------------------

TAGS_POOL = [
    ["python", "code"],
    ["javascript", "code"],
    ["typescript", "code"],
    ["markdown", "docs"],
    ["json", "data"],
    ["yaml", "config"],
    ["sql", "data"],
    ["html", "web"],
    ["bash", "devops"],
    ["csv", "data"],
    ["rust", "code"],
    ["go", "code"],
    ["notes", "personal"],
    ["work", "docs"],
    ["config", "devops"],
    ["logs", "data"],
    ["snippets", "code"],
    ["pics", "personal"],
    ["archive", "work"],
]

VERBS = ["draft", "final", "updated", "legacy", "refactored", "optimised", "broken", "working", "experimental"]
NOUNS = [
    "auth middleware", "rate limiter", "db migration", "api client",
    "parser utility", "config loader", "cache layer", "event handler",
    "data pipeline", "test fixture", "deployment script", "schema def",
    "error handler", "log formatter", "queue consumer", "batch job",
    "webhook handler", "metrics collector", "report generator", "seed data",
    "retry logic", "token validator", "response wrapper", "health check",
    "task runner", "file uploader", "cron job", "state machine",
]

def rname():
    return f"{random.choice(VERBS)} {random.choice(NOUNS)} v{random.randint(1, 9)}"


def python_content():
    fn = random.choice(["process", "handle", "validate", "transform", "fetch", "parse", "build", "emit"])
    arg = random.choice(["data", "payload", "item", "record", "event", "request", "response"])
    cls = arg.capitalize()
    return f"""\
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def {fn}_{arg}({arg}: dict, *, strict: bool = False) -> Optional[dict]:
    \"\"\"Process the incoming {arg} and return a normalised result.\"\"\"
    if not {arg}:
        logger.warning("Empty {arg} received")
        return None

    result = {{}}
    for key, value in {arg}.items():
        if strict and not isinstance(value, str):
            raise TypeError(f"Expected str for {{key}}, got {{type(value).__name__}}")
        result[key] = str(value).strip()

    logger.info("Processed %d fields from {arg}", len(result))
    return result


class {cls}Error(Exception):
    \"\"\"Raised when {arg} processing fails.\"\"\"
    pass


class {cls}Pipeline:
    def __init__(self, strict: bool = False):
        self.strict = strict
        self._errors: list[str] = []

    def run(self, items: list[dict]) -> list[dict]:
        results = []
        for item in items:
            try:
                out = {fn}_{arg}(item, strict=self.strict)
                if out:
                    results.append(out)
            except {cls}Error as e:
                self._errors.append(str(e))
        return results

    @property
    def errors(self) -> list[str]:
        return list(self._errors)
"""


def javascript_content():
    fn = random.choice(["fetchData", "handleEvent", "parseResponse", "buildQuery", "validateInput", "retryRequest", "batchProcess"])
    return f"""\
// {fn}.js
const BASE_URL = process.env.API_URL ?? 'http://localhost:8000';
const DEFAULT_TIMEOUT = 5_000;
const DEFAULT_RETRIES = 3;

/**
 * {fn} — utility function
 * @param {{object}} options
 * @returns {{Promise<object>}}
 */
export async function {fn}(options = {{}}) {{
  const {{ timeout = DEFAULT_TIMEOUT, retries = DEFAULT_RETRIES, ...rest }} = options;

  for (let attempt = 1; attempt <= retries; attempt++) {{
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    try {{
      const res = await fetch(`${{BASE_URL}}/api/v1`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(rest),
        signal: controller.signal,
      }});
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${{res.status}} ${{res.statusText}}`);
      return await res.json();
    }} catch (err) {{
      clearTimeout(timer);
      if (attempt === retries) throw err;
      await new Promise(r => setTimeout(r, 150 * 2 ** attempt));
    }}
  }}
}}

export function createBatch(items, batchSize = 10) {{
  const batches = [];
  for (let i = 0; i < items.length; i += batchSize) {{
    batches.push(items.slice(i, i + batchSize));
  }}
  return batches;
}}
"""


def markdown_content():
    topic = random.choice([
        "Setup Guide", "API Reference", "Troubleshooting", "Deployment",
        "Architecture Overview", "Changelog", "Contributing", "Security Policy",
        "Performance Tuning", "Database Schema",
    ])
    return f"""\
# {topic}

## Overview

This document covers **{topic.lower()}** for the project.
Generated ref: `{uuid.uuid4().hex[:8]}`

## Prerequisites

- Node.js >= 18
- Python >= 3.11
- Docker + Docker Compose

## Steps

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in values
3. Run `make dev-up` to start all services
4. Visit `http://localhost` in your browser

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Backend listening port |
| `DEBUG` | `false` | Enable verbose debug output |
| `DB_URL` | — | PostgreSQL connection string |
| `S3_BUCKET` | — | MinIO / S3 bucket name |

## Common Issues

### Service won't start

Check that ports 80, 8000, and 5432 are free:

```bash
lsof -i :80 -i :8000 -i :5432
```

### Database migration fails

Run migrations manually:

```bash
make migrate
```

> **Note**: Always back up the database before running migrations in production.

## See Also

- [README](./README.md)
- [CLAUDE.md](./CLAUDE.md)
"""


def json_content():
    import json
    keys = random.sample(["id", "name", "email", "role", "status", "created_at", "metadata", "tags", "score", "active", "region", "tier"], 6)
    def make_obj(i):
        obj = {k: f"value_{k}_{i}" for k in keys}
        obj["index"] = i
        obj["enabled"] = random.choice([True, False])
        obj["count"] = random.randint(0, 9999)
        return obj
    n = random.randint(3, 8)
    return json.dumps({"data": [make_obj(i) for i in range(n)], "total": n, "page": 1, "per_page": 25}, indent=2)


def yaml_content():
    svc = random.choice(["api", "worker", "scheduler", "frontend", "proxy", "ingester", "exporter"])
    return f"""\
service: {svc}
version: "1.{random.randint(0, 9)}.{random.randint(0, 9)}"

server:
  host: 0.0.0.0
  port: {random.randint(3000, 9000)}
  workers: {random.randint(1, 8)}
  timeout: {random.randint(10, 120)}s
  graceful_shutdown: 30s

database:
  url: postgresql://user:pass@localhost:5432/{svc}_db
  pool_size: {random.randint(5, 20)}
  max_overflow: {random.randint(5, 10)}
  echo: false

logging:
  level: {random.choice(["DEBUG", "INFO", "WARNING", "ERROR"])}
  format: json
  output: stdout

features:
  cache_enabled: {random.choice(["true", "false"])}
  rate_limiting: {random.choice(["true", "false"])}
  metrics: {random.choice(["true", "false"])}
  tracing: {random.choice(["true", "false"])}

healthcheck:
  path: /health
  interval: 30s
  timeout: 5s
  retries: 3
"""


def sql_content():
    table = random.choice(["users", "orders", "events", "sessions", "products", "logs", "notifications", "audit_trail"])
    return f"""\
-- {table} — DDL and common queries

CREATE TABLE IF NOT EXISTS {table} (
    id          BIGSERIAL PRIMARY KEY,
    uuid        UUID NOT NULL DEFAULT gen_random_uuid(),
    name        TEXT,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','deleted')),
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_{table}_status     ON {table}(status);
CREATE INDEX IF NOT EXISTS idx_{table}_created_at ON {table}(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_{table}_uuid       ON {table}(uuid);

-- updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_{table}_updated_at
BEFORE UPDATE ON {table}
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Recent active records
SELECT id, uuid, name, created_at
FROM {table}
WHERE status = 'active'
  AND created_at > now() - INTERVAL '{random.randint(1, 30)} days'
ORDER BY created_at DESC
LIMIT 100;

-- Status summary
SELECT status, count(*) AS total, max(created_at) AS latest
FROM {table}
GROUP BY status
ORDER BY total DESC;
"""


def bash_content():
    action = random.choice(["backup", "deploy", "cleanup", "monitor", "migrate", "restart", "rollback", "provision"])
    return f"""\
#!/usr/bin/env bash
# {action}.sh — generated utility script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
LOG_FILE="/var/log/relic-{action}.log"

log()  {{ echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee a "$LOG_FILE"; }}
die()  {{ log "ERROR: $*"; exit 1; }}
info() {{ log "INFO: $*"; }}

# Load environment
[[ -f "$SCRIPT_DIR/.env" ]] && source "$SCRIPT_DIR/.env" || die ".env not found"

check_deps() {{
  local missing=()
  for cmd in docker curl jq psql; do
    command -v "$cmd" &>/dev/null || missing+=("$cmd")
  done
  [[ ${{#missing[@]}} -eq 0 ]] || die "Missing dependencies: ${{missing[*]}}"
}}

preflight() {{
  info "Running preflight checks..."
  curl -sf "${{API_URL:-http://localhost}}/health" > /dev/null || die "API is not reachable"
  info "Preflight OK"
}}

{action}_main() {{
  info "Starting {action}..."
  # TODO: implement {action} logic
  sleep {random.randint(1, 3)}
  info "{action.capitalize()} complete"
}}

cleanup() {{
  local exit_code=$?
  [[ $exit_code -ne 0 ]] && log "Script exited with code $exit_code"
}}
trap cleanup EXIT

check_deps
preflight
{action}_main
"""


def html_content():
    component = random.choice(["modal", "data-table", "form", "card", "navbar", "sidebar", "toast", "dropdown"])
    css_class = component.replace("-", "_")
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{component.replace('-', ' ').title()} Component</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; padding: 2rem; color: #111827; }}
    .{css_class} {{ display: flex; flex-direction: column; gap: 1rem; border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 1.5rem; max-width: 480px; }}
    .{css_class}__header {{ font-weight: 600; font-size: 1.125rem; border-bottom: 1px solid #f3f4f6; padding-bottom: 0.75rem; }}
    .{css_class}__body {{ color: #374151; line-height: 1.6; }}
    .{css_class}__footer {{ display: flex; gap: 0.5rem; justify-content: flex-end; padding-top: 0.75rem; }}
    button {{ padding: 0.5rem 1rem; border-radius: 0.375rem; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }}
    button[type="submit"] {{ background: #1d4ed8; color: white; border-color: #1d4ed8; }}
  </style>
</head>
<body>
  <div class="{css_class}">
    <div class="{css_class}__header">{component.replace('-', ' ').title()}</div>
    <div class="{css_class}__body">
      <p>This is a <strong>{component}</strong> component example. Ref: <code>{uuid.uuid4().hex[:8]}</code></p>
      <ul style="margin-top: 0.75rem; padding-left: 1.25rem;">
        <li>Accessible and keyboard-navigable</li>
        <li>Mobile-responsive layout</li>
        <li>No external dependencies</li>
      </ul>
    </div>
    <div class="{css_class}__footer">
      <button type="button">Cancel</button>
      <button type="submit">Confirm</button>
    </div>
  </div>
</body>
</html>
"""


def csv_content():
    schema = random.choice([
        ["id", "name", "email", "role", "active", "created_at"],
        ["date", "product", "quantity", "unit_price", "total", "currency"],
        ["timestamp", "level", "service", "message", "trace_id", "duration_ms"],
        ["user_id", "event", "page", "referrer", "session_id", "created_at"],
        ["host", "method", "path", "status", "bytes", "response_time_ms"],
    ])
    rows = [",".join(schema)]
    for i in range(random.randint(15, 40)):
        row = []
        for col in schema:
            if col in ("id", "user_id"):
                row.append(str(random.randint(1000, 9999)))
            elif col in ("quantity", "status", "bytes", "duration_ms", "response_time_ms"):
                row.append(str(random.randint(1, 9999)))
            elif col in ("unit_price", "total"):
                row.append(f"{random.uniform(1, 999):.2f}")
            elif col == "active":
                row.append(random.choice(["true", "false"]))
            elif col in ("created_at", "timestamp", "date"):
                row.append(f"2026-{random.randint(1,3):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z")
            elif col == "level":
                row.append(random.choice(["INFO", "WARN", "ERROR", "DEBUG"]))
            elif col == "method":
                row.append(random.choice(["GET", "POST", "PUT", "DELETE", "PATCH"]))
            else:
                row.append(f"sample_{col}_{i}")
        rows.append(",".join(row))
    return "\n".join(rows)


def plaintext_content():
    sentences = [
        f"Note #{random.randint(1, 9999)} — ref: {uuid.uuid4().hex[:8]}",
        "This is a plain-text relic generated for load testing purposes.",
        "It contains multiple paragraphs of unstructured content.",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
        f"Random value: {random.random():.6f}",
        "Tags, search, and pagination should all work correctly with this content.",
        "End of note.",
    ]
    chosen = random.sample(sentences, random.randint(4, len(sentences)))
    # Group into paragraphs
    mid = len(chosen) // 2
    return "\n\n".join([" ".join(chosen[:mid]), " ".join(chosen[mid:])])


# (label, content_type, language_hint, generator_fn)
GENERATORS = [
    ("python",     "text/x-python",        "python",     python_content),
    ("javascript", "text/javascript",       "javascript", javascript_content),
    ("markdown",   "text/markdown",         "markdown",   markdown_content),
    ("json",       "application/json",      None,         json_content),
    ("yaml",       "text/yaml",             "yaml",       yaml_content),
    ("sql",        "text/x-sql",            "sql",        sql_content),
    ("bash",       "text/x-shellscript",    "bash",       bash_content),
    ("html",       "text/html",             "html",       html_content),
    ("csv",        "text/csv",              None,         csv_content),
    ("plain",      "text/plain",            None,         plaintext_content),
]

EXT_MAP = {
    "text/x-python": ".py",
    "text/javascript": ".js",
    "text/markdown": ".md",
    "application/json": ".json",
    "text/yaml": ".yaml",
    "text/x-sql": ".sql",
    "text/x-shellscript": ".sh",
    "text/html": ".html",
    "text/csv": ".csv",
    "text/plain": ".txt",
}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

async def create_relic_async(client, base_url, client_key, content, content_type, language_hint, name, tags, access_level, space_id=None):
    ext = EXT_MAP.get(content_type, ".txt")
    filename = name.replace(" ", "_") + ext
    
    files = {"file": (filename, content.encode(), content_type)}
    data = {
        "name": name,
        "access_level": access_level,
    }
    if language_hint:
        data["language_hint"] = language_hint
    
    # httpx handles multiple values for same key in data for tags if passed as list
    data["tags"] = tags
    
    if space_id:
        data["space_id"] = space_id

    r = await client.post(
        f"{base_url}/api/v1/relics",
        data=data,
        files=files,
        headers={"X-Client-Key": client_key},
        timeout=30.0
    )
    r.raise_for_status()
    return r.json()["id"]


async def create_space_async(client, base_url, client_key, name):
    r = await client.post(
        f"{base_url}/api/v1/spaces",
        json={"name": name, "visibility": "public"},
        headers={"X-Client-Key": client_key},
    )
    r.raise_for_status()
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

async def seed_one_relic_task(client, args, space_id, semaphore):
    async with semaphore:
        _, content_type, language_hint, gen_fn = random.choice(GENERATORS)
        tags = list(random.choice(TAGS_POOL))
        if random.random() < 0.3:
            tags = list(set(tags + random.choice(TAGS_POOL)))
        name = rname()
        content = gen_fn()

        return await create_relic_async(
            client, args.url, args.client_key,
            content, content_type, language_hint,
            name, tags, args.access_level,
            space_id=space_id
        )


async def main_async():
    parser = argparse.ArgumentParser(
        description="Seed sample relics into a Relic space (Optimized)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--count", type=int, default=100,
                        help="Number of relics to create (default: 100)")
    parser.add_argument("--url", default="http://localhost",
                        help="Base URL (default: http://localhost)")
    parser.add_argument("--client-key", required=True,
                        help="Your client key — get it from: localStorage.getItem('relic_client_key')")
    parser.add_argument("--space-id", default=None,
                        help="Use an existing space instead of creating a new one")
    parser.add_argument("--space-name", default="Seed Test Space",
                        help="Name for the new space (default: 'Seed Test Space')")
    parser.add_argument("--access-level", default="public", choices=["public", "private"],
                        help="Access level for created relics (default: public)")
    parser.add_argument("--workers", type=int, default=20,
                        help="Number of concurrent requests (default: 20)")
    args = parser.parse_args()

    start_time = time.time()
    
    # Use limits to ensure we don't open too many connections but reuse them effectively
    limits = httpx.Limits(max_connections=args.workers, max_keepalive_connections=args.workers)
    
    async with httpx.AsyncClient(limits=limits) as client:
        # Ensure client key is registered before seeding
        await client.post(f"{args.url}/api/v1/client/register", headers={"X-Client-Key": args.client_key})

        space_id = args.space_id
        if space_id:
            print(f"Using space: {space_id}")
        else:
            print("No space ID provided. Relics will be created globally.")

        print(f"Creating {args.count} relics with concurrency {args.workers} (async httpx)...")
        
        semaphore = asyncio.Semaphore(args.workers)
        tasks = []
        for _ in range(args.count):
            tasks.append(seed_one_relic_task(client, args, space_id, semaphore))
        
        ok = 0
        fail = 0
        
        # Process in chunks to show progress
        chunk_size = 100
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i+chunk_size]
            results = await asyncio.gather(*chunk, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    fail += 1
                    # print(f"  [FAIL] {res}", file=sys.stderr)
                else:
                    ok += 1
            
            print(f"  {min(i + chunk_size, args.count)}/{args.count} processed...")

    end_time = time.time()
    duration = end_time - start_time

    print(f"\nDone — {ok} created, {fail} failed.")
    print(f"Total time: {duration:.2f}s ({ok/duration:.2f} relics/sec)")

    if space_id:
        print(f"Space: {args.url}/spaces/{space_id}")
    else:
        print(f"View: {args.url}/recent")


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        sys.exit(0)
