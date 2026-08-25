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
