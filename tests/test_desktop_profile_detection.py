from subprocess import CompletedProcess, TimeoutExpired

import smurfdeck.desktop as desktop


def test_active_application_uses_kdotool_and_normalizes(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: "/usr/bin/kdotool")
    monkeypatch.setattr(
        desktop.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, "Org.KDE.Konsole\n", ""),
    )
    assert desktop.active_application() == "org.kde.konsole"


def test_active_application_is_optional_and_fail_safe(monkeypatch) -> None:
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: None)
    assert desktop.active_application() is None
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: "/usr/bin/kdotool")
    monkeypatch.setattr(
        desktop.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutExpired("kdotool", 1)),
    )
    assert desktop.active_application() is None
