"""Safety wrapper: any ranker problem returns Mozc's original order."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict

from ranker.protocol import validate_request, validate_response


def original_order(request: Dict[str, Any]) -> Dict[str, Any]:
    request = validate_request(request)
    ordered = sorted(request["candidates"], key=lambda item: item["rank"])
    return {
        "request_id": request["request_id"],
        "candidates": [
            {"id": item["id"], "score": float(len(ordered) - index), "rank": index}
            for index, item in enumerate(ordered, start=1)
        ],
    }


def safe_rank(request: Dict[str, Any], rank_call: Callable[[Dict[str, Any]], Dict[str, Any]],
              timeout_ms: int = 200) -> Dict[str, Any]:
    """Call the ranker with a hard deadline and validate its candidate-only reply."""
    original = original_order(request)
    request = validate_request(request)
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(rank_call, request)
    try:
        response = future.result(timeout=max(1, timeout_ms) / 1000.0)
        return validate_response(response, request)
    # A model/IPC adapter is optional code on the keystroke path.  Catch every
    # ordinary exception from it (including backend-specific IndexError,
    # KeyError, or library exceptions) so one failed inference cannot stop
    # conversion.  BaseException is intentionally excluded so process-level
    # interrupts still behave normally.
    except Exception:
        return original
    finally:
        # Do not wait for a crashed/hung ranker on the IME keystroke path.
        pool.shutdown(wait=False, cancel_futures=True)
