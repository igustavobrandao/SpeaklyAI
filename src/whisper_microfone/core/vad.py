from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from whisper_microfone.config.schemas import VADConfig

logger = logging.getLogger(__name__)

try:
    import torch
    from silero_vad import get_speech_timestamps

    _SILERO_AVAILABLE = True
except ImportError:
    _SILERO_AVAILABLE = False
    logger.warning(
        "silero-vad não está instalado. VAD desabilitado — áudio será repassado sem modificação. "
        "Instale com: pip install silero-vad"
    )


def _load_model_safe() -> torch.jit.ScriptModule:
    """Carrega o modelo JIT do Silero VAD tolerando paths com caracteres não-ASCII.

    No Windows, ``torch.jit.load`` falha se o path contém caracteres fora do
    range ASCII (e.g. letras acentuadas no nome do usuário). A estratégia é
    copiar o arquivo `.jit` para um path temporário de nome curto (8.3) antes
    de carregar.
    """
    import os
    import shutil
    import tempfile
    from importlib import resources as impresources

    jit_src = str(impresources.files("silero_vad.data").joinpath("silero_vad.jit"))

    needs_copy = not jit_src.isascii()
    if needs_copy:
        tmp_path = tempfile.mktemp(suffix=".jit", prefix="silero_vad_")
        shutil.copy2(jit_src, tmp_path)
        load_path = tmp_path
    else:
        tmp_path = None
        load_path = jit_src

    try:
        model = torch.jit.load(load_path, map_location="cpu")
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return model


class SileroVAD:
    """Wrapper do Silero VAD para remoção de silêncio em áudio float32 mono 16 kHz."""

    _SAMPLE_RATE: int = 16000
    _WINDOW_SIZE_SAMPLES: int = 512  # obrigatório para 16 kHz conforme documentação oficial

    def __init__(self, config: VADConfig) -> None:
        self._config = config
        self._model: object | None = None

        # Carregamento lazy — o modelo JIT é pesado e trava o __init__.
        # Será carregado na primeira chamada a trim_silence().
        if not _SILERO_AVAILABLE:
            logger.warning("SileroVAD instanciado sem biblioteca disponível. Operando em modo passthrough.")
        elif not config.enabled:
            logger.info("VAD desabilitado por configuração (config.vad.enabled=False).")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def trim_silence(self, audio: np.ndarray) -> np.ndarray:
        """Remove silêncio de *audio* (float32 mono 16 kHz) e retorna apenas fala.

        Retorna array vazio ``(0,)`` se nenhum segmento de fala for detectado.
        Retorna *audio* original se o VAD não estiver disponível ou desabilitado.
        """
        if not _SILERO_AVAILABLE or not self._config.enabled:
            return audio
        if self._model is None:
            self._model = _load_model_safe()
            logger.info("Silero VAD carregado (JIT, CPU).")

        if audio.size == 0:
            return audio

        tensor = self._to_tensor(audio)
        timestamps = self._detect_speech(tensor)

        if not timestamps:
            logger.debug("VAD: nenhum segmento de fala detectado.")
            return np.empty(0, dtype=np.float32)

        return self._collect(audio, timestamps)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _to_tensor(self, audio: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(audio)

    def _detect_speech(self, tensor: torch.Tensor) -> list[dict[str, int]]:
        cfg = self._config
        return get_speech_timestamps(
            tensor,
            self._model,
            threshold=cfg.threshold,
            sampling_rate=self._SAMPLE_RATE,
            min_silence_duration_ms=cfg.min_silence_ms,
            speech_pad_ms=cfg.speech_pad_ms,
            window_size_samples=self._WINDOW_SIZE_SAMPLES,
            return_seconds=False,  # coordenadas em amostras para slice direto no numpy
        )

    def _collect(self, audio: np.ndarray, timestamps: list[dict[str, int]]) -> np.ndarray:
        """Concatena segmentos de fala detectados em um único array."""
        chunks: list[np.ndarray] = []
        for seg in timestamps:
            start: int = seg["start"]
            end: int = seg["end"]
            chunks.append(audio[start:end])

        if not chunks:
            return np.empty(0, dtype=np.float32)

        result = np.concatenate(chunks)
        logger.debug(
            "VAD: %d segmento(s) → %d amostras de %d (%.1f%% mantido).",
            len(chunks),
            result.size,
            audio.size,
            100.0 * result.size / audio.size if audio.size else 0.0,
        )
        return result


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    from whisper_microfone.config.schemas import VADConfig

    vad = SileroVAD(VADConfig())

    silencio = np.zeros(16000 * 2, dtype=np.float32)
    resultado_silencio = vad.trim_silence(silencio)
    print(f"Silêncio puro  → shape: {resultado_silencio.shape}")

    ruido = np.random.uniform(-0.3, 0.3, 16000 * 2).astype(np.float32)
    resultado_ruido = vad.trim_silence(ruido)
    print(f"Ruído aleatório → shape: {resultado_ruido.shape}")
