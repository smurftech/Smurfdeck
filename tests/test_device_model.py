from smurfdeck.devices.base import DeckGeometry, DeckKeyEvent


def test_geometry_calculates_key_count() -> None:
    geometry = DeckGeometry(columns=5, rows=3, key_width=72, key_height=72)
    assert geometry.key_count == 15


def test_key_event_preserves_press_state() -> None:
    assert DeckKeyEvent(key=4, pressed=True).pressed is True
    assert DeckKeyEvent(key=4, pressed=False).pressed is False

