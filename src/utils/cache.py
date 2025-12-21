"""
Simple in-memory cache for API responses
"""

import time
from typing import Any, Optional


class SimpleCache:
    """Simple in-memory cache with TTL"""

    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                # Expired, remove it
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 60):
        """Set cache value with TTL in seconds"""
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)

    def clear(self):
        """Clear all cache"""
        self._cache.clear()


# Global cache instance
_cache = SimpleCache()


def get_cache() -> SimpleCache:
    """Get cache singleton"""
    return _cache
