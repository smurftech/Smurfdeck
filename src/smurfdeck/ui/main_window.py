from __future__ import annotations

from contextlib import suppress
from copy import deepcopy

from PySide6.QtCore import QObject, QSignalBlocker, QSize, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from smurfdeck.actions.desktop import (
    DesktopActionRunner,
    parse_command,
    validate_open_target,
    validate_working_directory,
)
from smurfdeck.actions.engine import ActionEngine
from smurfdeck.actions.shortcuts import (
    MEDIA_ACTIONS,
    media_key,
    parse_shortcut,
    supported_key_codes,
)
from smurfdeck.brand import STYLESHEET
from smurfdeck.devices.base import DeckKeyEvent
from smurfdeck.devices.streamdeck import StreamDeckDevice
from smurfdeck.input.uinput import LazyUInputEmitter
from smurfdeck.models.config import AppConfig, KeyConfig, PageConfig, ProfileConfig
from smurfdeck.persistence.config_store import ConfigStore
from smurfdeck.ui.key_button import ActionListWidget, KeyButton

ACTION_LABELS = {
    "none": "No action",
    "keyboard": "Keyboard shortcut",
    "media": "Media control",
    "launch": "Launch application",
    "open": "Open file or folder",
    "command": "Run command",
    "page": "Switch page",
}
ICON_PRESETS = (
    ("No icon", ""),
    ("Run", "RUN"),
    ("Keys", "KEY"),
    ("Media", "VOL"),
    ("App", "APP"),
    ("Page", "PAGE"),
)
COLOR_PRESETS = (
    ("Deep Night", "#0C111A"),
    ("Night Slate", "#121826"),
    ("Steel Blue", "#1E2A3A"),
    ("Electric Blue", "#0D6EFD"),
    ("Cyan Accent", "#4FC3FF"),
    ("Ice Blue", "#E6F0FF"),
    ("Clean White", "#F2F4F7"),
)


class HardwareEvents(QObject):
    key_changed = Signal(object)
    action_finished = Signal(int, object)


