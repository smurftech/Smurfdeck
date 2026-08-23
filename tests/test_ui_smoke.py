import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from smurfdeck.devices.base import DeckGeometry, DeckInfo
from smurfdeck.persistence.config_store import ConfigStore
from smurfdeck.ui.main_window import MainWindow


class FakeDevice:
    def __init__(self) -> None:
        self.labels: dict[int, str] = {}
        self.info = DeckInfo("Fake Deck", DeckGeometry(5, 3, 72, 72))

    def render_key_label(self, index: int, label: str) -> None:
        self.labels[index] = label


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
