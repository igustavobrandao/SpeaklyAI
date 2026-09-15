from __future__ import annotations

import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key

from whisper_microfone.config.schemas import InjectionConfig


class TypingTimeoutError(Exception):
    pass


class TextInjector:
    def __init__(self, config: InjectionConfig) -> None:
        self.config = config
        self._keyboard = Controller()

    def inject(self, text: str) -> None:
        text = self._post_process(text)
        if not text:
            return
        if self.config.strategy == "paste_only":
            self._paste(text)
        elif self.config.strategy == "type_only":
            self._type(text)
        else:
            try:
                self._type_with_timeout(text)
            except TypingTimeoutError:
                self._paste(text)

    def _post_process(self, text: str) -> str:
        if self.config.trim_whitespace:
            text = text.strip()

        if self.config.capitalize_first and text:
            text = text[0].upper() + text[1:]

        if self.config.sentence_end_punctuation and text and text[-1] not in ".!?":
            text = text + self.config.sentence_end_punctuation

        if self.config.add_trailing_space:
            text = text + " "

        return text

    def _paste(self, text: str) -> None:
        previous: str | None = None
        if self.config.restore_clipboard:
            try:
                previous = pyperclip.paste()
            except Exception:
                previous = None

        pyperclip.copy(text)

        with self._keyboard.pressed(Key.ctrl):
            self._keyboard.press("v")
            self._keyboard.release("v")

        if self.config.restore_clipboard and previous is not None:
            time.sleep(self.config.restore_clipboard_delay_ms / 1000)
            pyperclip.copy(previous)

    def _type(self, text: str) -> None:
        # Usa `keyboard` (SendInput) para suporte correto a Unicode/acentos no Windows.
        # Fallback para pynput se a lib não estiver disponível.
        delay = self.config.type_delay_ms / 1000
        try:
            import keyboard as kb
            kb.write(text, delay=delay)
        except Exception:
            ctrl = Controller()
            for char in text:
                ctrl.type(char)
                if delay > 0:
                    time.sleep(delay)

    def _type_with_timeout(self, text: str) -> None:
        timeout = self.config.paste_fallback_after_ms / 1000
        exc_holder: list[BaseException] = []

        def _worker() -> None:
            try:
                self._type(text)
            except Exception as exc:
                exc_holder.append(exc)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TypingTimeoutError(
                f"Typing did not complete within {timeout:.3f}s"
            )

        if exc_holder:
            raise exc_holder[0]
