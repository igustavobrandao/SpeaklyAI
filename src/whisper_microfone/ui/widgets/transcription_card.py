from __future__ import annotations

import pyperclip
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_COLOR_BG = "#181a20"
_COLOR_TITLE = "rgba(255,255,255,0.48)"
_COLOR_TEXT = "rgba(255,255,255,0.90)"
_COLOR_EMPTY = "rgba(255,255,255,0.35)"
_COLOR_FOOTER = "rgba(255,255,255,0.48)"

_FONT_TITLE = 11
_FONT_TEXT = 14
_FONT_FOOTER = 11

_MAX_LINES = 4


class TranscriptionCard(QFrame):
    """Card Apple-style exibindo a última transcrição com metadados."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._show_empty()

    def _build_ui(self) -> None:
        self.setObjectName("TranscriptionCard")
        self.setStyleSheet(
            """
            QFrame#TranscriptionCard {
                background-color: #181a20;
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.08);
            }
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Cabeçalho: título + botão copiar
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel("ÚLTIMA TRANSCRIÇÃO")
        self._title_label.setStyleSheet(
            f"color: {_COLOR_TITLE}; font-size: {_FONT_TITLE}px; font-weight: 500;"
            " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
            " letter-spacing: 0.5px; background: transparent;"
        )
        self._btn_copy = QPushButton("Copiar")
        self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy.setFixedHeight(24)
        self._btn_copy.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                background: rgba(255,255,255,0.05);
                font-size: 11px;
                color: rgba(255,255,255,0.48);
                padding: 0 10px;
            }
            QPushButton:hover {
                background: rgba(0,113,227,0.15);
                color: #0071E3;
                border-color: #0071E3;
            }
        """)
        self._btn_copy.setVisible(False)
        self._btn_copy.clicked.connect(self._on_copy)
        self._last_text = ""
        header.addWidget(self._title_label)
        header.addStretch()
        header.addWidget(self._btn_copy)
        layout.addLayout(header)

        # Texto da transcrição
        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addWidget(self._text_label)

        # Rodapé: idioma + latência
        self._footer_label = QLabel()
        self._footer_label.setStyleSheet(
            f"color: {_COLOR_FOOTER}; font-size: {_FONT_FOOTER}px;"
            " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
            " background: transparent;"
        )
        self._footer_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._footer_label)

    def _show_empty(self) -> None:
        self._text_label.setText("Nenhuma transcrição ainda")
        self._text_label.setStyleSheet(
            f"color: {_COLOR_EMPTY}; font-size: {_FONT_TEXT}px; font-style: italic;"
            " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
            " background: transparent;"
        )
        self._footer_label.setText("")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_transcription(self, text: str, metadata: dict[str, float | str]) -> None:
        """Atualiza o card com nova transcrição e metadados.

        Args:
            text: Texto transcrito.
            metadata: Dicionário com chaves opcionais:
                - latency_ms (float): latência em milissegundos.
                - language (str): idioma detectado/configurado.
                - duration_ms (float): duração do áudio em ms.
        """
        if not text:
            self._show_empty()
            return

        # Limita a exibição a _MAX_LINES linhas truncando por caracteres
        lines = text.splitlines()
        display_text = "\n".join(lines[:_MAX_LINES]) + "…" if len(lines) > _MAX_LINES else text

        self._last_text = text
        self._btn_copy.setVisible(True)
        self._text_label.setText(display_text)
        self._text_label.setStyleSheet(
            f"color: {_COLOR_TEXT}; font-size: {_FONT_TEXT}px;"
            " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
            " background: transparent;"
        )

        # Rodapé
        parts: list[str] = []
        language = metadata.get("language", "")
        if isinstance(language, str) and language and language != "auto":
            parts.append(language.upper())

        latency_ms = metadata.get("latency_ms")
        if isinstance(latency_ms, float):
            parts.append(f"{latency_ms:.0f} ms")

        duration_ms = metadata.get("duration_ms")
        if isinstance(duration_ms, float):
            parts.append(f"{duration_ms / 1000:.1f}s áudio")

        self._footer_label.setText("  ·  ".join(parts))

    def _on_copy(self) -> None:
        if self._last_text:
            pyperclip.copy(self._last_text)
