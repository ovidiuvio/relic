"""Rate limiting middleware for the API."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using in-memory storage."""

    def __init__(self, app, upload_limit: int = 10, read_limit: int = 100, window_minutes: int = 1):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI app
            upload_limit: Uploads per window per IP
            read_limit: Reads per window per IP
            window_minutes: Time window in minutes
        """
        super().__init__(app)
        self.upload_limit = upload_limit
        self.read_limit = read_limit
        self.window = timedelta(minutes=window_minutes)

        # Store: {ip: [(timestamp, method), ...]}
        self.requests = defaultdict(list)
        self.cleanup_task = None

    async def dispatch(self, request: Request, call_next):
        """Process request and apply rate limiting."""
        client_ip = request.client.host

        # Cleanup old requests periodically
        await self._cleanup_old_requests()

        # Check rate limits
        now = datetime.utcnow()
        method = request.method

        # Get requests in current window
        current_requests = [
            req for req in self.requests[client_ip]
            if now - req[0] < self.window
        ]

        # Update stored requests
        self.requests[client_ip] = current_requests

        # Check upload limit
        if method == "POST" and "/pastes" in request.url.path:
            upload_requests = sum(1 for _, m in current_requests if m == "POST")
            if upload_requests >= self.upload_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {self.upload_limit} uploads per minute."
                )

        # Check read limit
        elif method == "GET":
            read_requests = sum(1 for _, m in current_requests if m == "GET")
            if read_requests >= self.read_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {self.read_limit} reads per minute."
                )

        # Add current request
        self.requests[client_ip].append((now, method))

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(
            self.upload_limit if method == "POST" else self.read_limit
        )
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, (self.upload_limit if method == "POST" else self.read_limit) - len(current_requests) - 1)
        )
        response.headers["X-RateLimit-Reset"] = str(
            int((now + self.window).timestamp())
        )

        return response

    async def _cleanup_old_requests(self):
        """Remove old requests from memory."""
        now = datetime.utcnow()
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                req for req in self.requests[ip]
                if now - req[0] < self.window * 2  # Keep 2x window for safety
            ]
            if not self.requests[ip]:
                del self.requests[ip]
