from evdev import ecodes

from smurfdeck.actions.engine import ActionEngine
from smurfdeck.models.config import KeyConfig


class FakeEmitter:
    def __init__(self, error: OSError | None = None) -> None:
        self.chords: list[tuple[int, ...]] = []
        self.error = error
        self.closed = False

    def send_chord(self, keys: tuple[int, ...]) -> None:
        if self.error is not None:
            raise self.error
        self.chords.append(keys)

    def close(self) -> None:
        self.closed = True


def test_keyboard_action_executes_on_configured_press_trigger() -> None:
    emitter = FakeEmitter()
    engine = ActionEngine(emitter)
    key = KeyConfig(action_type="keyboard", action_value="Ctrl+S", trigger="press")
    pressed = engine.handle_key(0, key, True)
    released = engine.handle_key(0, key, False)
    assert pressed.success and pressed.executed
    assert not released.executed
    assert emitter.chords == [(ecodes.KEY_LEFTCTRL, ecodes.KEY_S)]


def test_release_trigger_and_media_control() -> None:
    emitter = FakeEmitter()
    engine = ActionEngine(emitter)
    key = KeyConfig(action_type="media", action_value="volume_up", trigger="release")
    assert not engine.handle_key(3, key, True).executed
    assert engine.handle_key(3, key, False).executed
    assert emitter.chords == [(ecodes.KEY_VOLUMEUP,)]


def test_duplicate_hardware_state_does_not_execute_twice() -> None:
    emitter = FakeEmitter()
    engine = ActionEngine(emitter)
    key = KeyConfig(action_type="media", action_value="mute")
    engine.handle_key(2, key, True)
    duplicate = engine.handle_key(2, key, True)
    assert not duplicate.executed
    assert emitter.chords == [(ecodes.KEY_MUTE,)]


def test_uinput_error_is_returned_without_crashing() -> None:
    engine = ActionEngine(FakeEmitter(PermissionError("uinput permission denied")))
    key = KeyConfig(action_type="media", action_value="play_pause")
    result = engine.handle_key(1, key, True)
    assert result.executed and not result.success
    assert "permission denied" in result.message

