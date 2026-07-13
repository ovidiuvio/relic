"""HTTP client for the ops-agent sidecar (service logs, restarts, deployments)."""
import logging
from typing import Optional

import httpx
from fastapi import HTTPException

from backend.config import settings

logger = logging.getLogger(__name__)


def ops_agent_configured() -> bool:
    return bool(settings.OPS_AGENT_URL)


async def ops_request(
    method: str,
    path: str,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
    timeout: float = 30.0,
) -> dict:
    """
    Call the ops agent and return its JSON response.

    Raises HTTPException(503) if the agent is not configured or unreachable,
    and passes through the agent's own error status/detail otherwise.
    """
    if not ops_agent_configured():
        raise HTTPException(status_code=503, detail="Ops agent not configured")

    url = settings.OPS_AGENT_URL.rstrip("/") + path
    headers = {"X-Ops-Token": settings.OPS_AGENT_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=params, json=json, headers=headers)
    except httpx.HTTPError as e:
        logger.error(f"Ops agent unreachable ({url}): {e}")
        raise HTTPException(status_code=503, detail="Ops agent unreachable")

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    return response.json()
