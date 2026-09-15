"""Mini janela flutuante de microfone — estilo Apple/dark card."""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Slot
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QDialog, QWidget

from whisper_microfone.engine import Engine

# ---------------------------------------------------------------------------
# Limites de tamanho
# ---------------------------------------------------------------------------
_MIN_SIZE = 120
_MAX_SIZE = 320
_DEFAULT  = 168
_CORNER   = 16   # zona de resize no canto inferior direito (px)

# Cores de fundo do card — alpha 230 = 90% opacidade
_BG_TOP      = QColor(0x18, 0x1a, 0x20, 230)
_BG_MID      = QColor(0x11, 0x13, 0x18, 230)
_BG_BOT      = QColor(0x09, 0x0a, 0x0d, 230)
_REC_BG_TOP  = QColor(0x25, 0x14, 0x16, 230)
_REC_BG_MID  = QColor(0x15, 0x10, 0x12, 230)
_REC_BG_BOT  = QColor(0x09, 0x0a, 0x0d, 230)
_BORDER_IDLE = QColor(255, 255, 255, 26)
_BORDER_REC  = QColor(248, 113, 113, 77)
_SPIN_COLOR  = QColor(255, 255, 255, 200)

_ANIM_MS     = 16
_COUNTDOWN_S = 1


def _tokens(size: int) -> dict:
    """Recalcula todos os tokens de layout proporcionalmente ao tamanho do card."""
    s  = size
    r  = max(14, round(s * 22 / 168))       # border-radius
    cx = s // 2
    cy = s // 2 - round(s * 8 / 168)        # levemente acima do centro
    cr = round(s * 40 / 168)                # raio do círculo interno
    ly = s - round(s * 32 / 168)            # posição Y do label
    return {"s": s, "r": r, "cx": cx, "cy": cy, "cr": cr, "ly": ly}


