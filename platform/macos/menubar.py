from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ui.main_window import MainWindow


class MacMenuBar(QObject):
    ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "mockups" / "myorii.png"

    def __init__(self, window: MainWindow) -> None:
        super().__init__()

        self.window = window
        self.tray_icon = QSystemTrayIcon(QIcon(str(self.ICON_PATH)), self)
        self.tray_icon.setToolTip("Myorii")
        self.tray_icon.activated.connect(self._handle_activation)
        self.tray_icon.setContextMenu(self._create_menu())

    def show(self) -> None:
        self.tray_icon.show()

    def toggle_window(self) -> None:
        self.window.toggle_at(self.tray_icon.geometry())
        self._sync_open_action_text()

    def _create_menu(self) -> QMenu:
        menu = QMenu()

        self.open_action = QAction("Open Myorii", menu)
        self.open_action.triggered.connect(self.toggle_window)
        menu.addAction(self.open_action)

        menu.addSeparator()

        quit_action = QAction("Quit Myorii", menu)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)

        menu.aboutToShow.connect(self._sync_open_action_text)
        return menu

    def _handle_activation(
        self,
        reason: QSystemTrayIcon.ActivationReason,
    ) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window()

    def _sync_open_action_text(self) -> None:
        if self.window.isVisible():
            self.open_action.setText("Close Myorii")
        else:
            self.open_action.setText("Open Myorii")
