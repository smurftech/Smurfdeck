from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

from smurfdeck.actions.engine import ActionEngine, ActionResult
from smurfdeck.actions.sequences import (
    STEP_TYPES,
    SequenceStep,
    parse_sequence,
    serialize_sequence,
)
from smurfdeck.models.config import KeyConfig


class SequenceRunner(QObject):
    """One cancellable sequence at a time; every action runs on the GUI thread."""

    state_changed = Signal(bool)

    def __init__(self, engine: ActionEngine, feedback, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.feedback = feedback
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._advance)
        self.steps = ()
        self.index = 0
        self.key_index = 0
        self.running = False

    def start(self, key_index: int, value: str) -> ActionResult:
        if self.running:
            return ActionResult(True, False, "A multi-action is already running")
        self.steps = parse_sequence(value)
        self.key_index, self.index, self.running = key_index, 0, True
        self.state_changed.emit(True)
        self.timer.start(0)
        return ActionResult(True, True, "Multi-action running…")

    def _advance(self):
        if not self.running:
            return
        if self.index == len(self.steps):
            self.running = False
            self.state_changed.emit(False)
            self.feedback(self.key_index, ActionResult(True, True, "Multi-action completed"))
            return
        step = self.steps[self.index]
        self.index += 1
        if step.action_type == "delay":
            self.timer.start(int(step.value))
            return
        result = self.engine.execute(
            self.key_index, KeyConfig(action_type=step.action_type, action_value=step.value)
        )
        if not result.success:
            self.running = False
            self.state_changed.emit(False)
            self.feedback(
                self.key_index, ActionResult(True, False, f"Step {self.index}: {result.message}")
            )
            return
        self.timer.start(100)

    def cancel(self):
        was_running = self.running
        self.timer.stop()
        self.running = False
        self.state_changed.emit(False)
        return was_running


class SequenceEditor(QDialog):
    def __init__(self, value: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-action steps")
        self.resize(620, 440)
        self.value = value
        layout = QVBoxLayout(self)
        note = QLabel(
            "Steps run in order. Delays use milliseconds. Stops on failure.\n"
            "Launch starts an app; add a delay before sending it a shortcut."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Action", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 160)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        for title, callback in (
            ("Add step", self.add_step),
            ("Remove", self.remove_step),
            ("Move up", lambda: self.move_step(-1)),
            ("Move down", lambda: self.move_step(1)),
        ):
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        try:
            steps = parse_sequence(value)
        except ValueError:
            steps = (SequenceStep("keyboard", "Ctrl+C"),)
        self.set_steps(steps)

    def add_step(self, _checked=False, step=None):
        if self.table.rowCount() >= 32:
            return
        step = step or SequenceStep("delay", "500")
        row = self.table.rowCount()
        self.table.insertRow(row)
        kind = QComboBox()
        for code, name in STEP_TYPES.items():
            kind.addItem(name, code)
        kind.setCurrentIndex(kind.findData(step.action_type))
        self.table.setCellWidget(row, 0, kind)
        value = QLineEdit(step.value)
        value.setPlaceholderText("Ctrl+S, play_pause, firefox, https://… or 500")
        self.table.setCellWidget(row, 1, value)
        self.table.setCurrentCell(row, 0)

    def steps(self):
        return tuple(
            SequenceStep(
                self.table.cellWidget(row, 0).currentData(), self.table.cellWidget(row, 1).text()
            )
            for row in range(self.table.rowCount())
        )

    def set_steps(self, steps):
        self.table.setRowCount(0)
        for step in steps:
            self.add_step(step=step)

    def remove_step(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def move_step(self, delta):
        row = self.table.currentRow()
        target = row + delta
        if 0 <= target < self.table.rowCount():
            steps = list(self.steps())
            steps[row], steps[target] = steps[target], steps[row]
            self.set_steps(steps)
            self.table.setCurrentCell(target, 0)

    def save(self):
        value = serialize_sequence(self.steps())
        try:
            parse_sequence(value)
        except ValueError as error:
            QMessageBox.warning(self, "Invalid multi-action", str(error))
            return
        self.value = value
        self.accept()
