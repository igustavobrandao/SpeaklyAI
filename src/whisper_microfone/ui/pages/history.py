from __future__ import annotations

import csv
from contextlib import suppress
from datetime import datetime
from pathlib import Path

import pyperclip
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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
RECORDING      = "#FF3B30"
BORDER         = "rgba(255,255,255,0.08)"

_COLUMNS = ["Hora", "Idioma", "Texto", "Duração", "Latência", ""]
_COL_TIMESTAMP = 0
_COL_LANGUAGE  = 1
_COL_TEXT      = 2
_COL_DURATION  = 3
_COL_LATENCY   = 4
_COL_COPY      = 5


# ---------------------------------------------------------------------------
# HistoryPage
# ---------------------------------------------------------------------------

class HistoryPage(QWidget):
    def __init__(self, engine: Engine, config: FullConfig) -> None:
        super().__init__()
        self._engine = engine
        self._config = config
        self._all_entries: list[dict] = []

        self._build_ui()
        self._connect_signals()
        self._load()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)
        self.setStyleSheet("background: #111318;")

        # --- Barra superior: busca + botões ---
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar transcrições...")
        self._search.setFixedHeight(36)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                color: {TEXT_PRIMARY};
                background: #181a20;
            }}
        """)
        self._search.textChanged.connect(self._on_search)

        self._btn_clear = QPushButton("Limpar histórico")
        self._btn_clear.setFixedHeight(36)
        self._btn_clear.setCursor(Qt.PointingHandCursor)
        self._btn_clear.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                font-size: 13px;
                color: {RECORDING};
                padding: 0 12px;
            }}
            QPushButton:hover {{ color: #CC2E26; }}
        """)
        self._btn_clear.clicked.connect(self._on_clear)

        self._btn_export = QPushButton("Exportar CSV")
        self._btn_export.setFixedHeight(36)
        self._btn_export.setCursor(Qt.PointingHandCursor)
        self._btn_export.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                font-size: 13px;
                color: {ACCENT};
                padding: 0 12px;
            }}
            QPushButton:hover {{ color: #0077ED; }}
        """)
        self._btn_export.clicked.connect(self._on_export)

        top_row.addWidget(self._search, stretch=1)
        top_row.addWidget(self._btn_export)
        top_row.addWidget(self._btn_clear)

        outer.addLayout(top_row)

        # --- Tabela ---
        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.verticalHeader().setVisible(False)
        self._table.setFrameShape(QFrame.NoFrame)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: #181a20;
                border-radius: 12px;
                border: 1px solid {BORDER};
                font-size: 13px;
                color: {TEXT_PRIMARY};
                alternate-background-color: #1c1e25;
                gridline-color: transparent;
            }}
            QHeaderView::section {{
                background: #181a20;
                color: {TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 500;
                letter-spacing: 0.3px;
                border: none;
                border-bottom: 1px solid {BORDER};
                padding: 6px 12px;
            }}
            QTableWidget::item {{
                padding: 6px 12px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background: rgba(0,113,227,0.25);
                color: rgba(255,255,255,0.90);
            }}
        """)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_TIMESTAMP, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_COL_LANGUAGE,  QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_COL_TEXT,      QHeaderView.Stretch)
        header.setSectionResizeMode(_COL_DURATION,  QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_COL_LATENCY,   QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_COL_COPY,      QHeaderView.Fixed)
        self._table.setColumnWidth(_COL_COPY, 72)

        self._table.setRowHeight(0, 40)
        self._table.verticalHeader().setDefaultSectionSize(36)

        outer.addWidget(self._table, stretch=1)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._engine.transcribed.connect(self._on_new_transcription)

    def _on_new_transcription(self, text: str, meta: dict) -> None:
        self._load()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            entries = self._engine._history.list(limit=500)
        except Exception:
            entries = []
        self._all_entries = entries
        self.load_entries(entries)

    def load_entries(self, entries: list[dict]) -> None:
        self._table.setRowCount(0)
        for entry in entries:
            self._append_row(entry)

    def _append_row(self, entry: dict) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Hora — formata ISO → HH:MM:SS local
        ts_raw = entry.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts_raw)
            ts_display = dt.astimezone().strftime("%H:%M:%S")
        except Exception:
            ts_display = ts_raw

        duration_s = entry.get("duration_ms", 0) / 1000
        latency_ms = entry.get("latency_ms", 0)

        cells = [
            ts_display,
            entry.get("language", ""),
            entry.get("text", ""),
            f"{duration_s:.1f}s",
            f"{latency_ms:.0f} ms",
        ]

        for col, value in enumerate(cells):
            item = QTableWidgetItem(value)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self._table.setItem(row, col, item)

        # Botão copiar
        text_to_copy = entry.get("text", "")
        btn = QPushButton("Copiar")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(26)
        btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {BORDER};
                border-radius: 6px;
                background: #1c1e25;
                font-size: 11px;
                color: {TEXT_SECONDARY};
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: rgba(0,113,227,0.15);
                color: {ACCENT};
                border-color: {ACCENT};
            }}
            QPushButton:pressed {{
                background: rgba(0,113,227,0.25);
            }}
        """)
        btn.clicked.connect(lambda _checked, t=text_to_copy: pyperclip.copy(t))
        self._table.setCellWidget(row, _COL_COPY, btn)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self.load_entries(self._all_entries)
            return

        filtered = [
            e for e in self._all_entries
            if q in e.get("text", "").lower()
        ]
        self.load_entries(filtered)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_clear(self) -> None:
        with suppress(Exception):
            self._engine._history.clear()
        self._all_entries = []
        self._table.setRowCount(0)

    def _on_export(self) -> None:
        downloads = Path.home() / "Downloads"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = downloads / f"whisper_historico_{timestamp}.csv"

        try:
            with open(dest, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Hora", "Idioma", "Texto", "Duração (ms)", "Latência (ms)"])
                for entry in self._all_entries:
                    writer.writerow([
                        entry.get("timestamp", ""),
                        entry.get("language", ""),
                        entry.get("text", ""),
                        entry.get("duration_ms", ""),
                        entry.get("latency_ms", ""),
                    ])
        except Exception:
            pass
