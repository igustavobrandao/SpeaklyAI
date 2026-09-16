from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_COLOR_LINE_DEFAULT = "#0071E3"
_MIN_HEIGHT = 60


class LiveChart(QWidget):
    """Gráfico de linha desenhado com QPainter puro (sem pyqtgraph).

    Mantém um buffer circular de N pontos. Cada chamada a add_point()
    adiciona um sample; paintEvent reconstrói a polilinha a cada frame.
    """

    def __init__(
        self,
        buffer_size: int = 120,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._buffer: deque[float] = deque(maxlen=buffer_size)
        self._min_val: float = 0.0
        self._max_val: float = 100.0
        self._line_color: QColor = QColor(_COLOR_LINE_DEFAULT)

        self.setMinimumHeight(_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Fundo transparente — o card pai fornece a superfície branca
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_point(self, value: float) -> None:
        """Adiciona um ponto ao buffer circular e agenda redesenho."""
        self._buffer.append(value)
        self.update()

    def set_range(self, min_val: float, max_val: float) -> None:
        """Define o intervalo Y para normalização."""
        self._min_val = min_val
        self._max_val = max_val if max_val != min_val else min_val + 1.0
        self.update()

    def set_color(self, hex_color: str) -> None:
        """Define a cor da linha."""
        self._line_color = QColor(hex_color)
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:
        if len(self._buffer) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        points = list(self._buffer)
        n = len(points)

        val_range = self._max_val - self._min_val

        def _to_x(index: int) -> float:
            return index / (n - 1) * w

        def _to_y(value: float) -> float:
            normalized = (value - self._min_val) / val_range
            # Y cresce para baixo; invertemos para que maior valor = mais alto
            return h - normalized * h

        pen = QPen(self._line_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        for i in range(1, n):
            x0 = _to_x(i - 1)
            y0 = _to_y(points[i - 1])
            x1 = _to_x(i)
            y1 = _to_y(points[i])
            painter.drawLine(int(x0), int(y0), int(x1), int(y1))

        painter.end()
