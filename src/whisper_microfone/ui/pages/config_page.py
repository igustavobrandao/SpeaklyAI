from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.engine import Engine

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
BG_PRIMARY     = "#181a20"
BG_SECONDARY   = "#111318"
TEXT_PRIMARY   = "rgba(255,255,255,0.90)"
TEXT_SECONDARY = "rgba(255,255,255,0.48)"
ACCENT         = "#0071E3"
BORDER         = "rgba(255,255,255,0.08)"

_GROQ_MODEL_LABELS = [
    "whisper-large-v3-turbo ★ recomendado",
    "whisper-large-v3",
    "distil-whisper-large-v3-en",
]
_GROQ_MODEL_VALUES = [
    "whisper-large-v3-turbo",
    "whisper-large-v3",
    "distil-whisper-large-v3-en",
]

_STRATEGY_LABELS = ["Digitar → Colar", "Só colar", "Só digitar"]
_STRATEGY_VALUES = ["type_then_paste", "paste_only", "type_only"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet("""
        QFrame#card {
            background: #181a20;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.08);
        }
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


def _field_row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    lbl = QLabel(label)
    lbl.setStyleSheet(
        f"font-size: 13px; color: {TEXT_PRIMARY}; background: transparent;"
    )
    lbl.setMinimumWidth(240)
    row.addWidget(lbl)
    row.addWidget(widget)
    row.addStretch()
    return row


def _styled_combo(items: list[str]) -> QComboBox:
    cb = QComboBox()
    cb.addItems(items)
    cb.setMinimumWidth(220)
    cb.setStyleSheet(f"""
        QComboBox {{
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 13px;
            color: {TEXT_PRIMARY};
            background: #1c1e25;
        }}
        QComboBox::drop-down {{ border: none; width: 20px; }}
        QComboBox QAbstractItemView {{
            background: #1c1e25;
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            selection-background-color: #0071E3;
            selection-color: #FFFFFF;
        }}
    """)
    return cb


def _styled_spin(min_val: int, max_val: int, step: int = 1) -> QSpinBox:
    sp = QSpinBox()
    sp.setRange(min_val, max_val)
    sp.setSingleStep(step)
    sp.setMinimumWidth(100)
    sp.setStyleSheet(f"""
        QSpinBox {{
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 13px;
            color: {TEXT_PRIMARY};
            background: #1c1e25;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{ width: 16px; border: none; }}
    """)
    return sp


def _styled_check(label: str) -> QCheckBox:
    cb = QCheckBox(label)
    cb.setStyleSheet(
        f"font-size: 13px; color: {TEXT_PRIMARY}; background: transparent;"
    )
    return cb


# ---------------------------------------------------------------------------
# ConfigPage
# ---------------------------------------------------------------------------

class ConfigPage(QWidget):
    def __init__(self, engine: Engine, config: FullConfig) -> None:
        super().__init__()
        self._engine = engine
        self._config = config

        self._build_ui()
        self._populate(config)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: #111318; border: none;")

        container = QWidget()
        container.setStyleSheet("background: #111318;")
        self._content = QVBoxLayout(container)
        self._content.setContentsMargins(32, 32, 32, 32)
        self._content.setSpacing(16)
        self._content.setAlignment(Qt.AlignTop)

        self._build_model_card()
        self._build_audio_card()
        self._build_injection_card()
        self._build_apply_row()

        self._content.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _build_model_card(self) -> None:
        card, layout = _make_card("Modelo Groq")

        self._cb_model = _styled_combo(_GROQ_MODEL_LABELS)
        self._cb_language = _styled_combo(["auto", "pt", "en", "es", "fr", "de"])

        layout.addLayout(_field_row("Modelo", self._cb_model))
        layout.addLayout(_field_row("Idioma de transcrição", self._cb_language))

        self._content.addWidget(card)

    def _build_audio_card(self) -> None:
        card, layout = _make_card("Áudio")

        self._spin_min_dur = _styled_spin(100, 5000, 50)
        self._spin_min_dur.setSuffix(" ms")
        self._spin_max_dur = _styled_spin(5, 300, 5)
        self._spin_max_dur.setSuffix(" s")

        layout.addLayout(_field_row("Duração mínima", self._spin_min_dur))
        layout.addLayout(_field_row("Duração máxima", self._spin_max_dur))

        self._content.addWidget(card)

    def _build_injection_card(self) -> None:
        card, layout = _make_card("Injeção de texto")

        self._cb_strategy = _styled_combo(_STRATEGY_LABELS)
        self._chk_capitalize = _styled_check("Capitalizar primeira letra")
        self._chk_trailing = _styled_check("Adicionar espaço ao final")

        layout.addLayout(_field_row("Estratégia", self._cb_strategy))
        layout.addWidget(self._chk_capitalize)
        layout.addWidget(self._chk_trailing)

        self._content.addWidget(card)

    def _build_apply_row(self) -> None:
        row = QHBoxLayout()
        row.addStretch()

        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setStyleSheet(f"font-size: 13px; color: {ACCENT};")
        row.addWidget(self._feedback_lbl)

        self._btn_apply = QPushButton("Aplicar")
        self._btn_apply.setFixedHeight(36)
        self._btn_apply.setMinimumWidth(100)
        self._btn_apply.setCursor(Qt.PointingHandCursor)
        self._btn_apply.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background: #0077ED; }}
            QPushButton:pressed {{ background: #006CD1; }}
        """)
        self._btn_apply.clicked.connect(self._on_apply)
        row.addWidget(self._btn_apply)

        self._content.addLayout(row)

    def _populate(self, config: FullConfig) -> None:
        model_idx = (
            _GROQ_MODEL_VALUES.index(config.model.groq_model)
            if config.model.groq_model in _GROQ_MODEL_VALUES
            else 0
        )
        self._cb_model.setCurrentIndex(model_idx)

        lang_map = {"auto": 0, "pt": 1, "en": 2, "es": 3, "fr": 4, "de": 5}
        self._cb_language.setCurrentIndex(lang_map.get(config.model.language, 0))

        self._spin_min_dur.setValue(config.audio.min_duration_ms)
        self._spin_max_dur.setValue(config.audio.max_duration_seconds)

        strategy_idx = (
            _STRATEGY_VALUES.index(config.injection.strategy)
            if config.injection.strategy in _STRATEGY_VALUES
            else 0
        )
        self._cb_strategy.setCurrentIndex(strategy_idx)
        self._chk_capitalize.setChecked(config.injection.capitalize_first)
        self._chk_trailing.setChecked(config.injection.add_trailing_space)

    def _on_apply(self) -> None:
        lang_values = ["auto", "pt", "en", "es", "fr", "de"]

        new_cfg = self._config.model_copy(deep=True)

        new_cfg.model.groq_model = _GROQ_MODEL_VALUES[self._cb_model.currentIndex()]
        new_cfg.model.language = lang_values[self._cb_language.currentIndex()]

        new_cfg.audio.min_duration_ms = self._spin_min_dur.value()
        new_cfg.audio.max_duration_seconds = self._spin_max_dur.value()

        new_cfg.injection.strategy = _STRATEGY_VALUES[self._cb_strategy.currentIndex()]  # type: ignore[assignment]
        new_cfg.injection.capitalize_first = self._chk_capitalize.isChecked()
        new_cfg.injection.add_trailing_space = self._chk_trailing.isChecked()

        self._config = new_cfg
        self._engine.update_config(new_cfg)

        self._show_feedback("Configuração aplicada")

    def _show_feedback(self, message: str) -> None:
        self._feedback_lbl.setText(message)
        QTimer.singleShot(2000, lambda: self._feedback_lbl.setText(""))
