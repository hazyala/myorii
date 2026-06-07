from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import storage.todo_store as todo_store
from storage.todo_store import Todo
from ui.assets import asset_path, tinted_icon


# ── 커스텀 체크박스 ────────────────────────────────────────

class CheckBox(QWidget):
    def __init__(self, checked: bool = False) -> None:
        super().__init__()
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._callback = None

    def set_callback(self, fn) -> None:
        self._callback = fn

    @property
    def checked(self) -> bool:
        return self._checked

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            if self._callback:
                self._callback(self._checked)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 5, 5)

        if self._checked:
            painter.fillPath(path, QColor("#2f80ff"))
            painter.setPen(QPen(QColor("#ffffff"), 1.8))
            cx, cy = rect.center().x(), rect.center().y()
            painter.drawLine(cx - 4, cy, cx - 1, cy + 3)
            painter.drawLine(cx - 1, cy + 3, cx + 4, cy - 3)
        else:
            painter.setPen(QPen(QColor("#cdd2db"), 1.5))
            painter.drawPath(path)

        painter.end()


# ── 드래그 핸들 ────────────────────────────────────────────

class DragHandle(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(14, 20)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#cdd2db"))
        for row in range(3):
            for col in range(2):
                painter.drawEllipse(col * 6 + 1, row * 6 + 1, 3, 3)
        painter.end()


# ── 할일 아이템 ───────────────────────────────────────────

class TodoItem(QFrame):
    def __init__(self, todo: Todo, parent_view: "TodoView") -> None:
        super().__init__()
        self._todo = todo
        self._parent_view = parent_view
        self.setObjectName("todoItem")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._setup_ui()
        self._setup_fade()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(8)

        self._handle = DragHandle()

        self._checkbox = CheckBox(self._todo.done)
        self._checkbox.set_callback(self._on_checked)

        self._label = QLabel(self._todo.text)
        self._label.setObjectName("todoLabel")
        self._label.setWordWrap(False)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        if self._todo.done:
            self._apply_done_style()

        layout.addWidget(self._handle)
        layout.addWidget(self._checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._label, 1, Qt.AlignmentFlag.AlignVCenter)

    def _setup_fade(self) -> None:
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(1.0)
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(lambda: self._parent_view.remove_item(self))

    def _on_checked(self, checked: bool) -> None:
        todo_store.toggle(self._todo.id)
        if checked:
            self._apply_done_style()
            QTimer.singleShot(600, self._anim.start)
        else:
            self._apply_undone_style()

    def _apply_done_style(self) -> None:
        self._label.setStyleSheet(
            "color: #b0b8c8; text-decoration: line-through;"
        )

    def _apply_undone_style(self) -> None:
        self._label.setStyleSheet(
            "color: #20242c; text-decoration: none;"
        )


# ── TodoView ─────────────────────────────────────────────

class TodoView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("todoView")
        self._items: list[TodoItem] = []
        self._setup_ui()
        self._load_todos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        # 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setObjectName("todoScrollArea")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("todoListContent")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(12, 10, 12, 6)
        self._list_layout.setSpacing(7)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # ← 핵심: 위에서 쌓임

        self._scroll.setWidget(self._list_widget)
        layout.addWidget(self._scroll, 1)

        layout.addWidget(self._build_add_bar())

    def _build_header(self) -> QWidget:
        from datetime import date
        today = date.today()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        day_str = f"{today.month}월 {today.day}일 ({weekdays[today.weekday()]})"

        frame = QFrame()
        frame.setObjectName("todoHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 11, 16, 11)
        layout.setSpacing(6)

        cal_label = QLabel()
        cal_label.setFixedSize(16, 16)
        try:
            cal_label.setPixmap(
                tinted_icon("calendar.png", QColor("#8c94a2"), QSize(14, 14)).pixmap(14, 14)
            )
        except Exception:
            cal_label.setText("📅")

        today_label = QLabel("오늘")
        today_label.setObjectName("todoTodayLabel")

        date_label = QLabel(day_str)
        date_label.setObjectName("todoDateLabel")

        layout.addWidget(cal_label)
        layout.addWidget(today_label)
        layout.addWidget(date_label)
        layout.addStretch(1)

        return frame

    def _build_add_bar(self) -> QWidget:
        self._add_bar = QFrame()
        self._add_bar.setObjectName("todoAddBar")
        bar_layout = QVBoxLayout(self._add_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        # 버튼
        self._add_btn = QPushButton("+ 할일 추가")
        self._add_btn.setObjectName("todoAddButton")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self.show_add_input)
        bar_layout.addWidget(self._add_btn)

        # 입력창 (숨김)
        self._input_frame = QFrame()
        self._input_frame.setObjectName("todoInputFrame")
        input_layout = QHBoxLayout(self._input_frame)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("todoInput")
        self._input.setPlaceholderText("할 일을 입력하세요...")
        self._input.returnPressed.connect(self._commit_input)

        cancel_btn = QPushButton("✕")
        cancel_btn.setObjectName("todoCancelBtn")
        cancel_btn.setFixedSize(22, 22)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.hide_add_input)

        input_layout.addWidget(self._input, 1)
        input_layout.addWidget(cancel_btn)

        self._input_frame.hide()
        bar_layout.addWidget(self._input_frame)

        return self._add_bar

    def show_add_input(self) -> None:
        self._add_btn.hide()
        self._input_frame.show()
        self._input.clear()
        QTimer.singleShot(0, self._input.setFocus)

    def hide_add_input(self) -> None:
        self._input_frame.hide()
        self._input.clear()
        self._add_btn.show()

    def add_todo(self, text: str) -> None:
        todo = todo_store.add(text)
        self._insert_item(todo)
        self.hide_add_input()

    def remove_item(self, item: TodoItem) -> None:
        if item in self._items:
            self._items.remove(item)
        self._list_layout.removeWidget(item)
        item.deleteLater()

    def _load_todos(self) -> None:
        for todo in todo_store.get_all():
            if not todo.done:
                self._insert_item(todo)

    def _insert_item(self, todo: Todo) -> None:
        item = TodoItem(todo, self)
        self._items.append(item)
        self._list_layout.addWidget(item)

    def _commit_input(self) -> None:
        text = self._input.text().strip()
        if text:
            self.add_todo(text)
        else:
            self.hide_add_input()