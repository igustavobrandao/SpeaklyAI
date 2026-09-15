from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np

from whisper_microfone.config.schemas import ModelConfig, TranscriptionConfig
from whisper_microfone.core import transcriber as transcriber_module


class _FakeTranscriptions:
    def __init__(self, result: object) -> None:
        self.result = result
        self.kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        return self.result


class _FakeGroqClient:
    def __init__(self, result: object) -> None:
        self.transcriptions = _FakeTranscriptions(result)
        self.audio = SimpleNamespace(transcriptions=self.transcriptions)


def _build_transcriber(monkeypatch, result: object) -> tuple[
    transcriber_module.GroqTranscriber, _FakeGroqClient,
]:
    client = _FakeGroqClient(result)
    captured: dict[str, str] = {}

    def fake_groq(*, api_key: str) -> _FakeGroqClient:
        captured["api_key"] = api_key
        return client

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(transcriber_module, "Groq", fake_groq)

    transcriber = transcriber_module.GroqTranscriber(
        ModelConfig(),
        TranscriptionConfig(initial_prompt="Pontue corretamente."),
    )
    assert captured["api_key"] == "test-key"
    return transcriber, client


def test_transcribe_sends_wav_with_current_groq_contract(monkeypatch) -> None:
    transcriber, client = _build_transcriber(monkeypatch, "  Olá, mundo.  ")

    text = transcriber.transcribe(np.zeros(1600, dtype=np.float32))

    assert text == "Olá, mundo."
    assert client.transcriptions.kwargs is not None
    request = client.transcriptions.kwargs
    assert request["model"] == "whisper-large-v3-turbo"
    assert request["response_format"] == "text"
    assert request["prompt"] == "Pontue corretamente."
    assert "language" not in request
    assert request["file"].getvalue().startswith(b"RIFF")


def test_transcribe_forwards_explicit_language_and_object_response(monkeypatch) -> None:
    transcriber, client = _build_transcriber(
        monkeypatch,
        SimpleNamespace(text=" English result "),
    )

    text = transcriber.transcribe(np.zeros(800, dtype=np.float32), language="en")

    assert text == "English result"
    assert client.transcriptions.kwargs is not None
    assert client.transcriptions.kwargs["language"] == "en"
