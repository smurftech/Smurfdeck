from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from smurfdeck.actions.shortcuts import media_key, parse_shortcut
from smurfdeck.models.config import KeyConfig


class ChordEmitter(Protocol):
    def send_chord(self, keys: tuple[int, ...]) -> None: ...

    def close(self) -> None: ...


class DesktopRunner(Protocol):
    def launch(self, value: str) -> ActionResult: ...

    def open_target(self, value: str) -> ActionResult: ...

    def run_command(
        self, value: str, working_directory: str, callback: Callable[[ActionResult], None]
    ) -> ActionResult: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ActionResult:
    executed: bool
    success: bool
    message: str


class ActionEngine:
    """Validate trigger transitions and execute input actions."""

    def __init__(
        self,
        emitter: ChordEmitter,
        desktop: DesktopRunner | None = None,
        navigate: Callable[[str], str] | None = None,
        feedback: Callable[[int, ActionResult], None] | None = None,
    ) -> None:
        self._emitter = emitter
        self._desktop = desktop
        self._navigate = navigate
        self._feedback = feedback
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
            elif key.action_type == "launch" and self._desktop is not None:
                return self._desktop.launch(key.action_value)
            elif key.action_type == "open" and self._desktop is not None:
                return self._desktop.open_target(key.action_value)
            elif key.action_type == "command" and self._desktop is not None:
                return self._desktop.run_command(
                    key.action_value,
                    key.working_directory,
                    lambda result: self._report(key_index, result),
                )
            elif key.action_type == "page" and self._navigate is not None:
                return ActionResult(True, True, self._navigate(key.action_value))
            else:
                return ActionResult(True, False, "Action service is unavailable")
        except (OSError, ValueError) as error:
            return ActionResult(True, False, str(error))
        return ActionResult(True, True, "Action sent")

    def _report(self, key_index: int, result: ActionResult) -> None:
        if self._feedback is not None:
            self._feedback(key_index, result)

    def close(self) -> None:
        self._emitter.close()
        if self._desktop is not None:
            self._desktop.close()
