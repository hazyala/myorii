from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap


ASSET_ROOT = Path("assets")


def asset_path(*parts: str) -> Path:
    app_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return app_root / ASSET_ROOT.joinpath(*parts)


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
