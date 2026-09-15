from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from whisper_microfone.config.paths import config_dir


class _TomlChangeHandler(FileSystemEventHandler):
    """Dispara callback ao detectar criação/modificação de *.toml."""

    def __init__(self, callback: Callable[[], None], debounce_ms: int) -> None:
        super().__init__()
        self._callback = callback
        self._debounce_s = debounce_ms / 1000.0
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_s, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        self._callback()

    def _is_toml(self, event: FileSystemEvent) -> bool:
        return not event.is_directory and str(event.src_path).endswith(".toml")

    def on_created(self, event: FileSystemEvent) -> None:
        if self._is_toml(event):
            self._schedule()

    def on_modified(self, event: FileSystemEvent) -> None:
        if self._is_toml(event):
            self._schedule()

    def on_moved(self, event: FileSystemEvent) -> None:
        dest = getattr(event, "dest_path", "")
        if not event.is_directory and str(dest).endswith(".toml"):
            self._schedule()


class ConfigWatcher:
    """Observa %APPDATA%/whisper-microfone/config/ e chama callbacks ao mudar.

    Uso:
        watcher = ConfigWatcher(on_change=reload_fn)
        watcher.start()
        ...
        watcher.stop()

    O callback é chamado em thread daemon, com debounce para evitar
    múltiplos disparos em edições rápidas (ex: editor salvando em etapas).
    """

    def __init__(
        self,
        on_change: Callable[[], None],
        watch_dir: Path | None = None,
        debounce_ms: int = 300,
    ) -> None:
        self._on_change = on_change
        self._watch_dir = watch_dir or config_dir()
        self._debounce_ms = debounce_ms
        self._observer: BaseObserver | None = None
        self._handler: _TomlChangeHandler | None = None

    def start(self) -> None:
        """Inicia o observer em background. Idempotente."""
        if self._observer is not None and self._observer.is_alive():
            return
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        self._handler = _TomlChangeHandler(self._on_change, self._debounce_ms)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self._watch_dir), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        """Para o observer. Seguro de chamar mesmo se não iniciado."""
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=2.0)
        self._observer = None
        self._handler = None

    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def __enter__(self) -> ConfigWatcher:
        self.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop()
