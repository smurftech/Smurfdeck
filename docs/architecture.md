# Architecture

SmurfDeck is split at hardware and framework boundaries so the application can
grow without placing Stream Deck calls throughout the UI.

```text
PySide6 UI
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
the hardware adapter.

## Next milestones

1. Persist profiles and pages with a versioned schema.
2. Add action definitions and bind them to key press/release policies.
3. Connect keyboard/media actions to `UInputEmitter`.
4. Add icon composition, folders/pages, brightness, and tray behavior.
5. Add hot-plug monitoring and multi-device selection.

