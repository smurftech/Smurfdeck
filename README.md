# SmurfDeck

SmurfDeck is a personal-use-first Stream Deck desktop application for CachyOS,
KDE Plasma, and Wayland. It is written in Python with PySide6 and keeps hardware,
rendering, input, and UI concerns separate so it can grow without becoming tied
to one device model.

SmurfDeck discovers a connected Stream Deck, presents the Balanced two-pane
editor, manages profiles and pages, assigns actions and labels to keys,
updates the physical device when pages change, and reports key-down/key-up state
in the desktop UI.

The editor keeps a deliberate action-library width while the central deck scales
responsively across normal and ultrawide displays. Its key grid always preserves
the connected device's physical rows and columns. Key configuration lives below
the deck, while runtime feedback appears in a compact status bar.

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

Keyboard and media actions use `evdev.UInput`; `/dev/uinput` access should be
granted with a narrowly scoped system rule rather than root execution.
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
  actions/desktop.py     safe desktop and asynchronous command runner
tests/                   dependency-light unit tests
```

See [`docs/architecture.md`](docs/architecture.md) for component boundaries and
[`docs/roadmap.md`](docs/roadmap.md) for the accepted feature backlog, including
the planned Balanced-interface fidelity pass.

## Configuration

Profiles, pages, active selections, and key drafts are saved automatically to
`$XDG_CONFIG_HOME/smurfdeck/config.json` (normally
`~/.config/smurfdeck/config.json`). Saves use an atomic replacement so a partial
write cannot corrupt the active file. If the file is invalid or uses an unknown
schema, SmurfDeck preserves a timestamped copy and starts with safe defaults.

The editor protects the final profile and the final page in each profile from
deletion. Configuration schema 3 adds command working directories while
transparently migrating schema 1 and 2 files.

## Input actions

Keyboard shortcuts accept readable combinations such as `Ctrl+S`,
`Ctrl+Shift+S`, `Alt+F4`, or `Meta+Left`. Supported modifiers are Ctrl, Shift,
Alt, and Meta/Super; letters, digits, F1–F12, navigation keys, Enter, Space,
Tab, Escape, Backspace, Delete, and common punctuation are supported.

Media actions provide fixed choices for play/pause, previous track, next track,
volume up, volume down, and mute. Every input action can execute on key press,
key release, or both. SmurfDeck opens `/dev/uinput` lazily when the first action
runs, and reports execution or permission errors in the status bar.

## Desktop and navigation actions

Application actions accept a program plus optional arguments. Open actions send
an existing file/folder or an `http`, `https`, `mailto`, or `file` URL to KDE's
default application. Command actions require an explicit working folder, run in
the background with a 60-second limit, and report running, completed, exit-code,
or timeout status without freezing the editor.

Commands and application launches are parsed as argument lists and never passed
through a command shell. Shell operators such as pipes, redirects, variable
expansion, and command substitution therefore do not run implicitly. Put
multi-step behavior in a reviewed script and configure SmurfDeck to launch that
script directly.

Page actions can move to the next or previous page (wrapping at either end), or
jump to a named page in the current profile. The desktop canvas and connected
Stream Deck are refreshed together.

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
