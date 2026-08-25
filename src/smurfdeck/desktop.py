from __future__ import annotations

import shutil
import subprocess


def active_application() -> str | None:
    """Return KWin's active application class when kdotool is available."""
    executable = shutil.which("kdotool")
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603
            [executable, "getactivewindow", "getwindowclassname"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    application = completed.stdout.strip().casefold()
    return application or None
