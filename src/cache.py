"""Simple async-aware TTL cache used for 4get API responses."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float

    def expired(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return current >= self.expires_at


class TTLCache:
    """Lightweight cache with TTL semantics for async contexts."""

    def __init__(self, ttl_seconds: float, maxsize: int) -> None:
        self._ttl = max(ttl_seconds, 0.0)
        self._maxsize = max(1, maxsize)
        self._entries: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expired():
                self._entries.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: Any) -> None:
        if self._ttl == 0:
            return
        expires_at = time.monotonic() + self._ttl
        entry = CacheEntry(value=value, expires_at=expires_at)
        async with self._lock:
            if len(self._entries) >= self._maxsize:
                self._evict_one_locked()
            self._entries[key] = entry

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()

    def _evict_one_locked(self) -> None:
        """Remove the oldest cache entry (by expiration time)."""
        if not self._entries:
            return
        oldest_key = min(self._entries, key=lambda key: self._entries[key].expires_at)
        self._entries.pop(oldest_key, None)
