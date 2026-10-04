import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication
from core.tools.links import memo_reference
from storage import database, memo_store
from ui.widgets.message_bubble import MessageBubble
from ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])


class MemoLinkTests(unittest.TestCase):
    def test_links_render_and_click_after_code_blocks(self):
        for prefix in ('답변입니다.\n\n', '```python\nprint(1)\n```\n\n'):
            bubble = MessageBubble('assistant', prefix + '참고한 메모: ' + memo_reference(12, '회의 [부산] *일정*'))
            bubble.render_markdown()
            requested = []
            bubble.memo_requested.connect(requested.append)
            browser = bubble._rendered_text_blocks[-1] if bubble._rendered_text_blocks else bubble._body
            self.assertIn('myorii://memo/12', browser.toHtml())
            self.assertIn('회의 [부산] *일정*', browser.toPlainText())
            browser.anchorClicked.emit(QUrl('myorii://memo/12'))
            self.assertEqual(requested, [12])

    def test_internal_links_never_launch_external_handler(self):
        bubble = MessageBubble('assistant', '')
        requested = []
        bubble.memo_requested.connect(requested.append)
        with patch('ui.widgets.message_bubble.QDesktopServices.openUrl') as external:
            for link in ('myorii://memo/0', 'myorii://memo/12?delete=true', 'myorii://todo/1',
                         'myorii://memo/-1', 'myorii://memo/12/extra', 'file:///tmp/test'):
                bubble._open_link(QUrl(link))
            self.assertEqual(requested, [])
            external.assert_not_called()
            bubble._open_link(QUrl('https://example.com'))
            external.assert_called_once()

    def test_navigation_flushes_edits_and_opens_current_memo(self):
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path', return_value=Path(folder)/'test.db'), \
                patch('ui.main_window.ModelWarmupWorker.start'), patch('ui.main_window.ModelListWorker.start'), \
                patch('ui.main_window.InternetStatusWatcher.check_now'):
            database.initialize()
            first = memo_store.add('명시한 제목', '첫 메모')
            second = memo_store.add('다음 메모', '둘째 본문')
            window = MainWindow()
            window._chat_view.memo_requested.emit(first.id)
            self.assertEqual(window._content_stack.currentIndex(), 2)
            self.assertTrue(window._tabs_group.button(2).isChecked())
            self.assertEqual(window._memo_view._editor._editor.toPlainText(), '첫 메모')
            window._select_content_tab(0)
            self.assertEqual(memo_store.get(first.id).title, '명시한 제목')
            window._open_memo(first.id)
            window._memo_view._editor._editor.setPlainText('수정 중인 본문')
            window._open_memo(second.id)
            self.assertEqual(memo_store.get(first.id).body, '수정 중인 본문')
            memo_store.delete(second.id)
            with patch('ui.main_window.QMessageBox.information') as message:
                window._open_memo(second.id)
                message.assert_called_once()
            window.close()

    def test_open_editor_tracks_chat_update_and_delete(self):
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path', return_value=Path(folder)/'test.db'), \
                patch('ui.main_window.ModelWarmupWorker.start'), patch('ui.main_window.ModelListWorker.start'), \
                patch('ui.main_window.InternetStatusWatcher.check_now'):
            database.initialize()
            memo = memo_store.add('회의', '3시')
            window = MainWindow()
            window._open_memo(memo.id)
            memo_store.update_if_unchanged(memo, '회의 일정', '4시')
            window._refresh_tool_storage()
            self.assertEqual(window._memo_view._editor._editor.toPlainText(), '4시')
            window._select_content_tab(0)
            self.assertEqual(memo_store.get(memo.id).title, '회의 일정')
            window._open_memo(memo.id)
            memo_store.delete(memo.id)
            window._refresh_tool_storage()
            self.assertIsNone(window._memo_view._editor._memo)
            self.assertTrue(window._memo_view._editor.isHidden())
            window.close()

    def test_unsaved_editor_does_not_overwrite_chat_changes(self):
        with tempfile.TemporaryDirectory() as folder, patch('storage.database.db_path', return_value=Path(folder)/'test.db'), \
                patch('ui.main_window.ModelWarmupWorker.start'), patch('ui.main_window.ModelListWorker.start'), \
                patch('ui.main_window.InternetStatusWatcher.check_now'):
            database.initialize()
            memo = memo_store.add('회의', '3시')
            window = MainWindow()
            window._open_memo(memo.id)
            window._memo_view._editor._editor.setPlainText('아직 저장하지 않은 수정')
            memo_store.update_if_unchanged(memo, '회의', '채팅에서 4시로 변경')
            window._refresh_tool_storage()
            window._memo_view._editor.save_now()
            self.assertEqual(memo_store.get(memo.id).body, '채팅에서 4시로 변경')
            self.assertEqual(window._memo_view._editor._editor.toPlainText(), '아직 저장하지 않은 수정')
            window.close()
