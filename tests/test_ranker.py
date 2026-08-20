from __future__ import annotations

import json
import importlib.util
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

from client.fallback import original_order, safe_rank
from ranker.protocol import ProtocolError, loads_strict, validate_request, validate_response
from ranker.ranker import (RuleBasedRanker, normalize_windows_pipe_name,
                           summarize_reorder)
from ranker.qwen_ranker import QwenReranker
from client.windows_pipe import rank_once as windows_rank_once


ROOT = Path(__file__).resolve().parents[1]
FULL_MODEL_TESTS = (
    os.environ.get("YAMATANA_FULL_MODEL_TESTS") == "1"
    and (ROOT / "models" / "ruri-v3-reranker-310m-ime-tuned" / "model.safetensors").is_file()
)
HAS_TORCH = importlib.util.find_spec("torch") is not None
HEADLESS_TESTS = os.environ.get("YAMATANA_HEADLESS_TESTS") == "1"


def request(context: str):
    return {
        "request_id": "test-1",
        "preceding_text": context,
        "read": "はな",
        "candidates": [
            {"id": "c1", "text": "はな", "rank": 1},
            {"id": "c2", "text": "花", "rank": 2},
            {"id": "c3", "text": "鼻", "rank": 3},
        ],
    }


class RankerTests(unittest.TestCase):
    def test_windows_pipe_name_is_canonical(self):
        expected = r"\\.\pipe\ai_ime_ranker"
        self.assertEqual(normalize_windows_pipe_name("ai_ime_ranker"), expected)
        self.assertEqual(normalize_windows_pipe_name(expected), expected)
        self.assertEqual(
            normalize_windows_pipe_name(r"\\.\pipe\\.\pipe\ai_ime_ranker"),
            expected,
        )

    def test_reorder_summary_does_not_store_candidate_text(self):
        req = validate_request(request(""))
        response = {
            "request_id": req["request_id"],
            "candidates": [
                {"id": "c3", "score": 3.0, "rank": 1},
                {"id": "c1", "score": 2.0, "rank": 2},
                {"id": "c2", "score": 1.0, "rank": 3},
            ],
        }
        self.assertEqual(summarize_reorder(req, response), (True, 3))

    def test_acceptance_elephant_nose(self):
        result = RuleBasedRanker().rank(request("象の長い"))
        self.assertEqual(result["candidates"][0]["id"], "c3")
        self.assertNotIn("text", result["candidates"][0])

    def test_acceptance_garden_flower(self):
        result = RuleBasedRanker().rank(request("庭に咲いた美しい"))
        self.assertEqual(result["candidates"][0]["id"], "c2")

    def test_acceptance_machine_calculation(self):
        req = {
            "request_id": "test-3",
            "preceding_text": "電子工学の分野において、計算",
            "read": "きかい",
            "candidates": [
                {"id": "c1", "text": "機会", "rank": 1},
                {"id": "c2", "text": "機械", "rank": 2},
                {"id": "c3", "text": "器械", "rank": 3},
            ],
        }
        result = RuleBasedRanker().rank(req)
        self.assertEqual(result["candidates"][0]["id"], "c2")

    @unittest.skipUnless(FULL_MODEL_TESTS, "requires the full PyTorch integration model")
    def test_ruri_reranker_homophone_disambiguation(self):
        from ranker.ruri_ranker import RuriReranker
        ranker = RuriReranker()
        req = {
            "request_id": "ruri-1",
            "preceding_text": "医師の治療で長年の病気を",
            "following_text": "ことができた。",
            "read": "なおす",
            "candidates": [
                {"id": "c1", "text": "直す", "rank": 1},
                {"id": "c2", "text": "治す", "rank": 2},
            ],
        }
        res = ranker.rank(req)
        self.assertEqual(res["candidates"][0]["id"], "c2")

    @unittest.skipUnless(FULL_MODEL_TESTS, "requires the full PyTorch integration model")
    def test_ruri_reranker_lexical_grounding_shukanshi(self):
        from ranker.ruri_ranker import RuriReranker
        ranker = RuriReranker()
        req = {
            "request_id": "ruri-2",
            "preceding_text": "出張のたびに買っていたので、いつの間にか",
            "following_text": "を読む習慣が付いた。",
            "read": "しゅうかんし",
            "candidates": [
                {"id": "c1", "text": "週間誌", "rank": 1},
                {"id": "c2", "text": "週刊誌", "rank": 2},
            ],
        }
        res = ranker.rank(req)
        self.assertEqual(res["candidates"][0]["id"], "c2")

    @unittest.skipUnless(HAS_TORCH, "requires torch")
    def test_ruri_preserves_duplicate_surface_form_ids(self):
        import torch
        from ranker.ruri_ranker import RuriReranker

        class FakeTokenizer:
            def __init__(self):
                self.batch_size = 0

            def __call__(self, queries, documents, **_kwargs):
                self.batch_size = len(queries)
                return {"input_ids": torch.arange(len(queries)).reshape(-1, 1)}

        class FakeModel:
            def __call__(self, **inputs):
                return type("Output", (), {"logits": inputs["input_ids"].float()})()

        tokenizer = FakeTokenizer()
        ranker = object.__new__(RuriReranker)
        ranker.tokenizer = tokenizer
        ranker.model = FakeModel()
        ranker.device = "cpu"
        ranker.lexicon = None
        ranker.prior_w = 0.1

        req = {
            "request_id": "duplicate-ids",
            "preceding_text": "",
            "read": "はな",
            "candidates": [
                {"id": "c0", "text": "花", "rank": 1},
                {"id": "c1", "text": "花", "rank": 2},
                {"id": "c2", "text": "鼻", "rank": 3},
            ],
        }
        response = ranker.rank(req)
        validated = validate_response(response, validate_request(req))
        self.assertEqual(tokenizer.batch_size, 2)
        self.assertEqual({item["id"] for item in validated["candidates"]},
                         {"c0", "c1", "c2"})

    @unittest.skipUnless(HAS_TORCH, "requires torch")
    def test_ruri_passes_domain_and_custom_instruction_to_model(self):
        import torch
        from ranker.ruri_ranker import RuriReranker

        class CapturingTokenizer:
            def __init__(self):
                self.queries = []
                self.documents = []

            def __call__(self, queries, documents, **_kwargs):
                self.queries = list(queries)
                self.documents = list(documents)
                return {"input_ids": torch.arange(len(queries)).reshape(-1, 1)}

        class FakeModel:
            def __call__(self, **inputs):
                return type("Output", (), {"logits": inputs["input_ids"].float()})()

        tokenizer = CapturingTokenizer()
        ranker = object.__new__(RuriReranker)
        ranker.tokenizer = tokenizer
        ranker.model = FakeModel()
        ranker.device = "cpu"
        ranker.lexicon = None
        ranker.prior_w = 0.1
        ranker.context_enabled = True
        ranker.context_chars = 8
        ranker.document_instruction = "医学文書。循環器内科の正式表記を優先する。"

        req = request("これは切り捨てる長い文脈の末尾")
        ranker.rank(req)
        self.assertTrue(tokenizer.queries)
        self.assertIn("循環器内科", tokenizer.queries[0])
        self.assertNotIn("これは切り捨てる", tokenizer.queries[0])
        self.assertIn("長い文脈の末尾"[-8:], tokenizer.queries[0])

    @unittest.skipUnless(not HEADLESS_TESTS, "native loading UI is not started on headless CI")
    def test_loading_indicator_lifecycle(self):
        from ranker.loading_ui import LoadingIndicator
        indicator = LoadingIndicator(text="AI変換中…", enabled=True)
        indicator.start()
        with indicator.active():
            pass
        indicator.stop()

    def test_protocol_rejects_candidate_generation(self):
        req = validate_request(request(""))
        bad = {
            "request_id": req["request_id"],
            "candidates": [{"id": "new", "text": "生成文字列", "score": 1, "rank": 1}],
        }
        with self.assertRaises(ProtocolError):
            validate_response(bad, req)

    def test_protocol_rejects_unknown_id_and_nan(self):
        req = validate_request(request(""))
        bad = {"request_id": req["request_id"], "candidates": [
            {"id": "unknown", "score": 1, "rank": 1},
            {"id": "c2", "score": float("nan"), "rank": 2},
            {"id": "c3", "score": 0, "rank": 3},
        ]}
        with self.assertRaises(ProtocolError):
            validate_response(bad, req)

    def test_protocol_rejects_duplicate_fields_and_non_contiguous_input_rank(self):
        with self.assertRaises(ProtocolError):
            loads_strict('{"request_id":"x","request_id":"y"}')
        req = request("")
        req["candidates"][1]["rank"] = 3
        with self.assertRaises(ProtocolError):
            validate_request(req)

    def test_invalid_and_timeout_fallback_to_original(self):
        req = request("象の長い")
        fallback = safe_rank(req, lambda _req: {"bad": True}, timeout_ms=200)
        self.assertEqual([item["id"] for item in fallback["candidates"]], ["c1", "c2", "c3"])
        fallback = safe_rank(req, lambda _req: (_ for _ in ()).throw(KeyError("backend")), timeout_ms=200)
        self.assertEqual(fallback, original_order(req))
        started = time.perf_counter()
        fallback = safe_rank(req, lambda _req: (time.sleep(0.5) or RuleBasedRanker().rank(req)), timeout_ms=30)
        elapsed = time.perf_counter() - started
        self.assertEqual(fallback, original_order(req))
        self.assertLess(elapsed, 0.2)

    def test_stdio_e2e(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proc = subprocess.Popen(
            [sys.executable, "-m", "ranker.ranker", "--stdio",
             "--backend", "rule"],
            cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        assert proc.stdin and proc.stdout
        proc.stdin.write((json.dumps(request("庭に咲いた美しい"), ensure_ascii=False) + "\n").encode())
        proc.stdin.flush()
        line = proc.stdout.readline()
        proc.terminate()
        proc.wait(timeout=2)
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
        response = json.loads(line.decode())
        validate_response(response, validate_request(request("庭に咲いた美しい")))
        self.assertEqual(response["candidates"][0]["id"], "c2")

    @unittest.skipUnless(HAS_TORCH, "requires torch")
    def test_qwen_backend_uses_batched_forward_and_existing_ids_only(self):
        import torch

        class FakeTokenizer:
            def convert_tokens_to_ids(self, token):
                return {"no": 0, "yes": 1}[token]

            def encode(self, text, add_special_tokens=False):
                return [9] if "system" in text else [8]

            def __call__(self, texts, **kwargs):
                # A marker stands in for each supplied document; it is not a
                # candidate produced by the backend.
                markers = []
                for text in texts:
                    document = text.rsplit("<Document>: ", 1)[-1]
                    markers.append(2 if document == "はな" else
                                   3 if document == "花" else 4)
                return {"input_ids": [[marker] for marker in markers]}

            def pad(self, encoded, **kwargs):
                return {"input_ids": torch.tensor(encoded["input_ids"])}

        class FakeModel:
            def __init__(self):
                self.forward_calls = 0

            def eval(self):
                return self

            def __call__(self, **inputs):
                self.forward_calls += 1
                ids = inputs["input_ids"]
                logits = torch.zeros((ids.shape[0], ids.shape[1], 5))
                # The fake model scores each input row independently in one
                # forward call, with no text output API.
                logits[:, -1, 1] = ids[:, 1].float()
                return type("Output", (), {"logits": logits})()

        model = FakeModel()
        ranker = QwenReranker(
            tokenizer=FakeTokenizer(), model=model, torch_module=torch,
        )
        result = ranker.rank(request("庭に咲いた美しい"))
        self.assertEqual(model.forward_calls, 1)
        self.assertEqual(result["candidates"][0]["id"], "c3")
        self.assertTrue(all(set(item) == {"id", "score", "rank"}
                            for item in result["candidates"]))

    @unittest.skipUnless(sys.platform == "win32", "Windows Named Pipe smoke test")
    def test_windows_named_pipe_e2e(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pipe = r"\\.\pipe\ai_ime_ranker_test_%d" % os.getpid()
        proc = subprocess.Popen(
            [sys.executable, "-m", "ranker.ranker", "--pipe", pipe,
             "--backend", "rule"],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            deadline = time.time() + 3
            while True:
                try:
                    response = windows_rank_once(pipe, request("象の長い"), timeout_ms=100)
                    break
                except (OSError, TimeoutError):
                    if time.time() > deadline:
                        raise
                    time.sleep(0.02)
            self.assertEqual(response["candidates"][0]["id"], "c3")
        finally:
            proc.terminate()
            proc.wait(timeout=2)
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
