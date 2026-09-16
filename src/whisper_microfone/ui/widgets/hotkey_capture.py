from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_COLOR_BG = "#181a20"
_COLOR_BADGE_BG = "#1c1e25"
_COLOR_BADGE_TEXT = "rgba(255,255,255,0.90)"
_COLOR_BADGE_BORDER = "rgba(255,255,255,0.10)"
_COLOR_CAPTURE_TEXT = "rgba(255,255,255,0.48)"
_COLOR_BTN_TEXT = "#0071E3"

_FONT_BADGE = 12
_FONT_BTN = 12

# Mapeamento de Qt.Key para string canônica do formato "ctrl+alt+space"
_MODIFIER_KEYS = {
    Qt.Key.Key_Control,
    Qt.Key.Key_Shift,
    Qt.Key.Key_Alt,
    Qt.Key.Key_Meta,
}

_KEY_NAME_MAP: dict[Qt.Key, str] = {
    Qt.Key.Key_Space: "space",
    Qt.Key.Key_Return: "enter",
    Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Tab: "tab",
    Qt.Key.Key_Escape: "esc",
    Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Insert: "insert",
    Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "pageup",
    Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down",
    Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
    Qt.Key.Key_F1: "f1",
    Qt.Key.Key_F2: "f2",
    Qt.Key.Key_F3: "f3",
    Qt.Key.Key_F4: "f4",
    Qt.Key.Key_F5: "f5",
    Qt.Key.Key_F6: "f6",
    Qt.Key.Key_F7: "f7",
    Qt.Key.Key_F8: "f8",
    Qt.Key.Key_F9: "f9",
    Qt.Key.Key_F10: "f10",
    Qt.Key.Key_F11: "f11",
    Qt.Key.Key_F12: "f12",
}


def _parse_combination(combo: str) -> list[str]:
    """Divide "ctrl+alt+space" em ["Ctrl", "Alt", "Space"]."""
    if not combo:
        return []
    parts = [p.strip() for p in combo.lower().split("+") if p.strip()]
    return [p.capitalize() for p in parts]


def _build_combination(modifiers: Qt.KeyboardModifier, key: Qt.Key) -> str:
    """Constrói a string canônica a partir de modificadores e tecla."""
    parts: list[str] = []
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        parts.append("ctrl")
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        parts.append("shift")
    if modifiers & Qt.KeyboardModifier.AltModifier:
        parts.append("alt")
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        parts.append("meta")

    key_name = _KEY_NAME_MAP.get(key)
    if key_name is None:
        text = chr(key.value).lower() if 32 <= key.value <= 126 else None
        key_name = text or f"key{key.value}"

    parts.append(key_name)
    return "+".join(parts)


class _Badge(QFrame):
    """Etiqueta visual representando uma tecla individual."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("KeyBadge")
        self.setStyleSheet(
            f"""
            QFrame#KeyBadge {{
                background-color: {_COLOR_BADGE_BG};
                border: 1px solid {_COLOR_BADGE_BORDER};
                border-radius: 4px;
                padding: 2px 6px;
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(0)

        label = QLabel(text)
        label.setStyleSheet(
            f"color: {_COLOR_BADGE_TEXT}; font-size: {_FONT_BADGE}px; font-weight: 500;"
            " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
            " background: transparent; border: none;"
        )
        layout.addWidget(label)


class HotkeyCapture(QWidget):
    """Campo interativo para capturar uma combinação de teclas.

    Emite combination_changed(str) com o novo combo no formato "ctrl+alt+space"
    sempre que o usuário confirma uma nova combinação.
    """

    combination_changed = Signal(str)

    def __init__(
        self,
        initial_combination: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._combination: str = initial_combination
        self._capturing: bool = False
        self._build_ui()
        self._refresh_display()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Área de badges / mensagem de captura
        self._badges_area = QHBoxLayout()
        self._badges_area.setContentsMargins(0, 0, 0, 0)
        self._badges_area.setSpacing(4)
        layout.addLayout(self._badges_area, 1)

        # Botão de alteração
        self._btn = QPushButton("Alterar")
        self._btn.setStyleSheet(
            f"color: {_COLOR_BTN_TEXT}; font-size: {_FONT_BTN}px; font-weight: 500;"
            " background: transparent; border: none; padding: 0;"
            " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
        )
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn.clicked.connect(self._enter_capture_mode)
        layout.addWidget(self._btn)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _clear_badges_area(self) -> None:
        while self._badges_area.count():
            item = self._badges_area.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_display(self) -> None:
        self._clear_badges_area()
        if self._capturing:
            label = QLabel("Pressione a combinação...")
            label.setStyleSheet(
                f"color: {_COLOR_CAPTURE_TEXT}; font-size: {_FONT_BADGE}px; font-style: italic;"
                " font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;"
                " background: transparent;"
            )
            self._badges_area.addWidget(label)
            self._badges_area.addStretch()
            self._btn.setText("Cancelar")
        else:
            parts = _parse_combination(self._combination)
            if parts:
                for part in parts:
                    self._badges_area.addWidget(_Badge(part))
            else:
                label = QLabel("Nenhum atalho definido")
                label.setStyleSheet(
                    f"color: {_COLOR_CAPTURE_TEXT}; font-size: {_FONT_BADGE}px;"
                    " background: transparent;"
                )
                self._badges_area.addWidget(label)
            self._badges_area.addStretch()
            self._btn.setText("Alterar")

    def _enter_capture_mode(self) -> None:
        if self._capturing:
            self._exit_capture_mode()
            return
        self._capturing = True
        self._refresh_display()
        self.setFocus()

    def _exit_capture_mode(self) -> None:
        self._capturing = False
        self._refresh_display()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_combination(self, combo: str) -> None:
        """Atualiza a combinação exibida sem emitir o sinal."""
        self._combination = combo
        self._capturing = False
        self._refresh_display()

    # ------------------------------------------------------------------
    # Captura de teclas
    # ------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._capturing:
            super().keyPressEvent(event)
            return

        key = Qt.Key(event.key())

        # Ignorar pressionamento de teclas modificadoras sozinhas
        if key in _MODIFIER_KEYS:
            return

        # Escape cancela a captura sem alterar a combinação
        if key == Qt.Key.Key_Escape:
            self._exit_capture_mode()
            return

        modifiers = event.modifiers()
        new_combo = _build_combination(modifiers, key)
        self._combination = new_combo
        self._capturing = False
        self._refresh_display()
        self.combination_changed.emit(new_combo)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        if self._capturing:
            self._exit_capture_mode()
        super().focusOutEvent(event)