class MicPopup(QDialog):
    """Mini popup de ditado estilo dark card com resize pelo canto."""

    def __init__(self, engine: Engine, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool,
        )
        self._engine    = engine
        self._card_size = _DEFAULT

        self._drag_pos:   QPoint | None = None
        self._press_pos:  QPoint = QPoint()
        self._did_drag:   bool = False
        self._is_resize:  bool = False
        self._resize_origin: QPoint = QPoint()
        self._resize_start_size: int = _DEFAULT
        self._hovered:    bool = False

        self._phase        = "idle"
        self._countdown_ms = 0
        self._spin_angle   = 0.0
        self._ping_t       = 0.0
        self._volume       = 0.0   # RMS atual 0..1
        self._vol_smooth   = 0.0   # suavizado para animação
        self._label        = "Pressione para falar"

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMinimumSize(_MIN_SIZE, _MIN_SIZE)
        self.setMaximumSize(_MAX_SIZE, _MAX_SIZE)
        self.resize(_DEFAULT, _DEFAULT)
        self.setMouseTracking(True)

        self._timer = QTimer(self)
        self._timer.setInterval(_ANIM_MS)
        self._timer.timeout.connect(self._tick)

        engine.state_changed.connect(self._on_state)
        engine.transcribed.connect(self._on_transcribed)
        engine.volume_updated.connect(self._on_volume)

        self._position()

    # ------------------------------------------------------------------
    # Posicionamento
    # ------------------------------------------------------------------

    def _position(self) -> None:
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            s  = self._card_size
            self.move(sg.center().x() - s // 2, sg.bottom() - s - 52)

    def _apply_size(self, new_size: int) -> None:
        new_size = max(_MIN_SIZE, min(_MAX_SIZE, new_size))
        self._card_size = new_size
        self.resize(new_size, new_size)
        self.update()

    # ------------------------------------------------------------------
    # Paint principal
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        t   = _tokens(self._card_size)
        W   = t["s"]
        H   = t["s"]
        R   = t["r"]
        cx  = float(t["cx"])
        cy  = float(t["cy"])
        cr  = float(t["cr"])
        ly  = t["ly"]

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_rec    = self._phase == "recording"
        card_rect = QRectF(0.5, 0.5, W - 1, H - 1)

        # ── 1. fundo gradiente diagonal ───────────────────────────────
        grad = QLinearGradient(0, 0, W, H)
        if is_rec:
            grad.setColorAt(0.0,  _REC_BG_TOP)
            grad.setColorAt(0.45, _REC_BG_MID)
            grad.setColorAt(1.0,  _REC_BG_BOT)
        else:
            grad.setColorAt(0.0,  _BG_TOP)
            grad.setColorAt(0.45, _BG_MID)
            grad.setColorAt(1.0,  _BG_BOT)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(card_rect, R, R)

        # ── 2. borda do card ──────────────────────────────────────────
        p.setPen(QPen(_BORDER_REC if is_rec else _BORDER_IDLE, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(card_rect, R, R)

        # ── 3. radial highlight no topo ───────────────────────────────
        rh = QRadialGradient(cx, H * 0.34, W * 0.5)
        rh.setColorAt(0.0,  QColor(255, 255, 255, 30))
        rh.setColorAt(0.35, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rh))
        p.drawRoundedRect(card_rect, R, R)

        # ── 4. linear overlay ─────────────────────────────────────────
        lo = QLinearGradient(0, 0, W * 0.7, H * 0.7)
        lo.setColorAt(0.0,  QColor(255, 255, 255, 15))
        lo.setColorAt(0.45, QColor(0, 0, 0, 0))
        lo.setColorAt(1.0,  QColor(0, 0, 0, 71))
        p.setBrush(QBrush(lo))
        p.drawRoundedRect(card_rect, R, R)

        # ── 5. ping ring (recording) ──────────────────────────────────
        ping_max = cr * 0.7
        if is_rec:
            t_ping  = self._ping_t
            ring_r  = cr + t_ping * ping_max
            alpha   = int(26 * (1 - t_ping))
            p.setPen(QPen(QColor(248, 113, 113, max(0, alpha)), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

            rr = QRadialGradient(cx, cy, cr * 1.2)
            rr.setColorAt(0.0, QColor(248, 113, 113, 46))
            rr.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(rr))
            p.drawEllipse(QPointF(cx, cy), cr * 1.5, cr * 1.5)

        # ── 6. círculo interno ────────────────────────────────────────
        # Pulsa com o volume durante gravação (±20% do raio)
        vol_scale = 1.0 + self._vol_smooth * 0.20 if is_rec else 1.0
        cr_draw = cr * vol_scale

        if is_rec:
            rc = QRadialGradient(cx, cy, cr_draw)
            rc.setColorAt(0.0, QColor(239, 68, 68, 38))
            rc.setColorAt(1.0, QColor(239, 68, 68, 0))
            p.setBrush(QBrush(rc))
        else:
            alpha_c = 28 if self._hovered else 20
            p.setBrush(QBrush(QColor(255, 255, 255, alpha_c)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), cr_draw, cr_draw)

        # borda do círculo
        rb = QColor(252, 165, 165, 56) if is_rec else QColor(255, 255, 255, 18)
        ring_alpha = rb.alpha() if (is_rec or self._hovered) else 0
        p.setPen(QPen(QColor(rb.red(), rb.green(), rb.blue(), ring_alpha), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), cr_draw + 9, cr_draw + 9)

        # brilho interno
        ri = QRadialGradient(cx, cy, cr_draw)
        ri.setColorAt(0.0,  QColor(255, 255, 255, 46))
        ri.setColorAt(0.68, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ri))
        p.drawEllipse(QPointF(cx, cy), cr_draw, cr_draw)

        # ── 7. conteúdo do círculo ────────────────────────────────────
        if self._phase in ("idle", "done"):
            self._draw_mic(p, cx, cy, cr, is_rec=False)
        elif self._phase == "countdown":
            self._draw_countdown(p, cx, cy, cr)
        elif self._phase == "recording":
            self._draw_mic(p, cx, cy, cr, is_rec=True)
        elif self._phase == "processing":
            self._draw_spinner(p, cx, cy, cr * 0.72)

        # ── 8. badge REC ──────────────────────────────────────────────
        if is_rec:
            self._draw_rec_badge(p)

        # ── 9. label ──────────────────────────────────────────────────
        self._draw_label(p, is_rec, ly, W, H)

        # ── 10. X (hover) ─────────────────────────────────────────────
        if self._hovered:
            self._draw_close_btn(p, W)

        # ── 11. alça de resize (hover, canto inferior direito) ────────
        if self._hovered:
            self._draw_resize_handle(p, W, H)

        # ── 12. inset shadow ──────────────────────────────────────────
        ig = QLinearGradient(0, 0, 0, H)
        ig.setColorAt(0.0,  QColor(255, 255, 255, 30))
        ig.setColorAt(0.08, QColor(0, 0, 0, 0))
        ig.setColorAt(1.0,  QColor(0, 0, 0, 97))
        p.setPen(QPen(QBrush(ig), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, W - 1, H - 1), R, R)

        p.end()

    # ------------------------------------------------------------------
    # Sub-renders
    # ------------------------------------------------------------------

    def _draw_mic(self, p: QPainter, cx: float, cy: float, cr: float, is_rec: bool) -> None:
        col  = QColor(254, 226, 226)       if is_rec else QColor(255, 255, 255, 230)
        glow = QColor(248, 113, 113, 80)   if is_rec else QColor(255, 255, 255, 40)

        icon_px = cr * 0.72
        scale   = icon_px / 17.5   # span vertical do SVG (y 2.5→20)

        def s(v: float) -> float:
            return v * scale

        ox = cx - s(12)
        oy = cy - s(11.25)

        def pt(x: float, y: float) -> QPointF:
            return QPointF(ox + s(x), oy + s(y))

        sw = max(1.5, s(2.4))
        mic_pen  = QPen(col,  sw,     Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        glow_pen = QPen(glow, sw + 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Corpo
        body_rect = QRectF(ox + s(8.3), oy + s(2.5), s(7.4), s(12.0))
        for pen in (glow_pen, mic_pen):
            p.setPen(pen)
            p.drawRoundedRect(body_rect, s(3.7), s(3.7))

        # Arco (abre para baixo)
        arc_r    = s(6.25)
        arc_rect = QRectF(ox + s(12) - arc_r, oy + s(10.65) - arc_r, arc_r * 2, arc_r * 2)
        for pen in (glow_pen, mic_pen):
            p.setPen(pen)
            p.drawArc(arc_rect, 0, -180 * 16)

        # Haste e base
        for pen in (glow_pen, mic_pen):
            p.setPen(pen)
            p.drawLine(pt(12, 16.9), pt(12, 20.0))
            p.drawLine(pt(8.75, 20.0), pt(15.25, 20.0))

    def _draw_countdown(self, p: QPainter, cx: float, cy: float, cr: float) -> None:
        remaining_s = math.ceil(self._countdown_ms / 1000)
        font = QFont("Segoe UI", max(10, round(cr * 0.55)))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(cx - cr, cy - cr, cr * 2, cr * 2),
                   Qt.AlignmentFlag.AlignCenter, str(max(1, remaining_s)))

    def _draw_spinner(self, p: QPainter, cx: float, cy: float, br: float) -> None:
        inset = br * 0.30
        rect  = QRectF(cx - br + inset, cy - br + inset, (br - inset) * 2, (br - inset) * 2)
        grad  = QConicalGradient(QPointF(cx, cy), -self._spin_angle)
        grad.setColorAt(0.0,  _SPIN_COLOR)
        grad.setColorAt(0.75, QColor(255, 255, 255, 0))
        pen = QPen(QBrush(grad), br * 0.16, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(rect, 0, 360 * 16)

    def _draw_rec_badge(self, p: QPainter) -> None:
        bx, by = 8.0, 8.0
        bh = 16.0
        font = QFont("Segoe UI", 7)
        font.setBold(True)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        from PySide6.QtGui import QFontMetrics
        fm     = QFontMetrics(font)
        dot_w  = 12
        text_w = fm.horizontalAdvance("REC")
        bw     = dot_w + text_w + 12
        bg     = QLinearGradient(bx, by, bx, by + bh)
        bg.setColorAt(0.0, QColor(252, 165, 165, 89))
        bg.setColorAt(0.5, QColor(248, 113, 113, 46))
        bg.setColorAt(1.0, QColor(69,  10,  10, 179))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), bh / 2, bh / 2)
        p.setBrush(QBrush(QColor(248, 113, 113)))
        p.drawEllipse(QPointF(bx + 8, by + bh / 2), 3, 3)
        p.setFont(font)
        p.setPen(QColor(254, 226, 226, 204))
        p.drawText(QRectF(bx + dot_w + 2, by, text_w + 8, bh),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "REC")

    def _draw_label(self, p: QPainter, is_rec: bool, ly: int, W: int, H: int) -> None:
        if is_rec:
            col = QColor(254, 226, 226, 204)
        elif self._hovered:
            col = QColor(255, 255, 255, 168)
        else:
            col = QColor(255, 255, 255, 122)
        font = QFont("Segoe UI", max(7, round(self._card_size * 9 / 168)))
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        p.setPen(col)
        p.drawText(QRectF(0, float(ly), float(W), float(H) - ly),
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                   self._label)

    def _draw_close_btn(self, p: QPainter, W: int) -> None:
        cx_c = float(W - 18)
        cy_c = 16.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(80, 80, 88, 160)))
        p.drawEllipse(QPointF(cx_c, cy_c), 9, 9)
        pen_x = QPen(QColor(200, 200, 208), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_x)
        d = 3.5
        p.drawLine(QPointF(cx_c - d, cy_c - d), QPointF(cx_c + d, cy_c + d))
        p.drawLine(QPointF(cx_c + d, cy_c - d), QPointF(cx_c - d, cy_c + d))

    def _draw_resize_handle(self, p: QPainter, W: int, H: int) -> None:
        """Três risquinhos diagonais no canto inferior direito."""
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for i in range(3):
            off = 5 + i * 4
            p.drawLine(QPointF(W - 6, H - 6 - off + off),
                       QPointF(W - 6 - off + off, H - 6))
        # simplificado: linhas paralelas à diagonal
        for i in (4, 8, 12):
            p.drawLine(QPointF(W - 4, H - 4 - i), QPointF(W - 4 - i, H - 4))

    # ------------------------------------------------------------------
    # Helpers de hit-test
    # ------------------------------------------------------------------

    def _over_corner(self, pos: QPointF) -> bool:
        W = H = self._card_size
        return pos.x() >= W - _CORNER and pos.y() >= H - _CORNER

    def _over_close(self, pos: QPointF) -> bool:
        W = self._card_size
        return math.hypot(pos.x() - (W - 18), pos.y() - 16) <= 11

    def _over_circle(self, pos: QPointF) -> bool:
        t  = _tokens(self._card_size)
        return math.hypot(pos.x() - t["cx"], pos.y() - t["cy"]) <= t["cr"] + 8

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        self._press_pos = pos.toPoint()
        self._did_drag  = False

        if self._over_corner(pos):
            self._is_resize       = True
            self._resize_origin   = event.globalPosition().toPoint()
            self._resize_start_size = self._card_size
        else:
            self._is_resize = False
            self._drag_pos  = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = False
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()

        if not (event.buttons() & Qt.MouseButton.LeftButton):
            # Cursores estáticos
            if self._over_close(pos) or self._over_circle(pos):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif self._over_corner(pos):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            return

        if self._is_resize:
            # Resize proporcional: delta diagonal → novo tamanho
            gpos  = event.globalPosition().toPoint()
            delta = ((gpos.x() - self._resize_origin.x()) +
                     (gpos.y() - self._resize_origin.y())) // 2
            self._apply_size(self._resize_start_size + delta)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            return

        if self._drag_pos is None:
            return
        delta = pos.toPoint() - self._press_pos
        if not self._did_drag and (abs(delta.x()) > 4 or abs(delta.y()) > 4):
            self._did_drag = True
        if self._did_drag:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._is_resize:
            self._is_resize = False
            return

        if not self._did_drag:
            pos = event.position()
            if self._over_close(pos):
                self._close_safe()
                return
            if self._over_circle(pos):
                self._on_btn_click()

        self._drag_pos = None
        self._did_drag = False

    # ------------------------------------------------------------------
    # Lógica de botão
    # ------------------------------------------------------------------

    def _on_btn_click(self) -> None:
        if self._phase in ("idle", "done"):
            self._start_countdown()
        elif self._phase == "countdown":
            self._cancel_countdown()
        elif self._phase == "recording":
            self._engine.toggle_recording()

    def _start_countdown(self) -> None:
        self._phase        = "countdown"
        self._countdown_ms = _COUNTDOWN_S * 1000
        self._label        = "Preparando..."
        self._timer.start()
        self.update()

    def _cancel_countdown(self) -> None:
        self._phase = "idle"
        self._label = "Pressione para falar"
        self._timer.stop()
        self.update()

    # ------------------------------------------------------------------
    # Sinais do engine
    # ------------------------------------------------------------------

    def _on_state(self, state: str) -> None:
        if state == "recording":
            self._phase  = "recording"
            self._ping_t = 0.0
            self._label  = "Ouvindo..."
            self._timer.start()
        elif state == "transcribing":
            self._phase      = "processing"
            self._spin_angle = 0.0
            self._label      = "Transcrevendo..."
            self._timer.start()
        elif state == "idle":
            if self._phase not in ("countdown",):
                self._phase = "idle"
                self._label = "Pressione para falar"
                self._timer.stop()
        self.update()

    def _on_volume(self, rms: float) -> None:
        self._volume = rms
        self.update()

    def _on_transcribed(self, _text: str, _meta: dict) -> None:
        self._phase = "done"
        self._label = "Colado ✓"
        self._vol_smooth = 0.0
        self._timer.stop()
        self.update()
        QTimer.singleShot(2000, self._reset_idle)

    def _reset_idle(self) -> None:
        if self._phase == "done":
            self._phase = "idle"
            self._label = "Pressione para falar"
            self.update()

    # ------------------------------------------------------------------
    # Animação
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if self._phase == "countdown":
            self._countdown_ms -= _ANIM_MS
            if self._countdown_ms <= 0:
                self._timer.stop()
                self._engine.toggle_recording()
            self.update()
        elif self._phase == "recording":
            self._ping_t += _ANIM_MS / 1200.0
            if self._ping_t >= 1.0:
                self._ping_t = 0.0
            # Suaviza o volume: sobe rápido, desce devagar
            target = self._volume
            if target > self._vol_smooth:
                self._vol_smooth += (target - self._vol_smooth) * 0.5
            else:
                self._vol_smooth += (target - self._vol_smooth) * 0.15
            self.update()
        elif self._phase == "processing":
            self._spin_angle = (self._spin_angle + 6) % 360
            self.update()

    # ------------------------------------------------------------------
    # Fechar
    # ------------------------------------------------------------------

    def _close_safe(self) -> None:
        self._timer.stop()
        if self._engine._recorder.is_recording:
            self._engine.toggle_recording()
        self._phase = "idle"
        self._label = "Pressione para falar"
        self.hide()

    # ------------------------------------------------------------------
    # Toggle (hotkey)
    # ------------------------------------------------------------------

    @Slot()
    def toggle(self) -> None:
        if not self.isVisible():
            # Popup fechado → abre e inicia countdown
            self._position()
            self.show()
            self.raise_()
            self._start_countdown()
        elif self._phase == "countdown":
            # Durante countdown → cancela e fecha
            self._cancel_countdown()
            self._close_safe()
        elif self._phase == "recording":
            # Gravando → para e processa
            self._engine.toggle_recording()
        elif self._phase == "processing":
            # Processando → ignora (aguarda terminar)
            pass
        elif self._phase in ("idle", "done"):
            # Idle ou done → reinicia countdown direto (sem fechar)
            self._start_countdown()
