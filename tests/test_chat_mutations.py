import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.llm.chat_service import ChatService, DEFAULT_MODEL
from core.tools.chat_tools import ChatTools, ToolPlanError
from storage import database, memo_store, todo_store


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


def plan(action, target, **fields):
    return {'action': action, 'target': target, **fields}


class MutationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = patch('storage.database.db_path', return_value=Path(self.folder.name)/'test.db')
        self.db.start()
        database.initialize()

    def tearDown(self):
        self.db.stop()
        self.folder.cleanup()

    def service(self, *responses):
        client = ScriptClient(*responses)
        return ChatService(client=client), client

    def test_todo_update_and_delete_preserve_status_order_dates(self):
        todo = todo_store.add('우유 사기')
        todo_store.toggle(todo.id)
        before = todo_store.get_all()[0]
        service, _ = self.service(plan('update', 'todo', query='우유 사기'), {'text': '두유 사기'},
                                  plan('delete', 'todo', query='두유 사기'))
        self.assertIn('수정했습니다', ''.join(service.send('/todo 우유 사기를 두유 사기로 바꿔줘')))
        after = todo_store.get_all()[0]
        self.assertEqual((after.id, after.done, after.ord, after.created_at),
                         (before.id, before.done, before.ord, before.created_at))
        self.assertEqual(after.text, '두유 사기')
        self.assertIn('삭제했습니다', ''.join(service.send('할일 두유 사기 삭제해줘')))
        self.assertEqual(todo_store.get_all(), [])

    def test_memo_title_only_body_edit_append_and_delete(self):
        memo = memo_store.add('부산 출장', '회의 3시\n준비물: 노트북')
        service, client = self.service(plan('update', 'memo', query='부산 출장'), {'title': '출장 일정'},
                                       plan('update', 'memo', query='출장 일정'), {'body': '회의 4시\n준비물: 노트북'},
                                       plan('update', 'memo', query='출장 일정'), {'body': '회의 4시\n준비물: 노트북\n충전기'},
                                       plan('delete', 'memo', query='출장 일정'))
        list(service.send('/memo 부산 출장 제목만 출장 일정으로 수정해줘'))
        self.assertEqual(memo_store.get(memo.id).body, memo.body)
        list(service.send('/memo 출장 일정 메모에서 회의 3시를 4시로 수정해줘'))
        self.assertEqual(memo_store.get(memo.id).title, '출장 일정')
        list(service.send('/memo 출장 일정 본문에 충전기를 덧붙이도록 수정해줘'))
        saved = memo_store.get(memo.id)
        self.assertEqual(saved.body, '회의 4시\n준비물: 노트북\n충전기')
        self.assertEqual((saved.ord, saved.created_at), (memo.ord, memo.created_at))
        self.assertIn('준비물: 노트북', client.requests[3][1][-1].content)
        list(service.send('/memo 출장 일정 삭제해줘'))
        self.assertIsNone(memo_store.get(memo.id))

    def test_ambiguous_duplicate_titles_require_explicit_id(self):
        first = memo_store.add('회의', '부산')
        second = memo_store.add('회의', '서울')
        service, _ = self.service(plan('delete', 'memo', query='회의'),
                                  plan('delete', 'memo', item_id=second.id))
        response = ''.join(service.send('/memo 회의 삭제해줘'))
        self.assertIn('여러 항목', response)
        self.assertIn(f'myorii://memo/{first.id}', response)
        self.assertEqual(len(memo_store.get_all()), 2)
        list(service.send(f'/memo #{second.id} 삭제해줘'))
        self.assertIsNotNone(memo_store.get(first.id))
        self.assertIsNone(memo_store.get(second.id))

    def test_missing_bulk_and_invalid_ids_do_not_delete(self):
        todo_store.add('우유 사기')
        service, _ = self.service(plan('delete', 'todo', query='보고서'), {'ids': []},
                                  plan('delete', 'todo', query=''), plan('delete', 'todo', item_id=999))
        self.assertIn('찾지 못했습니다', ''.join(service.send('/todo 보고서 삭제해줘')))
        self.assertIn('지정해주세요', ''.join(service.send('/todo 모두 삭제해줘')))
        self.assertIn('찾지 못했습니다', ''.join(service.send('/todo #999 삭제해줘')))
        service, _ = self.service(plan('delete', 'todo', item_id=1))
        with self.assertRaises(ToolPlanError): list(service.send('/todo 우유 사기 삭제해줘'))
        self.assertEqual(len(todo_store.get_all()), 1)

    def test_negation_and_readonly_requests_never_mutate(self):
        todo_store.add('우유 사기')
        for action, text in (('delete', '/todo 우유 사기 삭제하지 말고 읽어줘'),
                             ('update', '/todo 우유 사기 수정하지 말고 읽어줘'),
                             ('delete', '/todo 우유 사기 삭제하는 방법 알려줘'),
                             ('update', '/todo 우유 사기 언제 해야 하지?')):
            service, _ = self.service(plan(action, 'todo', query='우유 사기'))
            with self.assertRaises(ToolPlanError): list(service.send(text))
        self.assertEqual(todo_store.get_all()[0].text, '우유 사기')

    def test_partial_body_deletion_is_update_not_item_deletion(self):
        memo = memo_store.add('회의', '준비물: 노트북\n충전기')
        service, _ = self.service(plan('delete', 'memo', query='회의'))
        with self.assertRaises(ToolPlanError): list(service.send('/memo 회의 본문에서 충전기 문장 지워줘'))
        self.assertIsNotNone(memo_store.get(memo.id))
        service, _ = self.service(plan('update', 'memo', query='회의'), {'body': '준비물: 노트북'})
        list(service.send('/memo 회의 본문에서 충전기 문장 지워줘'))
        self.assertEqual(memo_store.get(memo.id).body, '준비물: 노트북')

    def test_memo_generic_text_response_is_replanned_not_reinterpreted(self):
        memo = memo_store.add('회의', '본문')
        service, client = self.service(plan('update', 'memo', query='회의'), {'text': '새 제목'}, {'title': '새 제목'})
        list(service.send('/memo 회의 제목만 새 제목으로 수정해줘'))
        self.assertEqual(memo_store.get(memo.id).title, '새 제목')
        self.assertEqual(memo_store.get(memo.id).body, '본문')
        self.assertIn('correction', client.requests[-1][1][-1].content)
        service, _ = self.service(plan('update', 'memo', query='새 제목'))
        with self.assertRaises(ToolPlanError): list(service.send('/memo 새 제목 본문은 지우지 마'))
        self.assertEqual(memo_store.get(memo.id).body, '본문')

    def test_invalid_update_responses_do_not_modify(self):
        memo = memo_store.add('회의', '3시')
        for changes in ('bad json', {'body': 123}, {'unexpected': 'bad'}, {}, {'body': 'x'*20001}):
            service, _ = self.service(plan('update', 'memo', query='회의'), changes)
            with self.assertRaises(ToolPlanError): list(service.send('/memo 회의 본문 수정해줘'))
            self.assertEqual(memo_store.get(memo.id).body, '3시')

    def test_concurrent_update_is_not_overwritten(self):
        memo = memo_store.add('회의', '3시')
        responses = iter([plan('update', 'memo', query='회의'), {'body': '4시'}])
        def complete(messages):
            response = next(responses)
            if 'original' in messages[-1].content:
                memo_store.update(memo.id, '회의', '5시로 직접 수정')
            return json.dumps(response, ensure_ascii=False)
        answer, intent = ChatTools(complete).execute('/memo 회의를 4시로 수정해줘', ())
        self.assertEqual(intent, 'tool_conflict')
        self.assertEqual(memo_store.get(memo.id).body, '5시로 직접 수정')

    def test_conditional_delete_does_not_remove_changed_record(self):
        todo = todo_store.add('우유 사기')
        todo_store.toggle(todo.id)
        self.assertFalse(todo_store.delete_if_unchanged(todo))
        self.assertIsNone(todo_store.update_if_unchanged(todo, '두유 사기'))
        memo = memo_store.add('회의', '3시')
        memo_store.update(memo.id, '회의', '4시')
        self.assertFalse(memo_store.delete_if_unchanged(memo))
        self.assertEqual(len(todo_store.get_all()), 1)
        self.assertEqual(len(memo_store.get_all()), 1)

    def test_all_api_providers_update_and_delete_both_stores(self):
        for provider in ('openai', 'gemini', 'anthropic'):
            todo_store.add('우유 사기')
            memo_store.add('회의', '3시')
            client = ScriptClient(plan('update', 'todo', query='우유 사기'), {'text': '두유 사기'},
                                  plan('delete', 'todo', query='두유 사기'),
                                  plan('update', 'memo', query='회의'), {'body': '4시'},
                                  plan('delete', 'memo', query='회의'))
            service = ChatService()
            service.set_backend(provider, 'selected-model')
            with patch('core.llm.cloud_client.CloudClient', return_value=client):
                list(service.send('/todo 우유 사기를 두유 사기로 수정해줘'))
                list(service.send('/todo 두유 사기 삭제해줘'))
                list(service.send('/memo 회의 시간을 4시로 수정해줘'))
                list(service.send('/memo 회의 삭제해줘'))
            self.assertEqual(todo_store.get_all(), [])
            self.assertEqual(memo_store.get_all(), [])
            self.assertTrue(all(model == 'selected-model' for model, _ in client.requests))
