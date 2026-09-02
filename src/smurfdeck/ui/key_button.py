from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag, QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QToolButton


class ActionListWidget(QListWidget):
    def mimeData(self, items: list[QListWidgetItem]) -> QMimeData:
        mime = QMimeData()
        if items:
            mime.setText(items[0].text())
        return mime


class KeyButton(QToolButton):
    """A deck key that accepts actions and supports key-to-key movement."""

    action_dropped = Signal(int, str)
    key_dropped = Signal(int, int, bool)

    def __init__(self, index: int) -> None:
        super().__init__()
        self.index = index
        self._drag_start = None
        self.setAcceptDrops(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is None or not event.buttons() & Qt.MouseButton.LeftButton:
            return super().mouseMoveEvent(event)
        if (
            event.position().toPoint() - self._drag_start
        ).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)
        self._drag_start = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-smurfdeck-key", str(self.index).encode())
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasFormat("application/x-smurfdeck-key") or mime.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        if mime.hasFormat("application/x-smurfdeck-key"):
            source = int(bytes(mime.data("application/x-smurfdeck-key")).decode())
            copy = bool(event.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)
            self.key_dropped.emit(source, self.index, copy)
        elif mime.hasText():
            self.action_dropped.emit(self.index, mime.text())
        event.acceptProposedAction()
