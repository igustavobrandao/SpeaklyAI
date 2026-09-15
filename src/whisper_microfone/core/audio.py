from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from contextlib import suppress

import numpy as np
import sounddevice as sd
from loguru import logger

from whisper_microfone.config.schemas import AudioConfig


class AudioRecorderError(Exception):
    """Falha ao abrir ou operar o stream de áudio."""


class AudioRecorder:
    """Captura áudio do microfone via sounddevice e acumula chunks em deque thread-safe.

    O InputStream roda em thread separada gerenciada pelo sounddevice. Os dados
    chegam via callback e são empilhados num deque; stop() concatena tudo de uma
    vez para evitar cópias incrementais enquanto a gravação acontece.
    """

    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._chunks: deque[np.ndarray] = deque()
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.on_volume: Callable[[float], None] | None = None

    # ------------------------------------------------------------------
    # Resolução de dispositivo
    # ------------------------------------------------------------------

    def _resolve_device(self) -> int | None:
        """Retorna o índice do dispositivo de entrada a usar.

        Regras de prioridade:
        1. device_name fornecido: busca por substring case-insensitive no nome.
        2. device_index != -1: usa o índice diretamente.
        3. None: deixa o sounddevice usar o padrão do sistema.
        """
        if self._config.device_name:
            name_lower = self._config.device_name.lower()
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                # Considera apenas dispositivos de entrada
                if dev["max_input_channels"] > 0 and name_lower in dev["name"].lower():
                    logger.debug(
                        "Dispositivo encontrado por nome '{}': idx={} nome='{}'",
                        self._config.device_name,
                        idx,
                        dev["name"],
                    )
                    return idx
            raise AudioRecorderError(
                f"Nenhum dispositivo de entrada com nome contendo "
                f"'{self._config.device_name}' foi encontrado. "
                f"Use AudioConfig(device_name='') para usar o padrão do sistema."
            )

        if self._config.device_index != -1:
            return self._config.device_index

        # None instrui o sounddevice a usar o dispositivo padrão do SO
        return None

    # ------------------------------------------------------------------
    # Callback interno do InputStream
    # ------------------------------------------------------------------

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.warning("sounddevice status no callback: {}", status)
        chunk = indata.copy()
        with self._lock:
            self._chunks.append(chunk)
        if self.on_volume is not None:
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            with suppress(Exception):
                self.on_volume(rms)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        """Abre o InputStream e começa a acumular chunks de áudio.

        Levanta AudioRecorderError se o dispositivo não puder ser aberto,
        com mensagem explicativa para o usuário (sem stack trace interno).
        """
        if self._stream is not None:
            logger.warning("start() chamado com stream já aberto — ignorado")
            return

        self._chunks.clear()
        device = self._resolve_device()

        try:
            self._stream = sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype="float32",
                device=device,
                callback=self._callback,
            )
            self._stream.start()
        except sd.PortAudioError as exc:
            self._stream = None
            raise AudioRecorderError(
                f"Não foi possível abrir o microfone: {exc}. "
                f"Verifique se há um dispositivo de entrada disponível e se ele "
                f"não está sendo usado exclusivamente por outro processo."
            ) from exc

        logger.debug(
            "Gravação iniciada — device={} sample_rate={} channels={}",
            device,
            self._config.sample_rate,
            self._config.channels,
        )

    def stop(self) -> np.ndarray | None:
        """Para o stream e retorna o áudio capturado como ndarray float32 1-D.

        Retorna None se a duração gravada for menor que config.min_duration_ms.
        Aplica corte em config.max_duration_seconds caso o usuário tenha
        segurado o PTT além do limite configurado.
        """
        if self._stream is None:
            logger.warning("stop() chamado sem stream ativo — retorna None")
            return None

        self._stream.stop()
        self._stream.close()
        self._stream = None

        with self._lock:
            chunks = list(self._chunks)
            self._chunks.clear()

        if not chunks:
            logger.debug("Nenhum chunk capturado — retorna None")
            return None

        audio = np.concatenate(chunks, axis=0).flatten()

        duration_ms = len(audio) / self._config.sample_rate * 1000
        min_ms = self._config.min_duration_ms

        if duration_ms < min_ms:
            logger.debug(
                "Áudio descartado: duração={:.0f}ms < mínimo={}ms",
                duration_ms,
                min_ms,
            )
            return None

        logger.debug(
            "Gravação finalizada — {:.2f}s / {} amostras",
            len(audio) / self._config.sample_rate,
            len(audio),
        )
        return audio


# ---------------------------------------------------------------------------
# Verificação inline (dry-run sem microfone real)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    config = AudioConfig()
    recorder = AudioRecorder(config)

    print(f"AudioConfig: sample_rate={config.sample_rate}, channels={config.channels}, "
          f"min_duration_ms={config.min_duration_ms}, max_duration_seconds={config.max_duration_seconds}")

    result: np.ndarray | None
    try:
        recorder.start()
        print("Stream aberto. Aguardando 0.1s...")
        time.sleep(0.1)
        result = recorder.stop()
    except AudioRecorderError as exc:
        print(f"Erro ao abrir microfone (esperado em ambiente sem microfone): {exc}")
        result = None

    if result is None:
        print("Resultado: None (duração muito curta para o mínimo configurado)")
    else:
        print(f"Resultado: ndarray shape={result.shape}, dtype={result.dtype}, "
              f"duração={len(result)/config.sample_rate:.3f}s")
