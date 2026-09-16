from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from whisper_microfone.assets.icon import make_app_icon
from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.engine import Engine
from whisper_microfone.ui.theme import AppTheme

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _make_placeholder_page(name: str) -> QWidget:
    """Cria uma página placeholder com rótulo centralizado."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl = QLabel(name)
    font = QFont()
    font.setPixelSize(AppTheme.FONT_SIZE_LARGE)
    lbl.setFont(font)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"color: {AppTheme.TEXT_SECONDARY};")
    layout.addWidget(lbl)

    return page


def _make_separator() -> QFrame:
    """Linha horizontal de separação na sidebar."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background-color: {AppTheme.BORDER}; border: none;")
    return sep


# ---------------------------------------------------------------------------
# StatusDot — indicador colorido de estado
# ---------------------------------------------------------------------------

class _StatusDot(QWidget):
    """Círculo colorido de 10×10px que reflete o estado do engine."""

    _DOT_SIZE = 10

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self._DOT_SIZE, self._DOT_SIZE)
        self._color = AppTheme.READY
        self._refresh_style()

    def set_state(self, state: str) -> None:
        self._color = AppTheme.STATE_COLOR.get(state, AppTheme.READY)
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color};"
            f"border-radius: {self._DOT_SIZE // 2}px;"
        )


# ---------------------------------------------------------------------------
# NavButton — botão de navegação da sidebar
# ---------------------------------------------------------------------------

class _NavButton(QPushButton):
    """Botão flat de navegação com suporte a estado selecionado."""

    def __init__(self, icon: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(f"{icon}  {label}", parent)
        self.setFlat(True)
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.setFixedHeight(36)

        # Margem lateral via stylesheet de container — o botão ocupa full-width
        # do espaço interno. A pill é controlada via propriedade "selected".
        self._selected = False
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                "QPushButton {"
                "  background-color: rgba(255,255,255,0.08);"
                "  color: rgba(255,255,255,0.90);"
                "  border: none;"
                "  border-radius: 8px;"
                f"  padding: 0 12px;"
                f"  font-size: {AppTheme.FONT_SIZE_BASE}px;"
                "  font-weight: 500;"
                "  text-align: left;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QPushButton {"
                "  background-color: transparent;"
                "  color: rgba(255,255,255,0.48);"
                "  border: none;"
                "  border-radius: 8px;"
                f"  padding: 0 12px;"
                f"  font-size: {AppTheme.FONT_SIZE_BASE}px;"
                "  font-weight: 400;"
                "  text-align: left;"
                "}"
                "QPushButton:hover {"
                "  background-color: rgba(255,255,255,0.06);"
                "  color: rgba(255,255,255,0.90);"
                "}"
            )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

_NAV_ITEMS: list[tuple[str, str]] = [
    ("⊙", "Início"),
    ("⊛", "Configurações"),
    ("≡", "Histórico"),
    ("◉", "Sobre"),
]


