"""File-based TTL cache for live-mode provider results.

Purpose: repeated development runs must not repurchase the same search or the
same page. Entries are JSON files under ``backend/.cache/`` (gitignored),
keyed by a hash of provider + query + parameters, namespaced per provider so
TTLs can differ.

What is deliberately NOT cached:
  * secrets or headers of any kind — only response payloads we constructed
  * provider authentication/permission errors (a cached 401 would mask a fix)
  * malformed responses (they would replay the failure until expiry)

The abstraction is a class with get/set on JSON-serialisable values, so a
deployment can swap in Redis or similar without touching call sites.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from app.config import settings


class TTLCache:
    def __init__(self, namespace: str, ttl_seconds: int, root: Path | None = None) -> None:
        self._dir = (root or settings.cache_dir) / namespace
        self._ttl = ttl_seconds

    def _path(self, key_parts: dict[str, Any]) -> Path:
        # Sorted JSON so logically identical requests hash identically.
        digest = hashlib.sha256(
            json.dumps(key_parts, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return self._dir / f"{digest}.json"

    def get(self, key_parts: dict[str, Any]) -> Any | None:
        path = self._path(key_parts)
        try:
            envelope = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        if time.time() - envelope["storedAt"] > self._ttl:
            # Expired. Remove eagerly so the cache dir does not grow unbounded.
            try:
                path.unlink()
            except OSError:
                pass
            return None
        return envelope["value"]

    def set(self, key_parts: dict[str, Any], value: Any) -> None:
        path = self._path(key_parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"storedAt": time.time(), "value": value}
        # Write-then-rename so a crash mid-write never leaves a torn JSON file.
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(envelope, ensure_ascii=False))
        tmp.replace(path)


def search_cache() -> TTLCache:
    return TTLCache("search", settings.cache_ttl_search_seconds)


def page_cache() -> TTLCache:
    return TTLCache("page", settings.cache_ttl_page_seconds)


def result_cache() -> TTLCache:
    return TTLCache("result", settings.cache_ttl_result_seconds)
