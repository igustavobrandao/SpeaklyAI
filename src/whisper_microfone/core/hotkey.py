from __future__ import annotations

import threading
import time
from collections.abc import Callable

from loguru import logger
from pynput.keyboard import Key, KeyCode, Listener

_MODIFIER_MAP: dict[str, Key] = {
    "ctrl": Key.ctrl_l,
    "alt": Key.alt_l,
    "shift": Key.shift,
    "space": Key.space,
    **{f"f{n}": getattr(Key, f"f{n}") for n in range(1, 25)},
}

# Mapa de letra minúscula → virtual key code do Windows
_CHAR_TO_VK: dict[str, int] = {chr(i): i - 32 for i in range(ord("a"), ord("z") + 1)}
_CHAR_TO_VK.update({str(i): ord(str(i)) for i in range(10)})


def _parse_combination(combination: str) -> frozenset[Key | KeyCode]:
    keys: set[Key | KeyCode] = set()
    for part in combination.lower().split("+"):
        part = part.strip()
        if part in _MODIFIER_MAP:
            keys.add(_MODIFIER_MAP[part])
        elif len(part) == 1:
            keys.add(KeyCode.from_char(part))
        else:
            raise ValueError(f"Token de tecla desconhecido: {part!r}")
    return frozenset(keys)


def _key_matches(pressed: Key | KeyCode, target: Key | KeyCode) -> bool:
    """Verifica se pressed bate com target tolerando divergências de vk vs char."""
    if pressed == target:
        return True
    if isinstance(pressed, KeyCode) and isinstance(target, KeyCode):
        # Normaliza chars para minúsculo antes de comparar
        pc = pressed.char.lower() if pressed.char else None
        tc = target.char.lower() if target.char else None
        if pc and tc and pc == tc:
            return True
        # Quando Alt/AltGr está pressionado no Windows, pynput pode reportar
        # apenas vk sem char. Compara vk diretamente.
        pvk = pressed.vk
        tvk = target.vk
        if pvk and tvk and pvk == tvk:
            return True
        # target foi criado via from_char → tem char mas não vk.
        # pressed tem vk mas não char. Deriva o vk esperado do char do target.
        if tc and pvk:
            expected_vk = _CHAR_TO_VK.get(tc)
            if expected_vk and pvk == expected_vk:
                return True
    return False


class PushToTalkHotkey:
    def __init__(
        self,
        combination: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._target = _parse_combination(combination)
        self._held: list[Key | KeyCode] = []
        self._active = False
        self._lock = threading.Lock()
        self._listener: Listener | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._listener = Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
            daemon=True,
        )
        self._listener.start()
        logger.debug("PushToTalkHotkey listener iniciado (combo={})", self._target)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        with self._lock:
            self._held.clear()
            self._active = False
        logger.debug("PushToTalkHotkey listener parado")

    def update_combination(self, combination: str) -> None:
        with self._lock:
            self._target = _parse_combination(combination)
            self._held.clear()
            self._active = False
        logger.debug("PushToTalkHotkey combo atualizado para {}", self._target)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _normalize(self, key: Key | KeyCode) -> Key | KeyCode:
        _left_right: dict[Key, Key] = {
            Key.ctrl_r: Key.ctrl_l,
            Key.alt_r: Key.alt_l,
            Key.shift_r: Key.shift,
            Key.shift_l: Key.shift,
        }
        if isinstance(key, Key):
            return _left_right.get(key, key)
        if key.char is not None and len(key.char) == 1:
            return KeyCode.from_char(key.char.lower())
        return key

    def _all_target_matched(self) -> bool:
        """Retorna True se cada tecla do target tem pelo menos uma correspondência em _held."""
        return all(any(_key_matches(h, target) for h in self._held) for target in self._target)

    def _held_matches(self, key: Key | KeyCode) -> bool:
        """Retorna True se key bate com alguma tecla do target."""
        return any(_key_matches(key, t) for t in self._target)

    def _handle_press(self, key: Key | KeyCode | None) -> None:
        if key is None:
            return
        normalized = self._normalize(key)
        with self._lock:
            # Evita duplicatas
            if not any(_key_matches(normalized, h) for h in self._held):
                self._held.append(normalized)
            if self._all_target_matched() and not self._active:
                self._active = True
                fire = True
            else:
                fire = False
        if fire:
            try:
                self._on_press()
            except Exception:
                logger.exception("Erro no callback on_press do hotkey")

    def _handle_release(self, key: Key | KeyCode | None) -> None:
        if key is None:
            return
        normalized = self._normalize(key)
        with self._lock:
            self._held = [h for h in self._held if not _key_matches(h, normalized)]
            if self._held_matches(normalized) and self._active:
                self._active = False
                fire = True
            else:
                fire = False
        if fire:
            try:
                self._on_release()
            except Exception:
                logger.exception("Erro no callback on_release do hotkey")


if __name__ == "__main__":
    hotkey = PushToTalkHotkey(
        "ctrl+alt+shift+q",
        on_press=lambda: print(">>> POPUP HOTKEY DETECTADO"),
        on_release=lambda: print("RELEASE"),
    )
    hotkey.start()
    print("Pressione Ctrl+Alt+Shift+Q (aguardando 15s)...")
    time.sleep(15)
    hotkey.stop()
    print("Encerrado.")
