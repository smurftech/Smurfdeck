import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import smurfdeck.ui.key_button as key_button_module
from smurfdeck.ui.key_button import KeyButton


def _mouse_event(event_type: QEvent.Type, position: QPointF) -> QMouseEvent:
    button = (
        Qt.MouseButton.LeftButton
        if event_type != QEvent.Type.MouseMove
        else Qt.MouseButton.NoButton
    )
    return QMouseEvent(
        event_type,
        position,
        position,
        button,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def test_small_pointer_movement_remains_a_click(monkeypatch) -> None:
    QApplication.instance() or QApplication([])
    button = KeyButton(3)
    monkeypatch.setattr(
        key_button_module,
        "QDrag",
        lambda _parent: (_ for _ in ()).throw(AssertionError("drag started")),
    )

    button.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, QPointF(10, 10)))
    button.mouseMoveEvent(_mouse_event(QEvent.Type.MouseMove, QPointF(11, 11)))
    button.mouseReleaseEvent(
        _mouse_event(QEvent.Type.MouseButtonRelease, QPointF(11, 11))
    )

    assert button._drag_start is None


def test_deliberate_movement_starts_only_one_drag(monkeypatch) -> None:
    QApplication.instance() or QApplication([])
    button = KeyButton(3)
    executions: list[Qt.DropAction] = []

    class FakeDrag:
        def __init__(self, _parent) -> None:
            pass

        def setMimeData(self, _mime) -> None:
            pass

        def exec(self, actions: Qt.DropAction) -> None:
            executions.append(actions)

    monkeypatch.setattr(key_button_module, "QDrag", FakeDrag)
    button.mousePressEvent(_mouse_event(QEvent.Type.MouseButtonPress, QPointF(10, 10)))
    move = _mouse_event(QEvent.Type.MouseMove, QPointF(100, 100))
    button.mouseMoveEvent(move)
    button.mouseMoveEvent(move)

    assert len(executions) == 1
    assert button._drag_start is None
