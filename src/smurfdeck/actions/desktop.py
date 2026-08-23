from __future__ import annotations

import shlex
import subprocess
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from smurfdeck.actions.engine import ActionResult

ResultCallback = Callable[[ActionResult], None]


def parse_command(value: str) -> list[str]:
    """Split a command without invoking a shell."""
    try:
        arguments = shlex.split(value)
    except ValueError as error:
        raise ValueError(f"Invalid command: {error}") from error
    if not arguments:
        raise ValueError("Enter an application or command")
    return arguments


def validate_open_target(value: str) -> str:
    target = value.strip()
    if not target:
        raise ValueError("Enter a file, folder, or URL")
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "mailto", "file"}:
        return target
    path = Path(target).expanduser()
    if not path.exists():
        raise ValueError(f"File or folder does not exist: {path}")
    return str(path.resolve())


def validate_working_directory(value: str) -> str:
    directory = Path(value.strip() or ".").expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"Working directory does not exist: {directory}")
    return str(directory)


class DesktopActionRunner:
    """Run desktop actions without blocking Qt or invoking a shell."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="smurfdeck")
        self._closed = False

    @staticmethod
    def launch(value: str) -> ActionResult:
        arguments = parse_command(value)
        subprocess.Popen(  # noqa: S603 - arguments are deliberately shell-free
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ActionResult(True, True, f"Launched {arguments[0]}")

    @staticmethod
    def open_target(value: str) -> ActionResult:
        target = validate_open_target(value)
        subprocess.Popen(  # noqa: S603
            ["xdg-open", target],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ActionResult(True, True, "Opened with the default application")

    def run_command(
        self, value: str, working_directory: str, callback: ResultCallback
    ) -> ActionResult:
        arguments = parse_command(value)
        directory = validate_working_directory(working_directory)
        future = self._executor.submit(self._execute, arguments, directory)
        future.add_done_callback(lambda completed: self._complete(completed, callback))
        return ActionResult(True, True, "Command running…")

    def _complete(
        self,
        future: Future[subprocess.CompletedProcess[str]],
        callback: ResultCallback,
    ) -> None:
        if not self._closed:
            callback(self._result(future))

    @staticmethod
    def _execute(arguments: list[str], directory: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            arguments,
            cwd=directory,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    @staticmethod
    def _result(future: Future[subprocess.CompletedProcess[str]]) -> ActionResult:
        try:
            completed = future.result()
        except subprocess.TimeoutExpired:
            return ActionResult(True, False, "Command timed out after 60 seconds")
        except OSError as error:
            return ActionResult(True, False, str(error))
        if completed.returncode == 0:
            return ActionResult(True, True, "Command completed")
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        suffix = f": {detail[-1][:160]}" if detail else ""
        return ActionResult(
            True, False, f"Command exited with status {completed.returncode}{suffix}"
        )

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
