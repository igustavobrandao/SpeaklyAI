from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.engine import Engine
from whisper_microfone.version import VERSION

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
BG_PAGE        = "#111318"
BG_CARD        = "#181a20"
BORDER         = "rgba(255,255,255,0.08)"
TEXT_PRIMARY   = "rgba(255,255,255,0.90)"
TEXT_SECONDARY = "rgba(255,255,255,0.48)"
ACCENT         = "#0071E3"

APP_VERSION    = f"v{VERSION} Alpha"
APP_NAME       = "Whisper Microfone"
APP_SUBTITLE   = "Ditado por voz via Groq Whisper API"
REPO_URL       = "https://github.com/Gustavo1341/whisper-microphone"
REPO_LABEL     = "github.com/Gustavo1341/whisper-microphone"
LICENSE_LINE   = "MIT License · Gustavo Brandão · 2026"


def _make_card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet(f"""
        QFrame#card {{
            background: {BG_CARD};
            border-radius: 12px;
            border: 1px solid {BORDER};
        }}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)
    if title:
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY}; letter-spacing: 0.5px;"
            " background: transparent;"
        )
        layout.addWidget(lbl)
    return card, layout


def _grid_row(grid: QGridLayout, row: int, label: str, value: str) -> None:
    lbl = QLabel(label)
    lbl.setStyleSheet(
        f"font-size: 13px; color: {TEXT_SECONDARY}; background: transparent;"
    )

    val = QLabel(value)
    val.setStyleSheet(
        f"font-size: 13px; color: {TEXT_PRIMARY}; font-weight: 500;"
        " background: transparent;"
    )
    val.setTextInteractionFlags(Qt.TextSelectableByMouse)

    grid.addWidget(lbl, row, 0, Qt.AlignLeft)
    grid.addWidget(val, row, 1, Qt.AlignLeft)


class AboutPage(QWidget):
    def __init__(self, engine: Engine, config: FullConfig) -> None:
        super().__init__()
        self._engine = engine
        self._config = config
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background: {BG_PAGE};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 48, 48, 48)
        outer.setSpacing(24)
        outer.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self._build_hero(outer)
        self._build_info_card(outer)
        self._build_footer(outer)

    def _build_hero(self, parent_layout: QVBoxLayout) -> None:
        hero = QVBoxLayout()
        hero.setSpacing(6)
        hero.setAlignment(Qt.AlignHCenter)

        icon_lbl = QLabel("🎙")
        icon_font = QFont()
        icon_font.setPointSize(36)
        icon_lbl.setFont(icon_font)
        icon_lbl.setAlignment(Qt.AlignHCenter)
        icon_lbl.setStyleSheet("background: transparent;")

        title_lbl = QLabel(APP_NAME)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; background: transparent;"
        )
        title_lbl.setAlignment(Qt.AlignHCenter)

        version_lbl = QLabel(APP_VERSION)
        version_lbl.setStyleSheet(
            f"font-size: 14px; color: {TEXT_SECONDARY}; background: transparent;"
        )
        version_lbl.setAlignment(Qt.AlignHCenter)

        subtitle_lbl = QLabel(APP_SUBTITLE)
        subtitle_lbl.setStyleSheet(
            f"font-size: 14px; color: {TEXT_SECONDARY}; background: transparent;"
        )
        subtitle_lbl.setAlignment(Qt.AlignHCenter)

        hero.addWidget(icon_lbl)
        hero.addWidget(title_lbl)
        hero.addWidget(version_lbl)
        hero.addWidget(subtitle_lbl)

        parent_layout.addLayout(hero)

    def _build_info_card(self, parent_layout: QVBoxLayout) -> None:
        card, layout = _make_card("Informações")

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(0, 140)
        grid.setColumnStretch(1, 1)

        _grid_row(grid, 0, "Modelo", self._config.model.groq_model)
        _grid_row(grid, 1, "Idioma", self._config.model.language)
        _grid_row(grid, 2, "Processamento", "API Groq (nuvem)")
        _grid_row(grid, 3, "Licença", "MIT License")

        layout.addLayout(grid)

        wrapper = QHBoxLayout()
        wrapper.addStretch()
        wrapper.addWidget(card)
        wrapper.addStretch()
        card.setMinimumWidth(420)
        card.setMaximumWidth(600)

        parent_layout.addLayout(wrapper)

    def _build_footer(self, parent_layout: QVBoxLayout) -> None:
        footer = QVBoxLayout()
        footer.setSpacing(4)
        footer.setAlignment(Qt.AlignHCenter)

        license_lbl = QLabel(LICENSE_LINE)
        license_lbl.setStyleSheet(
            f"font-size: 12px; color: {TEXT_SECONDARY}; background: transparent;"
        )
        license_lbl.setAlignment(Qt.AlignHCenter)

        repo_lbl = QLabel(
            f'<a href="{REPO_URL}" style="color: {ACCENT}; text-decoration: none;">'
            f"{REPO_LABEL}</a>"
        )
        repo_lbl.setTextFormat(Qt.RichText)
        repo_lbl.setOpenExternalLinks(False)
        repo_lbl.setCursor(Qt.PointingHandCursor)
        repo_lbl.setAlignment(Qt.AlignHCenter)
        repo_lbl.setStyleSheet("background: transparent;")
        repo_lbl.linkActivated.connect(
            lambda _: QDesktopServices.openUrl(QUrl(REPO_URL))
        )

        footer.addWidget(license_lbl)
        footer.addWidget(repo_lbl)

        parent_layout.addLayout(footer)
