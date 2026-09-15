from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QMetaObject, Qt

from whisper_microfone.config.loader import load_config
from whisper_microfone.core.hotkey import PushToTalkHotkey
from whisper_microfone.engine import Engine
from whisper_microfone.logging_setup import setup_logging
from whisper_microfone.ui.app import WhisperApp
from whisper_microfone.ui.main_window import MainWindow
from whisper_microfone.ui.mic_popup import MicPopup
from whisper_microfone.ui.pages.about import AboutPage
from whisper_microfone.ui.pages.config_page import ConfigPage
from whisper_microfone.ui.pages.history import HistoryPage
from whisper_microfone.ui.pages.home import HomePage
from whisper_microfone.ui.tray import SystemTray


def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    _load_dotenv()
    config = load_config()
    setup_logging(config.logging)

    # QApplication deve existir antes de qualquer QObject (Engine, MainWindow)
    app = WhisperApp(config, sys.argv)

    engine = Engine(config)  # QObject — requer QApplication já criada

    window = MainWindow(engine, config)

    # Injecta páginas reais nos placeholders
    window.replace_page(0, HomePage(engine, config))
    window.replace_page(1, ConfigPage(engine, config))
    window.replace_page(2, HistoryPage(engine, config))
    window.replace_page(3, AboutPage(engine, config))

    # Garante que a página inicial (Início) está selecionada após injeção
    window.navigate_to(0)

    tray = SystemTray(engine, window, config)
    tray.show()

    mic_popup = MicPopup(engine)

    def _toggle_popup_safe() -> None:
        print(">>> POPUP HOTKEY DETECTADO", flush=True)
        # Cruza da thread pynput → UI thread
        QMetaObject.invokeMethod(mic_popup, "toggle", Qt.ConnectionType.QueuedConnection)

    popup_hotkey: PushToTalkHotkey | None = None
    if config.shortcuts.open_mic_popup.enabled:
        popup_hotkey = PushToTalkHotkey(
            config.shortcuts.open_mic_popup.combination,
            on_press=_toggle_popup_safe,
            on_release=lambda: None,
        )
        popup_hotkey.start()

    # Inicia janela conforme configuração
    if config.app.start_minimized:
        window.hide()
    else:
        window.show()

    engine.start()

    exit_code = app.exec()

    engine.stop()
    if popup_hotkey is not None:
        popup_hotkey.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
