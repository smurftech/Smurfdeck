from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from evdev import UInput, ecodes


class WritableInputDevice(Protocol):
    def write(self, event_type: int, code: int, value: int) -> None: ...

    def syn(self) -> None: ...

    def close(self) -> None: ...


class UInputEmitter:
    """Emit Wayland-safe key and media events through Linux uinput."""

    def __init__(
        self,
        supported_keys: Iterable[int],
        device: WritableInputDevice | None = None,
    ) -> None:
        self._supported_keys = frozenset(supported_keys)
        self._device = device or UInput(
            {ecodes.EV_KEY: sorted(self._supported_keys)},
            name="SmurfDeck Virtual Input",
        )

    def send_chord(self, keys: Sequence[int]) -> None:
        """Press a chord in order and release it in reverse order."""
        unsupported = set(keys) - self._supported_keys
        if unsupported:
            raise ValueError(f"Unsupported uinput key codes: {sorted(unsupported)}")
        for key in keys:
            self._device.write(ecodes.EV_KEY, key, 1)
        self._device.syn()
        for key in reversed(keys):
            self._device.write(ecodes.EV_KEY, key, 0)
        self._device.syn()

    def close(self) -> None:
        self._device.close()

    def __enter__(self) -> UInputEmitter:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


class LazyUInputEmitter:
    """Open /dev/uinput only when the first configured action executes."""

    def __init__(self, supported_keys: Iterable[int]) -> None:
        self._supported_keys = frozenset(supported_keys)
        self._emitter: UInputEmitter | None = None

    def send_chord(self, keys: Sequence[int]) -> None:
        if self._emitter is None:
            self._emitter = UInputEmitter(self._supported_keys)
        self._emitter.send_chord(keys)

    def close(self) -> None:
        if self._emitter is not None:
            self._emitter.close()
            self._emitter = None
