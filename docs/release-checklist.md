# SmurfDeck release checklist

1. Run `uv sync`, `uv run ruff check .`, and `uv run pytest`.
2. Launch from a clean configuration and verify schema migration with a retained backup.
3. Physically verify key rendering, actions, hot-plug reconnection, brightness, and tray mode.
4. Verify command timeout and environment behavior with reviewed test commands.
5. Verify optional application-profile mapping on KDE/Wayland with `kdotool` installed.
6. Build and install the wheel; confirm the KDE launcher uses the SmurfDeck name and icon.
7. Confirm explicit tray Quit closes every device and process cleanly.
8. Review the diff for secrets or machine-specific configuration.
9. Tag the accepted commit as `v0.1.0` and publish release notes.

## Core-review branch acceptance (not yet physically verified)

- Confirm desktop Copy/Cut/Paste and Konsole Copy/Paste on CachyOS/Wayland,
  including the first shortcut after startup. Check customised Plasma bindings.
- Apply a static image and a GIF/WebP. Move the original file, restart, then
  check the preview and physical key. Test 15/32 animated keys for CPU/USB load.
- Test page navigation while a key is held, profile duplication with page links,
  page-local undo/redo and copy/paste across pages.
- Run a copy → delay → paste sequence in a disposable document; cancel a delayed
  sequence, induce an unavailable-app error and confirm later steps stop.
- Test delayed application mapping, device unplug/replug while pressed, device
  selection, brightness, close-to-tray and explicit Quit.
- Keep the schema backup until accepting the release. The previous build needs
  that original configuration restored for rollback.
- Profile export/import, folders, pinned keys and toggle multi-actions are not
  included in this branch. See the review for the remaining scope.