class _Sidebar(QFrame):
    """Painel lateral de navegação — largura fixa, fundo dark #0d0e11."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(AppTheme.SIDEBAR_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._nav_buttons: list[_NavButton] = []
        self._build_layout()

    # ------------------------------------------------------------------
    # Construção do layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Título do app
        title = QLabel("Whisper Mic")
        title_font = QFont()
        title_font.setPixelSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(
            "color: rgba(255,255,255,0.90);"
            "padding: 24px 20px 8px 20px;"
            "background: transparent;"
        )
        root.addWidget(title)

        root.addWidget(_make_separator())
        root.addSpacing(8)

        # Itens de navegação
        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 0, 8, 0)
        nav_layout.setSpacing(2)

        for icon, label in _NAV_ITEMS:
            btn = _NavButton(icon, label)
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        root.addWidget(nav_container)
        root.addStretch()

        # Rodapé com dot de status
        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 12, 16, 16)
        footer_layout.setSpacing(8)

        self._dot = _StatusDot()
        self._status_label = QLabel("Pronto")
        self._status_label.setStyleSheet(
            "color: rgba(255,255,255,0.35);"
            "font-size: 11px;"
            "background: transparent;"
        )

        footer_layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        footer_layout.addWidget(self._status_label, 1, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(footer)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def select(self, index: int) -> None:
        """Marca o botão no índice como selecionado, desmarca os demais."""
        for i, btn in enumerate(self._nav_buttons):
            btn.set_selected(i == index)

    def set_state(self, state: str) -> None:
        """Atualiza o dot de status e o label de estado."""
        self._dot.set_state(state)
        label_map: dict[str, str] = {
            "idle":         "Pronto",
            "recording":    "Ouvindo...",
            "transcribing": "Processando...",
            "paused":       "Pausado",
            "error":        "Erro",
        }
        self._status_label.setText(label_map.get(state, state))

    @property
    def nav_buttons(self) -> list[_NavButton]:
        return self._nav_buttons


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Janela principal do Whisper Microfone.

    Layout:
        ┌─ sidebar (220px) ─┬─ content (QStackedWidget) ─┐
        │  Logo / título    │  página ativa               │
        │  nav items        │                             │
        │  ...              │                             │
        │  status dot       │                             │
        └───────────────────┴─────────────────────────────┘

    A janela usa a barra de título nativa do Windows (sem frameless)
    para simplicidade e confiabilidade no ambiente Windows 11.
    """

    def __init__(self, engine: Engine, config: FullConfig) -> None:
        super().__init__()

        self._engine = engine
        self._config = config

        self.setWindowTitle("Whisper Microfone")
        self.setWindowIcon(make_app_icon())
        self.resize(config.ui.window_width, config.ui.window_height)
        self.setMinimumSize(QSize(640, 400))

        self._build_ui()
        self._connect_signals()

        # Seleciona a página inicial (Início)
        self.navigate_to(0)

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Widget central que contém sidebar + conteúdo
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {AppTheme.BG_PRIMARY}; border: none;")

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self._sidebar = _Sidebar()
        root_layout.addWidget(self._sidebar)

        # Área de conteúdo (stack de páginas)
        self._pages = QStackedWidget()
        self._pages.setStyleSheet(f"background-color: {AppTheme.BG_SECONDARY};")
        root_layout.addWidget(self._pages, 1)

        # Páginas placeholder (substituídas incrementalmente)
        self._page_home = _make_placeholder_page("Início")
        self._page_config = _make_placeholder_page("Configurações")
        self._page_history = _make_placeholder_page("Histórico")
        self._page_about = _make_placeholder_page("Sobre")

        for page in (
            self._page_home,
            self._page_config,
            self._page_history,
            self._page_about,
        ):
            self._pages.addWidget(page)

    def _connect_signals(self) -> None:
        # Sinais do engine
        self._engine.state_changed.connect(self._on_state_changed)
        self._engine.error_occurred.connect(self._on_error)

        # Navegação pelos botões da sidebar
        for index, btn in enumerate(self._sidebar.nav_buttons):
            # Captura index por valor default no lambda
            btn.clicked.connect(lambda _checked, i=index: self.navigate_to(i))

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def navigate_to(self, index: int) -> None:
        """Troca a página visível e atualiza o item selecionado na sidebar."""
        if index < 0 or index >= self._pages.count():
            return
        self._pages.setCurrentIndex(index)
        self._sidebar.select(index)

    def replace_page(self, index: int, widget: QWidget) -> None:
        """Substitui uma página placeholder pela implementação real.

        Útil para injeção tardia de páginas após construção do MainWindow.
        """
        if index < 0 or index >= self._pages.count():
            raise IndexError(f"Índice de página inválido: {index}")
        old_widget = self._pages.widget(index)
        if old_widget is None:
            raise RuntimeError(f"Página ausente no índice {index}")
        self._pages.insertWidget(index, widget)
        self._pages.removeWidget(old_widget)
        old_widget.deleteLater()

        # Atualiza referência no atributo correspondente
        _attrs = [
            "_page_home",
            "_page_config",
            "_page_history",
            "_page_about",
        ]
        if index < len(_attrs):
            setattr(self, _attrs[index], widget)

    # ------------------------------------------------------------------
    # Slots privados
    # ------------------------------------------------------------------

    def _on_state_changed(self, state: str) -> None:
        self._sidebar.set_state(state)

    def _on_error(self, message: str) -> None:
        self._sidebar.set_state("error")
        # Mensagem de erro fica no status label da sidebar via set_state;
        # a página home exibirá detalhes quando implementada.
