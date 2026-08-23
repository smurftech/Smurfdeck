from smurfdeck.devices.base import DeckKeyEvent
from smurfdeck.devices.streamdeck import StreamDeckDevice


class FakeDeck:
    callback = None
    images: dict[int, bytes]

    def __init__(self) -> None:
        self.images = {}
        self.closed = False
        self.reset_error: Exception | None = None

    def key_layout(self) -> tuple[int, int]:
        # Upstream API order is (rows, columns).
        return (3, 5)

    def key_image_format(self) -> dict[str, object]:
        return {"size": (72, 72)}

    def deck_type(self) -> str:
        return "Fake Deck"

    def get_serial_number(self) -> str:
        return "TEST-123"

    def get_firmware_version(self) -> str:
        return "1.0"

    def set_key_callback(self, callback: object) -> None:
        self.callback = callback

    def reset(self) -> None:
        if self.reset_error is not None:
            raise self.reset_error

    def close(self) -> None:
        self.closed = True


def test_adapter_reports_device_information() -> None:
    device = StreamDeckDevice(FakeDeck())
    assert device.info.model == "Fake Deck"
    assert device.info.geometry.columns == 5
    assert device.info.geometry.rows == 3
    assert device.info.geometry.key_count == 15
    assert device.info.serial == "TEST-123"


def test_adapter_translates_callback_to_event() -> None:
    deck = FakeDeck()
    device = StreamDeckDevice(deck)
    events: list[DeckKeyEvent] = []
    device.set_event_sink(events.append)
    assert deck.callback is not None
    deck.callback(deck, 2, True)
    deck.callback(deck, 2, False)
    assert events == [DeckKeyEvent(2, True), DeckKeyEvent(2, False)]


def test_close_releases_device_when_optional_reset_fails() -> None:
    deck = FakeDeck()
    deck.reset_error = OSError("feature report failed")
    StreamDeckDevice(deck).close()
    assert deck.closed
