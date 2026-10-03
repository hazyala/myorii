import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from core.llm.chat_service import ChatService, DEFAULT_MODEL
from core.llm.contracts import ChatMessagePayload
from core.tools.chat_tools import ChatTools, ToolPlanError, tool_target
from storage import database, memo_store, todo_store

app = QApplication.instance() or QApplication([])


class ScriptClient:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def list_models(self):
        return [DEFAULT_MODEL]

    def stream_chat(self, model, messages):
        self.requests.append((model, messages))
        response = next(self.responses)
        yield response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)


def plan(action, target='todo', **kwargs):
    return dict(action=action, target=target, **kwargs)


class ChatToolTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = patch('storage.database.db_path', return_value=Path(self.folder.name) / 'test.db')
        self.db.start()
        database.initialize()

    def tearDown(self):
        self.db.stop()
        self.folder.cleanup()

    def service(self, *responses):
        client = ScriptClient(*responses)
        return ChatService(client=client), client

    def test_add_and_previous_answer_and_summary(self):
        service, client = self.service(
            plan('add', content='우유 사기'),
            plan('add', 'memo', source='previous_assistant', title='직전 답변'),
            plan('add', content='발표 준비하기', source='text'),
            {'content': '발표 준비하기'},
        )
        self.assertIn('추가했습니다', ''.join(service.send('할일에 우유 사기 추가해줘')))
        self.assertEqual(todo_store.get_all()[0].text, '우유 사기')
        service.set_history([ChatMessagePayload('user', '발표 준비해야 해'), ChatMessagePayload('assistant', '자료를 준비하세요.')])
        list(service.send('/memo 방금 답변 메모에 저장해줘'))
        self.assertEqual(memo_store.get_all()[0].body, '자료를 준비하세요.')
        list(service.send('/todo 방금 한말 요약해서 할일에 적어줘'))
        self.assertEqual(todo_store.get_all()[-1].text, '발표 준비하기')
        self.assertIn('발표 준비해야 해', client.requests[-1][1][-1].content)
        self.assertNotIn('저장해줘', json.loads(client.requests[-1][1][-1].content)['original'])

    def test_previous_user_and_missing_history(self):
        service, _ = self.service(plan('add', source='previous_user'), plan('add', content='invented'))
        service.set_history([ChatMessagePayload('user', '보고서 보내기'), ChatMessagePayload('assistant', '네')])
        list(service.send('/todo 방금 한 말 저장해줘'))
        self.assertEqual(todo_store.get_all()[0].text, '보고서 보내기')
        service.clear()
        self.assertIn('찾지 못했습니다', ''.join(service.send('/todo 방금 답변 요약해서 저장해줘')))
        self.assertEqual(len(todo_store.get_all()), 1)

    def test_pending_only_and_empty(self):
        todo_store.add('미완료')
        done = todo_store.add('완료')
        todo_store.toggle(done.id)
        service, client = self.service(plan('list'), plan('list'))
        answer = ''.join(service.send('오늘 뭐 해야 하지?'))
        self.assertIn('미완료', answer)
        self.assertNotIn('- 완료', answer)
        todo_store.toggle(todo_store.get_all()[0].id)
        self.assertIn('없습니다', ''.join(service.send('/todo 오늘 뭐 해야 하지?')))
        self.assertEqual(len(client.requests), 2)

    def test_semantic_search_and_titles(self):
        memo = memo_store.add('출장 일정', '부산 회의는 오후 3시')
        memo_store.add('요리', '파스타 레시피')
        service, client = self.service(plan('search', 'memo', query='부산 미팅'), {'ids': [memo.id]}, '오후 3시입니다.')
        answer = ''.join(service.send('/memo 부산 미팅 언제야?'))
        self.assertIn('참고한 메모: 출장 일정', answer)
        self.assertNotIn('파스타', client.requests[-1][1][-1].content)
        self.assertEqual(service.history[-1].metadata['intent'], 'memo_search')

    def test_empty_search_never_generates_answer(self):
        service, client = self.service(plan('search', 'memo', query='회의'))
        self.assertIn('찾지 못했습니다', ''.join(service.send('/memo 회의 찾아줘')))
        self.assertEqual(len(client.requests), 1)
        memo_store.add('요리', '파스타')
        service, client = self.service(plan('search', 'memo', query='회의'), {'ids': []})
        self.assertIn('찾지 못했습니다', ''.join(service.send('메모에서 회의 찾아줘')))
        self.assertEqual(len(client.requests), 2)

    def test_bad_plans_do_not_write(self):
        for response in ('bad JSON', plan('delete'), plan('add', 'memo', content='bad'), plan('add', content=123)):
            service, _ = self.service(response)
            with self.assertRaises(ToolPlanError):
                list(service.send('/todo 우유 추가해줘'))
        self.assertEqual(todo_store.get_all(), [])
        self.assertEqual(memo_store.get_all(), [])
        service, _ = self.service(plan('add', content='oops'))
        with self.assertRaises(ToolPlanError): list(service.send('/todo 오늘 뭐 해야 하지?'))

    def test_invalid_search_id_does_not_invent_source(self):
        memo_store.add('회의', '부산')
        service, _ = self.service(plan('search', 'memo'), {'ids': [999]})
        with self.assertRaises(ToolPlanError): list(service.send('/memo 부산 찾아줘'))

    def test_long_memo_searches_all_chunks(self):
        memo = memo_store.add('긴 메모', 'x' * 9000 + '부산 회의 3시')
        service, client = self.service(plan('search', 'memo', query='부산'), {'ids': []}, {'ids': [memo.id]}, '3시입니다.')
        answer = ''.join(service.send('/memo 부산 회의 언제야?'))
        self.assertIn('3시', answer)
        self.assertIn('부산 회의 3시', client.requests[-1][1][-1].content)

    def test_cloud_providers_use_same_tools(self):
        for provider in ('openai', 'gemini', 'anthropic'):
            client = ScriptClient(plan('add', content=provider), plan('list'),
                                  plan('add', 'memo', content='부산 회의 3시', title='회의'),
                                  plan('search', 'memo', query='부산'),
                                  {'ids': [('openai', 'gemini', 'anthropic').index(provider) + 1]}, '3시입니다.')
            service = ChatService()
            service.set_backend(provider, 'selected-model')
            with patch('core.llm.cloud_client.CloudClient', return_value=client):
                list(service.send('/todo ' + provider + ' 추가해줘'))
                self.assertIn(provider, ''.join(service.send('/todo 오늘 뭐 해야 하지?')))
                list(service.send('/memo 부산 회의 3시 추가해줘'))
                self.assertIn('참고한 메모: 회의', ''.join(service.send('/memo 부산 일정 찾아줘')))
                memo_store.delete(('openai', 'gemini', 'anthropic').index(provider) + 1)
            self.assertTrue(all(model == 'selected-model' for model, _ in client.requests))

    def test_non_tool_request_and_none(self):
        service, client = self.service('일반 답변', plan('none', 'memo'), '메모 설명')
        self.assertEqual(''.join(service.send('안녕')), '일반 답변')
        self.assertEqual(''.join(service.send('메모가 뭔지 설명해줘')), '메모 설명')

    def test_tags_space_boundaries_and_conflict(self):
        self.assertEqual(tool_target('/todo 오늘'), 'todo')
        for text in ('/todo', 'https://a/todo x', '/todos x', 'abc/todo x'):
            self.assertIsNone(tool_target(text))
        with self.assertRaises(ToolPlanError): tool_target('/todo /memo 추가해줘')



if __name__ == '__main__':
    unittest.main()
