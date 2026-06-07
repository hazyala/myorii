from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextOption
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import storage.memo_store as memo_store
from storage.memo_store import Memo
from ui.assets import tinted_icon


LIST_MARGIN_X = 14
ITEM_GAP = 8


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)

        self._heading = QTextCharFormat()
        self._heading.setForeground(QColor("#1f5fbf"))
        self._heading.setFontWeight(QFont.Weight.Bold)

        self._marker = QTextCharFormat()
        self._marker.setForeground(QColor("#2f80ff"))
        self._marker.setFontWeight(QFont.Weight.DemiBold)

        self._code = QTextCharFormat()
        self._code.setForeground(QColor("#48566a"))
        self._code.setBackground(QColor("#f1f5fb"))
        self._code.setFontFamily("Menlo")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        stripped = text.lstrip()
        indent = len(text) - len(stripped)
        if stripped.startswith("#"):
            marker_len = len(stripped) - len(stripped.lstrip("#"))
            self.setFormat(indent, marker_len, self._marker)
            self.setFormat(indent + marker_len, len(text) - indent - marker_len, self._heading)
        elif stripped.startswith(("- ", "* ", "+ ", "> ")):
            self.setFormat(indent, 2, self._marker)

        start = 0
        while True:
            first = text.find("`", start)
            if first < 0:
                break
            second = text.find("`", first + 1)
            if second < 0:
                break
            self.setFormat(first, second - first + 1, self._code)
            start = second + 1


class MemoCard(QFrame):
    H_MARGIN = 24
    V_MARGIN = 24
    MIN_HEIGHT = 84
    CHROME_WIDTH = 24 + 28 + 14 + H_MARGIN

    def __init__(self, memo: Memo, parent_view: "MemoView") -> None:
        super().__init__()
        self._memo = memo
        self._parent_view = parent_view
        self._drag_active = False
        self.setObjectName("memoItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)

        self._handle = QPushButton("::")
        self._handle.setObjectName("memoDragHandle")
        self._handle.setFixedSize(24, 28)
        self._handle.setCursor(Qt.CursorShape.OpenHandCursor)
        self._handle.installEventFilter(self)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(5)

        self._title = QLabel(self._display_title())
        self._title.setObjectName("memoItemTitle")
        self._title.setWordWrap(False)
        self._title.installEventFilter(self)

        self._body = QLabel(self._display_body())
        self._body.setObjectName("memoItemBody")
        self._body.setWordWrap(True)
        self._body.installEventFilter(self)

        self._date = QLabel(self._display_date())
        self._date.setObjectName("memoItemDate")
        self._date.installEventFilter(self)

        text_col.addWidget(self._title)
        text_col.addWidget(self._body)
        text_col.addWidget(self._date)

        delete_btn = QPushButton("x")
        delete_btn.setObjectName("memoDeleteButton")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self._parent_view.delete_memo(self))

        layout.addWidget(self._handle, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_col, 1)
        layout.addWidget(delete_btn, 0, Qt.AlignmentFlag.AlignTop)

    @property
    def memo_id(self) -> int:
        return self._memo.id

    def set_card_width(self, width: int) -> None:
        width = max(160, width)
        text_width = max(80, width - self.CHROME_WIDTH)
        body_bounds = self._body.fontMetrics().boundingRect(
            QRect(0, 0, text_width, 42),
            int(Qt.TextFlag.TextWordWrap),
            self._display_body(),
        )
        self._title.setFixedWidth(text_width)
        self._body.setFixedSize(text_width, min(42, body_bounds.height() + 4))
        self._date.setFixedWidth(text_width)
        self.setFixedSize(width, self.MIN_HEIGHT)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._handle:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._handle.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.begin_drag(event.globalPosition().toPoint())
                return True
            if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                self.update_drag(event.globalPosition().toPoint())
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._handle.setCursor(Qt.CursorShape.OpenHandCursor)
                self.end_drag()
                return True

        if watched in (self._title, self._body, self._date):
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._parent_view.open_editor(self._memo)
                return True
        return super().eventFilter(watched, event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_active:
                self.end_drag()
                event.accept()
                return
            self._parent_view.open_editor(self._memo)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def begin_drag(self, global_pos: QPoint) -> None:
        self.grabMouse()
        self._drag_active = True
        self.setProperty("dragging", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self._parent_view.begin_drag(self, global_pos)

    def update_drag(self, global_pos: QPoint) -> None:
        self._parent_view.update_drag(global_pos)

    def end_drag(self) -> None:
        self._drag_active = False
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        if self.mouseGrabber() is self:
            self.releaseMouse()
        self._parent_view.end_drag()

    def _display_title(self) -> str:
        title = self._memo.title.strip()
        if title:
            return title
        first_line = next((line.strip("#*`- ") for line in self._memo.body.splitlines() if line.strip()), "")
        return first_line or "제목 없는 메모"

    def _display_body(self) -> str:
        body_lines = [line.strip() for line in self._memo.body.splitlines() if line.strip()]
        preview = " ".join(body_lines[1:] if len(body_lines) > 1 else body_lines)
        return preview[:95] + ("..." if len(preview) > 95 else "")

    def _display_date(self) -> str:
        value = self._memo.updated_at or self._memo.created_at
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
        except ValueError:
            return value

        now = datetime.now(timezone.utc).astimezone()
        if dt.date() == now.date():
            return dt.strftime("오늘 %p %-I:%M").replace("AM", "오전").replace("PM", "오후")
        return dt.strftime("%-m월 %-d일 %p %-I:%M").replace("AM", "오전").replace("PM", "오후")


class MemoEditor(QFrame):
    def __init__(self, parent_view: "MemoView") -> None:
        super().__init__()
        self._parent_view = parent_view
        self._memo: Memo | None = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self.save_now)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("memoEditor")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        back_btn = QPushButton("‹")
        back_btn.setObjectName("memoBackButton")
        back_btn.setFixedSize(30, 30)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self._parent_view.show_list)

        self._save_state = QLabel("저장됨")
        self._save_state.setObjectName("memoSaveState")

        top_row.addWidget(back_btn)
        top_row.addStretch(1)
        top_row.addWidget(self._save_state)

        self._editor = QTextEdit()
        self._editor.setObjectName("memoTextEdit")
        self._editor.setPlaceholderText("Markdown으로 메모를 작성하세요...")
        self._editor.setAcceptRichText(False)
        self._editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self._editor.textChanged.connect(self._schedule_save)
        self._highlighter = MarkdownHighlighter(self._editor.document())

        layout.addLayout(top_row)
        layout.addWidget(self._editor, 1)

    def edit(self, memo: Memo) -> None:
        self._memo = memo
        self._save_timer.stop()
        self._editor.blockSignals(True)
        self._editor.setPlainText(memo.body)
        self._editor.blockSignals(False)
        self._save_state.setText("저장됨")
        QTimer.singleShot(0, self._editor.setFocus)

    def save_now(self) -> None:
        if self._memo is None:
            return
        body = self._editor.toPlainText()
        title = next((line.strip("#*`- ") for line in body.splitlines() if line.strip()), "")
        updated = memo_store.update(self._memo.id, title[:80], body)
        if updated is not None:
            self._memo = updated
        self._save_state.setText("저장됨")
        self._parent_view.refresh_list()

    def _schedule_save(self) -> None:
        self._save_state.setText("저장 중...")
        self._save_timer.start()


