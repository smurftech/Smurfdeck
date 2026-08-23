import subprocess
from threading import Event

import pytest

from smurfdeck.actions.desktop import (
    DesktopActionRunner,
    parse_command,
    validate_open_target,
    validate_working_directory,
)


def test_command_parser_preserves_arguments_without_a_shell() -> None:
    assert parse_command('printf "%s %s" hello world') == [
        "printf",
        "%s %s",
        "hello",
        "world",
    ]
    with pytest.raises(ValueError, match="Enter an application"):
        parse_command("   ")


def test_open_target_accepts_urls_and_existing_paths(tmp_path) -> None:
    assert validate_open_target("https://example.com") == "https://example.com"
    assert validate_open_target(str(tmp_path)) == str(tmp_path.resolve())
    with pytest.raises(ValueError, match="does not exist"):
        validate_open_target(str(tmp_path / "missing"))


def test_working_directory_must_exist(tmp_path) -> None:
    assert validate_working_directory(str(tmp_path)) == str(tmp_path.resolve())
    with pytest.raises(ValueError, match="does not exist"):
        validate_working_directory(str(tmp_path / "missing"))


def test_completed_command_reports_success_and_failure() -> None:
    successful = subprocess.CompletedProcess(["true"], 0, "", "")
    failed = subprocess.CompletedProcess(["false"], 7, "", "last error\n")

    class Finished:
        def __init__(self, value):
            self.value = value

        def result(self):
            return self.value

    assert DesktopActionRunner._result(Finished(successful)).success
    result = DesktopActionRunner._result(Finished(failed))
    assert not result.success
    assert "status 7: last error" in result.message


def test_command_runs_asynchronously_and_reports_completion(tmp_path) -> None:
    runner = DesktopActionRunner()
    finished = Event()
    results = []
    started = runner.run_command(
        "true", str(tmp_path), lambda result: (results.append(result), finished.set())
    )
    assert started.success and "running" in started.message
    assert finished.wait(2)
    assert results[0].success and results[0].message == "Command completed"
    runner.close()
