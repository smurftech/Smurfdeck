from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from smurfdeck.devices.base import DeckKeyEvent
from smurfdeck.devices.streamdeck import StreamDeckDevice


class HardwareEvents(QObject):
    """Move callbacks from the Stream Deck worker thread onto Qt's UI thread."""

    key_changed = Signal(object)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SmurfDeck")
        self.resize(820, 600)
        self._device: StreamDeckDevice | None = None
        self._events = HardwareEvents(self)
        self._events.key_changed.connect(self._on_key_event)

        self._status = QLabel("No device connected")
        self._details = QLabel("Select Detect device to begin.")
        self._details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._key_grid = QGridLayout()
        self._key_labels: list[QLabel] = []
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._detect = QPushButton("Detect device")
        self._render = QPushButton("Render numbered keys")
        self._render.setEnabled(False)
        self._detect.clicked.connect(self.detect_device)
        self._render.clicked.connect(self.render_test_images)

        buttons = QHBoxLayout()
        buttons.addWidget(self._detect)
        buttons.addWidget(self._render)
        buttons.addStretch()
        deck_box = QGroupBox("Connected Stream Deck")
        deck_box.setLayout(self._key_grid)
        layout = QVBoxLayout()
        layout.addWidget(self._status)
        layout.addWidget(self._details)
        layout.addLayout(buttons)
        layout.addWidget(deck_box, 1)
        layout.addWidget(QLabel("Hardware events"))
        layout.addWidget(self._log, 1)
        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

    @Slot()
    def detect_device(self) -> None:
        self._disconnect_device()
        try:
            devices = StreamDeckDevice.discover()
        except Exception as error:
            self._show_detection_error(error)
            return
        if not devices:
            self._status.setText("No available Stream Deck found")
            self._details.setText("Check the USB connection and HID permissions, then retry.")
            return

        self._device = devices[0]
        for extra in devices[1:]:
            extra.close()
        info = self._device.info
        geometry = info.geometry
        self._status.setText(f"Connected: {info.model}")
        self._details.setText(
            f"{geometry.columns} × {geometry.rows} keys ({geometry.key_count} total), "
            f"{geometry.key_width} × {geometry.key_height} px each\n"
            f"Serial: {info.serial or 'unavailable'} · Firmware: "
            f"{info.firmware or 'unavailable'}"
        )
        self._build_key_grid(geometry.columns, geometry.rows)
        self._device.set_event_sink(self._events.key_changed.emit)
        self._render.setEnabled(True)
        self._log.appendPlainText(f"Connected to {info.model}")

    def _build_key_grid(self, columns: int, rows: int) -> None:
        while (item := self._key_grid.takeAt(0)) is not None:
            if item.widget() is not None:
                item.widget().deleteLater()
        self._key_labels.clear()
        for key in range(columns * rows):
            label = QLabel(str(key + 1))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumSize(70, 55)
            label.setStyleSheet(self._key_style("#64748b"))
            self._key_grid.addWidget(label, key // columns, key % columns)
            self._key_labels.append(label)

    @staticmethod
    def _key_style(colour: str) -> str:
        return f"border: 3px solid {colour}; border-radius: 8px; font-size: 20px;"

    @Slot()
    def render_test_images(self) -> None:
        if self._device is None:
            return
        try:
            for key in range(self._device.info.geometry.key_count):
                self._device.render_numbered_key(key, key + 1)
        except Exception as error:
            QMessageBox.warning(self, "Render failed", str(error))
            return
        self._log.appendPlainText("Rendered numbered test images")

    @Slot(object)
    def _on_key_event(self, event: DeckKeyEvent) -> None:
        action = "DOWN" if event.pressed else "UP"
        self._log.appendPlainText(f"Key {event.key + 1}: {action}")
        if event.key < len(self._key_labels):
            colour = "#38bdf8" if event.pressed else "#64748b"
            self._key_labels[event.key].setStyleSheet(self._key_style(colour))

    def _show_detection_error(self, error: Exception) -> None:
        self._status.setText("Device discovery failed")
        self._details.setText(str(error))
        QMessageBox.warning(self, "Stream Deck detection failed", str(error))

    def _disconnect_device(self) -> None:
        if self._device is not None:
            with suppress(Exception):
                self._device.close()
            self._device = None
        self._render.setEnabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._disconnect_device()
        super().closeEvent(event)