class MemoView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("memoView")
        self._items: list[MemoCard] = []
        self._drag_item: MemoCard | None = None
        self._setup_ui()
        self.refresh_list()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list_page = QWidget()
        list_layout = QVBoxLayout(self._list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self._build_header())

        self._scroll = QScrollArea()
        self._scroll.setObjectName("memoScrollArea")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("memoListContent")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(LIST_MARGIN_X, 12, LIST_MARGIN_X, 10)
        self._list_layout.setSpacing(ITEM_GAP)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list_widget)
        list_layout.addWidget(self._scroll, 1)
        list_layout.addWidget(self._build_add_bar())

        self._editor = MemoEditor(self)
        layout.addWidget(self._list_page)
        layout.addWidget(self._editor)
        self._editor.hide()

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("memoHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(17, 10, 17, 10)
        layout.setSpacing(7)

        note_icon = QLabel()
        note_icon.setFixedSize(20, 20)
        note_icon.setPixmap(tinted_icon("memo.png", QColor("#20242c"), QSize(17, 17)).pixmap(17, 17))

        self._count_label = QLabel("내 메모 0")
        self._count_label.setObjectName("memoCountLabel")

        layout.addWidget(note_icon)
        layout.addWidget(self._count_label)
        layout.addStretch(1)
        return frame

    def _build_add_bar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("memoAddBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self._add_btn = QPushButton("새로운 메모")
        self._add_btn.setObjectName("memoAddButton")
        self._add_btn.setIcon(tinted_icon("note.png", QColor("#667085"), QSize(17, 17)))
        self._add_btn.setIconSize(QSize(17, 17))
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self.create_memo)
        layout.addWidget(self._add_btn)
        return frame

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        QTimer.singleShot(0, self.sync_item_sizes)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self.sync_item_sizes)

    def create_memo(self) -> None:
        memo = memo_store.add("", "")
        self.open_editor(memo)

    def open_editor(self, memo: Memo) -> None:
        self._list_page.hide()
        self._editor.show()
        self._editor.edit(memo)

    def show_list(self) -> None:
        self._editor.save_now()
        self.refresh_list()
        self._editor.hide()
        self._list_page.show()

    def refresh_list(self) -> None:
        memos = memo_store.get_all()
        self._clear_items()
        for memo in memos:
            self._insert_item(memo)
        self._count_label.setText(f"내 메모 {len(memos)}")

    def delete_memo(self, item: MemoCard) -> None:
        memo_store.delete(item.memo_id)
        self.refresh_list()

    def begin_drag(self, item: MemoCard, global_pos: QPoint) -> None:
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
        memo_store.reorder_many([item.memo_id for item in self._items])
        self._drag_item = None

    def sync_item_sizes(self) -> None:
        if not hasattr(self, "_scroll"):
            return
        width = self._scroll.viewport().width() - (LIST_MARGIN_X * 2)
        for item in self._items:
            item.set_card_width(width)
        self._list_widget.setMinimumWidth(self._scroll.viewport().width())

    def _insert_item(self, memo: Memo) -> None:
        item = MemoCard(memo, self)
        self._items.append(item)
        self._list_layout.insertWidget(len(self._items) - 1, item, 0, Qt.AlignmentFlag.AlignTop)
        QTimer.singleShot(0, self.sync_item_sizes)

    def _clear_items(self) -> None:
        for item in self._items:
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def _index_for_global_y(self, global_pos: QPoint) -> int:
        local_y = self._list_widget.mapFromGlobal(global_pos).y()
        for index, item in enumerate(self._items):
            if local_y < item.geometry().center().y():
                return index
        return max(0, len(self._items) - 1)
