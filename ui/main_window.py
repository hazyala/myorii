from __future__ import annotations

import sys
import socket
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPixmap,
    QPolygonF,
    QTextOption,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QButtonGroup,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


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


class InternetStatusWatcher(QObject):
    status_changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._checking = False
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.check_now)
        self.check_now()
        self._timer.start()

    def check_now(self) -> None:
        if self._checking:
            return

        self._checking = True
        thread = threading.Thread(target=self._check_connection, daemon=True)
        thread.start()

    def _check_connection(self) -> None:
        online = False
        for endpoint in (("1.1.1.1", 53), ("8.8.8.8", 53), ("www.apple.com", 443)):
            try:
                with socket.create_connection(endpoint, timeout=1):
                    online = True
                    break
            except OSError:
                continue

        self._checking = False
        self.status_changed.emit(online)


class PopoverSurface(QWidget):
    RADIUS = 22
    NOTCH_WIDTH = 42
    NOTCH_HEIGHT = 28
    SURFACE_TOP = 22

    def __init__(self) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = self._surface_path()
        painter.fillPath(path, QColor(255, 255, 255, 242))
        painter.setPen(QColor(226, 231, 239, 150))
        painter.drawPath(path)

    def _surface_path(self) -> QPainterPath:
        width = self.width()
        height = self.height()
        rect = QRectF(0.5, self.SURFACE_TOP + 0.5, width - 1, height - self.SURFACE_TOP - 1)

        body_path = QPainterPath()
        body_path.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        center_x = width / 2
        notch = QPainterPath()
        notch.addPolygon(
            QPolygonF(
                [
                    QPointF(center_x - self.NOTCH_WIDTH / 2, self.SURFACE_TOP + 1),
                    QPointF(center_x, 0),
                    QPointF(center_x + self.NOTCH_WIDTH / 2, self.SURFACE_TOP + 1),
                ]
            )
        )

        return body_path.united(notch)


class TabButton(QPushButton):
    def __init__(self, label: str, icon_name: str, active: bool = False) -> None:
        super().__init__(label)
        self._icon_name = icon_name
        self.setCheckable(True)
        self.setChecked(active)
        self.setIconSize(QSize(16, 16))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggled.connect(lambda _checked: self._refresh_icon())
        self._refresh_icon()

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._refresh_icon(hovered=True)

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._refresh_icon()

    def _refresh_icon(self, hovered: bool = False) -> None:
        color = QColor("#2f80ff") if self.isChecked() or hovered else QColor("#555c68")
        self.setIcon(tinted_icon(self._icon_name, color, QSize(16, 16)))


class SwitchButton(QPushButton):
    def __init__(self) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setFixedSize(34, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("")
        self.toggled.connect(self.update)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_color = QColor("#2f80ff") if self.isChecked() else QColor("#dedfe4")
        knob_size = 16
        knob_x = self.width() - knob_size - 2 if self.isChecked() else 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(knob_x, 2, knob_size, knob_size))


class ChatInput(QTextEdit):
    send_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("promptInput")
        self.setPlaceholderText("무엇을 도와줄까?")
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContentsMargins(0, 0, 0, 0)
        self.document().setDocumentMargin(2)
        self.setFixedHeight(32)
        self.textChanged.connect(self._fit_height_to_document)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                return

            self._request_send()
            return

        super().keyPressEvent(event)

    def request_send(self) -> None:
        self._request_send()

    def _request_send(self) -> None:
        text = self.toPlainText().strip()
        if not text:
            return

        self.send_requested.emit(text)
        self.clear()

    def _fit_height_to_document(self) -> None:
        line_count = max(1, self.toPlainText().count("\n") + 1)
        next_height = 32 + ((line_count - 1) * 18)
        self.setFixedHeight(min(next_height, 78))


