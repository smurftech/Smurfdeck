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
        self.connected = True
        self.brightness = 0
        self.closed = False

    def render_key_label(self, index: int, label: str) -> None:
        self.labels[index] = label

    def set_event_sink(self, _sink: object) -> None:
        pass

    def set_brightness(self, percent: int) -> None:
        self.brightness = percent

    def close(self) -> None:
        self.closed = True


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


def test_command_editor_reflects_selected_action(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    window.config.active_profile.active_page.keys[0] = KeyConfig(
        label="Build",
        action_type="command",
        action_value="make test",
        working_directory="/tmp",
    )
    window._refresh_canvas()
    assert window._value_stack.currentWidget().layout() is not None
    assert window._command_edit.text() == "make test"
    assert window._working_directory_edit.text() == "/tmp"
    assert window._key_buttons[0].property("configured") is True
    window.close()
    app.processEvents()


def test_simple_header_uses_settings_menu_and_no_duplicate_inspector(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    assert window._profile_combo.objectName() == "primarySelector"
    assert window._page_combo.objectName() == "secondarySelector"
    assert len(window._settings_menu.actions()) >= 10
    assert not hasattr(window, "_inspector_key")
    assert window._action_status.parentWidget() is window.statusBar()
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


def test_phase_three_branding_is_applied(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    product_name = window.findChild(type(window._device_status), "productName")
    descriptor = window.findChild(type(window._device_status), "productDescriptor")
    assert product_name is not None and "Smurf" in product_name.text()
    assert descriptor is not None and descriptor.text() == "// CONTROL SYSTEM"
    assert window._apply_key_button.objectName() == "primaryButton"
    assert "#0D6EFD" in window.styleSheet()
    assert window._device_status.property("state") == "disconnected"
    window.close()
    app.processEvents()


def test_visual_key_editor_supports_copy_undo_and_redo(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    source = window.config.active_profile.active_page.key(0)
    source.label = "Music"
    source.icon = "VOL"
    source.background_color = "#0D6EFD"
    window._drop_key(0, 1, True)
    assert window.config.active_profile.active_page.key(1).icon == "VOL"
    window._undo()
    assert window.config.active_profile.active_page.key(1).icon == ""
    window._redo()
    assert window.config.active_profile.active_page.key(1).label == "Music"
    window.close()
    app.processEvents()


def test_action_drop_assigns_action_and_can_be_undone(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    window._drop_action(2, "Media control")
    assert window.config.active_profile.active_page.key(2).action_type == "media"
    window._undo()
    assert window.config.active_profile.active_page.keys.get(2) is None
    window.close()
    app.processEvents()


def test_three_row_key_editor_does_not_need_a_scrollbar(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(ConfigStore(tmp_path / "config.json"))
    window.resize(900, 600)
    window.show()
    app.processEvents()
    assert window._quick_scroll.height() >= 200
    assert window._quick_scroll.verticalScrollBar().maximum() == 0
    window.close()
    app.processEvents()


def test_device_preference_brightness_and_selection_are_restored(
    tmp_path, monkeypatch
) -> None:
    app = QApplication.instance() or QApplication([])
    store = ConfigStore(tmp_path / "config.json")
    config = store.load()
    config.preferred_device_serial = "SECOND"
    config.brightness = 50
    store.save(config)
    first, second = FakeDevice(), FakeDevice()
    first.info = DeckInfo("First", DeckGeometry(5, 3, 72, 72), serial="FIRST")
    second.info = DeckInfo("Second", DeckGeometry(5, 3, 72, 72), serial="SECOND")
    window = MainWindow(store)
    window._monitor_timer.stop()
    monkeypatch.setattr(
        "smurfdeck.ui.main_window.StreamDeckDevice.discover",
        lambda: [first, second],
    )
    window.detect_device()
    assert window._device is second
    assert window._device_combo.currentData() == "SECOND"
    assert second.brightness == 50
    window._quit_requested = True
    window.close()
    app.processEvents()
    assert first.closed and second.closed
