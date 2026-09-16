"""System tray icon e menu para o Whisper Microfone.

Design minimalista Apple-style com ícones gerados programaticamente via QPainter.
Animação de recording via QTimer não-bloqueante.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMainWindow, QMenu, QSystemTrayIcon

from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.engine import Engine

# ---------------------------------------------------------------------------
# Constantes de cor (Apple Human Interface Guidelines)
# ---------------------------------------------------------------------------
_COLOR_IDLE = QColor("#34C759")
_COLOR_RECORDING = QColor("#FF3B30")
_COLOR_TRANSCRIBING = QColor("#FF9500")
_COLOR_PAUSED = QColor("#8E8E93")
_COLOR_ERROR = QColor("#FF3B30")
_COLOR_TRANSPARENT = QColor(0, 0, 0, 0)

_ICON_SIZE = 32
_ANIMATION_INTERVAL_MS = 100

_TOOLTIPS: dict[str, str] = {
    "idle": "Pronto",
    "recording": "Ouvindo...",
    "transcribing": "Processando...",
    "paused": "Pausado",
    "error": "Erro",
}

_ANIMATED_STATES = frozenset({"recording"})

_MENU_STYLESHEET = """
QMenu {
    background: #181a20;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 4px;
    color: rgba(255,255,255,0.90);
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
    color: rgba(255,255,255,0.90);
    font-size: 13px;
    font-family: "Segoe UI", sans-serif;
}
QMenu::item:selected {
    background: rgba(255,255,255,0.08);
}
QMenu::item:disabled {
    color: rgba(255,255,255,0.35);
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.08);
    margin: 4px 0;
}
"""


# ---------------------------------------------------------------------------
# Geração programática de ícones
# ---------------------------------------------------------------------------

def _make_icon(state: str, angle: int = 0) -> QIcon:
    size = _ICON_SIZE
    pixmap = QPixmap(size, size)
    pixmap.fill(_COLOR_TRANSPARENT)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = 1.5
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    center_x = size / 2.0
    center_y = size / 2.0
    radius = (size / 2.0) - margin

    if state == "idle":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_COLOR_IDLE))
        painter.drawEllipse(rect)

    elif state == "recording":
        pulse_ratio = 0.70 + 0.30 * ((math.sin(math.radians(angle)) + 1.0) / 2.0)
        r = radius * pulse_ratio
        pulse_rect = QRectF(center_x - r, center_y - r, 2 * r, 2 * r)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_COLOR_RECORDING))
        painter.drawEllipse(pulse_rect)

    elif state == "transcribing":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_COLOR_TRANSCRIBING))
        painter.drawEllipse(rect)

    elif state == "paused":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_COLOR_PAUSED))
        painter.drawEllipse(rect)

        bar_color = QColor("#FFFFFF")
        painter.setBrush(QBrush(bar_color))
        bar_h = size * 0.40
        bar_w = size * 0.12
        bar_y = center_y - bar_h / 2
        gap = size * 0.08
        left_x = center_x - gap / 2 - bar_w
        right_x = center_x + gap / 2
        painter.drawRoundedRect(QRectF(left_x, bar_y, bar_w, bar_h), 1.0, 1.0)
        painter.drawRoundedRect(QRectF(right_x, bar_y, bar_w, bar_h), 1.0, 1.0)

    elif state == "error":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_COLOR_ERROR))
        painter.drawEllipse(rect)

        pen = QPen(QColor("#FFFFFF"))
        pen.setWidthF(2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        cross_margin = size * 0.28
        cross_rect = QRectF(cross_margin, cross_margin, size - 2 * cross_margin, size - 2 * cross_margin)
        painter.drawLine(cross_rect.topLeft(), cross_rect.bottomRight())
        painter.drawLine(cross_rect.topRight(), cross_rect.bottomLeft())

    painter.end()
    return QIcon(pixmap)


# ---------------------------------------------------------------------------
# SystemTray
# ---------------------------------------------------------------------------

class SystemTray(QSystemTrayIcon):
    def __init__(
        self,
        engine: Engine,
        main_window: QMainWindow,
        config: FullConfig,  # noqa: ARG002
    ) -> None:
        super().__init__()

        self._engine = engine
        self._main_window = main_window
        self._current_state = "idle"
        self._angle = 0

        self.setIcon(_make_icon("idle"))
        self.setToolTip(_TOOLTIPS["idle"])

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(_ANIMATION_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._tick_animation)

        self._build_menu()

        engine.state_changed.connect(self.update_state)
        engine.error_occurred.connect(lambda msg: self.show_notification("Erro", msg))

        self.activated.connect(self._on_activated)
        self.setVisible(True)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet(_MENU_STYLESHEET)

        action_show = QAction("Mostrar janela", menu)
        action_show.triggered.connect(self._show_window)
        menu.addAction(action_show)

        menu.addSeparator()

        self._action_pause = QAction("Pausado", menu)
        self._action_pause.setCheckable(True)
        self._action_pause.setChecked(False)
        self._action_pause.triggered.connect(self._toggle_pause)
        menu.addAction(self._action_pause)

        menu.addSeparator()

        action_quit = QAction("Sair", menu)
        action_quit.triggered.connect(self._quit)
        menu.addAction(action_quit)

        self.setContextMenu(menu)

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def update_state(self, state: str) -> None:
        self._current_state = state
        self.setToolTip(_TOOLTIPS.get(state, state))

        if state in _ANIMATED_STATES:
            if not self._anim_timer.isActive():
                self._angle = 0
                self._anim_timer.start()
        else:
            if self._anim_timer.isActive():
                self._anim_timer.stop()
            self.setIcon(_make_icon(state))

        self._action_pause.setChecked(state == "paused")

    def show_notification(self, title: str, message: str) -> None:
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _tick_animation(self) -> None:
        self._angle = (self._angle + 36) % 360
        self.setIcon(_make_icon(self._current_state, self._angle))

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self) -> None:
        self._main_window.show()
        self._main_window.raise_()
        self._main_window.activateWindow()

    def _toggle_pause(self, checked: bool) -> None:
        if checked:
            self._engine.pause()
        else:
            self._engine.resume()

    def _quit(self) -> None:
        from PySide6.QtWidgets import QApplication
        self._engine.stop()
        QApplication.quit()
