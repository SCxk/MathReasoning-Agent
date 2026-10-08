import json
import os
import unittest
from io import StringIO
from contextlib import redirect_stderr
import tempfile
import requests
from unittest.mock import Mock, patch

from llm_client import (
    ChatCompletionError,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_MODE,
    InternChatClient,
)


class InternChatClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(
            os.environ,
            {
                "INTERN_API_KEY": "test-token",
                "INTERN_MODEL": "test-model",
            },
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    def successful_response(message):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": message}]}
        return response

    @patch("llm_client.requests.post")
    def test_keeps_existing_defaults_and_text_response(self, post: Mock) -> None:
        post.return_value = self.successful_response(
            {"role": "assistant", "content": "hello"}
        )
        messages = [{"role": "user", "content": "hi"}]

        result = InternChatClient().chat(messages)

        self.assertEqual(result, "hello")
        self.assertEqual(post.call_args.kwargs["timeout"], 240)
        payload = json.loads(post.call_args.kwargs["data"])
        self.assertEqual(
            payload,
            {
                "model": "test-model",
                "messages": messages,
                "temperature": DEFAULT_TEMPERATURE,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "thinking_mode": DEFAULT_THINKING_MODE,
            },
        )

    @patch("llm_client.requests.post")
    def test_long_phase_request_uses_one_full_budget_http_attempt(self, post: Mock) -> None:
        post.side_effect = requests.Timeout("slow model")

        with self.assertRaisesRegex(RuntimeError, "after 1 attempts"):
            InternChatClient(timeout=240, retry=3).chat(
                [{"role": "user", "content": "solve"}],
                request_timeout=600,
            )

        self.assertEqual(post.call_count, 1)
        self.assertAlmostEqual(post.call_args.kwargs["timeout"], 600.0, places=3)

    @patch("llm_client.requests.post")
    def test_forwards_defaults_and_per_call_args(self, post: Mock) -> None:
        post.return_value = self.successful_response(
            {"role": "assistant", "content": "done"}
        )
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        client = InternChatClient(
            default_args={
                "thinking_mode": True,
                "temperature": 0.6,
                "top_p": 0.9,
            },
            n=2,
        )

        client.chat(
            [{"role": "user", "content": "1 + 1"}],
            temperature=0.1,
            max_tokens=128,
            thinking_mode=False,
            tools=tools,
            tool_choice="auto",
            top_p=0.8,
        )

        payload = json.loads(post.call_args.kwargs["data"])
        self.assertEqual(payload["temperature"], 0.1)
        self.assertEqual(payload["max_tokens"], 128)
        self.assertIs(payload["thinking_mode"], False)
        self.assertEqual(payload["tools"], tools)
        self.assertEqual(payload["tool_choice"], "auto")
        self.assertEqual(payload["top_p"], 0.8)
        self.assertEqual(payload["n"], 2)

    @patch("llm_client.requests.post")
    def test_can_return_complete_message_for_plain_content(self, post: Mock) -> None:
        message = {"role": "assistant", "content": "hello"}
        post.return_value = self.successful_response(message)

        result = InternChatClient().chat(
            [{"role": "user", "content": "hi"}],
            return_message=True,
        )

        self.assertEqual(result, message)

    @patch("llm_client.requests.post")
    def test_returns_complete_message_for_tool_calls(self, post: Mock) -> None:
        message = {
            "role": "assistant",
            "content": "calculate",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "calculate",
                        "arguments": '{"expression": "1 + 1"}',
                    },
                }
            ],
        }
        post.return_value = self.successful_response(message)

        result = InternChatClient().chat(
            [{"role": "user", "content": "1 + 1"}],
            tools=[],
        )

        self.assertEqual(result, message)

    @patch("llm_client.requests.post")
    def test_accepts_multimodal_and_tool_messages(self, post: Mock) -> None:
        post.return_value = self.successful_response(
            {"role": "assistant", "content": "done"}
        )
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "describe"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/image.png"},
                    },
                ],
            },
            {
                "role": "assistant",
                "content": "calculate",
                "tool_calls": [{"id": "call-1", "type": "function"}],
            },
            {
                "role": "tool",
                "content": '{"result": 2}',
                "tool_call_id": "call-1",
            },
        ]

        InternChatClient().chat(messages)

        payload = json.loads(post.call_args.kwargs["data"])
        self.assertEqual(payload["messages"], messages)

    @patch("llm_client.requests.post")
    def test_does_not_log_request_summary_for_success(self, post: Mock) -> None:
        post.return_value = self.successful_response(
            {"role": "assistant", "content": "done"}
        )
        messages = [{"role": "user", "content": "hello"}]
        stderr = StringIO()

        with patch("llm_client.DEBUG_CHAT_REQUESTS", True), redirect_stderr(stderr):
            InternChatClient().chat(messages, max_tokens=256)

        output = stderr.getvalue()
        self.assertEqual(output, "")
        self.assertEqual(post.call_count, 1)

    @patch("llm_client.requests.post")
    def test_logs_request_summary_for_http_400(self, post: Mock) -> None:
        response_400 = Mock()
        response_400.status_code = 400
        response_400.text = '{"error":"bad request"}'
        post.side_effect = requests.HTTPError("400 Client Error", response=response_400)
        messages = [{"role": "user", "content": "hello"}]
        stderr = StringIO()

        with patch("llm_client.DEBUG_CHAT_REQUESTS", True), redirect_stderr(stderr):
            with self.assertRaises(ChatCompletionError) as raised:
                InternChatClient(retry=1).chat(messages, max_tokens=256)

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.response_body, '{"error":"bad request"}')
        output = stderr.getvalue()
        self.assertIn("[intern_chat_request]", output)
        self.assertIn('"message_count": 1', output)
        self.assertIn('"chars": 5', output)
        self.assertIn('"preview": "hello"', output)
        self.assertIn('"started_at":', output)
        self.assertIn('"ended_at":', output)
        self.assertIn('"duration_seconds":', output)
        self.assertIn('"response_body": "{\\"error\\":\\"bad request\\"}"', output)
        self.assertEqual(post.call_count, 1)

    @patch("llm_client.requests.post")
    def test_request_summary_truncates_response_body(self, post: Mock) -> None:
        response_400 = Mock()
        response_400.status_code = 400
        response_400.text = "x" * 1200
        post.side_effect = requests.HTTPError("400 Client Error", response=response_400)
        stderr = StringIO()

        with patch("llm_client.DEBUG_CHAT_REQUESTS", True), redirect_stderr(stderr):
            with self.assertRaises(RuntimeError):
                InternChatClient(retry=1).chat([{"role": "user", "content": "hello"}])

        summary = json.loads(stderr.getvalue().removeprefix("[intern_chat_request] "))
        self.assertEqual(len(summary["response_body"]), 1000)

    @patch("llm_client.requests.post")
    def test_dump_request_payload_for_http_400(self, post: Mock) -> None:
        response_400 = Mock()
        response_400.status_code = 400
        response_400.text = '{"error":"bad request"}'
        post.side_effect = requests.HTTPError("400 Client Error", response=response_400)
        messages = [{"role": "user", "content": "hello"}]
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("llm_client.DUMP_CHAT_REQUESTS", True), patch(
                "llm_client.DUMP_CHAT_REQUEST_DIR", temp_dir
            ):
                with self.assertRaises(RuntimeError):
                    InternChatClient(retry=1).chat(messages, max_tokens=256)

            dumped = list(os.listdir(temp_dir))
            self.assertEqual(len(dumped), 1)
            self.assertIn("-400-attempt-1.json", dumped[0])
            with open(os.path.join(temp_dir, dumped[0]), encoding="utf-8") as handle:
                dump = json.load(handle)
            self.assertEqual(dump["status_code"], 400)
            self.assertEqual(dump["payload"]["messages"], messages)
            self.assertEqual(dump["payload"]["max_tokens"], 256)
            self.assertIsInstance(dump["started_at"], str)
            self.assertIsInstance(dump["ended_at"], str)
            self.assertIsInstance(dump["duration_seconds"], float)
            self.assertGreaterEqual(dump["duration_seconds"], 0.0)
            self.assertIn("bad request", dump["response_body"])

    @patch("llm_client.requests.post")
    def test_dumps_successful_request_payload_without_console_log(self, post: Mock) -> None:
        post.return_value = self.successful_response(
            {"role": "assistant", "content": "done"}
        )
        messages = [{"role": "user", "content": "hello"}]
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("llm_client.DUMP_CHAT_REQUESTS", True), patch(
                "llm_client.DUMP_CHAT_REQUEST_DIR", temp_dir
            ), patch("llm_client.DEBUG_CHAT_REQUESTS", True), redirect_stderr(stderr):
                InternChatClient().chat(messages, max_tokens=256)

            dumped = list(os.listdir(temp_dir))
            self.assertEqual(len(dumped), 1)
            self.assertIn("-200-attempt-1.json", dumped[0])
            with open(os.path.join(temp_dir, dumped[0]), encoding="utf-8") as handle:
                dump = json.load(handle)
            self.assertTrue(dump["success"])
            self.assertEqual(dump["status_code"], 200)
            self.assertIsInstance(dump["started_at"], str)
            self.assertIsInstance(dump["ended_at"], str)
            self.assertIsInstance(dump["duration_seconds"], float)
            self.assertGreaterEqual(dump["duration_seconds"], 0.0)
            self.assertEqual(dump["payload"]["messages"], messages)
            self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
