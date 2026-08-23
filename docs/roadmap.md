# SmurfDeck roadmap

## Completed and physically verified

- Stream Deck discovery, geometry, rendering, and key state callbacks.
- Balanced editor foundation with persistent profiles, pages, and key labels.
- Versioned, atomic configuration persistence with safe recovery.
- Keyboard shortcuts with press/release trigger policies.
- Media controls for playback, track navigation, volume, and mute.
- Wayland-safe event injection through lazy UInput access.
- Launch applications.
- Open files, folders, and URLs.
- Run commands with explicit working directories and safe process handling.
- Navigate to the next, previous, or a specific page from a key.
- Show running, success, exit-code, and timeout feedback in the inspector.

## Next action refinements

- Show richer running, success, and failure feedback directly on physical and
  on-screen keys.
- Add configurable command timeouts and optional environment variables.

## Editor and visual fidelity

- Bring the implementation into close visual alignment with the approved
  **Balanced** concept rather than treating the current functional shell as the
  finished interface.
- Make the three-pane proportions responsive across normal, ultrawide, and
  high-DPI KDE displays; avoid an undersized deck surrounded by unused space.
- Establish deliberate minimum, preferred, and maximum widths for the action
  library, central canvas, and inspector.
- Scale the on-screen deck and keys with the available canvas while preserving
  the physical model's aspect ratio and geometry.
- Refine top-bar hierarchy, spacing, typography, icons, button affordances, and
  selected/pressed/action-result states to match the approved mockup.
- Improve the quick editor and inspector so action-specific controls appear
  cleanly without stretching into sparse ultrawide rows.

The items above are implemented on the Milestone 4 branch and await physical
KDE/Wayland visual acceptance.

The physical keymap is anchored above a same-width, vertically scrollable key
editor; the keymap itself never scrolls. Selecting an action-library item drives
that shared editor directly so future action types follow the same interaction.

## Later editor enhancements

- Add drag and drop from the action library, key-to-key movement, and undo/redo.
- Add key icon, label, colour, and background editing with live device preview.

## Desktop integration

- Device hot-plug and automatic reconnection.
- System tray operation and background mode.
- Brightness control and restoration.
- Multi-device selection.
- Optional application-aware profile switching.
