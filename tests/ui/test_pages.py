from __future__ import annotations

from PySide6.QtWidgets import QLabel

from whisper_microfone.config.schemas import FullConfig
from whisper_microfone.ui.pages.about import AboutPage
from whisper_microfone.version import VERSION


def test_about_page_describes_the_current_groq_runtime(qtbot) -> None:
    page = AboutPage(object(), FullConfig())
    qtbot.addWidget(page)
    labels = [label.text() for label in page.findChildren(QLabel)]

    assert f"v{VERSION} Alpha" in labels
    assert "API Groq (nuvem)" in labels
    assert not any("Rate limit" in label for label in labels)
