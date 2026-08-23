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

## Next milestones

1. Add executable action definitions and key press/release policies.
2. Connect keyboard/media actions to `UInputEmitter`.
3. Add launch, open-path, command, and page-navigation actions.
4. Add icon composition, drag/drop, brightness, and tray behavior.
5. Add hot-plug monitoring and multi-device selection.
