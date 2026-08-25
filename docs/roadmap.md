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
- Show running, success, exit-code, and timeout feedback in the status bar.

## Action refinements — completed

- Show richer running, success, and failure feedback directly on physical and
  on-screen keys.
- Add configurable command timeouts and optional environment variables.

Direct physical/on-screen feedback shipped in Phase 4; advanced command options
ship in Phase 6.

## Editor and visual fidelity — completed and physically verified

- Bring the implementation into close visual alignment with the approved
  **Balanced** concept rather than treating the current functional shell as the
  finished interface.
- Make the two-pane proportions responsive across normal, ultrawide, and
  high-DPI KDE displays; avoid an undersized deck surrounded by unused space.
- Establish deliberate widths for the action library and central canvas.
- Scale the on-screen deck and keys with the available canvas while preserving
  the physical model's aspect ratio and geometry.
- Refine top-bar hierarchy, spacing, typography, icons, button affordances, and
  selected/pressed/action-result states to match the approved mockup.
- Keep action-specific controls compact below the keymap without stretching
  into sparse ultrawide rows.

The items above were physically accepted on KDE/Wayland in Milestone 4.

The physical keymap is anchored above a same-width, vertically scrollable key
editor; the keymap itself never scrolls. Selecting an action-library item drives
that shared editor directly so future action types follow the same interaction.
Profile and page selection use a compact two-level header; management operations
and device detection live in its settings menu. The duplicate inspector pane was
removed, with its useful runtime feedback retained in the status bar.

## Phase 4 visual key editor

- Drag actions from the library onto keys.
- Move or copy key configurations with drag and drop.
- Undo and redo key edits and drag/drop changes.
- Configure portable technical icon presets, foreground colours, and backgrounds.
- Preview key visuals on screen and on the connected device.
- Show running, success, and failure feedback directly on physical and on-screen keys.

## Phase 5 desktop integration

- Device hot-plug monitoring and automatic reconnection.
- System tray operation, notifications, and background mode.
- Persisted brightness control and restoration.
- Multi-device discovery, selection, and preferred-device restoration.
- Safe explicit-quit cleanup for every opened device.

## Phase 6 automation and release readiness

- Configurable command timeouts and shell-free environment variables.
- Optional KDE/Wayland application-aware profile switching.
- Profile mapping, global enable/disable control, notifications, and stale-rule recovery.
- Linux application-menu launcher and canonical installed icon.
- Configuration schema 6 migration and final release documentation.

The original phased implementation roadmap is complete after physical acceptance
of Phase 6. Further work should use normal feature releases and issue-driven milestones.
