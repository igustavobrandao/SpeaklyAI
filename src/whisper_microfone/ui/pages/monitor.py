from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
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


# ---------------------------------------------------------------------------
# Helper
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


# ---------------------------------------------------------------------------
# LiveChart — QPainter puro, zero dependências externas
# ---------------------------------------------------------------------------

class LiveChart(QWidget):
    """Mini gráfico de linha para métricas em tempo real."""

    def __init__(
        self,
        max_points: int = 60,
        color: str = ACCENT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._max_points = max_points
        self._color = QColor(color)
        self._points: list[float] = []
        self.setMinimumHeight(48)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def add_point(self, value: float) -> None:
        self._points.append(value)
        if len(self._points) > self._max_points:
            self._points.pop(0)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        painter.fillRect(0, 0, w, h, QColor("#111318"))

        if len(self._points) < 2:
            painter.end()
            return

        max_val = max(self._points) if max(self._points) > 0 else 1.0
        n = len(self._points)
        step = w / (n - 1)

        pen = QPen(self._color, 2)
        painter.setPen(pen)

        prev_x = 0
        prev_y = h - int((self._points[0] / max_val) * h * 0.85)

        for i in range(1, n):
            x = int(i * step)
            y = h - int((self._points[i] / max_val) * h * 0.85)
            painter.drawLine(prev_x, prev_y, x, y)
            prev_x, prev_y = x, y

        painter.end()


# ---------------------------------------------------------------------------
# _StatItem
# ---------------------------------------------------------------------------

class _StatItem(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._value_lbl = QLabel("—")
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        self._value_lbl.setFont(font)
        self._value_lbl.setStyleSheet(f"color: {ACCENT}; background: transparent;")

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY}; background: transparent;"
        )

        layout.addWidget(self._value_lbl)
        layout.addWidget(self._label_lbl)

    def set_value(self, text: str) -> None:
        self._value_lbl.setText(text)


# ---------------------------------------------------------------------------
# _MetricRow
# ---------------------------------------------------------------------------

class _MetricRow(QWidget):
    def __init__(
        self,
        title: str,
        unit: str = "",
        color: str = ACCENT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._unit = unit

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(2)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"font-size: 12px; color: {TEXT_PRIMARY}; font-weight: 500;"
            " background: transparent;"
        )
        self._title_lbl.setFixedWidth(60)

        self._val_lbl = QLabel("—")
        self._val_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY}; background: transparent;"
        )

        left.addWidget(self._title_lbl)
        left.addWidget(self._val_lbl)

        self._chart = LiveChart(color=color)

        row.addLayout(left)
        row.addWidget(self._chart, stretch=1)

    def add_point(self, value: float) -> None:
        self._chart.add_point(value)
        self._val_lbl.setText(f"{value:.1f}{self._unit}")


# ---------------------------------------------------------------------------
# MonitorPage
# ---------------------------------------------------------------------------

class MonitorPage(QWidget):
    def __init__(self, engine: Engine, config: FullConfig) -> None:
        super().__init__()
        self._engine = engine
        self._config = config

        self._transcription_count: int = 0
        self._total_latency_ms: float = 0.0
        self._total_chars: int = 0
        self._total_duration_ms: float = 0.0

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

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

        self._build_stats_card()
        self._build_metrics_card()

        self._content.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _build_stats_card(self) -> None:
        card, layout = _make_card("Estatísticas da sessão")

        row = QHBoxLayout()
        row.setSpacing(0)

        specs: list[tuple[str, str]] = [
            ("Transcrições", "transcriptions"),
            ("Latência média", "avg_latency"),
            ("Chars ditados", "chars"),
            ("Tempo total", "total_time"),
        ]

        self._stat_items: dict[str, _StatItem] = {}
        for label, key in specs:
            item = _StatItem(label)
            self._stat_items[key] = item
            row.addWidget(item, stretch=1)

        layout.addLayout(row)
        self._content.addWidget(card)

    def _build_metrics_card(self) -> None:
        card, layout = _make_card("Histórico de métricas")

        self._metric_rows: dict[str, _MetricRow] = {
            "ram":  _MetricRow("RAM",  unit=" MB", color="#0071E3"),
            "vram": _MetricRow("VRAM", unit=" MB", color="#34C759"),
            "gpu":  _MetricRow("GPU",  unit="%",   color="#FF9F0A"),
            "cpu":  _MetricRow("CPU",  unit="%",   color="#FF3B30"),
        }

        for row_widget in self._metric_rows.values():
            layout.addWidget(row_widget)

        self._content.addWidget(card)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._engine.metrics_updated.connect(self.update_metrics)
        self._engine.transcribed.connect(self._on_transcribed)

    def _on_transcribed(self, text: str, meta: dict) -> None:
        self._transcription_count += 1
        self._total_latency_ms += meta.get("latency_ms", 0.0)
        self._total_chars += len(text)
        self._total_duration_ms += meta.get("duration_ms", 0.0)

        avg_lat = (
            self._total_latency_ms / self._transcription_count
            if self._transcription_count > 0
            else 0.0
        )
        self.update_stats(
            transcriptions=self._transcription_count,
            avg_latency_ms=avg_lat,
            chars=self._total_chars,
            total_ms=self._total_duration_ms,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_stats(
        self,
        transcriptions: int,
        avg_latency_ms: float,
        chars: int,
        total_ms: float,
    ) -> None:
        self._stat_items["transcriptions"].set_value(str(transcriptions))
        self._stat_items["avg_latency"].set_value(f"{avg_latency_ms:.0f} ms")
        self._stat_items["chars"].set_value(str(chars))

        total_s = total_ms / 1000
        if total_s >= 60:
            label = f"{int(total_s // 60)}m {int(total_s % 60)}s"
        else:
            label = f"{total_s:.1f}s"
        self._stat_items["total_time"].set_value(label)

    def update_metrics(self, metrics) -> None:
        self._metric_rows["ram"].add_point(metrics.ram_mb)
        self._metric_rows["vram"].add_point(metrics.vram_mb)
        self._metric_rows["gpu"].add_point(metrics.gpu_percent)
        self._metric_rows["cpu"].add_point(metrics.cpu_percent)
