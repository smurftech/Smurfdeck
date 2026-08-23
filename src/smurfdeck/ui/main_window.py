from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import QObject, QSignalBlocker, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from smurfdeck.devices.base import DeckKeyEvent
from smurfdeck.devices.streamdeck import StreamDeckDevice
from smurfdeck.models.config import AppConfig, KeyConfig, PageConfig, ProfileConfig
from smurfdeck.persistence.config_store import ConfigStore

ACTION_LABELS = {
    "none": "No action",
    "keyboard": "Keyboard shortcut",
    "media": "Media control",
    "launch": "Launch application",
    "open": "Open file or folder",
    "command": "Run command",
    "page": "Switch page",
}


class HardwareEvents(QObject):
    key_changed = Signal(object)


class MainWindow(QMainWindow):
    def __init__(self, store: ConfigStore | None = None) -> None:
        super().__init__()
        self.setWindowTitle("SmurfDeck")
        self.resize(1180, 720)
        self.setMinimumSize(900, 600)
        self._store = store or ConfigStore()
        self._config = self._store.load()
        self._device: StreamDeckDevice | None = None
        self._selected_key = 0
        self._columns, self._rows = 5, 3
        self._key_buttons: list[QToolButton] = []
        self._events = HardwareEvents(self)
        self._events.key_changed.connect(self._on_key_event)

        self._profile_combo, self._page_combo = QComboBox(), QComboBox()
        self._device_status = QLabel("No device connected")
        self._detect_button = QPushButton("Detect device")
        self._detect_button.clicked.connect(self.detect_device)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        self._page_combo.currentIndexChanged.connect(self._on_page_selected)

        self._action_list = QListWidget()
        self._populate_action_library()
        self._action_list.itemDoubleClicked.connect(self._on_action_activated)
        self._key_grid = QGridLayout()
        self._key_grid.setSpacing(10)
        self._canvas_title = QLabel()
        self._canvas_title.setObjectName("canvasTitle")
        self._canvas_hint = QLabel()
        self._canvas_hint.setObjectName("mutedText")

        self._quick_title = QLabel("Key 1")
        self._quick_title.setObjectName("sectionTitle")
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Key label")
        self._action_combo = QComboBox()
        for action_type, action_label in ACTION_LABELS.items():
            self._action_combo.addItem(action_label, action_type)
        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("Action value (configured in Milestone 3)")
        self._apply_key_button = QPushButton("Apply to key")
        self._apply_key_button.clicked.connect(self._apply_key_edits)

        self._inspector_key, self._inspector_action = QLabel(), QLabel()
        self._inspector_value, self._inspector_position = QLabel(), QLabel()
        self._recovery_notice = QLabel()
        self._recovery_notice.setWordWrap(True)
        self._recovery_notice.setObjectName("warningText")

        self._build_window()
        self._apply_style()
        self._refresh_profile_combo()
        self._build_key_grid(self._columns, self._rows)
        self._select_key(0)
        if self._store.recovery_path is not None:
            self._recovery_notice.setText(
                f"Invalid configuration preserved as {self._store.recovery_path.name}. "
                "Safe defaults are active."
            )

    @property
    def config(self) -> AppConfig:
        return self._config

    def _build_window(self) -> None:
        top = QHBoxLayout()
        top.setContentsMargins(14, 10, 14, 10)
        top.addWidget(QLabel("Profile"))
        top.addWidget(self._profile_combo, 1)
        top.addWidget(self._small_button("＋", self._add_profile, "New profile"))
        top.addWidget(self._small_button("✎", self._rename_profile, "Rename profile"))
        top.addWidget(self._small_button("⧉", self._duplicate_profile, "Duplicate profile"))
        top.addWidget(self._small_button("−", self._delete_profile, "Delete profile"))
        top.addSpacing(16)
        top.addWidget(QLabel("Page"))
        top.addWidget(self._page_combo, 1)
        top.addWidget(self._small_button("＋", self._add_page, "New page"))
        top.addWidget(self._small_button("✎", self._rename_page, "Rename page"))
        top.addWidget(self._small_button("←", lambda: self._move_page(-1), "Move page left"))
        top.addWidget(self._small_button("→", lambda: self._move_page(1), "Move page right"))
        top.addWidget(self._small_button("−", self._delete_page, "Delete page"))
        top.addSpacing(18)
        top.addWidget(self._device_status)
        top.addWidget(self._detect_button)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.addWidget(self._heading("Action library"))
        search = QLineEdit()
        search.setPlaceholderText("Find an action…")
        search.textChanged.connect(self._filter_actions)
        left_layout.addWidget(search)
        left_layout.addWidget(self._action_list, 1)
        help_text = QLabel("Double-click an action to assign it to the selected key.")
        help_text.setWordWrap(True)
        help_text.setObjectName("mutedText")
        left_layout.addWidget(help_text)

        canvas = QWidget()
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(22, 16, 22, 18)
        canvas_header = QHBoxLayout()
        canvas_header.addWidget(self._canvas_title)
        canvas_header.addStretch()
        canvas_header.addWidget(self._canvas_hint)
        canvas_layout.addLayout(canvas_header)
        deck_frame = QFrame()
        deck_frame.setObjectName("deckFrame")
        deck_frame.setLayout(self._key_grid)
        deck_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas_layout.addWidget(deck_frame, 1, Qt.AlignmentFlag.AlignCenter)
        quick = QFrame()
        quick.setObjectName("quickEditor")
        quick_layout = QVBoxLayout(quick)
        quick_layout.addWidget(self._quick_title)
        fields = QHBoxLayout()
        fields.addWidget(self._label_edit, 2)
        fields.addWidget(self._action_combo, 2)
        fields.addWidget(self._value_edit, 3)
        fields.addWidget(self._apply_key_button)
        quick_layout.addLayout(fields)
        canvas_layout.addWidget(quick)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(15, 14, 15, 14)
        right_layout.addWidget(self._heading("Selected key"))
        preview = QLabel("S")
        preview.setObjectName("keyPreview")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setFixedSize(76, 76)
        right_layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignHCenter)
        for caption, value in (
            ("KEY", self._inspector_key),
            ("ACTION", self._inspector_action),
            ("VALUE", self._inspector_value),
            ("POSITION", self._inspector_position),
        ):
            right_layout.addWidget(self._caption(caption))
            value.setWordWrap(True)
            value.setObjectName("inspectorValue")
            right_layout.addWidget(value)
        right_layout.addSpacing(12)
        right_layout.addWidget(self._heading("Configuration"))
        config_path = QLabel(str(self._store.path))
        config_path.setWordWrap(True)
        config_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        config_path.setObjectName("mutedText")
        right_layout.addWidget(config_path)
        right_layout.addWidget(self._recovery_notice)
        right_layout.addStretch()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(canvas)
        splitter.addWidget(right)
        splitter.setSizes([225, 680, 245])
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addLayout(top)
        root_layout.addWidget(splitter, 1)
        root = QWidget()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

    @staticmethod
    def _small_button(text: str, callback: object, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("caption")
        return label

    def _populate_action_library(self) -> None:
        for action_type, label in ACTION_LABELS.items():
            if action_type != "none":
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, action_type)
                self._action_list.addItem(item)

    def _filter_actions(self, text: str) -> None:
        query = text.casefold()
        for row in range(self._action_list.count()):
            item = self._action_list.item(row)
            item.setHidden(query not in item.text().casefold())

    def _active_profile(self) -> ProfileConfig:
        return self._config.active_profile

    def _active_page(self) -> PageConfig:
        return self._active_profile().active_page

    def _refresh_profile_combo(self) -> None:
        with QSignalBlocker(self._profile_combo):
            self._profile_combo.clear()
            for profile in self._config.profiles:
                self._profile_combo.addItem(profile.name, profile.id)
            self._profile_combo.setCurrentIndex(
                max(self._profile_combo.findData(self._config.active_profile_id), 0)
            )
        self._refresh_page_combo()

    def _refresh_page_combo(self) -> None:
        profile = self._active_profile()
        with QSignalBlocker(self._page_combo):
            self._page_combo.clear()
            for page in profile.pages:
                self._page_combo.addItem(page.name, page.id)
            self._page_combo.setCurrentIndex(
                max(self._page_combo.findData(profile.active_page_id), 0)
            )
        self._refresh_canvas()

    def _refresh_canvas(self) -> None:
        profile, page = self._active_profile(), self._active_page()
        self._canvas_title.setText(f"{profile.name} · {page.name}")
        self._canvas_hint.setText(f"Page {profile.pages.index(page) + 1} of {len(profile.pages)}")
        for index, button in enumerate(self._key_buttons):
            key = page.keys.get(index, KeyConfig())
            button.setText(key.label.strip() or str(index + 1))
            button.setToolTip(ACTION_LABELS.get(key.action_type, key.action_type))
        if self._key_buttons:
            self._select_key(min(self._selected_key, len(self._key_buttons) - 1))
        self._render_active_page()

    def _build_key_grid(self, columns: int, rows: int) -> None:
        while (item := self._key_grid.takeAt(0)) is not None:
            if item.widget() is not None:
                item.widget().deleteLater()
        self._key_buttons.clear()
        for index in range(columns * rows):
            button = QToolButton()
            button.setMinimumSize(76, 62)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            button.clicked.connect(lambda _checked=False, key=index: self._select_key(key))
            self._key_grid.addWidget(button, index // columns, index % columns)
            self._key_buttons.append(button)
        self._refresh_canvas()

    def _select_key(self, index: int) -> None:
        if not self._key_buttons:
            return
        self._selected_key = index
        key = self._active_page().keys.get(index, KeyConfig())
        for button_index, button in enumerate(self._key_buttons):
            button.setProperty("selected", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
        action_name = ACTION_LABELS.get(key.action_type, "Action")
        self._quick_title.setText(f"Key {index + 1} · {action_name}")
        self._label_edit.setText(key.label)
        self._action_combo.setCurrentIndex(max(self._action_combo.findData(key.action_type), 0))
        self._value_edit.setText(key.action_value)
        self._inspector_key.setText(key.label or f"Key {index + 1}")
        self._inspector_action.setText(ACTION_LABELS.get(key.action_type, key.action_type))
        self._inspector_value.setText(key.action_value or "Not configured")
        row, column = divmod(index, self._columns)
        self._inspector_position.setText(f"Row {row + 1}, column {column + 1} · index {index}")

    @Slot()
    def _apply_key_edits(self) -> None:
        key = self._active_page().key(self._selected_key)
        key.label = self._label_edit.text().strip()
        key.action_type = str(self._action_combo.currentData())
        key.action_value = self._value_edit.text().strip()
        self._save()
        self._refresh_canvas()

    def _on_action_activated(self, item: QListWidgetItem) -> None:
        self._action_combo.setCurrentIndex(
            self._action_combo.findData(item.data(Qt.ItemDataRole.UserRole))
        )
        self._apply_key_edits()

    def _on_profile_selected(self, index: int) -> None:
        if index >= 0:
            self._config.active_profile_id = str(self._profile_combo.itemData(index))
            self._save()
            self._refresh_page_combo()

    def _on_page_selected(self, index: int) -> None:
        if index >= 0:
            self._active_profile().active_page_id = str(self._page_combo.itemData(index))
            self._save()
            self._refresh_canvas()

    def _ask_name(self, title: str, label: str, current: str = "") -> str | None:
        value, accepted = QInputDialog.getText(self, title, label, text=current)
        value = value.strip()
        return value if accepted and value else None

    def _add_profile(self) -> None:
        if name := self._ask_name("New profile", "Profile name:"):
            self._config.add_profile(name)
            self._save()
            self._refresh_profile_combo()

    def _rename_profile(self) -> None:
        profile = self._active_profile()
        if name := self._ask_name("Rename profile", "Profile name:", profile.name):
            profile.name = name
            self._save()
            self._refresh_profile_combo()

    def _duplicate_profile(self) -> None:
        self._config.duplicate_profile(self._config.active_profile_id)
        self._save()
        self._refresh_profile_combo()

    def _delete_profile(self) -> None:
        profile = self._active_profile()
        if len(self._config.profiles) == 1:
            self._show_guardrail("The final profile cannot be deleted.")
        elif QMessageBox.question(
            self, "Delete profile", f"Delete profile ‘{profile.name}’?"
        ) == QMessageBox.StandardButton.Yes:
            self._config.delete_profile(profile.id)
            self._save()
            self._refresh_profile_combo()

    def _add_page(self) -> None:
        self._active_profile().add_page()
        self._save()
        self._refresh_page_combo()

    def _rename_page(self) -> None:
        page = self._active_page()
        if name := self._ask_name("Rename page", "Page name:", page.name):
            page.name = name
            self._save()
            self._refresh_page_combo()

    def _move_page(self, direction: int) -> None:
        profile = self._active_profile()
        current = next(
            i for i, page in enumerate(profile.pages) if page.id == profile.active_page_id
        )
        destination = current + direction
        if 0 <= destination < len(profile.pages):
            profile.pages[current], profile.pages[destination] = (
                profile.pages[destination],
                profile.pages[current],
            )
            self._save()
            self._refresh_page_combo()

    def _delete_page(self) -> None:
        profile, page = self._active_profile(), self._active_page()
        if len(profile.pages) == 1:
            self._show_guardrail("The final page in a profile cannot be deleted.")
        elif QMessageBox.question(
            self, "Delete page", f"Delete page ‘{page.name}’?"
        ) == QMessageBox.StandardButton.Yes:
            profile.delete_page(page.id)
            self._save()
            self._refresh_page_combo()

    def _show_guardrail(self, message: str) -> None:
        QMessageBox.information(self, "SmurfDeck safeguard", message)

    def _save(self) -> None:
        try:
            self._store.save(self._config)
        except OSError as error:
            QMessageBox.warning(self, "Configuration save failed", str(error))

    @Slot()
    def detect_device(self) -> None:
        self._disconnect_device()
        try:
            devices = StreamDeckDevice.discover()
        except Exception as error:
            self._show_detection_error(error)
            return
        if not devices:
            self._device_status.setText("No Stream Deck found")
            return
        self._device = devices[0]
        for extra in devices[1:]:
            extra.close()
        geometry = self._device.info.geometry
        self._columns, self._rows = geometry.columns, geometry.rows
        self._device_status.setText(
            f"● {self._device.info.model} · {geometry.columns}×{geometry.rows}"
        )
        self._build_key_grid(geometry.columns, geometry.rows)
        self._device.set_event_sink(self._events.key_changed.emit)
        self._render_active_page()

    def _render_active_page(self) -> None:
        if self._device is not None:
            for index in range(self._device.info.geometry.key_count):
                if not self._render_key(index):
                    break

    def _render_key(self, index: int) -> bool:
        if self._device is None or index >= self._device.info.geometry.key_count:
            return False
        key = self._active_page().keys.get(index, KeyConfig())
        try:
            self._device.render_key_label(index, key.label.strip() or str(index + 1))
        except Exception as error:
            self._show_detection_error(error)
            return False
        return True

    @Slot(object)
    def _on_key_event(self, event: DeckKeyEvent) -> None:
        if event.key < len(self._key_buttons):
            button = self._key_buttons[event.key]
            button.setProperty("pressed", event.pressed)
            button.style().unpolish(button)
            button.style().polish(button)
            if event.pressed:
                self._select_key(event.key)

    def _show_detection_error(self, error: Exception) -> None:
        self._device_status.setText("Device error")
        QMessageBox.warning(self, "Stream Deck error", str(error))

    def _disconnect_device(self) -> None:
        if self._device is not None:
            with suppress(Exception):
                self._device.close()
            self._device = None
        self._device_status.setText("No device connected")

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #0f1621; }
            QWidget { color: #e7edf8; font-size: 13px; }
            QLineEdit, QComboBox, QListWidget {
                background: #0e1622; border: 1px solid #354257;
                border-radius: 5px; padding: 5px; color: #e7edf8;
            }
            QComboBox QAbstractItemView {
                background: #151e2b; color: #e7edf8;
                selection-background-color: #17384a;
            }
            QSplitter::handle { background: #2c384a; width: 1px; }
            QLabel#canvasTitle { font-size: 18px; font-weight: 700; }
            QLabel#sectionTitle { font-size: 14px; font-weight: 700; }
            QLabel#caption { color: #91a1b7; font-size: 10px; font-weight: 700; margin-top: 8px; }
            QLabel#mutedText { color: #91a1b7; }
            QLabel#warningText { color: #f0a65b; }
            QLabel#inspectorValue {
                background: #0e1622; border: 1px solid #354257;
                border-radius: 5px; padding: 8px;
            }
            QLabel#keyPreview {
                background: #0b1724; border: 2px solid #2db7e2;
                border-radius: 10px; color: #74daf7;
                font-size: 28px; font-weight: 700;
            }
            QFrame#deckFrame {
                background: #05090f; border-radius: 14px;
                padding: 14px; max-width: 570px;
            }
            QFrame#quickEditor {
                background: #162131; border: 1px solid #3a485d;
                border-radius: 8px;
            }
            QToolButton {
                min-width: 25px; background: #182332;
                border: 1px solid #3a485d; border-radius: 4px;
                padding: 5px; color: #e7edf8;
            }
            QFrame#deckFrame QToolButton {
                background: #101c2a; border: 2px solid #2b3b50;
                border-radius: 9px; color: #eef8ff; font-weight: 600;
            }
            QFrame#deckFrame QToolButton[selected="true"] { border-color: #31bfea; }
            QFrame#deckFrame QToolButton[pressed="true"] {
                background: #17425a; border-color: #75ddf8;
            }
            QPushButton {
                background: #182332; border: 1px solid #3a485d;
                border-radius: 5px; padding: 7px 11px; color: #e7edf8;
            }
            QPushButton:hover, QToolButton:hover { border-color: #31bfea; }
            QListWidget::item { padding: 9px; }
            QListWidget::item:selected { background: #17384a; color: #80d4f1; }
            """
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save()
        self._disconnect_device()
        super().closeEvent(event)
