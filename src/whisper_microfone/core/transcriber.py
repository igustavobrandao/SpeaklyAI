from __future__ import annotations

import io
import os

import numpy as np
import soundfile as sf
from groq import Groq
from loguru import logger

from whisper_microfone.config.schemas import ModelConfig, TranscriptionConfig


class GroqTranscriber:
    """Transcritor via Groq Whisper API (sem modelo local)."""

    def __init__(self, model_cfg: ModelConfig, transcription_cfg: TranscriptionConfig) -> None:
        self._model_cfg = model_cfg
        self._transcription = transcription_cfg
        api_key = os.environ.get("GROQ_API_KEY", "")
        self._client = Groq(api_key=api_key)

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        raw = language if language is not None else self._model_cfg.language
        lang = raw if raw and raw != "auto" else None

        buf = io.BytesIO()
        sf.write(buf, audio, 16000, format="WAV", subtype="PCM_16")
        buf.seek(0)
        buf.name = "audio.wav"

        model_name = self._model_cfg.groq_model or "whisper-large-v3-turbo"

        prompt = self._transcription.initial_prompt
        logger.debug("Enviando áudio para Groq ({} amostras, modelo={})", len(audio), model_name)
        if lang and prompt:
            result = self._client.audio.transcriptions.create(
                file=buf,
                model=model_name,
                response_format="text",
                temperature=self._transcription.temperature,
                language=lang,
                prompt=prompt,
            )
        elif lang:
            result = self._client.audio.transcriptions.create(
                file=buf,
                model=model_name,
                response_format="text",
                temperature=self._transcription.temperature,
                language=lang,
            )
        elif prompt:
            result = self._client.audio.transcriptions.create(
                file=buf,
                model=model_name,
                response_format="text",
                temperature=self._transcription.temperature,
                prompt=prompt,
            )
        else:
            result = self._client.audio.transcriptions.create(
                file=buf,
                model=model_name,
                response_format="text",
                temperature=self._transcription.temperature,
            )

        text = result if isinstance(result, str) else getattr(result, "text", "")
        return text.strip()
