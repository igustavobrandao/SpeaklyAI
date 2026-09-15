from __future__ import annotations

from typing import Any

import numpy as np

from whisper_microfone import engine as engine_module
from whisper_microfone.config.schemas import FullConfig


class _FakeRecorder:
    def __init__(self, _config: object) -> None:
        self.is_recording = False
        self.on_volume = None

    def start(self) -> None:
        self.is_recording = True

    def stop(self) -> np.ndarray:
        self.is_recording = False
        return np.ones(16000, dtype=np.float32)


class _FakeVAD:
    def __init__(self, _config: object) -> None:
        self.trimmed_audio: np.ndarray | None = None

    def trim_silence(self, audio: np.ndarray) -> np.ndarray:
        self.trimmed_audio = audio
        return audio


class _SilentVAD(_FakeVAD):
    def trim_silence(self, audio: np.ndarray) -> np.ndarray:
        self.trimmed_audio = audio
        return np.array([], dtype=np.float32)


class _FakeTranscriber:
    def __init__(self, _model_config: object, _transcription_config: object) -> None:
        self.calls: list[tuple[np.ndarray, str]] = []

    def transcribe(self, audio: np.ndarray, language: str) -> str:
        self.calls.append((audio, language))
        return "Texto ditado"


class _FakeInjector:
    def __init__(self, _config: object) -> None:
        self.texts: list[str] = []

    def inject(self, text: str) -> None:
        self.texts.append(text)


class _FakeHistory:
    def __init__(self, _config: object) -> None:
        self.entries: list[tuple[str, float, float, str]] = []

    def add(self, text: str, duration_ms: float, latency_ms: float, language: str) -> None:
        self.entries.append((text, duration_ms, latency_ms, language))


class _FakeHotkey:
    def __init__(self, _combination: str, on_press: object, on_release: object) -> None:
        self.on_press = on_press
        self.on_release = on_release

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def update_combination(self, _combination: str) -> None:
        pass


class _FakeMetrics:
    def get_metrics(self) -> object:
        return object()


def _make_engine(monkeypatch, vad_class: type[_FakeVAD] = _FakeVAD):
    monkeypatch.setattr(engine_module, "AudioRecorder", _FakeRecorder)
    monkeypatch.setattr(engine_module, "SileroVAD", vad_class)
    monkeypatch.setattr(engine_module, "GroqTranscriber", _FakeTranscriber)
    monkeypatch.setattr(engine_module, "TextInjector", _FakeInjector)
    monkeypatch.setattr(engine_module, "HistoryStore", _FakeHistory)
    monkeypatch.setattr(engine_module, "PushToTalkHotkey", _FakeHotkey)
    monkeypatch.setattr(engine_module, "MetricsCollector", _FakeMetrics)
    return engine_module.Engine(FullConfig())


def test_engine_processes_dictation_without_real_devices_or_api(qapp, monkeypatch) -> None:
    engine = _make_engine(monkeypatch)
    transcribed: list[tuple[str, dict[str, Any]]] = []
    states: list[str] = []
    engine.transcribed.connect(lambda text, metadata: transcribed.append((text, metadata)))
    engine.state_changed.connect(states.append)

    engine._transcribe_and_inject(np.ones(16000, dtype=np.float32))

    assert engine._injector.texts == ["Texto ditado"]
    assert engine._history.entries[0][0] == "Texto ditado"
    assert engine._history.entries[0][1] == 1000.0
    assert engine._history.entries[0][3] == "auto"
    assert transcribed[0][0] == "Texto ditado"
    assert transcribed[0][1]["duration_ms"] == 1000.0
    assert states == ["idle"]


def test_engine_reports_vad_silence_without_calling_groq(qapp, monkeypatch) -> None:
    engine = _make_engine(monkeypatch, _SilentVAD)
    errors: list[str] = []
    states: list[str] = []
    engine.error_occurred.connect(errors.append)
    engine.state_changed.connect(states.append)

    engine._transcribe_and_inject(np.ones(16000, dtype=np.float32))

    assert engine._transcriber.calls == []
    assert engine._injector.texts == []
    assert errors == ["Nenhuma fala detectada após VAD"]
    assert states == ["idle"]
