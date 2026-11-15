"""Small in-memory TTL cache for JSON route responses.

Several devices looking at the same region and dates get the stored response
instead of each queueing a DuckDB query. Identical requests that arrive while
the first one is still computing wait for it rather than running it again.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: float = 300, max_entries: int = 128):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._key_locks: dict[Any, threading.Lock] = {}

    def get(self, key: Any) -> tuple[bool, Any]:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return False, None
            expires, value = hit
            if expires < time.monotonic():
                del self._data[key]
                return False, None
            self._data.move_to_end(key)
            return True, value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def _key_lock(self, key: Any) -> threading.Lock:
        with self._lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = self._key_locks[key] = threading.Lock()
            return lock

    def cached(self, fn: Callable) -> Callable:
        """Decorator for sync FastAPI handlers. Keys on the route name plus the
        handler's keyword arguments (FastAPI passes query params as kwargs).
        Only successful responses are stored; errors are never cached."""

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            found, value = self.get(key)
            if found:
                return value
            key_lock = self._key_lock(key)
            with key_lock:
                found, value = self.get(key)
                if found:
                    return value
                value = fn(*args, **kwargs)
                self.set(key, value)
            with self._lock:
                if self._key_locks.get(key) is key_lock and not key_lock.locked():
                    del self._key_locks[key]
            return value

        return wrapper


# 5-minute TTL, at most 128 responses (summary/series/calendar/anomalies/meta).
response_cache = TTLCache(ttl_seconds=300, max_entries=128)
# Day bundles carry a GeoJSON map payload (a few MB each), so far fewer of them.
bundle_cache = TTLCache(ttl_seconds=300, max_entries=8)