class MainWindow(QMainWindow):
    DEFAULT_SIZE = QSize(430, 610)
    EDGE_MARGIN = 12
    ICON_GAP = 8

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Myorii")
        self.setFixedSize(self.DEFAULT_SIZE)
        self._tabs_group = QButtonGroup(self)
        self._tabs_group.setExclusive(True)
        self._content_stack = QStackedWidget()
        self._status_dot = QLabel()
        self._status_text = QLabel("오프라인")
        self._internet_status = InternetStatusWatcher()
        self._internet_status.status_changed.connect(self._set_online_status)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setCentralWidget(self._build_window())

    def toggle_at(self, icon_geometry: QRect) -> None:
        if self.isVisible():
            self.hide()
            return

        self.move(self._position_for(icon_geometry))
        self.show()
        self.raise_()

    def _build_window(self) -> QWidget:
        root = PopoverSurface()
        shadow = QGraphicsDropShadowEffect(root)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(45, 57, 80, 38))
        root.setGraphicsEffect(shadow)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 32, 14, 14)
        layout.setSpacing(0)

        layout.addLayout(self._header())
        layout.addSpacing(10)
        layout.addWidget(self._tabs())
        layout.addWidget(self._content_stack, 1)

        self._content_stack.addWidget(self._content_panel("chatPanel"))
        self._content_stack.addWidget(self._content_panel("todoPanel"))
        self._content_stack.addWidget(self._content_panel("memoPanel"))
        self._content_stack.setCurrentIndex(0)

        return root

    def _header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 0, 8, 0)
        layout.setSpacing(10)

        avatar = QLabel()
        avatar.setFixedSize(44, 44)
        avatar.setPixmap(
            QPixmap(str(asset_path("characters", "myorii_profile.png"))).scaled(
                avatar.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        title = QLabel("Myorii")
        title.setObjectName("windowTitle")
        self._status_dot.setFixedSize(7, 7)
        self._status_dot.setObjectName("statusDot")
        self._status_text.setObjectName("statusText")
        self._set_online_status(False)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(title)
        title_row.addWidget(self._status_dot)
        title_row.addWidget(self._status_text)
        title_row.addStretch(1)

        settings = QPushButton()
        settings.setObjectName("iconButton")
        settings.setIcon(QIcon(str(asset_path("icons", "settings.png"))))
        settings.setIconSize(QSize(21, 21))
        settings.setFixedSize(36, 36)
        settings.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(avatar)
        layout.addLayout(title_row)
        layout.addItem(QSpacerItem(20, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(settings, 0, Qt.AlignmentFlag.AlignVCenter)

        return layout

    def _set_online_status(self, online: bool) -> None:
        color = "#32d17c" if online else "#f04452"
        text = "온라인" if online else "오프라인"
        self._status_text.setText(text)
        self._status_dot.setStyleSheet(f"background: {color}; border-radius: 4px;")

    def _tabs(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("tabsFrame")
        frame.setFixedHeight(46)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        chat = TabButton("채팅", "chat.png", active=True)
        todo = TabButton("할일", "check.png")
        memo = TabButton("메모", "memo.png")

        for index, button in enumerate((chat, todo, memo)):
            self._tabs_group.addButton(button, index)

        self._tabs_group.idClicked.connect(self._content_stack.setCurrentIndex)

        layout.addWidget(chat)
        layout.addWidget(todo)
        layout.addWidget(memo)

        return frame

    def _content_panel(self, object_name: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName(object_name)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(0)

        if object_name == "chatPanel":
            layout.addWidget(self._chat_scroll_area(), 1)
            layout.addWidget(self._input_panel())
        else:
            layout.addStretch(1)

        return frame

    def _chat_scroll_area(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setObjectName("chatScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("chatScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addStretch(1)

        scroll_area.setWidget(content)
        return scroll_area

    def _input_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("inputPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        history = QHBoxLayout()
        history.setSpacing(7)
        history_label = QLabel("대화 기록 저장")
        history_label.setObjectName("historyLabel")
        toggle = SwitchButton()
        toggle.setObjectName("historySwitch")

        history.addWidget(history_label)
        history.addWidget(toggle)
        history.addStretch(1)

        prompt_wrap = QFrame()
        prompt_wrap.setObjectName("promptWrap")
        prompt_layout = QHBoxLayout(prompt_wrap)
        prompt_layout.setContentsMargins(13, 7, 8, 7)
        prompt_layout.setSpacing(7)

        prompt = ChatInput()
        send = QPushButton()
        send.setObjectName("sendButton")
        send.setIcon(QIcon(str(asset_path("icons", "send.png"))))
        send.setIconSize(QSize(19, 19))
        send.setFixedSize(38, 38)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.clicked.connect(prompt.request_send)

        prompt_layout.addWidget(prompt, 1, Qt.AlignmentFlag.AlignVCenter)
        prompt_layout.addWidget(send, 0, Qt.AlignmentFlag.AlignBottom)

        layout.addLayout(history)
        layout.addWidget(prompt_wrap)

        return frame

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

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.setStyleSheet(STYLE_SHEET)


STYLE_SHEET = """
QWidget {
    color: #20242c;
    font-family: "SF Pro Display", "Apple SD Gothic Neo", "Pretendard";
    font-size: 15px;
}

#windowTitle {
    color: #11131a;
    font-size: 18px;
    font-weight: 700;
}

#statusText {
    color: #69707c;
    font-size: 12px;
    font-weight: 600;
}

#iconButton,
#historySwitch {
    background: transparent;
    border: none;
}

#iconButton:hover {
    background: rgba(238, 242, 247, 180);
    border-radius: 15px;
}

#tabsFrame {
    background: rgba(255, 255, 255, 166);
    border: 1px solid rgba(222, 227, 235, 170);
    border-top-left-radius: 17px;
    border-top-right-radius: 17px;
}

QStackedWidget {
    background: transparent;
}

TabButton {
    background: transparent;
    border: none;
    color: #555c68;
    font-size: 14px;
    font-weight: 650;
}

TabButton:checked {
    background: #ffffff;
    color: #2f80ff;
    border-radius: 13px;
    border: 1px solid rgba(239, 242, 246, 210);
}

TabButton:hover {
    background: rgba(255, 255, 255, 140);
    border-radius: 13px;
}

#chatPanel,
#todoPanel,
#memoPanel {
    background: rgba(255, 255, 255, 132);
    border-left: 1px solid rgba(222, 227, 235, 150);
    border-right: 1px solid rgba(222, 227, 235, 150);
    border-bottom: 1px solid rgba(222, 227, 235, 150);
    border-bottom-left-radius: 17px;
    border-bottom-right-radius: 17px;
}

#inputPanel {
    background: rgba(255, 255, 255, 110);
    border-top: 1px solid rgba(222, 227, 235, 170);
}

#chatScrollArea {
    background: transparent;
    border: none;
}

#chatScrollArea QWidget,
#chatScrollContent {
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 4px 0 4px 0;
}

QScrollBar::handle:vertical {
    background: rgba(154, 164, 180, 105);
    border-radius: 3px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

#historyLabel {
    color: #565f6e;
    font-size: 12px;
    font-weight: 550;
}

#promptWrap {
    background: #ffffff;
    border: 1px solid #e0e4ec;
    border-radius: 17px;
    min-height: 50px;
}

#promptInput {
    color: #222833;
    background: transparent;
    border: none;
    font-size: 13px;
    line-height: 19px;
}

#promptInput::placeholder {
    color: #8c94a2;
}

#sendButton {
    background: #f0f1f4;
    border: none;
    border-radius: 19px;
}

#sendButton:hover {
    background: #e8ebf1;
}
"""
