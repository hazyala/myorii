import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from datetime import date, datetime, time, timedelta, timezone
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

    def test_reference_alias_and_plan_context_budget(self):
        service, client = self.service(plan('add', 'memo', source='text', content='wrong'))
        history = [ChatMessagePayload(role, 'x' * 3000) for _ in range(10) for role in ('user', 'assistant')]
        service.set_history(history)
        list(service.send('/memo 그거 저장해줘'))
        self.assertEqual(memo_store.get_all()[0].body, history[-1].content)
        self.assertLessEqual(sum(len(m.content) for m in client.requests[0][1]), 12000)

    def test_oversized_summary_does_not_save_truncated_content(self):
        service, _ = self.service(plan('add', content='invented'))
        service.set_history([ChatMessagePayload('user', '원문' * 10000), ChatMessagePayload('assistant', '답변')])
        with self.assertRaises(ToolPlanError):
            list(service.send('/todo 방금 한말 요약해서 저장해줘'))
        self.assertEqual(todo_store.get_all(), [])

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

    def test_yesterday_pending_uses_local_creation_date(self):
        yesterday = date.today() - timedelta(days=1)
        old = todo_store.add('어제 남은 일')
        done = todo_store.add('어제 완료한 일')
        todo_store.toggle(done.id)
        today_item = todo_store.add('오늘 추가한 일')
        two_days = todo_store.add('그제 추가한 일')
        local_zone = datetime.now().astimezone().tzinfo
        with database.get_connection() as conn:
            for item, day in ((old, yesterday), (done, yesterday), (today_item, date.today()), (two_days, yesterday-timedelta(days=1))):
                # A local midnight may be the previous date in UTC (e.g. Seoul).
                timestamp = datetime.combine(day, time(0, 30), local_zone).astimezone(timezone.utc).isoformat()
                conn.execute('UPDATE todos SET created_at=? WHERE id=?', (timestamp, item.id))
        service, client = self.service(plan('list'))
        answer = ''.join(service.send('어제 할일중에 아직 못한거 남았나?'))
        self.assertIn('어제 남은 일', answer)
        for excluded in ('어제 완료한 일', '오늘 추가한 일', '그제 추가한 일'):
            self.assertNotIn(excluded, answer)
        self.assertIn(yesterday.isoformat(), answer)
        self.assertEqual(len(client.requests), 1)
        todo_store.toggle(old.id)
        service, _ = self.service(plan('list'))
        self.assertIn('없습니다', ''.join(service.send('/todo 어제 할일중에 아직 못한거 남았나?')))

    def test_date_range_and_invalid_dates(self):
        todo = todo_store.add('지난달 보고서')
        with database.get_connection() as conn:
            conn.execute("UPDATE todos SET created_at='2026-09-15T12:00:00Z' WHERE id=?", (todo.id,))
        service, _ = self.service(plan('list', date_from='2026-09-01', date_to='2026-09-30'))
        self.assertIn('지난달 보고서', ''.join(service.send('/todo 9월에 추가한 미완료 할일 알려줘')))
        for bounds in ({'date_from': '2026-02-30'}, {'date_from': 'yesterday'}, {'date_from': 123},
                       {'date_from': '2026-09-30', 'date_to': '2026-09-01'}):
            service, _ = self.service(plan('list', **bounds))
            with self.assertRaises(ToolPlanError):
                list(service.send('/todo 해당 기간에 추가한 일 조회해줘'))

    def test_conversation_summary_uses_both_sides_and_all_turns(self):
        service, client = self.service(plan('add', 'memo', source='conversation', content='잘못된 계획 내용'),
                                       {'title': '부산 출장 계획', 'content': '부산 출장을 정하고 회의 시간을 오후 3시로 확정했다.'})
        service.set_history([
            ChatMessagePayload('user', '부산 출장을 가기로 했어'),
            ChatMessagePayload('assistant', '회의 시간을 정해주세요.'),
            ChatMessagePayload('user', '회의는 오후 3시로 하자'),
            ChatMessagePayload('assistant', '오후 3시로 정했습니다.'),
        ])
        list(service.send('/memo 지금 우리가 대화 한 내용 요약해서 적어줘'))
        summary_request = json.loads(client.requests[-1][1][-1].content)
        self.assertEqual([m['role'] for m in summary_request['conversation']], ['user', 'assistant', 'user', 'assistant'])
        self.assertIn('부산 출장을 가기로 했어', str(summary_request))
        self.assertEqual(memo_store.get_all()[0].body, '부산 출장을 정하고 회의 시간을 오후 3시로 확정했다.')
        self.assertNotIn('잘못된', memo_store.get_all()[0].body)
        self.assertEqual(memo_store.get_all()[0].title, '부산 출장 계획')

    def test_conversation_empty_and_save_confirmations(self):
        service, _ = self.service(plan('add', 'memo', source='conversation', content='invented'))
        self.assertIn('찾지 못했습니다', ''.join(service.send('/memo 지금 대화 내용 요약해서 적어줘')))
        self.assertEqual(memo_store.get_all(), [])
        service, _ = self.service(plan('add', 'memo', source='conversation', content='invented'))
        service.set_history([ChatMessagePayload('user', '/memo 테스트 저장해줘'),
                             ChatMessagePayload('assistant', '메모에 저장했습니다. 테스트')])
        self.assertIn('찾지 못했습니다', ''.join(service.send('/memo 지금 대화 내용 요약해서 적어줘')))
        self.assertEqual(memo_store.get_all(), [])

    def test_long_conversation_summary_covers_oldest_and_latest(self):
        service, client = self.service(plan('add', 'memo', source='conversation'),
                                       {'content': '첫 계획: 부산 출장을 간다.'},
                                       {'content': '마지막 계획: 회의는 오후 3시다.'},
                                       {'content': '부산 출장, 회의 오후 3시.'})
        service.set_history([ChatMessagePayload('user', '부산 출장 ' + '가' * 4000),
                             ChatMessagePayload('assistant', '확인 ' + '나' * 4000),
                             ChatMessagePayload('user', '마지막 회의는 오후 3시'),
                             ChatMessagePayload('assistant', '3시 확인')])
        list(service.send('지금 우리가 대화 한 내용 요약해서 적어줘'))
        requests = [json.loads(messages[-1].content) for _, messages in client.requests[1:]]
        chunks = [str(request['conversation']) for request in requests[:-1]]
        self.assertIn('부산 출장', ''.join(chunks))
        self.assertIn('마지막 회의는 오후 3시', ''.join(chunks))
        self.assertTrue(all(sum(len(m.content) for m in messages) <= 12000 for _, messages in client.requests))
        self.assertEqual(memo_store.get_all()[0].body, '부산 출장, 회의 오후 3시.')

    def test_summary_relative_date_is_corrected_before_save(self):
        service, client = self.service(plan('add', 'memo', source='conversation'),
                                       {'content': '이번 주 부산 출장'}, {'content': '다음 주 부산 출장'})
        service.set_history([ChatMessagePayload('user', '다음 주 부산 출장'), ChatMessagePayload('assistant', '확인')])
        list(service.send('/memo 지금 대화 내용 요약해서 적어줘'))
        self.assertEqual(memo_store.get_all()[0].body, '다음 주 부산 출장')
        self.assertIn('correction', client.requests[-1][1][-1].content)

    def test_summary_relative_date_failure_does_not_save(self):
        service, _ = self.service(plan('add', 'memo', source='conversation'),
                                  {'content': '이번 주 부산 출장'}, {'content': '내일 부산 출장'})
        service.set_history([ChatMessagePayload('user', '다음 주 부산 출장'), ChatMessagePayload('assistant', '확인')])
        with self.assertRaises(ToolPlanError): list(service.send('/memo 지금 대화 내용 요약해서 적어줘'))
        self.assertEqual(memo_store.get_all(), [])

    def test_cloud_date_lookup_and_conversation_summary(self):
        yesterday = date.today() - timedelta(days=1)
        todo = todo_store.add('어제 보고서')
        local_zone = datetime.now().astimezone().tzinfo
        timestamp = datetime.combine(yesterday, time(12), local_zone).isoformat()
        with database.get_connection() as conn:
            conn.execute('UPDATE todos SET created_at=? WHERE id=?', (timestamp, todo.id))
        for provider in ('openai', 'gemini', 'anthropic'):
            client = ScriptClient(plan('list'), plan('add', 'memo', source='conversation'), {'content': '회의 3시'})
            service = ChatService()
            service.set_backend(provider, 'selected-model')
            with patch('core.llm.cloud_client.CloudClient', return_value=client):
                self.assertIn('어제 보고서', ''.join(service.send('어제 할일중에 아직 못한거 남았나?')))
                service.set_history([ChatMessagePayload('user', '회의 3시'), ChatMessagePayload('assistant', '확인')])
                list(service.send('/memo 지금 우리가 대화 한 내용 요약해서 적어줘'))
            self.assertTrue(all(model == 'selected-model' for model, _ in client.requests))
        self.assertEqual([memo.body for memo in memo_store.get_all()], ['회의 3시'] * 3)

    def test_semantic_search_and_titles(self):
        memo = memo_store.add('출장 일정', '부산 회의는 오후 3시')
        memo_store.add('요리', '파스타 레시피')
        service, client = self.service(plan('search', 'memo', query='부산 미팅'), {'ids': [memo.id]}, '오후 3시입니다.')
        answer = ''.join(service.send('/memo 부산 미팅 언제야?'))
        self.assertIn('참고한 메모: [출장 일정](myorii://memo/', answer)
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
                self.assertIn('참고한 메모: [회의](myorii://memo/', ''.join(service.send('/memo 부산 일정 찾아줘')))
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