class ResponsiveDeckCanvas(QWidget):
    """Centre and scale a physical-layout deck without distorting its keys."""

    surface_width_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("deckCanvas")
        self._columns, self._rows = 5, 3
        self._buttons: list[QToolButton] = []
        self._surface_width = 0
        self.frame = QFrame(self)
        self.frame.setObjectName("deckFrame")
        self.grid = QGridLayout(self.frame)
        self.grid.setContentsMargins(18, 18, 18, 18)
        self.grid.setSpacing(12)
        self.setMinimumHeight(300)
        self.setMaximumHeight(480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def sizeHint(self) -> QSize:
        return QSize(800, 460)

    def configure(
        self, columns: int, rows: int, buttons: list[QToolButton]
    ) -> None:
        self._columns, self._rows = columns, rows
        self._buttons = buttons
        self._reflow()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        if not self._buttons or self.width() <= 0 or self.height() <= 0:
            return
        margin, gap = 18, 12
        usable_width = min(max(self.width() - 48, 0), 1050)
        usable_height = min(max(self.height() - 36, 0), 650)
        key_size = int(
            min(
                (usable_width - 2 * margin - gap * (self._columns - 1)) / self._columns,
                (usable_height - 2 * margin - gap * (self._rows - 1)) / self._rows,
                150,
            )
        )
        key_size = max(key_size, 58)
        frame_width = 2 * margin + self._columns * key_size + gap * (self._columns - 1)
        frame_height = 2 * margin + self._rows * key_size + gap * (self._rows - 1)
        self.frame.setGeometry(
            (self.width() - frame_width) // 2,
            10,
            frame_width,
            frame_height,
        )
        if frame_width != self._surface_width:
            self._surface_width = frame_width
            self.surface_width_changed.emit(frame_width)
        for button in self._buttons:
            button.setFixedSize(key_size, key_size)


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
        self._undo_stack: list[dict[int, KeyConfig]] = []
        self._redo_stack: list[dict[int, KeyConfig]] = []
        self._events = HardwareEvents(self)
        self._events.key_changed.connect(self._on_key_event)
        self._events.action_finished.connect(self._on_action_finished)
        self._action_engine = ActionEngine(
            LazyUInputEmitter(supported_key_codes()),
            DesktopActionRunner(),
            self._navigate_page,
            self._events.action_finished.emit,
        )

        self._profile_combo, self._page_combo = QComboBox(), QComboBox()
        self._profile_combo.setObjectName("primarySelector")
        self._page_combo.setObjectName("secondarySelector")
        self._profile_combo.setMinimumWidth(170)
        self._page_combo.setMinimumWidth(170)
        self._profile_combo.setMaximumWidth(260)
        self._page_combo.setMaximumWidth(260)
        self._device_status = QLabel("No device connected")
        self._device_status.setObjectName("deviceStatus")
        self._device_status.setProperty("state", "disconnected")
        self._profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        self._page_combo.currentIndexChanged.connect(self._on_page_selected)

        self._action_list = ActionListWidget()
        self._action_list.setDragEnabled(True)
        self._populate_action_library()
        self._action_list.itemClicked.connect(self._on_action_activated)
        self._deck_canvas = ResponsiveDeckCanvas()
        self._key_grid = self._deck_canvas.grid
        self._quick_title = QLabel("Key 1")
        self._quick_title.setObjectName("sectionTitle")
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Key label")
        self._action_combo = QComboBox()
        for action_type, action_label in ACTION_LABELS.items():
            self._action_combo.addItem(action_label, action_type)
        self._action_combo.currentIndexChanged.connect(self._update_action_editor)
        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("Action value")
        self._command_edit = QLineEdit()
        self._command_edit.setPlaceholderText("Command and arguments (no shell syntax)")
        self._media_combo = QComboBox()
        for media_id, (media_label, _code) in MEDIA_ACTIONS.items():
            self._media_combo.addItem(media_label, media_id)
        self._page_action_combo = QComboBox()
        self._working_directory_edit = QLineEdit()
        self._working_directory_edit.setPlaceholderText("Working folder (required)")
        self._trigger_combo = QComboBox()
        self._trigger_combo.addItem("On key press", "press")
        self._trigger_combo.addItem("On key release", "release")
        self._trigger_combo.addItem("On press and release", "both")
        self._icon_combo = QComboBox()
        self._background_combo = QComboBox()
        self._foreground_combo = QComboBox()
        for label, value in ICON_PRESETS:
            self._icon_combo.addItem(label, value)
        for label, value in COLOR_PRESETS:
            self._background_combo.addItem(f"Background · {label}", value)
            self._foreground_combo.addItem(f"Text · {label}", value)
        self._undo_button = QPushButton("Undo")
        self._redo_button = QPushButton("Redo")
        self._undo_button.clicked.connect(self._undo)
        self._redo_button.clicked.connect(self._redo)
        self._apply_key_button = QPushButton("Apply to key")
        self._apply_key_button.setObjectName("primaryButton")
        self._apply_key_button.clicked.connect(self._apply_key_edits)

        self._action_status = QLabel("Ready")
        self._action_status.setObjectName("actionStatus")
        self._action_status.setProperty("state", "idle")

        self._build_window()
        self._apply_style()
        self._refresh_profile_combo()
        self._build_key_grid(self._columns, self._rows)
        self._select_key(0)
        if self._store.recovery_path is not None:
            self._action_status.setText(
                f"Invalid configuration preserved as {self._store.recovery_path.name}. "
                "Safe defaults are active."
            )

    @property
    def config(self) -> AppConfig:
        return self._config

    def _build_window(self) -> None:
        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 12)
        brand = QWidget()
        brand.setObjectName("brandLockup")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 20, 0)
        brand_layout.setSpacing(0)
        product_name = QLabel(
            '<span style="color:#F2F4F7">Smurf</span>'
            '<span style="color:#0D6EFD">Deck</span>'
        )
        product_name.setObjectName("productName")
        product_name.setTextFormat(Qt.TextFormat.RichText)
        product_descriptor = QLabel("// CONTROL SYSTEM")
        product_descriptor.setObjectName("productDescriptor")
        brand_layout.addWidget(product_name)
        brand_layout.addWidget(product_descriptor)
        top.addWidget(brand)

        selectors = QVBoxLayout()
        selectors.setSpacing(0)
        selectors.addWidget(self._profile_combo)
        selectors.addWidget(self._page_combo)
        top.addLayout(selectors)
        top.addStretch(1)
        top.addWidget(self._device_status)
        top.addWidget(self._settings_button())

        left = QWidget()
        left.setObjectName("actionPanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.addWidget(self._heading("Action library"))
        search = QLineEdit()
        search.setPlaceholderText("Find an action…")
        search.textChanged.connect(self._filter_actions)
        left_layout.addWidget(search)
        left_layout.addWidget(self._action_list, 1)
        help_text = QLabel("Select an action, configure it, then choose Apply to key.")
        help_text.setWordWrap(True)
        help_text.setObjectName("mutedText")
        left_layout.addWidget(help_text)
        left.setMinimumWidth(210)
        left.setMaximumWidth(300)

        canvas = QWidget()
        canvas.setObjectName("workspace")
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(22, 12, 22, 18)
        canvas_layout.addWidget(self._deck_canvas)
        quick = QFrame()
        quick.setObjectName("quickEditor")
        quick_layout = QVBoxLayout(quick)
        quick_layout.addWidget(self._quick_title)
        fields = QGridLayout()
        fields.setHorizontalSpacing(10)
        fields.setVerticalSpacing(8)
        fields.addWidget(self._label_edit, 0, 0)
        fields.addWidget(self._action_combo, 0, 1)
        fields.addWidget(self._trigger_combo, 0, 2)
        fields.addWidget(self._apply_key_button, 0, 3, 2, 1)
        self._value_stack = QStackedWidget()
        self._empty_editor = QWidget()
        self._value_stack.addWidget(self._empty_editor)
        self._value_stack.addWidget(self._value_edit)
        self._value_stack.addWidget(self._media_combo)
        self._value_stack.addWidget(self._page_action_combo)
        command_editor = QWidget()
        command_fields = QHBoxLayout(command_editor)
        command_fields.setContentsMargins(0, 0, 0, 0)
        command_fields.setSpacing(10)
        command_fields.addWidget(self._command_edit, 3)
        command_fields.addWidget(self._working_directory_edit, 2)
        self._value_stack.addWidget(command_editor)
        fields.addWidget(self._value_stack, 1, 0, 1, 3)
        visual_fields = QHBoxLayout()
        visual_fields.addWidget(self._icon_combo)
        visual_fields.addWidget(self._background_combo)
        visual_fields.addWidget(self._foreground_combo)
        visual_fields.addStretch(1)
        visual_fields.addWidget(self._undo_button)
        visual_fields.addWidget(self._redo_button)
        fields.addLayout(visual_fields, 2, 0, 1, 4)
        fields.setColumnStretch(0, 2)
        fields.setColumnStretch(1, 2)
        fields.setColumnStretch(2, 2)
        quick_layout.addLayout(fields)
        quick_scroll = QScrollArea()
        quick_scroll.setObjectName("quickScroll")
        quick_scroll.setWidgetResizable(True)
        quick_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        quick_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        quick_scroll.setFrameShape(QFrame.Shape.NoFrame)
        quick_scroll.setWidget(quick)
        quick_scroll.setMinimumHeight(120)
        quick_scroll.setMaximumHeight(190)
        self._quick_scroll = quick_scroll
        self._deck_canvas.surface_width_changed.connect(self._set_editor_width)
        canvas_layout.addWidget(quick_scroll, 0, Qt.AlignmentFlag.AlignHCenter)
        canvas_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(canvas)
        splitter.setSizes([240, 1040])
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setLayout(top)
        root_layout.addWidget(toolbar)
        root_layout.addWidget(splitter, 1)
        root = QWidget()
        root.setLayout(root_layout)
        self.setCentralWidget(root)
        self.statusBar().addWidget(self._action_status, 1)

    def _settings_button(self) -> QToolButton:
        button = QToolButton()
        button.setObjectName("settingsButton")
        button.setText("⚙")
        button.setToolTip("Profile, page, and device settings")
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        actions = (
            ("Detect Stream Deck", self.detect_device),
            (None, None),
            ("New profile", self._add_profile),
            ("Rename profile", self._rename_profile),
            ("Duplicate profile", self._duplicate_profile),
            ("Delete profile", self._delete_profile),
            (None, None),
            ("New page", self._add_page),
            ("Rename page", self._rename_page),
            ("Move page left", lambda: self._move_page(-1)),
            ("Move page right", lambda: self._move_page(1)),
            ("Delete page", self._delete_page),
        )
        for label, callback in actions:
            if label is None:
                menu.addSeparator()
            else:
                action = menu.addAction(label)
                action.triggered.connect(callback)
        button.setMenu(menu)
        self._settings_menu = menu
        return button

    @Slot(int)
    def _set_editor_width(self, width: int) -> None:
        self._quick_scroll.setFixedWidth(width)

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
        self._refresh_page_action_combo()
        self._refresh_canvas()

    def _refresh_page_action_combo(self) -> None:
        current = self._page_action_combo.currentData()
        with QSignalBlocker(self._page_action_combo):
            self._page_action_combo.clear()
            self._page_action_combo.addItem("Next page", "next")
            self._page_action_combo.addItem("Previous page", "previous")
            for page in self._active_profile().pages:
                self._page_action_combo.addItem(f"Go to {page.name}", f"page:{page.id}")
            index = self._page_action_combo.findData(current)
            self._page_action_combo.setCurrentIndex(max(index, 0))

    def _refresh_canvas(self) -> None:
        page = self._active_page()
        for index, button in enumerate(self._key_buttons):
            key = page.keys.get(index, KeyConfig())
            label = key.label.strip() or str(index + 1)
            button.setText(f"{key.icon}\n{label}".strip())
            button.setStyleSheet(
                f"background-color: {key.background_color}; color: {key.foreground_color};"
            )
            button.setToolTip(ACTION_LABELS.get(key.action_type, key.action_type))
            button.setProperty("configured", key.action_type != "none")
            button.setProperty("actionState", "")
            button.style().unpolish(button)
            button.style().polish(button)
        if self._key_buttons:
            self._select_key(min(self._selected_key, len(self._key_buttons) - 1))
        self._render_active_page()

    def _build_key_grid(self, columns: int, rows: int) -> None:
        while (item := self._key_grid.takeAt(0)) is not None:
            if item.widget() is not None:
                item.widget().deleteLater()
        self._key_buttons.clear()
        for index in range(columns * rows):
            button = KeyButton(index)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, key=index: self._select_key(key))
            button.action_dropped.connect(self._drop_action)
            button.key_dropped.connect(self._drop_key)
            self._key_grid.addWidget(button, index // columns, index % columns)
            self._key_buttons.append(button)
        self._deck_canvas.configure(columns, rows, self._key_buttons)
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
        self._command_edit.setText(key.action_value)
        self._media_combo.setCurrentIndex(max(self._media_combo.findData(key.action_value), 0))
        self._page_action_combo.setCurrentIndex(
            max(self._page_action_combo.findData(key.action_value), 0)
        )
        self._working_directory_edit.setText(key.working_directory)
        self._trigger_combo.setCurrentIndex(max(self._trigger_combo.findData(key.trigger), 0))
        self._icon_combo.setCurrentIndex(max(self._icon_combo.findData(key.icon), 0))
        self._background_combo.setCurrentIndex(
            max(self._background_combo.findData(key.background_color), 0)
        )
        self._foreground_combo.setCurrentIndex(
            max(self._foreground_combo.findData(key.foreground_color), 0)
        )
        self._update_action_editor()

    @Slot()
    def _apply_key_edits(self) -> None:
        action_type = str(self._action_combo.currentData())
        action_value = (
            str(self._media_combo.currentData())
            if action_type == "media"
            else str(self._page_action_combo.currentData())
            if action_type == "page"
            else self._command_edit.text().strip()
            if action_type == "command"
            else self._value_edit.text().strip()
        )
        working_directory = self._working_directory_edit.text().strip()
        try:
            if action_type == "keyboard":
                parse_shortcut(action_value)
            elif action_type == "media":
                media_key(action_value)
            elif action_type == "launch":
                parse_command(action_value)
            elif action_type == "open":
                validate_open_target(action_value)
            elif action_type == "command":
                parse_command(action_value)
                working_directory = validate_working_directory(working_directory)
            elif action_type == "page" and not action_value:
                raise ValueError("Choose a page destination")
        except ValueError as error:
            QMessageBox.warning(self, "Invalid action", str(error))
            return
        self._push_undo()
        key = self._active_page().key(self._selected_key)
        key.label = self._label_edit.text().strip()
        key.action_type = action_type
        key.action_value = action_value
        key.trigger = str(self._trigger_combo.currentData())
        key.working_directory = working_directory if action_type == "command" else ""
        key.icon = str(self._icon_combo.currentData())
        key.background_color = str(self._background_combo.currentData())
        key.foreground_color = str(self._foreground_combo.currentData())
        self._save()
        self._refresh_canvas()

    def _push_undo(self) -> None:
        self._undo_stack.append(deepcopy(self._active_page().keys))
        self._undo_stack = self._undo_stack[-50:]
        self._redo_stack.clear()

    def _restore_keys(self, keys: dict[int, KeyConfig]) -> None:
        self._active_page().keys = deepcopy(keys)
        self._save()
        self._refresh_canvas()

    def _undo(self) -> None:
        if self._undo_stack:
            self._redo_stack.append(deepcopy(self._active_page().keys))
            self._restore_keys(self._undo_stack.pop())

    def _redo(self) -> None:
        if self._redo_stack:
            self._undo_stack.append(deepcopy(self._active_page().keys))
            self._restore_keys(self._redo_stack.pop())

    @Slot(int, str)
    def _drop_action(self, index: int, label: str) -> None:
        action_type = next(
            (key for key, value in ACTION_LABELS.items() if value == label), None
        )
        if action_type is None:
            return
        self._push_undo()
        self._active_page().key(index).action_type = action_type
        self._selected_key = index
        self._save()
        self._refresh_canvas()

    @Slot(int, int, bool)
    def _drop_key(self, source: int, destination: int, copy: bool) -> None:
        if source == destination:
            return
        self._push_undo()
        page = self._active_page()
        source_config = deepcopy(page.keys.get(source, KeyConfig()))
        if copy:
            page.keys[destination] = source_config
        else:
            destination_config = deepcopy(page.keys.get(destination, KeyConfig()))
            page.keys[destination] = source_config
            page.keys[source] = destination_config
        self._selected_key = destination
        self._save()
        self._refresh_canvas()

    def _on_action_activated(self, item: QListWidgetItem) -> None:
        self._action_combo.setCurrentIndex(
            self._action_combo.findData(item.data(Qt.ItemDataRole.UserRole))
        )
        if str(self._action_combo.currentData()) == "command":
            self._command_edit.setFocus()
        else:
            self._value_edit.setFocus()

    def _update_action_editor(self, _index: int | None = None) -> None:
        action_type = str(self._action_combo.currentData())
        stack_index = {
            "none": 0,
            "media": 2,
            "page": 3,
            "command": 4,
        }.get(action_type, 1)
        self._value_stack.setCurrentIndex(stack_index)
        if action_type == "keyboard":
            self._value_edit.setPlaceholderText("Example: Ctrl+Shift+S")
        elif action_type == "launch":
            self._value_edit.setPlaceholderText("Example: firefox --private-window")
        elif action_type == "open":
            self._value_edit.setPlaceholderText("File, folder, or https:// address")
        elif action_type == "command":
            self._command_edit.setPlaceholderText("Command and arguments (no shell syntax)")
        else:
            self._value_edit.setPlaceholderText("No value required")

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

    def _navigate_page(self, destination: str) -> str:
        profile = self._active_profile()
        current = next(
            index for index, page in enumerate(profile.pages) if page.id == profile.active_page_id
        )
        if destination == "next":
            target = profile.pages[(current + 1) % len(profile.pages)]
        elif destination == "previous":
            target = profile.pages[(current - 1) % len(profile.pages)]
        elif destination.startswith("page:"):
            try:
                target = profile.page_by_id(destination.removeprefix("page:"))
            except KeyError as error:
                raise ValueError("The configured page no longer exists") from error
        else:
            raise ValueError("Invalid page destination")
        profile.active_page_id = target.id
        self._save()
        self._refresh_page_combo()
        return f"Switched to {target.name}"

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
            self._set_device_state("disconnected")
            return
        self._device = devices[0]
        for extra in devices[1:]:
            extra.close()
        geometry = self._device.info.geometry
        self._columns, self._rows = geometry.columns, geometry.rows
        self._device_status.setText(
            f"● {self._device.info.model} · {geometry.columns}×{geometry.rows}"
        )
        self._set_device_state("connected")
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
            if hasattr(self._device, "render_key_config"):
                render_config = deepcopy(key)
                render_config.label = render_config.label.strip() or str(index + 1)
                self._device.render_key_config(index, render_config)
            else:
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
            key = self._active_page().keys.get(event.key, KeyConfig())
            result = self._action_engine.handle_key(event.key, key, event.pressed)
            if result.executed:
                state = "running" if "running" in result.message.casefold() else (
                    "success" if result.success else "failure"
                )
                self._show_action_result(event.key, result.message, state)

    @Slot(int, object)
    def _on_action_finished(self, key_index: int, result: object) -> None:
        if not hasattr(result, "success") or not hasattr(result, "message"):
            return
        state = "success" if result.success else "failure"
        self._show_action_result(key_index, str(result.message), state, include_key=True)

    def _show_action_result(
        self, key_index: int, message: str, state: str, include_key: bool = False
    ) -> None:
        prefix = {"running": "●", "success": "✓", "failure": "⚠"}[state]
        key_text = f"Key {key_index + 1}: " if include_key else ""
        self._action_status.setText(f"{prefix} {key_text}{message}")
        self._action_status.setProperty("state", state)
        self._action_status.style().unpolish(self._action_status)
        self._action_status.style().polish(self._action_status)
        if 0 <= key_index < len(self._key_buttons):
            button = self._key_buttons[key_index]
            button.setProperty("actionState", state)
            button.style().unpolish(button)
            button.style().polish(button)
            if self._device is not None and hasattr(self._device, "render_key_config"):
                key = self._active_page().keys.get(key_index, KeyConfig())
                self._device.render_key_config(key_index, key, state)

    def _show_detection_error(self, error: Exception) -> None:
        self._device_status.setText("Device error")
        self._set_device_state("failure")
        QMessageBox.warning(self, "Stream Deck error", str(error))

    def _set_device_state(self, state: str) -> None:
        self._device_status.setProperty("state", state)
        self._device_status.style().unpolish(self._device_status)
        self._device_status.style().polish(self._device_status)

    def _disconnect_device(self) -> None:
        if self._device is not None:
            with suppress(Exception):
                self._device.close()
            self._device = None
        self._device_status.setText("No device connected")
        self._set_device_state("disconnected")

    def _apply_style(self) -> None:
        self.setStyleSheet(STYLESHEET)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save()
        self._disconnect_device()
        with suppress(OSError):
            self._action_engine.close()
        super().closeEvent(event)
