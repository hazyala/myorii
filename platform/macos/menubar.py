from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon

from ui.main_window import MainWindow


class MacMenuBar(QObject):
    ICON_PATH = Path("assets") / "mockups" / "myorii.png"

    def __init__(self, window: MainWindow) -> None:
        super().__init__()

        self.window = window
        self.tray_icon = QSystemTrayIcon(QIcon(str(self._icon_path())), self)
        self.tray_icon.setToolTip("Myorii")
        self.tray_icon.activated.connect(self._handle_activation)

    def show(self) -> None:
        self.tray_icon.show()

    def toggle_window(self) -> None:
        self.window.toggle_at(self.tray_icon.geometry())

    def _handle_activation(
        self,
        reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window()

    def _icon_path(self) -> Path:
        app_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        return app_root / self.ICON_PATH
