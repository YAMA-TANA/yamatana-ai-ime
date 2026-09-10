"""Bounded, process-local reuse of validated candidate rankings."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import time
from typing import Any, Callable

from ranker.protocol import validate_request, validate_response


class CachedRanker:
    """Cache one fixed backend/settings instance on the serial serving path.

    Keys include every semantic request field, including candidate IDs and
    order. Only request_id is excluded. Input text is hashed, never retained
    by this cache or written to disk. Recreating the backend (as the tray does
    on settings changes) also creates an empty cache.
    """

    def __init__(
        self,
        delegate: Any,
        *,
        ttl_seconds: float = 30.0,
        max_entries: int = 128,
        max_candidates: int = 64,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._delegate = delegate
        self._ttl = max(0.0, float(ttl_seconds))
        self._max_entries = max(0, int(max_entries))
        self._max_candidates = max(0, int(max_candidates))
        self._clock = clock
        self._entries: OrderedDict[
            bytes, tuple[float, tuple[tuple[str, float, int], ...]]
        ] = OrderedDict()
        self.cache_hits = 0
        self.cache_misses = 0
        self.last_cache_hit = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def clear(self) -> None:
        self._entries.clear()
        self.last_cache_hit = False

    def rank(self, request: dict[str, Any]) -> dict[str, Any]:
        self.last_cache_hit = False
        request = validate_request(request)
        now = self._clock()
        # TTL is measured from computation, not refreshed on a hit. An LRU
        # reorder therefore cannot keep an expired result alive indefinitely.
        for old_key, (expires, _) in list(self._entries.items()):
            if now >= expires:
                del self._entries[old_key]

        cacheable = (
            self._ttl > 0
            and self._max_entries > 0
            and len(request["candidates"]) <= self._max_candidates
        )
        key = b""
        if cacheable:
            semantic_request = {
                name: value for name, value in request.items()
                if name != "request_id"
            }
            key = hashlib.sha256(json.dumps(
                semantic_request, ensure_ascii=False, separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")).digest()
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
                self.cache_hits += 1
                self.last_cache_hit = True
                return {
                    "request_id": request["request_id"],
                    "candidates": [
                        {"id": cid, "score": score, "rank": rank}
                        for cid, score, rank in cached[1]
                    ],
                }

        self.cache_misses += 1
        # Exceptions and malformed replies must never poison later requests.
        response = validate_response(self._delegate.rank(request), request)
        if cacheable:
            self._entries[key] = (
                self._clock() + self._ttl,
                tuple((item["id"], item["score"], item["rank"])
                      for item in response["candidates"]),
            )
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
        return response
