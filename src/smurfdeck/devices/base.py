from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DeckGeometry:
    columns: int
    rows: int
    key_width: int
    key_height: int

    @property
    def key_count(self) -> int:
        return self.columns * self.rows


@dataclass(frozen=True, slots=True)
class DeckInfo:
    model: str
    geometry: DeckGeometry
    serial: str | None = None
    firmware: str | None = None


@dataclass(frozen=True, slots=True)
class DeckKeyEvent:
    key: int
    pressed: bool


class DeckEventSink(Protocol):
    def __call__(self, event: DeckKeyEvent) -> None: ...


class DeckDevice(Protocol):
    @property
    def info(self) -> DeckInfo: ...

    def set_event_sink(self, sink: DeckEventSink | None) -> None: ...

    def render_numbered_key(self, key: int, number: int) -> None: ...

    def render_key_label(self, key: int, label: str) -> None: ...

    def close(self) -> None: ...
