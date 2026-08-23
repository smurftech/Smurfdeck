from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from smurfdeck.actions.shortcuts import media_key, parse_shortcut
from smurfdeck.models.config import KeyConfig


class ChordEmitter(Protocol):
    def send_chord(self, keys: tuple[int, ...]) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ActionResult:
    executed: bool
    success: bool
    message: str


class ActionEngine:
    """Validate trigger transitions and execute input actions."""

    def __init__(self, emitter: ChordEmitter) -> None:
        self._emitter = emitter
        self._key_states: dict[int, bool] = {}

    def handle_key(self, key_index: int, key: KeyConfig, pressed: bool) -> ActionResult:
        previous = self._key_states.get(key_index, False)
        self._key_states[key_index] = pressed
        if previous == pressed:
            return ActionResult(False, True, "Duplicate key state ignored")
        if key.action_type == "none":
            return ActionResult(False, True, "No action assigned")
        trigger_matches = key.trigger == "both" or (
            key.trigger == "press" and pressed
        ) or (key.trigger == "release" and not pressed)
        if not trigger_matches:
            return ActionResult(False, True, "Waiting for configured trigger")
        try:
            if key.action_type == "keyboard":
                self._emitter.send_chord(parse_shortcut(key.action_value))
            elif key.action_type == "media":
                self._emitter.send_chord((media_key(key.action_value),))
            else:
                return ActionResult(True, False, "This action is not executable yet")
        except (OSError, ValueError) as error:
            return ActionResult(True, False, str(error))
        return ActionResult(True, True, "Action sent")

    def close(self) -> None:
        self._emitter.close()
