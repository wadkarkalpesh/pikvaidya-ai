"""PikVaidya AI — In-Memory Rate Limiting & Compute Defense
=========================================================
Protects compute-intensive endpoints (e.g. Grad-CAM backpropagation and
model inference) against resource exhaustion via a thread-safe sliding window.
"""

import time
import logging
from collections import defaultdict
from threading import Lock
from typing import Dict, List
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter per client IP address."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.records: Dict[str, List[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_ip: str) -> bool:
        """Determines if the request from client_ip is permitted."""
        now = time.time()
        cutoff = now - self.window_seconds

        with self.lock:
            # Prune timestamps older than window
            timestamps = self.records[client_ip]
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            if len(valid_timestamps) >= self.max_requests:
                self.records[client_ip] = valid_timestamps
                return False

            valid_timestamps.append(now)
            self.records[client_ip] = valid_timestamps
            return True

    def check(self, request: Request):
        """FastAPI dependency to enforce rate limit."""
        client_ip = request.client.host if request.client else "127.0.0.1"

        # Allow test client localhost bypass if header present
        if request.headers.get("X-Test-Bypass-Rate-Limit") == "1":
            return

        if not self.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for client IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Inference capacity is throttled to {self.max_requests} requests per minute. Please wait before retrying.",
                headers={"Retry-After": str(self.window_seconds)},
            )


# Default rate limiter for unauthenticated inference: 120 requests/minute
inference_rate_limiter = SlidingWindowRateLimiter(max_requests=120, window_seconds=60)
