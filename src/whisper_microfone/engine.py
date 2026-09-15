from __future__ import annotations

import threading
import time

import numpy as np
from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal

from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.core.audio import AudioRecorder
from whisper_microfone.core.history import HistoryStore
from whisper_microfone.core.hotkey import PushToTalkHotkey
from whisper_microfone.core.injector import TextInjector
from whisper_microfone.core.metrics import MetricsCollector
from whisper_microfone.core.transcriber import GroqTranscriber
from whisper_microfone.core.vad import SileroVAD


class Engine(QObject):
    """Bridge entre os módulos core e a UI Qt.

    Coordena o ciclo PTT: hotkey → gravação → VAD → transcrição Groq → injeção.
    Callbacks do pynput rodam em thread separada — apenas emitir sinais aqui,
    nunca tocar widgets Qt diretamente.
    """

    state_changed = Signal(str)      # idle | recording | transcribing | paused | error
    transcribed = Signal(str, dict)  # (texto, {"latency_ms": float, "language": str, "duration_ms": float})
    metrics_updated = Signal(object) # Metrics dataclass
    error_occurred = Signal(str)     # mensagem legível sem stack trace interno
    config_reloaded = Signal()
    volume_updated = Signal(float)   # RMS 0.0..1.0 durante gravação

    def __init__(self, config: FullConfig) -> None:
        super().__init__()
        self.config = config
        self._paused = False

        self._recorder = AudioRecorder(config.audio)
        self._vad = SileroVAD(config.vad) if config.vad.enabled else None
        self._transcriber = GroqTranscriber(config.model, config.transcription)
        self._injector = TextInjector(config.injection)
        self._metrics = MetricsCollector()
        self._history = HistoryStore(config.history)
        self._hotkey = PushToTalkHotkey(
            config.shortcuts.push_to_talk.combination,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

        self._metrics_timer = QTimer(self)
        self._metrics_timer.setInterval(config.ui.metrics_update_interval_ms)
        self._metrics_timer.timeout.connect(self._emit_metrics)

    # ------------------------------------------------------------------
    # Ciclo de vida público
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self.config.shortcuts.push_to_talk.enabled:
            self._hotkey.start()
        self._metrics_timer.start()
        self.state_changed.emit("idle")
        logger.info("Engine iniciado (Groq)")

    def stop(self) -> None:
        self._metrics_timer.stop()
        self._hotkey.stop()
        logger.info("Engine parado")

    def toggle_recording(self) -> None:
        """Alterna entre gravar e parar+transcrever (modo click-to-talk)."""
        if self._paused:
            return
        if self._recorder.is_recording:
            self._on_hotkey_release()
        else:
            self._on_hotkey_press()

    def pause(self) -> None:
        self._paused = True
        self.state_changed.emit("paused")
        logger.debug("Engine pausado")

    def resume(self) -> None:
        self._paused = False
        self.state_changed.emit("idle")
        logger.debug("Engine retomado")

    def update_config(self, new_config: FullConfig) -> None:
        old_combo = self.config.shortcuts.push_to_talk.combination
        old_hotkey_enabled = self.config.shortcuts.push_to_talk.enabled
        self.config = new_config

        self._recorder = AudioRecorder(new_config.audio)
        self._vad = SileroVAD(new_config.vad) if new_config.vad.enabled else None
        self._transcriber = GroqTranscriber(new_config.model, new_config.transcription)
        self._injector = TextInjector(new_config.injection)
        self._history = HistoryStore(new_config.history)

        if new_config.shortcuts.push_to_talk.combination != old_combo:
            self._hotkey.update_combination(new_config.shortcuts.push_to_talk.combination)

        new_hotkey_enabled = new_config.shortcuts.push_to_talk.enabled
        if old_hotkey_enabled and not new_hotkey_enabled:
            self._hotkey.stop()
        elif not old_hotkey_enabled and new_hotkey_enabled:
            self._hotkey.start()

        self._metrics_timer.setInterval(new_config.ui.metrics_update_interval_ms)

        self.config_reloaded.emit()
        self.state_changed.emit("idle")
        logger.info("Configuração recarregada")

    # ------------------------------------------------------------------
    # Callbacks do hotkey — rodam em thread pynput, NÃO na UI thread
    # ------------------------------------------------------------------

    def _on_hotkey_press(self) -> None:
        if self._paused:
            return
        self._recorder.on_volume = lambda rms: self.volume_updated.emit(min(rms * 8, 1.0))
        self.state_changed.emit("recording")
        self._recorder.start()

    def _on_hotkey_release(self) -> None:
        if self._paused:
            return
        audio = self._recorder.stop()

        if audio is None:
            self.state_changed.emit("idle")
            return

        self.state_changed.emit("transcribing")
        threading.Thread(
            target=self._transcribe_and_inject,
            args=(audio,),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # Worker de transcrição — roda em thread daemon
    # ------------------------------------------------------------------

    def _transcribe_and_inject(self, audio: np.ndarray) -> None:
        try:
            if self._vad is not None:
                audio = self._vad.trim_silence(audio)
                if len(audio) == 0:
                    self.error_occurred.emit("Nenhuma fala detectada após VAD")
                    return

            t0 = time.perf_counter()
            text = self._transcriber.transcribe(audio, self.config.model.language)
            latency_ms = (time.perf_counter() - t0) * 1000
            duration_ms = len(audio) / 16000 * 1000

            if text:
                self._injector.inject(text)
                self._history.add(
                    text,
                    duration_ms,
                    latency_ms,
                    self.config.model.language,
                )
                self.transcribed.emit(
                    text,
                    {
                        "latency_ms": latency_ms,
                        "duration_ms": duration_ms,
                        "language": self.config.model.language,
                    },
                )
                logger.info(
                    "Transcrição concluída — {:.0f}ms latência, {:.0f}ms áudio, {} chars",
                    latency_ms,
                    duration_ms,
                    len(text),
                )

        except Exception as exc:
            logger.exception("Erro na transcrição")
            self.error_occurred.emit(str(exc))

        finally:
            self.state_changed.emit("idle" if not self._paused else "paused")

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _emit_metrics(self) -> None:
        try:
            metrics = self._metrics.get_metrics()
            self.metrics_updated.emit(metrics)
            if self.config.logging.log_metrics:
                logger.debug(
                    "Métricas: RAM={:.0f}MB GPU={:.0f}%",
                    metrics.ram_mb,
                    metrics.gpu_percent,
                )
        except Exception:
            pass
