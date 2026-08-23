import pytest
from evdev import ecodes

from smurfdeck.actions.shortcuts import media_key, parse_shortcut


def test_shortcut_parser_accepts_readable_key_names() -> None:
    assert parse_shortcut("Ctrl + Shift + S") == (
        ecodes.KEY_LEFTCTRL,
        ecodes.KEY_LEFTSHIFT,
        ecodes.KEY_S,
    )


def test_shortcut_parser_supports_function_and_navigation_keys() -> None:
    assert parse_shortcut("Alt+F4") == (ecodes.KEY_LEFTALT, ecodes.KEY_F4)
    assert parse_shortcut("Meta+Left") == (ecodes.KEY_LEFTMETA, ecodes.KEY_LEFT)


def test_shortcut_parser_rejects_unknown_and_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        parse_shortcut("Ctrl+Smurf")
    with pytest.raises(ValueError, match="same key twice"):
        parse_shortcut("Ctrl+Ctrl")


def test_media_key_maps_stable_action_identifier() -> None:
    assert media_key("play_pause") == ecodes.KEY_PLAYPAUSE
    with pytest.raises(ValueError, match="Unsupported media"):
        media_key("eject_everything")

