import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from smurfdeck.actions.engine import ActionEngine
from smurfdeck.devices.base import DeckGeometry, DeckInfo, DeckKeyEvent
from smurfdeck.models.config import KeyConfig
from smurfdeck.persistence.config_store import ConfigStore
from smurfdeck.ui.main_window import MainWindow


class FakeDevice:
    def __init__(self) -> None:
        self.labels: dict[int, str] = {}
        self.info = DeckInfo("Fake Deck", DeckGeometry(5, 3, 72, 72))

    def render_key_label(self, index: int, label: str) -> None:
        self.labels[index] = label


class FakeEmitter:
    def __init__(self) -> None:
        self.chords: list[tuple[int, ...]] = []

    def send_chord(self, keys: tuple[int, ...]) -> None:
        self.chords.append(keys)

    def close(self) -> None:
        pass


def test_balanced_window_starts_with_persisted_configuration(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(tmp_path / "config.json")
    window = MainWindow(store)
    assert window.config.active_profile.name == "Desktop"
    assert len(window._key_buttons) == 15
    window.close()
    app.processEvents()
    assert store.path.exists()


def test_active_page_is_rendered_to_connected_device(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    device = FakeDevice()
    window._device = device
    page = window.config.active_profile.add_page("Media")
    page.key(0).label = "Play"
    window._refresh_page_combo()
    assert device.labels[0] == "Play"
    assert device.labels[14] == "15"
    window.close()
    app.processEvents()


def test_hardware_event_dispatches_configured_action(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    emitter = FakeEmitter()
    window._action_engine = ActionEngine(emitter)
    window.config.active_profile.active_page.keys[0] = KeyConfig(
        action_type="keyboard", action_value="Ctrl+S"
    )
    window._on_key_event(DeckKeyEvent(0, True))
    window._on_key_event(DeckKeyEvent(0, False))
    assert len(emitter.chords) == 1
    assert window._action_status.text() == "✓ Action sent"
    window.close()
    app.processEvents()


def test_page_action_wraps_and_renders_the_destination(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    device = FakeDevice()
    window._device = device
    first = window.config.active_profile.active_page
    first.key(0).label = "Next"
    second = window.config.active_profile.add_page("Media")
    second.key(0).label = "Play"
    window._refresh_page_combo()
    assert window._navigate_page("next") == "Switched to Page 1"
    assert device.labels[0] == "Next"
    assert window._navigate_page("previous") == "Switched to Media"
    assert device.labels[0] == "Play"
    window.close()
    app.processEvents()


def test_balanced_canvas_preserves_five_by_three_layout_and_scales(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    window.resize(1920, 900)
    window.show()
    app.processEvents()
    assert window._key_grid.getItemPosition(4)[:2] == (0, 4)
    assert window._key_grid.getItemPosition(5)[:2] == (1, 0)
    assert 100 <= window._key_buttons[0].width() <= 150
    assert window._key_buttons[0].width() == window._key_buttons[0].height()
    window.close()
    app.processEvents()


def test_key_preview_and_command_editor_reflect_selected_action(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    window.config.active_profile.active_page.keys[0] = KeyConfig(
        label="Build",
        action_type="command",
        action_value="make test",
        working_directory="/tmp",
    )
    window._refresh_canvas()
    assert window._key_preview.text() == "Build"
    assert window._value_stack.currentWidget().layout() is not None
    assert window._command_edit.text() == "make test"
    assert window._working_directory_edit.text() == "/tmp"
    assert window._key_buttons[0].property("configured") is True
    window.close()
    app.processEvents()


def test_action_library_selects_the_shared_key_editor(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    command_item = next(
        window._action_list.item(row)
        for row in range(window._action_list.count())
        if window._action_list.item(row).text() == "Run command"
    )
    window._on_action_activated(command_item)
    assert window._action_combo.currentData() == "command"
    assert window._value_stack.currentWidget().layout() is not None
    window.close()
    app.processEvents()
