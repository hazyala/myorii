import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from storage import database, todo_store, memo_store
from ui.widgets.todo_view import TodoView
from ui.widgets.memo_view import MemoView
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from ui.widgets.chat_view import ChatInput

app = QApplication.instance() or QApplication([])


class ChatTagTests(unittest.TestCase):
    def test_tag_format_space_edit_undo_send(self):
        editor = ChatInput()
        QTest.keyClicks(editor, '/todo')
        app.processEvents()
        self.assertFalse(editor.document().firstBlock().layout().formats())
        QTest.keyClick(editor, Qt.Key.Key_Space)
        app.processEvents()
        formats = editor.document().firstBlock().layout().formats()
        self.assertEqual(formats[0].length, 5)
        self.assertEqual(formats[0].format.foreground().color().name(), '#2f80ff')
        QTest.keyClicks(editor, ' hello')
        sent = []
        editor.send_requested.connect(sent.append)
        QTest.keyClick(editor, Qt.Key.Key_Return)
        self.assertEqual(sent, ['/todo  hello'])
        editor.setPlainText('/memo test')
        app.processEvents()
        self.assertEqual(editor.document().firstBlock().layout().formats()[0].format.foreground().color().name(), '#9862d9')
        editor.clear()
        QTest.keyClicks(editor, '/memo ')
        QTest.keyClick(editor, Qt.Key.Key_Backspace)
        app.processEvents()
        self.assertFalse(editor.document().firstBlock().layout().formats())
        editor.undo()
        app.processEvents()
        self.assertTrue(editor.document().firstBlock().layout().formats())


    def test_tabs_reload_chat_writes_and_clear_empty_groups(self):
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path', return_value=Path(folder)/'test.db'):
            database.initialize()
            todos = TodoView()
            memos = MemoView()
            todo = todo_store.add('채팅에서 추가한 항목')
            memo_store.add('채팅 메모', '본문')
            todos.show()
            memos.show()
            app.processEvents()
            self.assertEqual(len(todos._items), 1)
            self.assertEqual(len(memos._items), 1)
            todos.hide()
            todo_store.delete(todo.id)
            todos.show()
            app.processEvents()
            self.assertEqual(len(todos._items), 0)
            self.assertEqual(len(todos._date_headers), 0)
            todos.close()
            memos.close()
