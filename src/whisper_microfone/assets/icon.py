"""Ícone da aplicação (janela principal / taskbar), desenhado em runtime.

Segue o mesmo padrão procedural usado em `ui/tray.py` — sem depender de
arquivo .ico/.png externo.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap

from whisper_microfone.ui.theme import AppTheme

_SIZES = (16, 24, 32, 48, 64, 128, 256)
_COLOR_BG = QColor(AppTheme.ACCENT)
_COLOR_FG = QColor("#FFFFFF")


def _draw_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.04
    bg_rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(_COLOR_BG))
    painter.drawRoundedRect(bg_rect, size * 0.22, size * 0.22)

    # Cápsula do microfone
    capsule_w = size * 0.26
    capsule_h = size * 0.42
    capsule_x = size / 2.0 - capsule_w / 2.0
    capsule_y = size * 0.20
    capsule_rect = QRectF(capsule_x, capsule_y, capsule_w, capsule_h)
    painter.setBrush(QBrush(_COLOR_FG))
    painter.drawRoundedRect(capsule_rect, capsule_w / 2.0, capsule_w / 2.0)

    # Suporte (arco) do microfone
    pen = QPen(_COLOR_FG)
    pen.setWidthF(size * 0.06)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    arc_rect = QRectF(
        size * 0.28,
        capsule_y + capsule_h * 0.35,
        size * 0.44,
        size * 0.40,
    )
    painter.drawArc(arc_rect, 200 * 16, 140 * 16)

    # Haste e base
    stem_top_y = arc_rect.center().y() + arc_rect.height() / 2.0
    stem_bottom_y = size * 0.82
    painter.drawLine(
        int(size / 2.0), int(stem_top_y), int(size / 2.0), int(stem_bottom_y)
    )
    base_half_w = size * 0.14
    painter.drawLine(
        int(size / 2.0 - base_half_w),
        int(stem_bottom_y),
        int(size / 2.0 + base_half_w),
        int(stem_bottom_y),
    )

    painter.end()
    return pixmap


def make_app_icon() -> QIcon:
    """Cria o ícone da aplicação em múltiplas resoluções (janela/taskbar)."""
    icon = QIcon()
    for size in _SIZES:
        icon.addPixmap(_draw_pixmap(size))
    return icon
