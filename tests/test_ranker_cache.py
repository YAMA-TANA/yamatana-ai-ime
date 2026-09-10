from copy import deepcopy
import json
from unittest.mock import Mock, patch

import pytest

from ranker.cache import CachedRanker
from ranker.protocol import validate_response, validate_request
from ranker.ranker import InteractiveBurstGuard, RuleBasedRanker, main, process_line


def request():
    return {
        "request_id": "mozc-1",
        "inference_trigger": "explicit",
        "preceding_text": "象の長い",
        "following_text": "が見える",
        "read": "はな",
        "candidates": [
            {"id": "c0", "text": "花", "rank": 1},
            {"id": "c1", "text": "鼻", "rank": 2},
        ],
    }


def backend():
    return Mock(wraps=RuleBasedRanker())


def test_reconversion_reuses_result_with_current_request_id_and_isolated_reply():
    delegate = backend()
    cache = CachedRanker(delegate)
    first = cache.rank(request())
    expected = deepcopy(first["candidates"])
    first["candidates"][0]["id"] = "caller-mutated"
    req = request() | {"request_id": "mozc-2"}
    second = cache.rank(req)
    assert second == {"request_id": "mozc-2", "candidates": expected}
    validate_response(second, validate_request(req))
    second["candidates"].clear()
    assert cache.rank(req)["candidates"] == expected
    assert delegate.rank.call_count == 1
    assert cache.cache_hits == 2


@pytest.mark.parametrize("changed", [
    {"preceding_text": "庭に咲いた美しい"},
    {"following_text": "を摘む"},
    {"read": "ばな"},
    {"inference_trigger": "interactive"},
    {"candidates": [
        {"id": "c0", "text": "華", "rank": 1},
        {"id": "c1", "text": "鼻", "rank": 2},
    ]},
    {"candidates": [
        {"id": "new0", "text": "花", "rank": 1},
        {"id": "new1", "text": "鼻", "rank": 2},
    ]},
    {"candidates": [
        {"id": "c1", "text": "鼻", "rank": 1},
        {"id": "c0", "text": "花", "rank": 2},
    ]},
])
def test_semantic_changes_are_recomputed(changed):
    delegate = backend()
    cache = CachedRanker(delegate)
    cache.rank(request())
    req = request() | changed
    assert cache.rank(req) == RuleBasedRanker().rank(req)
    assert delegate.rank.call_count == 2
    assert not cache.last_cache_hit


def test_ttl_is_not_extended_by_hits_and_lru_evicts_least_recent_request():
    clock = Mock(return_value=0.0)
    delegate = backend()
    cache = CachedRanker(delegate, clock=clock, ttl_seconds=30, max_entries=2)
    a = request()
    b = a | {"read": "b"}
    c = a | {"read": "c"}
    cache.rank(a)
    cache.rank(b)
    clock.return_value = 29.0
    cache.rank(a)
    cache.rank(c)  # b is the least recently used entry.
    cache.rank(a)
    assert delegate.rank.call_count == 3
    cache.rank(b)
    assert delegate.rank.call_count == 4
    clock.return_value = 30.0
    cache.rank(a)  # a expires despite being touched at t=29.
    assert delegate.rank.call_count == 5


@pytest.mark.parametrize("failure", [
    RuntimeError("temporary backend failure"),
    {"request_id": "wrong", "candidates": []},
    {"request_id": "mozc-1", "candidates": [
        {"id": "c0", "score": float("nan"), "rank": 1},
        {"id": "c1", "score": 0, "rank": 2},
    ]},
])
def test_failure_does_not_poison_cache_or_break_wire_fallback(failure):
    good = RuleBasedRanker().rank(request())
    delegate = Mock()
    delegate.rank.side_effect = [failure, good]
    cache = CachedRanker(delegate)
    line = (json.dumps(request()) + "\n").encode()
    assert process_line(line, cache) is None
    assert json.loads(process_line(line, cache)) == good
    assert json.loads(process_line(line, cache)) == good
    assert delegate.rank.call_count == 2


@pytest.mark.parametrize("options", [
    {"max_entries": 0}, {"ttl_seconds": 0}, {"max_candidates": 1},
])
def test_disabled_or_oversized_cache_preserves_results(options):
    delegate = backend()
    cache = CachedRanker(delegate, **options)
    assert cache.rank(request()) == cache.rank(request())
    assert delegate.rank.call_count == 2


def test_clear_and_new_backend_do_not_reuse_previous_settings_results():
    delegate = backend()
    cache = CachedRanker(delegate)
    cache.rank(request())
    cache.clear()
    cache.rank(request())
    assert delegate.rank.call_count == 2
    replacement = backend()
    CachedRanker(replacement).rank(request())
    assert replacement.rank.call_count == 1


def test_legacy_debounce_result_is_not_cached_as_ai_result():
    delegate = backend()
    guard = InteractiveBurstGuard(CachedRanker(delegate), settle_seconds=0)
    req = request() | {"inference_trigger": "interactive"}
    assert guard.rank(req)["candidates"][0]["id"] == "c0"
    assert delegate.rank.call_count == 0
    assert guard.rank(req)["candidates"][0]["id"] == "c1"
    assert delegate.rank.call_count == 1
    explicit = request()
    guard.rank(explicit)
    guard.rank(explicit | {"request_id": "mozc-3"})
    assert delegate.rank.call_count == 2


def test_pipe_entrypoint_installs_cache_around_model():
    delegate = backend()
    delegate.device = "cpu"
    with patch("ranker.onnx_ranker.OnnxRuriReranker", return_value=delegate), \
         patch("ranker.ranker._windows_pipe_server") as server:
        def serve(_pipe, ranker, **_kwargs):
            ranker.rank(request())
            ranker.rank(request() | {"request_id": "mozc-2"})
            assert delegate.rank.call_count == 1
            return 0
        server.side_effect = serve
        assert main(["--backend", "onnx", "--pipe", "cache-test", "--no-ui"]) == 0
