import logging
import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Generator

from slowapi import Limiter
from starlette.requests import Request

logger = logging.getLogger(__name__)


def get_real_ip(request: Request) -> str:
    """
    Get the real client IP address, accounting for proxies like Cloud Run.

    Cloud Run sets X-Forwarded-For header with the original client IP.
    Format: "client_ip, proxy1_ip, proxy2_ip, ..."
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the chain is the original client
        return forwarded.split(",")[0].strip()
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_real_ip)


class ConcurrencyLimiter:
    """
    Tracks concurrent operations per IP address.

    Used to prevent resource exhaustion attacks where a single IP
    spawns many simultaneous narrative generation streams.
    """

    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self._active: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.Lock()

    def can_start(self, ip: str, session_id: str) -> bool:
        """Check if a new operation can start for this IP."""
        with self._lock:
            return len(self._active[ip]) < self.max_concurrent

    def start(self, ip: str, session_id: str) -> bool:
        """
        Register a new concurrent operation.

        Returns True if successfully registered, False if limit exceeded.
        """
        with self._lock:
            if len(self._active[ip]) >= self.max_concurrent:
                logger.warning(
                    f"[concurrency] IP {ip} exceeded limit ({self.max_concurrent}) "
                    f"for session {session_id}"
                )
                return False
            self._active[ip].add(session_id)
            logger.debug(f"[concurrency] Started {session_id} for {ip} (active: {len(self._active[ip])})")
            return True

    def finish(self, ip: str, session_id: str) -> None:
        """Release a concurrent operation slot."""
        with self._lock:
            self._active[ip].discard(session_id)
            if not self._active[ip]:
                del self._active[ip]
            logger.debug(f"[concurrency] Finished {session_id} for {ip}")

    @contextmanager
    def track(self, ip: str, session_id: str) -> Generator[bool, None, None]:
        """
        Context manager for tracking concurrent operations.

        Yields True if operation was allowed to start, False otherwise.
        Automatically releases the slot on exit.
        """
        allowed = self.start(ip, session_id)
        try:
            yield allowed
        finally:
            if allowed:
                self.finish(ip, session_id)

    def active_count(self, ip: str) -> int:
        """Get the number of active operations for an IP."""
        with self._lock:
            return len(self._active[ip])


# Global instance for narrative generation concurrency
generation_limiter = ConcurrencyLimiter(max_concurrent=2)
