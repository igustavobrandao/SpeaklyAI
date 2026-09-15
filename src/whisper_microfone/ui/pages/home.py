from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.engine import Engine
from whisper_microfone.ui.widgets.status_card import StatusCard
from whisper_microfone.ui.widgets.transcription_card import TranscriptionCard

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_BG = "#111318"
_PAGE_PADDING = 32
_SECTION_SPACING = 20


class HomePage(QWidget):
    """Página principal — estado do engine e última transcrição."""

    def __init__(
        self,
        engine: Engine,
        config: FullConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._config = config

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        self.setObjectName("HomePage")
        self.setStyleSheet(f"QWidget#HomePage {{ background-color: {_BG}; }}")

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        scroll.setWidget(container)

        content = QVBoxLayout(container)
        content.setContentsMargins(_PAGE_PADDING, _PAGE_PADDING, _PAGE_PADDING, _PAGE_PADDING)
        content.setSpacing(_SECTION_SPACING)

        self._status_card = StatusCard()
        content.addWidget(self._status_card)

        self._transcription_card = TranscriptionCard()
        content.addWidget(self._transcription_card)

        content.addStretch()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _connect_signals(self) -> None:
        self._engine.state_changed.connect(self._on_state_changed)
        self._engine.transcribed.connect(self._transcription_card.set_transcription)

    def _on_state_changed(self, state: str) -> None:
        self._status_card.set_state(state)
