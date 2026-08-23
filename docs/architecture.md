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
    └── InputEmitter protocol ── UInputEmitter ── evdev.UInput
             ▲
             └── ActionEngine ── shortcut/media validation + trigger policy
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

## Next milestones

1. Add launch, open-path, command, and page-navigation actions.
2. Add icon composition, drag/drop, brightness, and tray behavior.
3. Add hot-plug monitoring and multi-device selection.
