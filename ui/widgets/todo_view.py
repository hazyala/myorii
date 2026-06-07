from __future__ import annotations

from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
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
from ui.assets import tinted_icon


LIST_MARGIN_X = 14
ITEM_GAP = 8


class CheckBox(QWidget):
    def __init__(self, checked: bool = False) -> None:
        super().__init__()
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._pressed = False
        self._callback = None

    def set_callback(self, fn) -> None:
        self._callback = fn

    def isChecked(self) -> bool:  # noqa: N802
        return self._checked

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        if self._checked == checked:
            return
        self._checked = checked
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            if self.rect().contains(event.position().toPoint()):
                self._checked = not self._checked
                self.update()
                if self._callback:
                    self._callback(self._checked)
            event.accept()
            return
        self._pressed = False
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event

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


class DragHandle(QWidget):
    def __init__(self, item: "TodoItem") -> None:
        super().__init__()
        self._item = item
        self.setFixedSize(14, 20)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.grabMouse()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._item.begin_drag(event.globalPosition().toPoint(), grab_mouse=False)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._item.update_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._item.end_drag()
            self.releaseMouse()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#cdd2db"))
        for row in range(3):
            for col in range(2):
                painter.drawEllipse(col * 6 + 1, row * 6 + 1, 3, 3)
        painter.end()


