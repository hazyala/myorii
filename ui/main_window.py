from __future__ import annotations

import socket
import threading
import sys
from ctypes import c_void_p

from PyQt6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, pyqtSignal
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
    QMainWindow,
    QPushButton,
    QButtonGroup,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.llm.chat_service import ChatService
from ui.assets import asset_path, tinted_icon
from ui.chat_worker import ModelListWorker
from ui.settings_view import SettingsView
from ui.widgets.chat_view import ChatView
from ui.widgets.todo_view import TodoView


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
        self._chat_service = ChatService()
        self._model_list_worker = ModelListWorker(self._chat_service)
        self._model_list_worker.models_loaded.connect(self._update_available_models)
        self._page_stack = QStackedWidget()
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

        layout.addWidget(self._page_stack, 1)

        main_page = QWidget()
        main_layout = QVBoxLayout(main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(self._header())
        main_layout.addSpacing(10)
        main_layout.addWidget(self._tabs())
        main_layout.addWidget(self._content_stack, 1)

        self._chat_view = ChatView(self._chat_service)
        self._content_stack.addWidget(self._content_panel("chatPanel"))
        self._content_stack.addWidget(self._content_panel("todoPanel"))
        self._content_stack.addWidget(self._content_panel("memoPanel"))
        self._content_stack.setCurrentIndex(0)

        self._settings_view = SettingsView()
        self._settings_view.back_requested.connect(self._show_main_view)
        self._settings_view.model_changed.connect(self._chat_view.set_model)
        self._page_stack.addWidget(main_page)
        self._page_stack.addWidget(self._settings_view)
        self._page_stack.setCurrentWidget(main_page)
        self._model_list_worker.start()

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
        settings.clicked.connect(self._show_settings_view)

        close = QPushButton("×")
        close.setObjectName("closeButton")
        close.setFixedSize(32, 32)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.hide)

        layout.addWidget(avatar)
        layout.addLayout(title_row)
        layout.addItem(QSpacerItem(20, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(settings, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignVCenter)

        return layout

    def _show_settings_view(self) -> None:
        self._page_stack.setCurrentWidget(self._settings_view)

    def _show_main_view(self) -> None:
        self._page_stack.setCurrentIndex(0)

    def _update_available_models(self, models: list[str]) -> None:
        self._settings_view.update_models(models)

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if object_name == "chatPanel":
            layout.setContentsMargins(14, 14, 14, 14)
            layout.addWidget(self._chat_view, 1)
        elif object_name == "todoPanel":
            self._todo_view = TodoView()
            layout.addWidget(self._todo_view, 1)
        else:
            layout.addStretch(1)

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
        self._keep_open_on_deactivate()

    def _keep_open_on_deactivate(self) -> None:
        # 바깥 클릭(앱 비활성화) 시 자동으로 숨지 않도록. 아이콘 재클릭으로만 닫힘.
        if sys.platform != "darwin":
            return
        try:
            import objc

            view = objc.objc_object(c_void_p=int(self.winId()))
            ns_window = view.window()
            if ns_window is not None:
                ns_window.setHidesOnDeactivate_(False)
        except Exception:
            pass


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
#closeButton,
#attachmentButton,
#promptPlusButton,
#historySwitch {
    background: transparent;
    border: none;
}

#iconButton:hover,
#closeButton:hover {
    background: rgba(238, 242, 247, 180);
    border-radius: 15px;
}

#closeButton {
    color: #555c68;
    font-size: 18px;
    font-weight: 500;
}

#attachmentButton {
    color: #5d6572;
    font-size: 15px;
    font-weight: 650;
    border: 1px solid rgba(215, 221, 230, 165);
    border-radius: 11px;
}

#attachmentButton:hover {
    background: rgba(238, 242, 247, 160);
    color: #2f80ff;
}

#attachmentLabel {
    color: #565f6e;
    font-size: 12px;
    font-weight: 550;
}

#historyListButton {
    background: #ffffff;
    border: 1px solid rgba(215, 221, 230, 180);
    border-radius: 8px;
    color: #565f6e;
    font-size: 12px;
    font-weight: 650;
    padding: 0 10px;
}

#historyListButton:hover {
    background: #f7f9fc;
    color: #565f6e;
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

#userMessageRow,
#assistantMessageRow {
    background: transparent;
}

#userMessageBubble {
    background: #2f80ff;
    border-radius: 14px;
}

#assistantMessageBubble {
    background: #ffffff;
    border: none;
    border-radius: 14px;
}

#userMessageBody,
#assistantMessageBody {
    background: transparent;
    border: none;
    font-size: 13px;
}

#userMessageBody {
    color: #ffffff;
}

#assistantMessageBody {
    color: #222833;
}

#assistantAvatar {
    border-radius: 14px;
}

#copyToast {
    background: rgba(32, 36, 44, 210);
    color: #ffffff;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 650;
    min-height: 28px;
    padding: 0 10px;
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
    min-height: 45px;
}

