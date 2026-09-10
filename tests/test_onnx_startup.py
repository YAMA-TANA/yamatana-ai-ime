from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from ranker import onnx_ranker


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    model_dir = tmp_path / "models" / "onnx"
    model_dir.mkdir(parents=True)
    for name in ("ruri-ime-fp16.onnx", "ruri-ime-int8.onnx", "tokenizer.json"):
        (model_dir / name).touch()
    monkeypatch.setattr(onnx_ranker, "_runtime_roots", lambda: [tmp_path])
    providers = Mock(return_value=["DmlExecutionProvider", "CPUExecutionProvider"])
    monkeypatch.setattr(onnx_ranker.ort, "get_available_providers", providers)
    tokenizer = Mock()
    tokenizer.encode_batch.side_effect = lambda pairs: [
        SimpleNamespace(ids=[1, 2], attention_mask=[1, 1]) for _ in pairs
    ]
    tokenizer_factory = Mock()
    tokenizer_factory.from_file.return_value = tokenizer
    monkeypatch.setattr(onnx_ranker, "Tokenizer", tokenizer_factory)
    calls = []

    def install(failure=None):
        def create(path, *, sess_options, providers):
            gpu = "DmlExecutionProvider" in providers
            calls.append((Path(path), sess_options, providers))
            if failure == "all" or (gpu and failure == "create"):
                raise RuntimeError("session creation failed")
            session = Mock()
            session.get_providers.return_value = (
                ["CPUExecutionProvider"] if failure == "inactive" else providers
            )
            if gpu and failure == "warmup":
                session.run.side_effect = RuntimeError("GPU execution failed")
            else:
                session.run.return_value = [np.zeros((32, 1), dtype=np.float32)]
            return session
        monkeypatch.setattr(onnx_ranker.ort, "InferenceSession", create)

    install()
    return SimpleNamespace(
        model_dir=model_dir, calls=calls, install=install,
        providers=providers, tokenizer_factory=tokenizer_factory,
    )


def create_ranker(mode="auto", **kwargs):
    return onnx_ranker.OnnxRuriReranker(
        settings={"compute_mode": mode, "lexical_grounding": False}, **kwargs
    )


@pytest.mark.parametrize("failure", ["create", "warmup", "inactive"])
def test_auto_recovers_from_gpu_failure_with_fresh_cpu_int8_session(runtime, failure):
    runtime.install(failure)
    ranker = create_ranker()
    assert [call[0].name for call in runtime.calls] == [
        "ruri-ime-fp16.onnx", "ruri-ime-int8.onnx",
    ]
    gpu_options, cpu_options = [call[1] for call in runtime.calls]
    assert gpu_options is not cpu_options
    assert not gpu_options.enable_mem_pattern
    assert cpu_options.enable_mem_pattern
    assert runtime.calls[-1][2] == ["CPUExecutionProvider"]
    assert ranker.device == "cpu"
    assert Path(ranker.model_path).name == "ruri-ime-int8.onnx"
    ranker.session.run.assert_called_once()  # CPU is warmed before ready.


def test_auto_handles_missing_gpu_artifact(runtime):
    (runtime.model_dir / "ruri-ime-fp16.onnx").unlink()
    ranker = create_ranker()
    assert len(runtime.calls) == 1
    assert Path(ranker.model_path).name == "ruri-ime-int8.onnx"
    assert ranker.device == "cpu"


@pytest.mark.parametrize("mode", ["auto", "gpu"])
def test_working_directml_is_retained(runtime, mode):
    ranker = create_ranker(mode)
    assert len(runtime.calls) == 1
    assert ranker.device == "gpu-directml"
    assert Path(ranker.model_path).name == "ruri-ime-fp16.onnx"


@pytest.mark.parametrize("failure", ["create", "warmup", "inactive"])
def test_explicit_gpu_failure_is_reported_without_silent_cpu_switch(runtime, failure):
    runtime.install(failure)
    with pytest.raises(RuntimeError):
        create_ranker("gpu")
    assert len(runtime.calls) == 1


def test_explicit_gpu_without_provider_has_actionable_error(runtime):
    runtime.providers.return_value = ["CPUExecutionProvider"]
    with pytest.raises(RuntimeError, match="設定"):
        create_ranker("gpu")
    assert not runtime.calls


@pytest.mark.parametrize("mode", ["auto", "cpu"])
def test_cpu_only_runtime_starts_directly_on_int8(runtime, mode):
    runtime.providers.return_value = ["CPUExecutionProvider"]
    ranker = create_ranker(mode)
    assert len(runtime.calls) == 1
    assert runtime.calls[0][2] == ["CPUExecutionProvider"]
    assert Path(ranker.model_path).name == "ruri-ime-int8.onnx"


def test_explicit_cpu_does_not_try_available_gpu(runtime):
    assert create_ranker("cpu").device == "cpu"
    assert runtime.calls[0][2] == ["CPUExecutionProvider"]


def test_cpu_failure_propagates_after_one_auto_retry(runtime):
    runtime.install("all")
    with pytest.raises(RuntimeError, match="session creation failed"):
        create_ranker()
    assert len(runtime.calls) == 2


def test_explicit_model_and_its_tokenizer_are_preserved_on_cpu_retry(runtime, tmp_path):
    custom = tmp_path / "custom"
    custom.mkdir()
    model = custom / "custom.onnx"
    model.touch()
    tokenizer = custom / "tokenizer.json"
    tokenizer.touch()
    runtime.install("create")
    ranker = create_ranker(model_path=model)
    assert [call[0] for call in runtime.calls] == [model, model]
    assert Path(ranker.model_path) == model
    assert all(call.args == (str(tokenizer),)
               for call in runtime.tokenizer_factory.from_file.call_args_list)
