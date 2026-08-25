from evdev import ecodes

from smurfdeck.actions.engine import ActionEngine, ActionResult
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


class FakeDesktop:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.callback = None
        self.closed = False

    def launch(self, value: str) -> ActionResult:
        self.calls.append(("launch", value))
        return ActionResult(True, True, "Launched")

    def open_target(self, value: str) -> ActionResult:
        self.calls.append(("open", value))
        return ActionResult(True, True, "Opened")

    def run_command(
        self, value, working_directory, callback, timeout=60, environment=None
    ) -> ActionResult:
        self.calls.append(("command", value, working_directory, timeout, environment or {}))
        self.callback = callback
        return ActionResult(True, True, "Command running…")

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


def test_desktop_and_page_actions_are_dispatched() -> None:
    desktop = FakeDesktop()
    navigated: list[str] = []
    feedback: list[tuple[int, ActionResult]] = []
    engine = ActionEngine(
        FakeEmitter(),
        desktop,
        lambda destination: navigated.append(destination) or "Switched page",
        lambda key, result: feedback.append((key, result)),
    )
    launch = KeyConfig(action_type="launch", action_value="firefox")
    assert engine.handle_key(0, launch, True).success
    engine.handle_key(0, KeyConfig(), False)
    open_url = KeyConfig(action_type="open", action_value="https://example.com")
    assert engine.handle_key(1, open_url, True).success
    engine.handle_key(1, KeyConfig(), False)
    command = KeyConfig(
        action_type="command",
        action_value="echo hello",
        working_directory="/tmp",
        command_timeout=120,
        environment={"MODE": "test"},
    )
    assert "running" in engine.handle_key(2, command, True).message
    desktop.callback(ActionResult(True, True, "Command completed"))
    engine.handle_key(2, KeyConfig(), False)
    assert engine.handle_key(3, KeyConfig(action_type="page", action_value="next"), True).success
    assert desktop.calls == [
        ("launch", "firefox"),
        ("open", "https://example.com"),
        ("command", "echo hello", "/tmp", 120, {"MODE": "test"}),
    ]
    assert navigated == ["next"]
    assert feedback[0][0] == 2


def test_close_releases_both_action_services() -> None:
    emitter, desktop = FakeEmitter(), FakeDesktop()
    engine = ActionEngine(emitter, desktop)
    engine.close()
    assert emitter.closed and desktop.closed
