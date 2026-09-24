"""Curated, editable defaults; application shortcuts target the focused window."""

from dataclasses import dataclass

from smurfdeck.models.config import KeyConfig


@dataclass(frozen=True, slots=True)
class ShortcutPreset:
    id: str
    name: str
    category: str
    shortcut: str

    @property
    def title(self) -> str:
        return f"{self.name} · {self.category}"

    @property
    def description(self) -> str:
        context = (
            "Global KDE shortcut"
            if self.category == "Plasma"
            else (
                "Focus a desktop application before pressing this key"
                if self.category == "Desktop"
                else f"Focus {self.category} before pressing this key"
            )
        )
        return f"{self.shortcut} — {context}. Custom key bindings may differ."

    def key_config(self) -> KeyConfig:
        label = f"{self.name}\nTerminal" if self.category == "Konsole" else self.name
        return KeyConfig(label=label, action_type="keyboard", action_value=self.shortcut)


# Sources and scope are recorded in docs/shortcuts.md. These are useful defaults,
# not a measured popularity ranking. IDs remain stable when display names change.
_DATA = {
    "Desktop": (
        ("copy", "Copy", "Ctrl+C"),
        ("cut", "Cut", "Ctrl+X"),
        ("paste", "Paste", "Ctrl+V"),
        ("select_all", "Select all", "Ctrl+A"),
        ("undo", "Undo", "Ctrl+Z"),
        ("redo", "Redo", "Ctrl+Shift+Z"),
        ("new", "New document", "Ctrl+N"),
        ("save", "Save", "Ctrl+S"),
        ("print", "Print", "Ctrl+P"),
        ("find", "Find", "Ctrl+F"),
        ("close", "Close tab", "Ctrl+W"),
        ("refresh", "Refresh", "F5"),
        ("help", "Help", "F1"),
        ("quit", "Quit app", "Ctrl+Q"),
    ),
    "Dolphin": (
        ("location", "Location", "Ctrl+L"),
        ("back", "Back", "Alt+Left"),
        ("forward", "Forward", "Alt+Right"),
        ("up", "Parent folder", "Alt+Up"),
        ("home", "Home folder", "Alt+Home"),
        ("rename", "Rename", "F2"),
        ("trash", "Move to trash", "Delete"),
        ("properties", "Properties", "Alt+Enter"),
        ("new_tab", "New tab", "Ctrl+T"),
        ("reopen", "Reopen tab", "Ctrl+Shift+T"),
        ("split", "Split view", "F3"),
        ("hidden", "Hidden files", "Ctrl+H"),
        ("terminal", "Terminal panel", "F4"),
        ("open_terminal", "Open terminal", "Shift+F4"),
        ("filter", "Filter files", "Ctrl+I"),
        ("duplicate", "Duplicate files", "Ctrl+D"),
    ),
    "Konsole": (
        ("copy", "Copy", "Ctrl+Shift+C"),
        ("paste", "Paste", "Ctrl+Shift+V"),
        ("new_tab", "New tab", "Ctrl+Shift+T"),
        ("new_window", "New window", "Ctrl+Shift+N"),
        ("close", "Close session", "Ctrl+Shift+W"),
        ("find", "Find", "Ctrl+Shift+F"),
        ("next_tab", "Next tab", "Shift+Right"),
        ("previous_tab", "Previous tab", "Shift+Left"),
        ("save_output", "Save output", "Ctrl+Shift+S"),
        ("menu", "Menu bar", "Ctrl+Shift+M"),
        ("font_reset", "Reset font", "Ctrl+0"),
        ("fullscreen", "Full screen", "F11"),
    ),
    "Plasma": (
        ("launcher", "App launcher", "Meta"),
        ("run", "Run / search", "Alt+Space"),
        ("next_window", "Next window", "Alt+Tab"),
        ("previous_window", "Previous window", "Alt+Shift+Tab"),
        ("close", "Close window", "Alt+F4"),
        ("menu", "Window menu", "Alt+F3"),
        ("desktop", "Show desktop", "Ctrl+F12"),
        ("lock", "Lock screen", "Ctrl+Alt+L"),
    ),
}
SHORTCUT_PRESETS = tuple(
    ShortcutPreset(f"{category.lower()}.{identifier}", name, category, shortcut)
    for category, entries in _DATA.items()
    for identifier, name, shortcut in entries
)
PRESETS_BY_ID = {preset.id: preset for preset in SHORTCUT_PRESETS}
