from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from smurfdeck.brand import APP_ICON_PATH
from smurfdeck.ui.main_window import MainWindow


def main() -> int:
    """Launch the SmurfDeck desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("SmurfDeck")
    app.setApplicationName("smurfdeck")
    app.setOrganizationName("Smurftech")
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = MainWindow()
    window.show()
    return app.exec()

