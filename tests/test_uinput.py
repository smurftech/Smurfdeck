import pytest
from evdev import ecodes

from smurfdeck.input.uinput import UInputEmitter


class FakeInput:
    def __init__(self) -> None:
        self.events: list[tuple[int, int, int] | str] = []
        self.closed = False

    def write(self, event_type: int, code: int, value: int) -> None:
        self.events.append((event_type, code, value))

    def syn(self) -> None:
        self.events.append("sync")

    def close(self) -> None:
        self.closed = True


def test_chord_presses_in_order_and_releases_in_reverse() -> None:
    fake = FakeInput()
    emitter = UInputEmitter([ecodes.KEY_LEFTCTRL, ecodes.KEY_S], device=fake)
    emitter.send_chord([ecodes.KEY_LEFTCTRL, ecodes.KEY_S])
    assert fake.events == [
        (ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1),
        (ecodes.EV_KEY, ecodes.KEY_S, 1),
        "sync",
        (ecodes.EV_KEY, ecodes.KEY_S, 0),
        (ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0),
        "sync",
    ]


def test_chord_rejects_unadvertised_key() -> None:
    emitter = UInputEmitter([ecodes.KEY_S], device=FakeInput())
    with pytest.raises(ValueError, match="Unsupported"):
        emitter.send_chord([ecodes.KEY_A])

