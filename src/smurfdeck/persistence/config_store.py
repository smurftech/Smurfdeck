from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from smurfdeck.models.config import AppConfig


def default_config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "smurfdeck" / "config.json"


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()
        self.recovery_path: Path | None = None

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            with self.path.open(encoding="utf-8") as file:
                return AppConfig.from_dict(json.load(file))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            self.recovery_path = self.path.with_name(f"config.invalid-{timestamp}.json")
            with suppress(OSError):
                shutil.copy2(self.path, self.recovery_path)
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".config-", suffix=".tmp", dir=self.path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(config.to_dict(), file, indent=2, ensure_ascii=False)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
