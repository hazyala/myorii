import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QInputMethodEvent
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from core.llm.chat_service import ChatService, DEFAULT_MODEL
from core.llm.contracts import ChatMessagePayload, ChatAttachmentPayload
from core.llm.ollama_client import ContextLimitExceeded
from storage import database, chat_store
from ui.widgets.memo_view import MemoTextEdit, MarkdownHighlighter
from ui.widgets.message_bubble import MessageBubble

app = QApplication.instance() or QApplication([])

class FakeClient:
    def list_models(self): return [DEFAULT_MODEL]
    def stream_chat(self, model, messages):
        self.messages = messages
        yield 'answer'

class StabilityTests(unittest.TestCase):
    def test_independent_and_followup_history(self):
        client = FakeClient(); service = ChatService(client=client)
        service.set_history([ChatMessagePayload('user','무관한 코드'), ChatMessagePayload('assistant','unrelated')])
        list(service.send('사과 영어로'))
        self.assertEqual([m.role for m in client.messages], ['system','user'])
        list(service.send('방금 답을 한국어로 번역해줘'))
        self.assertGreater(len(client.messages), 2)
        list(service.send('사용자 변수명 추천해줘'))
        self.assertEqual(len(client.messages),2)

    def test_attachment_followup_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder)/'sample.yaml'; file.write_text('price 1000')
            service = ChatService(client=FakeClient())
            list(service.send('요약해줘', (ChatAttachmentPayload.from_path(file),)))
            list(service.send('방금 파일에서 문법이 잘못된 부분을 설명해줘. 수정 코드는 필요 없어.'))
            self.assertEqual(service.history[-1].metadata['intent'], 'document_question')

    def test_history_budget_and_oversize(self):
        client = FakeClient(); service = ChatService(client=client)
        history = [ChatMessagePayload(role, 'x'*2000) for _ in range(20) for role in ('user','assistant')]
        service.set_history(history)
        list(service.send('계속 설명해줘'))
        self.assertLessEqual(sum(len(m.content) for m in client.messages),12000)
        self.assertEqual(client.messages[1].role,'user')
        self.assertEqual(len(service.history),42)
        with self.assertRaises(ContextLimitExceeded): list(service.send('x'*13000))

    def test_attachment_snapshot_and_migration(self):
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path', return_value=Path(folder)/'test.db'):
            database.initialize(); database.initialize()
            file = Path(folder)/'document.txt'; file.write_text('Project budget is 1234 won.')
            service = ChatService(client=FakeClient())
            attachment = ChatAttachmentPayload.from_path(file)
            list(service.send('요약해줘',(attachment,)))
            snapshot = service.history[0].content
            session = chat_store.create_session()
            row = chat_store.add_message(session.id,'user','요약해줘',snapshot)
            chat_store.add_attachment(row.id,str(file),'text/plain')
            saved = chat_store.get_messages(session.id)[0]
            file.unlink()
            restored = service.restore_message(ChatMessagePayload('user',saved.content,(attachment,)),saved.model_content)
            self.assertIn('1234',restored.content)
            self.assertFalse(restored.attachments)
            service.set_history([restored,ChatMessagePayload('assistant','summary')])
            list(service.send('예산이 얼마라고 했지?'))
            self.assertTrue(any('1234' in m.content for m in service._client.messages))

    def test_memo_typing_ime_undo(self):
        editor = MemoTextEdit(); highlighter = MarkdownHighlighter(editor.document())
        editor.show(); editor.setFocus()
        QTest.keyClicks(editor,'# ')
        for char in 'abc':
            QTest.keyClicks(editor,char); app.processEvents()
            block = editor.document().firstBlock()
            for span in block.layout().formats():
                if span.start <= len(editor.toPlainText())-1 < span.start+span.length:
                    self.assertNotEqual(span.format.foreground().color().alpha(),0)
        event = QInputMethodEvent(); event.setCommitString('한글')
        QApplication.sendEvent(editor,event); app.processEvents()
        self.assertEqual(editor.toPlainText(),'# abc한글')
        editor.undo(); self.assertNotEqual(editor.toPlainText(),'# abc한글')
        editor.close()

    def test_todo_check_persists_until_delete(self):
        from storage import todo_store
        from ui.widgets.todo_view import TodoView
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path', return_value=Path(folder)/'test.db'):
            database.initialize()
            view = TodoView(); view.resize(360,400); view.show()
            view.add_todo('완료 후에도 남는 긴 할 일 ' * 5); app.processEvents()
            item = view._items[0]
            QTest.mouseClick(item._checkbox, Qt.MouseButton.LeftButton)
            QTest.qWait(120)
            self.assertEqual(len(view._items),1)
            self.assertTrue(todo_store.get_all()[0].done)
            reopened = TodoView()
            self.assertEqual(len(reopened._items),1)
            self.assertTrue(reopened._items[0]._checkbox.isChecked())
            QTest.mouseClick(item._checkbox, Qt.MouseButton.LeftButton)
            self.assertFalse(todo_store.get_all()[0].done)
            QTest.mouseClick(item._delete_button, Qt.MouseButton.LeftButton)
            self.assertFalse(todo_store.get_all())
            self.assertFalse(view._items)
            view.close(); reopened.close()

    def test_chat_scroll_after_layout_growth(self):
        from ui.widgets.chat_view import ChatView
        with patch("storage.chat_store.get_all_sessions", return_value=[]):
            view = ChatView()
        view.resize(360,400); view.show()
        for _ in range(8): view._add_message('user','긴 문장입니다. ' * 35)
        QTest.qWait(80)
        bar = view._scroll_area.verticalScrollBar()
        self.assertGreater(bar.maximum(),0)
        bar.setValue(0)
        with patch.object(view._worker,'start'):
            view._send_message('새로 보낸 긴 내용 ' * 60)
            QTest.qWait(80)
            self.assertEqual(bar.value(),bar.maximum())
            view._append_assistant_token('응답이 길어집니다. ' * 120)
            QTest.qWait(80)
            self.assertEqual(bar.value(),bar.maximum())
            view._finish_response('응답이 길어집니다. ' * 120)
            QTest.qWait(80)
            self.assertEqual(bar.value(),bar.maximum())
        view.close()

    def test_heading_and_fence_first_character_visible(self):
        import time
        editor = MemoTextEdit(); highlighter = MarkdownHighlighter(editor.document())
        editor.show(); editor.setFocus()
        for prefix in ('# ', '## ', '### ', '```python\n'):
            editor.clear()
            QTest.keyClicks(editor,prefix.rstrip('\n'))
            if prefix.endswith('\n'): QTest.keyClick(editor,Qt.Key.Key_Return)
            start = time.perf_counter()
            QTest.keyClicks(editor,'a'); app.processEvents()
            self.assertLess(time.perf_counter()-start,0.1)
            block = editor.textCursor().block()
            self.assertGreater(editor.cursorRect().height(),5)
            for span in block.layout().formats():
                if span.start <= len(block.text())-1 < span.start+span.length:
                    self.assertNotEqual(span.format.foreground().color().alpha(),0)
                    self.assertGreater(span.format.fontPointSize(),1)
        editor.close()

    def test_code_fence_space_shortcut_and_hidden_markers(self):
        editor = MemoTextEdit(); highlighter = MarkdownHighlighter(editor.document())
        editor.cursorPositionChanged.connect(lambda: highlighter.set_active_block(editor.textCursor().blockNumber()))
        highlighter.set_active_block(0)
        editor.show(); editor.setFocus()
        QTest.keyClicks(editor,'```python '); app.processEvents()
        self.assertEqual(editor.toPlainText(),'```python\n\n```')
        self.assertEqual(editor.textCursor().blockNumber(),1)
        QTest.keyClicks(editor,'print(1)'); app.processEvents()
        self.assertGreater(editor.cursorRect().height(),5)
        fence = editor.document().firstBlock()
        self.assertTrue(any(span.format.foreground().color().alpha()==0 for span in fence.layout().formats()))
        QTest.keyClick(editor,Qt.Key.Key_Return); app.processEvents()
        self.assertEqual(editor.toPlainText().count('```'),2)
        self.assertEqual(editor.textCursor().blockNumber(),3)
        QTest.keyClicks(editor,'# title'); app.processEvents()
        QTest.keyClick(editor,Qt.Key.Key_Return); app.processEvents()
        heading = editor.document().findBlockByNumber(3)
        self.assertTrue(any(span.start==0 and span.format.foreground().color().alpha()==0 for span in heading.layout().formats()))
        editor.close()

    def test_todos_grouped_by_local_creation_date(self):
        from storage import todo_store
        from ui.widgets.todo_view import TodoView
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path',return_value=Path(folder)/'test.db'):
            database.initialize()
            for text, stamp in [('old','2026-10-02T03:00:00Z'),('new A','2026-10-03T16:00:00Z'),('new B','2026-10-04T01:00:00Z')]:
                todo = todo_store.add(text)
                with database.get_connection() as conn:
                    conn.execute('UPDATE todos SET created_at=? WHERE id=?',(stamp,todo.id))
            view = TodoView()
            self.assertEqual(len(view._date_headers),2)
            self.assertEqual([i._todo.text for i in view._items],['new A','new B','old'])
            view.remove_item(view._items[-1])
            self.assertEqual(len(view._date_headers),1)
            view.close()

    def test_nested_prose_and_code_rendering(self):
        text = '1. **컬럼**\n   - 이름: 상품\n   - 가격: 100\n2. **샘플**\n   - 값: 사과\n\n```python\ndef f():\n    return 1\n```\n\n주의: 확인하세요.'
        bubble = MessageBubble('assistant',text)
        bubble.render_markdown(); bubble.show(); app.processEvents()
        self.assertEqual(len(bubble._rendered_code_blocks),1)
        self.assertEqual(bubble._body.document().indentWidth(),18)
        self.assertIn('컬럼',bubble._body.toPlainText())
        bubble.close()

if __name__ == '__main__': unittest.main()
