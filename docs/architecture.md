# Architecture

SmurfDeck is split at hardware and framework boundaries so the application can
grow without placing Stream Deck calls throughout the UI.

```text
PySide6 UI
    │
    ├── AppConfig ── ProfileConfig ── PageConfig ── KeyConfig
    │        │
    │        └── ConfigStore ── versioned atomic JSON persistence
    │
    ├── DeckDevice protocol ── StreamDeckDevice ── python-elgato-streamdeck
    │                                  │
    │                                  └── Pillow/PILHelper key rendering
    │
    └── ActionEngine ─┬─ InputEmitter ── UInputEmitter ── evdev.UInput
                     ├─ DesktopActionRunner ── safe subprocess/xdg-open
                     └─ page navigator ── persisted UI + device refresh
```

The Stream Deck library invokes key callbacks from its reader thread. The
adapter converts those callbacks to immutable `DeckKeyEvent` values, and the UI
forwards them through a Qt signal before touching widgets.

The application owns every opened device and closes it on replacement or
shutdown. Discovery currently selects the first usable device and closes any
additional devices; a later selector can replace that policy without changing
the hardware adapter. Selecting a profile or page refreshes both the on-screen
canvas and the physical key labels.

Configuration objects are independent of Qt and hardware. `ConfigStore` writes
schema-versioned JSON with `fsync` followed by atomic replacement. Invalid input
is copied aside before defaults are loaded, so recovery never destroys the
original evidence.

`ActionEngine` receives normalized key state changes after Qt has moved the
hardware callback onto the UI thread. It suppresses duplicate states, applies
the configured press/release policy, validates the typed action value, and then
emits Linux input codes. `LazyUInputEmitter` does not open `/dev/uinput` until a
configured keyboard or media action actually executes.

Desktop processes are launched without a shell. Short commands run in a bounded
worker pool, use an explicit validated working directory, and return completion
feedback to the Qt thread through a signal. Applications and desktop-open
requests detach immediately so SmurfDeck never waits for their windows to close.

## Next milestones

1. Complete the responsive visual-fidelity pass for the approved Balanced UI.
2. Add icon composition, drag/drop, brightness, and tray behavior.
3. Add hot-plug monitoring and multi-device selection.

The maintained backlog and acceptance status live in
[`roadmap.md`](roadmap.md).
