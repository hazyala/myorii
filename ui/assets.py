from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap

from core.paths import resource_path

ASSET_ROOT = Path("assets")


def asset_path(*parts: str) -> Path:
    return resource_path(str(ASSET_ROOT), *parts)


def tinted_icon(icon_name: str, color: QColor, size: QSize = QSize(20, 20)) -> QIcon:
    pixmap = QPixmap(str(asset_path("icons", icon_name))).scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if pixmap.isNull():
        return QIcon(str(asset_path("icons", icon_name)))

    tinted = QPixmap(pixmap.size())
    tinted.fill(Qt.GlobalColor.transparent)

    painter = QPainter(tinted)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()

    return QIcon(tinted)