class TodoItem(QFrame):
    H_MARGIN = 24
    V_MARGIN = 18
    MIN_HEIGHT = 40
    CHROME_WIDTH = 14 + 20 + 16 + H_MARGIN

    def __init__(self, todo: Todo, parent_view: "TodoView") -> None:
        super().__init__()
        self._todo = todo
        self._parent_view = parent_view
        self.setObjectName("todoItem")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(8)

        self._handle = DragHandle(self)

        self._checkbox = CheckBox(self._todo.done)
        self._checkbox.set_callback(self._on_checked)

        self._label = QLabel(self._todo.text)
        self._label.setObjectName("todoLabel")
        self._label.setWordWrap(True)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._label.installEventFilter(self)

        if self._todo.done:
            self._apply_done_style()

        layout.addWidget(self._handle, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._checkbox, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._label, 1)

    def _on_checked(self, checked: bool) -> None:
        todo_store.toggle(self._todo.id)
        if checked:
            self._apply_done_style()
            QTimer.singleShot(80, self._remove_if_done)
        else:
            self._apply_undone_style()

    def _remove_if_done(self) -> None:
        if self._checkbox.isChecked():
            self._parent_view.remove_item(self)

    def _apply_done_style(self) -> None:
        self._label.setStyleSheet("color: #b0b8c8; text-decoration: line-through;")

    def _apply_undone_style(self) -> None:
        self._label.setStyleSheet("color: #20242c; text-decoration: none;")

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._label:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.begin_drag(event.globalPosition().toPoint())
                return True
            if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                self.update_drag(event.globalPosition().toPoint())
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self.end_drag()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.update_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.end_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_card_width(self, width: int) -> None:
        width = max(160, width)
        label_width = max(80, width - self.CHROME_WIDTH)
        bounds = self._label.fontMetrics().boundingRect(
            QRect(0, 0, label_width, 1000),
            int(Qt.TextFlag.TextWordWrap),
            self._todo.text,
        )
        label_height = bounds.height() + 3
        row_height = max(self.MIN_HEIGHT, label_height + self.V_MARGIN)
        self._label.setFixedSize(label_width, label_height)
        self.setFixedSize(width, row_height)

    @property
    def todo_id(self) -> int:
        return self._todo.id

    def begin_drag(self, global_pos: QPoint, grab_mouse: bool = True) -> None:
        if grab_mouse:
            self.grabMouse()
        self.setProperty("dragging", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self._parent_view.begin_drag(self, global_pos)

    def update_drag(self, global_pos: QPoint) -> None:
        self._parent_view.update_drag(global_pos)

    def end_drag(self) -> None:
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if self.mouseGrabber() is self:
            self.releaseMouse()
        self._parent_view.end_drag()


class TodoView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("todoView")
        self._items: list[TodoItem] = []
        self._drag_item: TodoItem | None = None
        self._setup_ui()
        self._load_todos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self._scroll = QScrollArea()
        self._scroll.setObjectName("todoScrollArea")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("todoListContent")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(LIST_MARGIN_X, 12, LIST_MARGIN_X, 10)
        self._list_layout.setSpacing(ITEM_GAP)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list_widget)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
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
        layout.setContentsMargins(17, 10, 17, 10)
        layout.setSpacing(7)

        cal_label = QLabel()
        cal_label.setFixedSize(20, 20)
        cal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cal_label.setPixmap(
            tinted_icon("calendar.png", QColor("#20242c"), QSize(17, 17)).pixmap(17, 17)
        )

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

        self._add_btn = QPushButton("+ 할일 추가")
        self._add_btn.setObjectName("todoAddButton")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self.show_add_input)
        bar_layout.addWidget(self._add_btn)

        self._input_frame = QFrame()
        self._input_frame.setObjectName("todoInputFrame")
        input_layout = QHBoxLayout(self._input_frame)
        input_layout.setContentsMargins(14, 10, 14, 10)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("todoInput")
        self._input.setPlaceholderText("할 일을 입력하세요...")
        self._input.returnPressed.connect(self._commit_input)

        cancel_btn = QPushButton("x")
        cancel_btn.setObjectName("todoCancelBtn")
        cancel_btn.setFixedSize(22, 22)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.hide_add_input)

        input_layout.addWidget(self._input, 1)
        input_layout.addWidget(cancel_btn)

        self._input_frame.hide()
        bar_layout.addWidget(self._input_frame)

        return self._add_bar

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        QTimer.singleShot(0, self.sync_item_sizes)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self.sync_item_sizes)

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
        self.sync_item_sizes()

    def begin_drag(self, item: TodoItem, global_pos: QPoint) -> None:
        self._drag_item = item
        self.update_drag(global_pos)

    def update_drag(self, global_pos: QPoint) -> None:
        if self._drag_item is None or len(self._items) < 2:
            return

        old_index = self._items.index(self._drag_item)
        new_index = self._index_for_global_y(global_pos)
        if new_index == old_index:
            return

        self._items.pop(old_index)
        self._items.insert(new_index, self._drag_item)
        self._list_layout.removeWidget(self._drag_item)
        self._list_layout.insertWidget(new_index, self._drag_item, 0, Qt.AlignmentFlag.AlignTop)
        self.sync_item_sizes()

    def end_drag(self) -> None:
        if self._drag_item is None:
            return

        todo_store.reorder_many([item.todo_id for item in self._items])
        self._drag_item = None

    def sync_item_sizes(self) -> None:
        width = self._scroll.viewport().width() - (LIST_MARGIN_X * 2)
        for item in self._items:
            item.set_card_width(width)
        self._list_widget.setMinimumWidth(self._scroll.viewport().width())

    def _index_for_global_y(self, global_pos: QPoint) -> int:
        local_y = self._list_widget.mapFromGlobal(global_pos).y()
        for index, item in enumerate(self._items):
            if local_y < item.geometry().center().y():
                return index
        return max(0, len(self._items) - 1)

    def _load_todos(self) -> None:
        for todo in todo_store.get_all():
            if not todo.done:
                self._insert_item(todo)

    def _insert_item(self, todo: Todo) -> None:
        item = TodoItem(todo, self)
        self._items.append(item)
        self._list_layout.insertWidget(len(self._items) - 1, item, 0, Qt.AlignmentFlag.AlignTop)
        QTimer.singleShot(0, self.sync_item_sizes)

    def _commit_input(self) -> None:
        text = self._input.text().strip()
        if text:
            self.add_todo(text)
        else:
            self.hide_add_input()
