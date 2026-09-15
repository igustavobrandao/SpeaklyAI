from __future__ import annotations

import sys

from loguru import logger

from whisper_microfone.config.paths import logs_dir
from whisper_microfone.config.schemas import LoggingConfig

_INITIALIZED = False

_FORMAT_CONSOLE = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>"
)

_FORMAT_FILE = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{line} — {message}"
)


def setup_logging(config: LoggingConfig | None = None) -> None:
    """Configura loguru com saída no console e arquivo rotativo.

    Pode ser chamado múltiplas vezes (ex: após hot-reload de config) —
    remove handlers anteriores antes de reconfigurar.

    Args:
        config: LoggingConfig com level, rotação e retenção.
                None usa defaults (INFO, 10 MB, 5 arquivos).
    """
    global _INITIALIZED

    logger.remove()  # remove todos os handlers anteriores (incluindo stderr padrão)

    level = "INFO"
    rotation_mb = 10
    retention = 5
    log_metrics = False

    if config is not None:
        level = config.level
        rotation_mb = config.file_rotation_mb
        retention = config.file_retention
        log_metrics = config.log_metrics

    # Console — apenas WARNING+ em produção para não poluir; DEBUG mostra tudo
    # sys.stderr é None em executáveis --noconsole do PyInstaller
    if sys.stderr is not None:
        console_level = level if level == "DEBUG" else "WARNING"
        logger.add(
            sys.stderr,
            level=console_level,
            format=_FORMAT_CONSOLE,
            colorize=True,
            backtrace=True,
            diagnose=level == "DEBUG",
        )

    # Arquivo rotativo em logs_dir()
    log_file = logs_dir() / "whisper-microfone.log"
    logger.add(
        str(log_file),
        level=level,
        format=_FORMAT_FILE,
        rotation=f"{rotation_mb} MB",
        retention=retention,
        encoding="utf-8",
        backtrace=True,
        diagnose=level == "DEBUG",
        enqueue=True,   # escrita assíncrona — não bloqueia threads de áudio
    )

    if not _INITIALIZED:
        logger.debug("Logging inicializado — arquivo: {}", log_file)
        _INITIALIZED = True
    else:
        logger.debug("Logging reconfigurado — nível: {}", level)

    if log_metrics:
        logger.debug("log_metrics ativo — métricas serão registradas no log")


def reconfigure(config: LoggingConfig) -> None:
    """Reconifgura logging após hot-reload. Alias semântico de setup_logging()."""
    setup_logging(config)
