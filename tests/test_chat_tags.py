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
from core.llm.chat_service import ChatService, DEFAULT_MODEL
from core.tools.chat_tools import is_tool_request

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

    def test_unspaced_tags_are_plain_text_in_ui_and_service(self):
        class OrdinaryClient:
            def list_models(self):
                return [DEFAULT_MODEL]

            def stream_chat(self, model, messages):
                self.messages = messages
                yield '일반 질문 답변'

        editor = ChatInput()
        for text in ('폴더명 /memo괜찮아?', '/MEMO?', '/todo', '/memo\t괜찮아?', '/memo\n괜찮아?', 'https://example.com/memo 이름 괜찮아?'):
            with self.subTest(text=text):
                self.assertFalse(is_tool_request(text))
                editor.setPlainText(text)
                app.processEvents()
                block = editor.document().firstBlock()
                while block.isValid():
                    self.assertFalse(block.layout().formats())
                    block = block.next()
                client = OrdinaryClient()
                service = ChatService(client=client)
                self.assertEqual(''.join(service.send(text)), '일반 질문 답변')
                self.assertEqual(client.messages[-1].content, text)
                self.assertNotIn('current_request', client.messages[-1].content)
        self.assertTrue(is_tool_request('/memo 괜찮아?'))
        # A separate natural command still works; an unspaced slash name can
        # remain part of the data being saved.
        self.assertTrue(is_tool_request('메모에 폴더명 /todo를 저장해줘'))
