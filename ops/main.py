"""Relic ops-agent: internal sidecar for service monitoring and deployments.

Holds the docker socket so the public-facing backend doesn't have to.
Only reachable on the internal compose network; every endpoint except
/health requires the X-Ops-Token shared secret.
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import docker
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ops-agent")

OPS_AGENT_TOKEN = os.getenv("OPS_AGENT_TOKEN", "")
COMPOSE_PROJECT_NAME = os.getenv("COMPOSE_PROJECT_NAME", "deploy")
DEPLOY_DIR = os.getenv("DEPLOY_DIR", "/deploy")
DEPLOY_SERVICES = os.getenv("DEPLOY_SERVICES", "backend frontend s3-sync").split()
DEPLOY_ENABLED = os.getenv("DEPLOY_ENABLED", "true").lower() == "true"
AGENT_SERVICE_NAME = os.getenv("AGENT_SERVICE_NAME", "ops-agent")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
JOURNAL_FILE = DATA_DIR / "deployments.jsonl"
ENV_FILE = Path(DEPLOY_DIR) / ".env"

VERSION_RE = re.compile(r"^(v\d+\.\d+\.\d+|latest)$")
MAX_LOG_TAIL = 5000

app = FastAPI(title="Relic Ops Agent", docs_url=None, redoc_url=None)

_docker_client: Optional[docker.DockerClient] = None


def get_docker() -> docker.DockerClient:
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client


@app.middleware("http")
async def token_auth(request: Request, call_next):
    """Require the shared token on everything except /health. Fail closed."""
    if request.url.path != "/health":
        if not OPS_AGENT_TOKEN:
            return JSONResponse(
                status_code=503,
                content={"detail": "Ops agent has no OPS_AGENT_TOKEN configured"},
            )
        if request.headers.get("X-Ops-Token") != OPS_AGENT_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "Invalid ops token"})
    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def _project_containers():
    return get_docker().containers.list(
        all=True,
        filters={"label": f"com.docker.compose.project={COMPOSE_PROJECT_NAME}"},
    )


def _service_name(container) -> str:
    return container.labels.get("com.docker.compose.service", container.name)


def _find_container(service: str):
    for c in _project_containers():
        if _service_name(c) == service:
            return c
    raise HTTPException(status_code=404, detail=f"Service '{service}' not found")


@app.get("/services")
async def list_services():
    services = []
    for c in _project_containers():
        attrs = c.attrs
        state = attrs.get("State", {})
        health = state.get("Health", {}).get("Status")
        image_tag = c.image.tags[0] if c.image.tags else attrs.get("Config", {}).get("Image", "")
        services.append({
            "service": _service_name(c),
            "container_name": c.name,
            "image": image_tag,
            "state": c.status,
            "health": health,
            "started_at": state.get("StartedAt"),
            "restart_count": attrs.get("RestartCount", 0),
        })
    services.sort(key=lambda s: s["service"])
    return {"project": COMPOSE_PROJECT_NAME, "services": services}


@app.get("/services/{service}/logs")
async def service_logs(
    service: str,
    tail: int = Query(200, ge=1),
    since: Optional[int] = Query(None, description="Unix timestamp lower bound"),
):
    container = _find_container(service)
    tail = min(tail, MAX_LOG_TAIL)
    kwargs = {"tail": tail, "timestamps": True, "stdout": True, "stderr": True}
    if since:
        kwargs["since"] = since
    raw = await asyncio.to_thread(container.logs, **kwargs)
    return {
        "service": service,
        "tail": tail,
        "logs": raw.decode("utf-8", errors="replace"),
    }


@app.post("/services/{service}/restart")
async def restart_service(service: str):
    if service == AGENT_SERVICE_NAME:
        raise HTTPException(status_code=400, detail="The ops agent cannot restart itself")
    container = _find_container(service)
    logger.warning(f"Restarting service '{service}' ({container.name})")
    await asyncio.to_thread(container.restart, timeout=30)
    return {"success": True, "message": f"Service '{service}' restarted"}


# ---------------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------------

class DeployRequest(BaseModel):
    version: str


# Single-flight deploy job state, guarded by _job_lock
_job_lock = asyncio.Lock()
_job = {
    "state": "idle",  # idle | running | succeeded | failed
    "version": None,
    "previous_version": None,
    "started_at": None,
    "finished_at": None,
    "log": "",
}


def _read_current_version() -> str:
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.strip().startswith("RELIC_VERSION="):
                return line.split("=", 1)[1].strip() or "latest"
    except FileNotFoundError:
        pass
    return "latest"


def _write_version(version: str):
    """Update (or append) the RELIC_VERSION line in the deploy .env file."""
    lines = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("RELIC_VERSION="):
            lines[i] = f"RELIC_VERSION={version}"
            replaced = True
    if not replaced:
        lines.append(f"RELIC_VERSION={version}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


async def _run_step(args: list, log_parts: list) -> int:
    log_parts.append(f"$ {' '.join(args)}\n")
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=DEPLOY_DIR,
    )
    stdout, _ = await proc.communicate()
    log_parts.append(stdout.decode("utf-8", errors="replace"))
    return proc.returncode


def _append_journal(entry: dict):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with JOURNAL_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        logger.error(f"Failed to write deployment journal: {e}")


async def _deploy_worker(version: str, previous_version: str):
    log_parts = []
    compose_base = [
        "docker", "compose",
        "-p", COMPOSE_PROJECT_NAME,
        "--project-directory", DEPLOY_DIR,
    ]
    status = "failed"
    try:
        _write_version(version)
        log_parts.append(f"RELIC_VERSION set to {version} (was {previous_version})\n")

        rc = await _run_step(compose_base + ["pull"] + DEPLOY_SERVICES, log_parts)
        if rc != 0:
            # Nothing recreated yet - restore the previous pin
            _write_version(previous_version)
            log_parts.append(f"Pull failed (exit {rc}); RELIC_VERSION reverted to {previous_version}\n")
        else:
            rc = await _run_step(
                compose_base + ["up", "-d", "--no-deps"] + DEPLOY_SERVICES, log_parts
            )
            if rc == 0:
                status = "succeeded"
                log_parts.append(f"Deployment of {version} completed\n")
            else:
                log_parts.append(f"'up -d' failed (exit {rc}); stack may be partially updated\n")
    except Exception as e:
        logger.error(f"Deploy of {version} crashed: {e}", exc_info=True)
        log_parts.append(f"Deploy crashed: {e}\n")
    finally:
        finished = datetime.now(timezone.utc).isoformat()
        _job.update(state=status, finished_at=finished, log="".join(log_parts))
        _append_journal({
            "version": version,
            "previous_version": previous_version,
            "status": status,
            "started_at": _job["started_at"],
            "finished_at": finished,
            "log": "".join(log_parts)[-8000:],
        })
        logger.warning(f"Deploy of {version}: {status}")


@app.post("/deploy")
async def deploy(req: DeployRequest):
    if not DEPLOY_ENABLED:
        raise HTTPException(status_code=400, detail="Deployments are disabled in this environment")
    if not VERSION_RE.match(req.version):
        raise HTTPException(status_code=400, detail="Invalid version (expected vX.Y.Z or 'latest')")

    async with _job_lock:
        if _job["state"] == "running":
            raise HTTPException(status_code=409, detail=f"A deployment of {_job['version']} is already running")
        previous = _read_current_version()
        _job.update(
            state="running",
            version=req.version,
            previous_version=previous,
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=None,
            log="",
        )
    asyncio.create_task(_deploy_worker(req.version, previous))
    return {"success": True, "message": f"Deployment of {req.version} started", "previous_version": previous}


@app.get("/deploy/status")
async def deploy_status():
    return {**_job, "deploy_enabled": DEPLOY_ENABLED, "current_version": _read_current_version()}


@app.get("/deployments")
async def deployments(limit: int = Query(50, ge=1, le=500)):
    entries = []
    try:
        with JOURNAL_FILE.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    entries.reverse()  # newest first
    return {"total": len(entries), "deployments": entries[:limit]}
