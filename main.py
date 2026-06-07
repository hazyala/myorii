"""Myorii application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QLockFile, QStandardPaths
from PyQt6.QtWidgets import QApplication

from platform.macos.menubar import MacMenuBar
from ui.main_window import MainWindow
from storage import database


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Myorii")
    app.setQuitOnLastWindowClosed(False)

    lock_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation)
    app_lock = QLockFile(f"{lock_path}/myorii.lock")
    app_lock.setStaleLockTime(1000)
    if not app_lock.tryLock(100):
        return 0
    
    database.initialize()

    window = MainWindow()
    menu_bar = MacMenuBar(window)
    menu_bar.show()

    app.setProperty("myorii_lock", app_lock)
    app.setProperty("myorii_window", window)
    app.setProperty("myorii_menu_bar", menu_bar)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
