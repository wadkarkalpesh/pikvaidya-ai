"""
PikVaidya AI — Resilient Weather In-Memory Cache
================================================
Implements an asynchronous, thread-safe in-memory caching layer
with geographic coordinate quantization and Time-To-Live (TTL) expiration.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class WeatherCache:
    """
    Caches weather responses keyed by geographic grid coordinates.
    Quantizes coordinates to 2 decimal places (~1.1 km spatial resolution)
    to aggregate nearby farm requests and prevent external API exhaustion.
    """

    def __init__(self, default_ttl_seconds: int = 900):  # 15 minutes default TTL
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def make_key(latitude: float, longitude: float, prefix: str = "weather") -> str:
        """Quantizes coordinates to ~1.1km grid cells for spatial deduplication."""
        q_lat = round(float(latitude), 2)
        q_lon = round(float(longitude), 2)
        return f"{prefix}:{q_lat:.2f}:{q_lon:.2f}"

    async def get(self, latitude: float, longitude: float, prefix: str = "weather") -> Optional[Any]:
        """Retrieves cached payload if present and unexpired."""
        key = self.make_key(latitude, longitude, prefix)
        now = time.time()

        async with self._lock:
            entry = self._cache.get(key)
            if entry:
                if now < entry["expires_at"]:
                    logger.debug(f"Cache HIT for {key} (valid for {int(entry['expires_at'] - now)}s)")
                    return entry["data"]
                else:
                    # Expired entry cleanup
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED for {key}")
        return None

    async def set(
        self,
        latitude: float,
        longitude: float,
        data: Any,
        prefix: str = "weather",
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Stores payload in cache with expiration timestamp."""
        key = self.make_key(latitude, longitude, prefix)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl

        async with self._lock:
            self._cache[key] = {
                "data": data,
                "expires_at": expires_at,
                "created_at": time.time(),
            }
            logger.debug(f"Cache SET for {key} with TTL={ttl}s")

    async def clear(self) -> None:
        """Flushes all cached entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Weather cache flushed.")

    def size(self) -> int:
        """Returns total active cached entries."""
        return len(self._cache)


weather_cache = WeatherCache(default_ttl_seconds=900)

