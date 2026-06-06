"""Myorii application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from platform.macos.menubar import MacMenuBar
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Myorii")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    menu_bar = MacMenuBar(window)
    menu_bar.show()

    app.setProperty("myorii_window", window)
    app.setProperty("myorii_menu_bar", menu_bar)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
