from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    DEFAULT_SIZE = QSize(360, 480)
    EDGE_MARGIN = 12
    ICON_GAP = 8

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Myorii")
        self.setFixedSize(self.DEFAULT_SIZE)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        placeholder = QLabel("Myorii")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(placeholder)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def toggle_at(self, icon_geometry: QRect) -> None:
        if self.isVisible():
            self.hide()
            return

        self.move(self._position_for(icon_geometry))
        self.show()
        self.raise_()
        self.activateWindow()

    def _position_for(self, icon_geometry: QRect) -> QPoint:
        screen_geometry = self._screen_geometry(icon_geometry)
        size = self.size()

        if icon_geometry.isValid() and not icon_geometry.isNull():
            x = icon_geometry.center().x() - size.width() // 2
            y = icon_geometry.bottom() + self.ICON_GAP
        else:
            cursor_position = QGuiApplication.primaryScreen().availableGeometry().topRight()
            x = cursor_position.x() - size.width() - self.EDGE_MARGIN
            y = cursor_position.y() + self.EDGE_MARGIN

        x = min(
            max(x, screen_geometry.left() + self.EDGE_MARGIN),
            screen_geometry.right() - size.width() - self.EDGE_MARGIN + 1,
        )
        y = min(
            max(y, screen_geometry.top() + self.EDGE_MARGIN),
            screen_geometry.bottom() - size.height() - self.EDGE_MARGIN + 1,
        )

        return QPoint(x, y)

    def _screen_geometry(self, icon_geometry: QRect) -> QRect:
        if icon_geometry.isValid() and not icon_geometry.isNull():
            screen = QGuiApplication.screenAt(icon_geometry.center())
            if screen is not None:
                return screen.availableGeometry()

        primary_screen = QGuiApplication.primaryScreen()
        return primary_screen.availableGeometry()
