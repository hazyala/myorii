from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


ASSET_ROOT = Path("assets")


def asset_path(*parts: str) -> Path:
    app_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return app_root / ASSET_ROOT.joinpath(*parts)


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
        self.setCheckable(True)
        self.setChecked(active)
        self.setIcon(QIcon(str(asset_path("icons", icon_name))))
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class MainWindow(QMainWindow):
    DEFAULT_SIZE = QSize(430, 610)
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
        layout.setContentsMargins(20, 44, 20, 20)
        layout.setSpacing(0)

        layout.addLayout(self._header())
        layout.addSpacing(20)
        layout.addWidget(self._tabs())
        layout.addWidget(self._chat_panel(), 1)

        return root

    def _header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(22, 0, 8, 0)
        layout.setSpacing(12)

        avatar = QLabel()
        avatar.setFixedSize(68, 68)
        avatar.setPixmap(
            QPixmap(str(asset_path("characters", "myorii_profile.png"))).scaled(
                avatar.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        title = QLabel("Myorii")
        title.setObjectName("windowTitle")
        status_dot = QLabel()
        status_dot.setFixedSize(8, 8)
        status_dot.setObjectName("statusDot")
        status_text = QLabel("로컬 모드")
        status_text.setObjectName("statusText")

        title_group = QVBoxLayout()
        title_group.setSpacing(4)
        title_group.addStretch(1)
        title_group.addWidget(title)

        status = QHBoxLayout()
        status.setSpacing(7)
        status.addWidget(status_dot)
        status.addWidget(status_text)
        status.addStretch(1)
        title_group.addLayout(status)
        title_group.addStretch(1)

        settings = QPushButton()
        settings.setObjectName("iconButton")
        settings.setIcon(QIcon(str(asset_path("icons", "settings.png"))))
        settings.setIconSize(QSize(22, 22))
        settings.setFixedSize(38, 38)
        settings.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(avatar)
        layout.addLayout(title_group)
        layout.addItem(QSpacerItem(20, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(settings, 0, Qt.AlignmentFlag.AlignVCenter)

        return layout

    def _tabs(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("tabsFrame")
        frame.setFixedHeight(58)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        chat = TabButton("채팅", "chat.png", active=True)
        todo = TabButton("할일", "check.png")
        memo = TabButton("메모", "memo.png")

        layout.addWidget(chat)
        layout.addWidget(todo)
        layout.addWidget(memo)

        return frame

    def _chat_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("chatPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 24, 22, 20)
        layout.setSpacing(0)

        layout.addWidget(self._user_message(), 0, Qt.AlignmentFlag.AlignRight)
        layout.addSpacing(32)
        layout.addLayout(self._assistant_message())
        layout.addStretch(1)
        layout.addWidget(self._input_panel())

        return frame

    def _user_message(self) -> QWidget:
        bubble = QFrame()
        bubble.setObjectName("userBubble")
        bubble.setFixedSize(278, 82)

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(6)

        text = QLabel("사용자 프로필 이미지 저장 함수")
        text.setObjectName("bubbleText")
        time = QLabel("오전 9:41")
        time.setObjectName("timeText")
        time.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(text)
        layout.addWidget(time)

        return bubble

    def _assistant_message(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        avatar = QLabel()
        avatar.setFixedSize(46, 46)
        avatar.setPixmap(
            QPixmap(str(asset_path("characters", "myorii_profile.png"))).scaled(
                avatar.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        content = QVBoxLayout()
        content.setSpacing(12)

        message = QLabel("추천하는 함수명이에요!")
        message.setObjectName("assistantText")
        code = self._code_suggestion()
        retry = QPushButton("다른 추천 보기")
        retry.setObjectName("retryButton")
        retry.setIcon(QIcon(str(asset_path("icons", "power.png"))))
        retry.setIconSize(QSize(16, 16))
        retry.setCursor(Qt.CursorShape.PointingHandCursor)

        content.addWidget(message)
        content.addWidget(code)
        content.addWidget(retry, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(avatar)
        layout.addLayout(content)

        return layout

    def _code_suggestion(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("codeBox")
        frame.setFixedSize(292, 70)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 0, 18, 0)
        layout.setSpacing(12)

        code = QLabel("saveUserProfileImage")
        code.setObjectName("codeText")
        copy = QPushButton()
        copy.setObjectName("copyButton")
        copy.setIcon(QIcon(str(asset_path("icons", "note.png"))))
        copy.setIconSize(QSize(20, 20))
        copy.setFixedSize(30, 30)
        copy.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(code)
        layout.addStretch(1)
        layout.addWidget(copy)

        return frame

    def _input_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("inputPanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        history = QHBoxLayout()
        history.setSpacing(8)
        history_icon = QLabel()
        history_icon.setPixmap(
            QPixmap(str(asset_path("icons", "memo.png"))).scaled(
                18,
                18,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        history_label = QLabel("대화 기록 저장")
        history_label.setObjectName("historyLabel")
        toggle = QFrame()
        toggle.setObjectName("toggleOff")
        toggle.setFixedSize(34, 20)

        history.addWidget(history_icon)
        history.addWidget(history_label)
        history.addWidget(toggle)
        history.addStretch(1)

        prompt_wrap = QFrame()
        prompt_wrap.setObjectName("promptWrap")
        prompt_layout = QHBoxLayout(prompt_wrap)
        prompt_layout.setContentsMargins(16, 0, 10, 0)
        prompt_layout.setSpacing(8)

        prompt = QLineEdit()
        prompt.setObjectName("promptInput")
        prompt.setPlaceholderText("무엇을 도와줄까?")
        prompt.setFrame(False)
        send = QPushButton()
        send.setObjectName("sendButton")
        send.setIcon(QIcon(str(asset_path("icons", "send.png"))))
        send.setIconSize(QSize(22, 22))
        send.setFixedSize(46, 46)
        send.setCursor(Qt.CursorShape.PointingHandCursor)

        prompt_layout.addWidget(prompt)
        prompt_layout.addWidget(send)

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
    font-size: 20px;
    font-weight: 700;
}

#statusDot {
    background: #43d682;
    border-radius: 4px;
}

#statusText {
    color: #69707c;
    font-size: 13px;
    font-weight: 600;
}

#iconButton,
#copyButton {
    background: transparent;
    border: none;
}

#iconButton:hover,
#copyButton:hover {
    background: rgba(238, 242, 247, 180);
    border-radius: 15px;
}

#tabsFrame {
    background: rgba(255, 255, 255, 166);
    border: 1px solid rgba(222, 227, 235, 170);
    border-top-left-radius: 17px;
    border-top-right-radius: 17px;
}

TabButton {
    background: transparent;
    border: none;
    color: #555c68;
    font-size: 15px;
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

#chatPanel {
    background: rgba(255, 255, 255, 132);
    border-left: 1px solid rgba(222, 227, 235, 150);
    border-right: 1px solid rgba(222, 227, 235, 150);
    border-bottom: 1px solid rgba(222, 227, 235, 150);
    border-bottom-left-radius: 17px;
    border-bottom-right-radius: 17px;
}

#userBubble {
    background: #eef1fb;
    border-radius: 18px;
}

#bubbleText {
    color: #2f333b;
    font-size: 15px;
    font-weight: 500;
}

#timeText {
    color: #77808e;
    font-size: 12px;
}

#assistantText {
    color: #333843;
    font-size: 15px;
    font-weight: 550;
}

#codeBox {
    background: #ffffff;
    border: 1px solid #e0e4ec;
    border-radius: 14px;
}

#codeText {
    color: #11131a;
    font-family: "SF Mono", "Menlo", "Consolas";
    font-size: 17px;
    font-weight: 650;
}

#retryButton {
    background: rgba(255, 255, 255, 150);
    border: 1px solid #e3e7ef;
    border-radius: 18px;
    color: #4c5461;
    font-size: 13px;
    padding: 8px 14px;
}

#inputPanel {
    background: rgba(255, 255, 255, 110);
    border-top: 1px solid rgba(222, 227, 235, 170);
}

#historyLabel {
    color: #565f6e;
    font-size: 13px;
    font-weight: 550;
}

#toggleOff {
    background: #dedfe4;
    border-radius: 10px;
}

#promptWrap {
    background: #ffffff;
    border: 1px solid #e0e4ec;
    border-radius: 20px;
    min-height: 58px;
}

#promptInput {
    color: #222833;
    background: transparent;
    font-size: 15px;
}

#promptInput::placeholder {
    color: #8c94a2;
}

#sendButton {
    background: #f0f1f4;
    border: none;
    border-radius: 23px;
}

#sendButton:hover {
    background: #e8ebf1;
}
"""
