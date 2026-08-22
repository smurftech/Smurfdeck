from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from smurfdeck.ui.main_window import MainWindow


def main() -> int:
    """Launch the SmurfDeck desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationDisplayName("SmurfDeck")
    app.setApplicationName("smurfdeck")
    app.setOrganizationName("Smurftech")
    window = MainWindow()
    window.show()
    return app.exec()

