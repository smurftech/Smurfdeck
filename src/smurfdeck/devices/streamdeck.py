from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from contextlib import suppress
from typing import Any

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Transport.Transport import TransportError

from smurfdeck.devices.base import DeckEventSink, DeckGeometry, DeckInfo, DeckKeyEvent
from smurfdeck.rendering.keys import numbered_key_image

LOGGER = logging.getLogger(__name__)


class StreamDeckDevice:
    """Own and adapt one opened python-elgato-streamdeck device."""

    def __init__(self, deck: Any) -> None:
        self._deck = deck
        self._sink: DeckEventSink | None = None
        self._lock = threading.RLock()

    @classmethod
    def discover(cls) -> Sequence[StreamDeckDevice]:
        """Open every usable Stream Deck currently visible to the process."""
        devices: list[StreamDeckDevice] = []
        for deck in DeviceManager().enumerate():
            try:
                deck.open()
                deck.reset()
                devices.append(cls(deck))
            except (OSError, TransportError) as error:
                LOGGER.warning("Could not open Stream Deck: %s", error)
                with suppress(Exception):
                    deck.close()
        return devices

    @property
    def info(self) -> DeckInfo:
        columns, rows = self._deck.key_layout()
        key_width, key_height = self._deck.key_image_format()["size"]
        return DeckInfo(
            model=self._deck.deck_type(),
            serial=self._safe_string("get_serial_number"),
            firmware=self._safe_string("get_firmware_version"),
            geometry=DeckGeometry(columns, rows, key_width, key_height),
        )

    def _safe_string(self, method_name: str) -> str | None:
        try:
            return str(getattr(self._deck, method_name)())
        except (AttributeError, OSError, TransportError):
            return None

    def set_event_sink(self, sink: DeckEventSink | None) -> None:
        with self._lock:
            self._sink = sink
        callback = self._on_key_change if sink is not None else None
        self._deck.set_key_callback(callback)

    def _on_key_change(self, _deck: Any, key: int, state: bool) -> None:
        with self._lock:
            sink = self._sink
        if sink is not None:
            sink(DeckKeyEvent(key=key, pressed=bool(state)))

    def render_numbered_key(self, key: int, number: int) -> None:
        image = numbered_key_image(self._deck, number)
        self._deck.set_key_image(key, image)

    def close(self) -> None:
        with self._lock:
            self._sink = None
        self._deck.set_key_callback(None)
        self._deck.reset()
        self._deck.close()

