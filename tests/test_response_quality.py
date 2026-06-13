from __future__ import annotations

import unittest

from core.llm.chat_service import ChatService, EmptyModelResponse
from core.llm.contracts import ChatMessagePayload, ChatRequest
from core.llm.ollama_client import OllamaClient
from core.llm.router import IntentRouter, ModelRouter, ResponseFormatter
from ui.widgets.message_bubble import MessageBubble


class FakeOllamaClient:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def chat(self, **kwargs):
        self.kwargs = kwargs
        yield {"message": {"thinking": "hidden reasoning"}}
        yield {"message": {"content": "answer"}}


class EmptyStreamChatClient:
    def list_models(self) -> list[str]:
        return ["qwen3-vl:4b", "qwen3:1.7b"]

    def stream_chat(self, model: str, messages: list[ChatMessagePayload]):
        if False:
            yield ""


class ResponseQualityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.router = IntentRouter()
        self.formatter = ResponseFormatter()

    def _request(self, text: str) -> ChatRequest:
        return ChatRequest(
            model="qwen3-vl:4b",
            user_message=ChatMessagePayload(role="user", content=text),
        )

    def test_ollama_chat_disables_thinking_stream(self) -> None:
        client = OllamaClient()
        fake_client = FakeOllamaClient()
        client._client = fake_client

        tokens = list(client.stream_chat("qwen3:1.7b", [ChatMessagePayload(role="user", content="안녕")]))

        self.assertEqual(tokens, ["answer"])
        self.assertIs(fake_client.kwargs["think"], False)
        self.assertIs(fake_client.kwargs["stream"], True)

    def test_empty_model_response_is_explicit_error(self) -> None:
        service = ChatService(client=EmptyStreamChatClient())

        with self.assertRaisesRegex(EmptyModelResponse, "모델 응답이 비어 있습니다"):
            list(service.send("자바 덧셈 변수명 3개만 추천해줘봐"))

        self.assertEqual(service._messages, [])

    def test_general_summary_stays_plain_streaming_text(self) -> None:
        request = self._request("이 내용 요약해줘")
        route = self.router.route(request)

        self.assertEqual(route.intent, "simple_chat")
        self.assertFalse(self.formatter.should_buffer(route.intent))
        self.assertEqual(
            self.formatter.format("핵심은 응답 포맷 정리입니다.", route.intent, request),
            "핵심은 응답 포맷 정리입니다.",
        )

    def test_plain_analysis_without_code_context_stays_simple_chat(self) -> None:
        request = self._request("분석해줘")
        route = self.router.route(request)

        self.assertEqual(route.intent, "simple_chat")
        self.assertFalse(self.formatter.should_buffer(route.intent))

    def test_java_variable_names_are_copyable_text_blocks(self) -> None:
        request = self._request("자바 덧셈 변수명 3개만 추천해줘봐")
        route = self.router.route(request)

        self.assertEqual(route.intent, "naming_variable")
        self.assertTrue(self.formatter.should_buffer(route.intent))
        self.assertEqual(
            self.formatter.format("sum\ntotal\naddResult", route.intent, request),
            "```text\nsum\n```\n\n"
            "```text\ntotal\n```\n\n"
            "```text\naddResult\n```",
        )

    def test_general_name_recommendation_keeps_short_intro(self) -> None:
        request = self._request("사용자 이름 변수명 추천")
        route = self.router.route(request)

        self.assertEqual(
            self.formatter.format("user_name", route.intent, request),
            "가장 무난한 후보입니다.\n\n```python\nuser_name\n```",
        )

    def test_python_variable_names_keep_python_blocks(self) -> None:
        request = self._request("사용자 이름 변수명 추천")
        route = self.router.route(request)

        self.assertEqual(route.intent, "naming_variable")
        self.assertIn("```python\nuser_name\n```", self.formatter.format("user_name", route.intent, request))

    def test_short_word_translation_is_copyable_text_block(self) -> None:
        request = self._request("단어 사과 영어로 뭐야?")
        route = self.router.route(request)

        self.assertEqual(route.intent, "translate")
        self.assertEqual(self.formatter.format("apple", route.intent, request), "```text\napple\n```")

    def test_sentence_translation_stays_plain_text(self) -> None:
        request = self._request("처음 뵙겠습니다 영어로 번역해줘")
        route = self.router.route(request)

        self.assertEqual(route.intent, "translate")
        self.assertEqual(self.formatter.format("Nice to meet you.", route.intent, request), "Nice to meet you.")

    def test_code_generation_uses_requested_language_fences(self) -> None:
        cases = (
            ("자바 코드 줘 사용자 클래스", "public class User {\n    private String name;\n}", "java"),
            ("HTML 코드 줘 로그인 폼", '<form>\n    <input type="text" name="email">\n</form>', "html"),
            ("CSS 코드 줘 버튼 스타일", ".button {\n    display: flex;\n}", "css"),
            ("C언어 코드 줘 hello world", '#include <stdio.h>\n\nint main(void) {\n\treturn 0;\n}', "c"),
            ("활성 사용자 조회 SQL문 줘", "SELECT *\nFROM users\nWHERE active = true;", "sql"),
        )

        for prompt, output, language in cases:
            with self.subTest(prompt=prompt):
                request = self._request(prompt)
                route = self.router.route(request)
                formatted = self.formatter.format(output, route.intent, request)

                self.assertEqual(route.intent, "code_generation")
                self.assertTrue(formatted.startswith(f"```{language}\n"))
                self.assertTrue(formatted.endswith("\n```"))
                self.assertIn(output, formatted)

    def test_command_formatter_drops_language_label_lines(self) -> None:
        request = self._request("터미널에서 현재 폴더 파일 목록 보는 명령어 알려줘")
        route = self.router.route(request)

        self.assertEqual(route.intent, "command")
        self.assertEqual(self.formatter.format("bash\nls", route.intent, request), "```bash\nls\n```")

    def test_markdown_renderer_preserves_text_after_code_order(self) -> None:
        self.assertTrue(
            MessageBubble._should_preserve_markdown_order(
                [
                    ("text", "설명입니다."),
                    ("code", "print('hello')"),
                    ("text", "주의점입니다."),
                ]
            )
        )

    def test_code_generation_uses_selected_model_not_fast_text_model(self) -> None:
        request = self._request("자바 코드 줘 사용자 클래스")
        route = self.router.route(request)
        model_route = ModelRouter().route(request, route.intent, ("qwen3-vl:4b", "qwen3:1.7b"))

        self.assertEqual(route.intent, "code_generation")
        self.assertEqual(model_route.model, "qwen3-vl:4b")
        self.assertEqual(model_route.reason, "code_generation_selected_model")
        self.assertFalse(
            MessageBubble._should_preserve_markdown_order(
                [
                    ("text", "가장 무난한 후보입니다."),
                    ("code", "sum"),
                    ("code", "total"),
                ]
            )
        )


if __name__ == "__main__":
    unittest.main()
