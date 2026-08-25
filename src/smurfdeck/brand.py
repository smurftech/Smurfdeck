"""Smurftech V1 design tokens and desktop presentation."""

from pathlib import Path

ASSET_DIR = Path(__file__).with_name("assets")
APP_ICON_PATH = ASSET_DIR / "smurfdeck-app-icon.svg"

COLORS = {
    "deep_night": "#0C111A",
    "night_slate": "#121826",
    "steel_blue": "#1E2A3A",
    "electric_blue": "#0D6EFD",
    "cyan_accent": "#4FC3FF",
    "ice_blue": "#E6F0FF",
    "clean_white": "#F2F4F7",
}

STYLESHEET = """
QMainWindow { background: #0C111A; }
QWidget { color: #E6F0FF; font: 13px "Inter", "Noto Sans", sans-serif; }
QWidget#workspace { background: #0C111A; }
QWidget#actionPanel { background: #101722; border-right: 1px solid #1E2A3A; }
QWidget#deckCanvas { background: #0C111A; }
QScrollArea#quickScroll, QScrollArea#quickScroll > QWidget > QWidget { background: transparent; }
QWidget#toolbar { background: #121826; border-bottom: 1px solid #1E2A3A; }
QWidget#brandLockup { background: transparent; }
QLabel#productName { font: 800 22px "Orbitron", "Eurostile", sans-serif; }
QLabel#productDescriptor {
    color: #4FC3FF; font: 700 10px "Rajdhani", "Noto Sans", sans-serif;
    letter-spacing: 2px;
}
QLineEdit, QComboBox, QListWidget {
    background: #0C111A; border: 1px solid #33445A;
    border-radius: 6px; padding: 6px; color: #E6F0FF;
}
QLineEdit:focus, QComboBox:focus, QListWidget:focus { border-color: #0D6EFD; }
QComboBox QAbstractItemView {
    background: #121826; color: #E6F0FF; border: 1px solid #33445A;
    selection-background-color: #173A66;
}
QComboBox#primarySelector, QComboBox#secondarySelector {
    background: transparent; border: 0; padding: 1px 4px;
}
QComboBox#primarySelector {
    color: #F2F4F7; font: 700 17px "Rajdhani", "Noto Sans", sans-serif;
}
QComboBox#secondarySelector { color: #8EA1B8; font-size: 13px; }
QSplitter::handle { background: #1E2A3A; width: 1px; }
QLabel#sectionTitle {
    color: #F2F4F7; font: 700 15px "Rajdhani", "Noto Sans", sans-serif;
}
QLabel#mutedText { color: #8EA1B8; }
QLabel#warningText { color: #F0A65B; }
QLabel#deviceStatus {
    background: #0F1723; border: 1px solid #2A394B; border-radius: 10px;
    color: #8EA1B8; font: 600 11px "JetBrains Mono", monospace; padding: 6px 10px;
}
QLabel#deviceStatus[state="connected"] { color: #4FE0B6; border-color: #286B5D; }
QLabel#deviceStatus[state="failure"] { color: #F0A65B; border-color: #7B5434; }
QLabel#actionStatus { font: 600 11px "JetBrains Mono", monospace; }
QLabel#actionStatus[state="running"] { color: #4FC3FF; }
QLabel#actionStatus[state="success"] { color: #4FE0B6; }
QLabel#actionStatus[state="failure"] { color: #F0A65B; }
QStatusBar { background: #121826; border-top: 1px solid #1E2A3A; }
QMenu { background: #121826; border: 1px solid #33445A; padding: 6px; }
QMenu::item { padding: 7px 28px 7px 12px; }
QMenu::item:selected { background: #173A66; color: #F2F4F7; }
QFrame#deckFrame {
    background: #060A10; border: 1px solid #1E2A3A; border-radius: 12px;
}
QFrame#quickEditor {
    background: #121826; border: 1px solid #2A3A4E; border-radius: 8px;
}
QToolButton {
    min-width: 25px; background: #182332; border: 1px solid #33445A;
    border-radius: 6px; padding: 5px; color: #E6F0FF;
}
QToolButton#settingsButton {
    border: 0; background: transparent; font-size: 22px; color: #8EA1B8; padding: 8px;
}
QFrame#deckFrame QToolButton {
    background: #111C2A; border: 2px solid #2B3B50; border-radius: 11px;
    color: #F2F4F7; font-weight: 600; font-size: 14px;
}
QFrame#deckFrame QToolButton[selected="true"] {
    background: #122947; border-color: #0D6EFD;
}
QFrame#deckFrame QToolButton[configured="true"] { background: #13263A; }
QFrame#deckFrame QToolButton[actionState="running"] { border-color: #4FC3FF; }
QFrame#deckFrame QToolButton[actionState="success"] { border-color: #4FE0B6; }
QFrame#deckFrame QToolButton[actionState="failure"] { border-color: #F0A65B; }
QFrame#deckFrame QToolButton[pressed="true"] {
    background: #17446B; border-color: #4FC3FF;
}
QPushButton {
    background: #182332; border: 1px solid #33445A; border-radius: 6px;
    padding: 8px 12px; color: #E6F0FF; font-weight: 600;
}
QPushButton#primaryButton {
    background: #0D6EFD; border-color: #3F9CFF; color: #FFFFFF;
    font: 700 13px "Rajdhani", "Noto Sans", sans-serif;
}
QPushButton#primaryButton:hover { background: #1683FF; }
QPushButton:hover, QToolButton:hover { border-color: #4FC3FF; }
QListWidget::item { padding: 9px; border-radius: 4px; }
QListWidget::item:selected { background: #173A66; color: #4FC3FF; }
"""