#promptInput {
    color: #222833;
    background: transparent;
    border: none;
    font-size: 13px;
    line-height: 20px;
}

#promptInput::placeholder {
    color: #8c94a2;
}

#sendButton {
    background: #f0f1f4;
    border: none;
    border-radius: 19px;
}

#promptPlusButton {
    background: #f0f1f4;
    color: #5d6572;
    border-radius: 19px;
    font-size: 16px;
    font-weight: 650;
}

#sendButton:hover,
#promptPlusButton:hover {
    background: #e8ebf1;
}

#codeBlockFrame {
    background: rgba(232, 238, 247, 218);
    border: 1px solid rgba(255, 255, 255, 190);
    border-radius: 8px;
}

#codeCopyButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #3d4b5f;
    padding: 0;
}

#codeCopyButton:hover {
    background: rgba(255, 255, 255, 120);
}

#pawLoadingIndicator,
#pawLoadingDot {
    background: transparent;
    border: none;
}

#settingsPanel {
    background: transparent;
}

#settingsTitle {
    color: #11131a;
    font-size: 20px;
    font-weight: 750;
}

#settingsSubtitle,
#settingsRowCaption {
    color: #737b88;
    font-size: 12px;
    font-weight: 550;
}

#settingsScrollArea {
    background: transparent;
    border: none;
}

#settingsScrollArea QWidget,
#settingsScrollContent {
    background: transparent;
}

#settingsSection,
#exitActionButton {
    background: rgba(255, 255, 255, 145);
    border: 1px solid rgba(222, 227, 235, 155);
    border-radius: 14px;
}

#settingsSectionHeader {
    background: transparent;
    border-bottom: 1px solid rgba(222, 227, 235, 135);
}

#settingsSectionTitle {
    color: #171b22;
    font-size: 14px;
    font-weight: 750;
}

#settingsRow {
    background: transparent;
    border-top: 1px solid rgba(222, 227, 235, 112);
}

#settingsRowTitle {
    color: #171b22;
    font-size: 13px;
    font-weight: 650;
}

#segmentedControl {
    background: rgba(246, 248, 252, 170);
    border: 1px solid #dfe4ed;
    border-radius: 9px;
}

#segmentedControl QPushButton {
    background: transparent;
    border: none;
    border-radius: 7px;
    color: #626a76;
    font-size: 12px;
    font-weight: 650;
    padding: 0 10px;
}

#segmentedControl QPushButton:checked {
    background: #ffffff;
    border: 1px solid #78aefe;
    color: #2f80ff;
}

#modelComboBox {
    background: #ffffff;
    border: 1px solid #dfe4ed;
    border-radius: 9px;
    color: #2b3038;
    padding: 0 10px;
    font-size: 12px;
}

#secondaryButton,
#ghostActionButton {
    background: #ffffff;
    border: 1px solid #dfe4ed;
    border-radius: 9px;
    color: #20242c;
    font-size: 12px;
    font-weight: 650;
    min-height: 31px;
    padding: 0 12px;
}

#secondaryButton:hover,
#ghostActionButton:hover {
    background: #f7f9fc;
}

#versionLabel {
    color: #737b88;
    font-size: 12px;
    font-weight: 650;
}

#exitActionButton {
    color: #ff2d2d;
    font-size: 13px;
    font-weight: 750;
    min-height: 48px;
    padding: 0 14px;
    text-align: left;
}

#exitActionButton:hover {
    background: rgba(255, 45, 45, 24);
}

#todoHeader {
    border-bottom: 1px solid rgba(222, 227, 235, 150);
}

#todoTodayLabel {
    color: #11131a;
    font-size: 13px;
    font-weight: 700;
}

#todoDateLabel {
    color: #8c94a2;
    font-size: 13px;
    font-weight: 500;
}

#todoScrollArea,
#todoListContent {
    background: transparent;
}

#todoItem {
    background: #ffffff;
    border: 1px solid rgba(222, 227, 235, 180);
    border-radius: 12px;
}

#todoLabel {
    color: #20242c;
    font-size: 13px;
    font-weight: 500;
}

#todoAddBar {
    border-top: 1px solid rgba(222, 227, 235, 150);
    background: transparent;
}

#todoAddButton {
    background: transparent;
    border: none;
    color: #8c94a2;
    font-size: 13px;
    font-weight: 500;
    padding: 13px 0;
}

#todoAddButton:hover {
    color: #2f80ff;
}

#todoInputFrame {
    background: transparent;
}

#todoInput {
    background: #ffffff;
    border: 1px solid rgba(215, 221, 230, 200);
    border-radius: 10px;
    color: #20242c;
    font-size: 13px;
    padding: 7px 12px;
    min-height: 34px;
}

#todoInput:focus {
    border: 1px solid #2f80ff;
}

#todoCancelBtn {
    background: transparent;
    border: none;
    color: #b0b8c8;
    font-size: 12px;
    font-weight: 600;
}

#todoCancelBtn:hover {
    color: #f04452;
}
"""
