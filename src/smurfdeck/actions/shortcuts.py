from __future__ import annotations

import re

from evdev import ecodes

MODIFIERS = {
    "CTRL": ecodes.KEY_LEFTCTRL,
    "CONTROL": ecodes.KEY_LEFTCTRL,
    "SHIFT": ecodes.KEY_LEFTSHIFT,
    "ALT": ecodes.KEY_LEFTALT,
    "META": ecodes.KEY_LEFTMETA,
    "SUPER": ecodes.KEY_LEFTMETA,
}

NAMED_KEYS = {
    "ENTER": ecodes.KEY_ENTER,
    "RETURN": ecodes.KEY_ENTER,
    "SPACE": ecodes.KEY_SPACE,
    "TAB": ecodes.KEY_TAB,
    "ESC": ecodes.KEY_ESC,
    "ESCAPE": ecodes.KEY_ESC,
    "BACKSPACE": ecodes.KEY_BACKSPACE,
    "DELETE": ecodes.KEY_DELETE,
    "INSERT": ecodes.KEY_INSERT,
    "HOME": ecodes.KEY_HOME,
    "END": ecodes.KEY_END,
    "PAGEUP": ecodes.KEY_PAGEUP,
    "PAGEDOWN": ecodes.KEY_PAGEDOWN,
    "UP": ecodes.KEY_UP,
    "DOWN": ecodes.KEY_DOWN,
    "LEFT": ecodes.KEY_LEFT,
    "RIGHT": ecodes.KEY_RIGHT,
    "MINUS": ecodes.KEY_MINUS,
    "EQUAL": ecodes.KEY_EQUAL,
    "COMMA": ecodes.KEY_COMMA,
    "DOT": ecodes.KEY_DOT,
    "SLASH": ecodes.KEY_SLASH,
}

MEDIA_ACTIONS = {
    "play_pause": ("Play / Pause", ecodes.KEY_PLAYPAUSE),
    "next": ("Next track", ecodes.KEY_NEXTSONG),
    "previous": ("Previous track", ecodes.KEY_PREVIOUSSONG),
    "volume_up": ("Volume up", ecodes.KEY_VOLUMEUP),
    "volume_down": ("Volume down", ecodes.KEY_VOLUMEDOWN),
    "mute": ("Mute", ecodes.KEY_MUTE),
}


def _key_names() -> dict[str, int]:
    keys = dict(MODIFIERS | NAMED_KEYS)
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        keys[letter] = int(getattr(ecodes, f"KEY_{letter}"))
    for digit in "0123456789":
        keys[digit] = int(getattr(ecodes, f"KEY_{digit}"))
    for number in range(1, 13):
        keys[f"F{number}"] = int(getattr(ecodes, f"KEY_F{number}"))
    return keys


KEY_NAMES = _key_names()


def parse_shortcut(value: str) -> tuple[int, ...]:
    """Convert a human shortcut such as Ctrl+Shift+S to Linux key codes."""
    tokens = [token.strip().upper().replace(" ", "") for token in re.split(r"\+", value)]
    if not tokens or any(not token for token in tokens):
        raise ValueError("Enter a shortcut such as Ctrl+Shift+S")
    unknown = [token for token in tokens if token not in KEY_NAMES]
    if unknown:
        raise ValueError(f"Unsupported shortcut key: {unknown[0]}")
    codes = tuple(KEY_NAMES[token] for token in tokens)
    if len(set(codes)) != len(codes):
        raise ValueError("A shortcut cannot contain the same key twice")
    return codes


def media_key(value: str) -> int:
    try:
        return MEDIA_ACTIONS[value][1]
    except KeyError as error:
        raise ValueError(f"Unsupported media control: {value or 'none'}") from error


def supported_key_codes() -> frozenset[int]:
    media_codes = frozenset(code for _label, code in MEDIA_ACTIONS.values())
    return frozenset(KEY_NAMES.values()) | media_codes
