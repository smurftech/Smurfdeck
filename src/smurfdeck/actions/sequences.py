"""Validated, non-nested multi-actions; scheduling is handled by the Qt adapter."""

import json
from dataclasses import dataclass

from smurfdeck.actions.desktop import parse_command, validate_open_target
from smurfdeck.actions.shortcuts import media_key, parse_shortcut

STEP_TYPES = {
    "keyboard": "Shortcut",
    "media": "Media",
    "launch": "Launch app",
    "open": "Open file / URL",
    "delay": "Delay (ms)",
}


@dataclass(frozen=True)
class SequenceStep:
    action_type: str
    value: str


def parse_sequence(value: str) -> tuple[SequenceStep, ...]:
    try:
        rows = json.loads(value)
    except (ValueError, TypeError) as error:
        raise ValueError("Configure the multi-action steps") from error
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        raise ValueError("Use between 1 and 32 steps")
    steps = []
    total_delay = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("type") not in STEP_TYPES:
            raise ValueError("Unsupported multi-action step")
        kind, text = row["type"], str(row.get("value", "")).strip()
        if kind == "keyboard":
            parse_shortcut(text)
        elif kind == "media":
            media_key(text)
        elif kind == "launch":
            parse_command(text)
        elif kind == "open":
            validate_open_target(text)
        else:
            try:
                delay = int(text)
            except ValueError as error:
                raise ValueError("Delay must be a whole number of milliseconds") from error
            if not 0 <= delay <= 60000:
                raise ValueError("Each delay must be between 0 and 60000 ms")
            total_delay += delay
        steps.append(SequenceStep(kind, text))
    if total_delay > 300000:
        raise ValueError("Total delay must not exceed five minutes")
    return tuple(steps)


def serialize_sequence(steps: tuple[SequenceStep, ...]) -> str:
    return json.dumps([{"type": step.action_type, "value": step.value} for step in steps])
