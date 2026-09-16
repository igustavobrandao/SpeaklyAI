from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_COLOR_LABEL = "rgba(255,255,255,0.48)"
_COLOR_VALUE = "rgba(255,255,255,0.90)"
_COLOR_TRACK = "#2a2d35"  # equivalente dark de rgba(255,255,255,0.08) sobre #111318
_COLOR_FILL_DEFAULT = "#0071E3"
_FONT_LABEL = 11
_FONT_VALUE = 13
_BAR_HEIGHT = 4
_BAR_RADIUS = 2


class _ProgressTrack(QWidget):
    """Barra de progresso custom desenhada com QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ratio: float = 0.0
        self._fill_color: QColor = QColor(_COLOR_FILL_DEFAULT)
        self.setFixedHeight(_BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_ratio(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def set_color(self, hex_color: str) -> None:
        self._fill_color = QColor(hex_color)
        self.update()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = _BAR_RADIUS

        # Track
        track_path = QPainterPath()
        track_path.addRoundedRect(0, 0, w, h, r, r)
        painter.fillPath(track_path, QColor(_COLOR_TRACK))

        # Fill
        fill_w = max(0, int(w * self._ratio))
        if fill_w > 0:
            fill_path = QPainterPath()
            fill_path.addRoundedRect(0, 0, fill_w, h, r, r)
            painter.fillPath(fill_path, self._fill_color)

        painter.end()


class MetricBar(QWidget):
    """Widget horizontal: label | barra de progresso | valor."""

    def __init__(
        self,
        name: str,
        color: str = _COLOR_FILL_DEFAULT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._name_label = QLabel(name)
        self._name_label.setFixedWidth(40)
        self._name_label.setStyleSheet(
            f"color: {_COLOR_LABEL}; font-size: {_FONT_LABEL}px;"
        )
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._track = _ProgressTrack()
        self._track.set_color(color)

        self._value_label = QLabel("—")
        self._value_label.setFixedWidth(72)
        self._value_label.setStyleSheet(
            f"color: {_COLOR_VALUE}; font-size: {_FONT_VALUE}px; font-weight: 600;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self._name_label)
        layout.addWidget(self._track)
        layout.addWidget(self._value_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_value(self, current: float, total: float, label: str) -> None:
        """Atualiza a barra e o texto de valor.

        Args:
            current: Valor atual (ex: 612.0 para RAM em MB).
            total: Valor máximo para normalizar a barra (ex: 16384.0).
            label: String já formatada exibida à direita (ex: "612 MB").
        """
        ratio = current / total if total > 0 else 0.0
        self._track.set_ratio(ratio)
        self._value_label.setText(label)

    def set_color(self, hex_color: str) -> None:
        """Muda a cor do fill da barra."""
        self._track.set_color(hex_color)
