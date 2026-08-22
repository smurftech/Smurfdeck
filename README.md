# SmurfDeck

SmurfDeck is a personal-use-first Stream Deck desktop application for CachyOS,
KDE Plasma, and Wayland. It is written in Python with PySide6 and keeps hardware,
rendering, input, and UI concerns separate so it can grow without becoming tied
to one device model.

The first milestone discovers a connected Stream Deck, shows its model and key
geometry, draws numbered test cards on every key, and reports key-down/key-up
events in the desktop UI.

## Setup

Install `uv`, then run:

```bash
uv sync
uv run smurfdeck
```

Development checks:

```bash
uv run ruff check .
uv run pytest
```

On Arch/CachyOS, the logged-in user must have permission to open the Stream Deck
HID device. Install an appropriate udev rule from the
`python-elgato-streamdeck` documentation or your distribution package, reload
the rules, and reconnect the device. Do not run the desktop application as root.
The hardware library also needs a HIDAPI backend; on CachyOS install the
`hidapi` package if discovery reports that no functional backend was found.

Keyboard/media output is intentionally not connected to actions in this first
milestone. That layer will use `evdev.UInput`; `/dev/uinput` access should also
be granted with a narrowly scoped system rule rather than root execution.
The `evdev-binary` distribution supplies the standard `evdev` Python package
without requiring kernel headers during installation.

## Layout

```text
src/smurfdeck/
  app.py                 application entry point
  devices/base.py        hardware-neutral device contract
  devices/streamdeck.py  python-elgato-streamdeck adapter
  rendering/keys.py      Pillow key artwork
  ui/main_window.py      initial PySide6 desktop shell
  input/uinput.py        Wayland-safe input emitter
tests/                   dependency-light unit tests
```

See [`docs/architecture.md`](docs/architecture.md) for component boundaries and
the next milestones.

## Git workflow

Use `main` as the always-runnable branch and short-lived branches such as
`feature/profile-pages`. Keep commits focused and run lint/tests before merging.
Dependencies are declared in `pyproject.toml`; commit `uv.lock` so personal
installations remain reproducible.

The Stream Deck library is temporarily pinned to an exact upstream Git revision
because upstream 0.10.0 has not yet been published to PyPI. This retains the
newer device support without tracking a moving branch.

SmurfDeck contains original application code and uses third-party libraries only
through their published APIs. It is licensed under the MIT License.
