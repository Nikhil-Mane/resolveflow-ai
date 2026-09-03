"""Offline tests for the FastAPI boundary."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from support_agent.api import conversation_key, create_app


class FakeAgent:
    """Small test double that avoids Azure OpenAI and network calls."""

    def __init__(self) -> None:
        self.calls = []
        self.stream_calls = []

    async def ainvoke(self, state, config):
        self.calls.append((state, config))
        return {
            "messages": [
                HumanMessage(content=state["messages"][0][1]),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "lookup_order",
                            "args": {"order_id": "ORD-101"},
                            "id": "test-call",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="Test answer"),
            ]
        }

    async def astream_events(self, state, config, version):
        self.stream_calls.append((state, config, version))
        yield {
            "event": "on_tool_start",
            "name": "lookup_order",
            "data": {},
            "metadata": {"langgraph_node": "tools"},
        }
        yield {
            "event": "on_tool_end",
            "name": "lookup_order",
            "data": {},
            "metadata": {"langgraph_node": "tools"},
        }
        yield {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "data": {"chunk": AIMessageChunk(content="Test ")},
            "metadata": {"langgraph_node": "assistant"},
        }
        yield {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "data": {"chunk": AIMessageChunk(content="answer")},
            "metadata": {"langgraph_node": "assistant"},
        }


class SupportApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = FakeAgent()
        self.app = create_app(agent=self.agent)

    def test_health_endpoint(self) -> None:
        with TestClient(self.app) as client:
            response = client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ok"}, response.json())

    def test_chat_invokes_existing_agent_with_namespaced_thread(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/chat",
                json={
                    "message": "Look up ORD-101",
                    "user_id": "user-7",
                    "thread_id": "orders",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "answer": "Test answer",
                "user_id": "user-7",
                "thread_id": "orders",
                "tools_used": ["lookup_order"],
            },
            response.json(),
        )
        self.assertEqual(
            conversation_key("user-7", "orders"),
            self.agent.calls[0][1]["configurable"]["thread_id"],
        )

    def test_chat_generates_thread_id_when_omitted(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/chat",
                json={"message": "Hello", "user_id": "user-7"},
            )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["thread_id"].startswith("thread-"))

    def test_chat_rejects_blank_message(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/chat",
                json={"message": "   ", "user_id": "user-7"},
            )

        self.assertEqual(422, response.status_code)

    def test_chat_rejects_invalid_identifier(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/chat",
                json={"message": "Hello", "user_id": "user:7"},
            )

        self.assertEqual(422, response.status_code)

    def test_stream_chat_returns_progress_tokens_and_completion(self) -> None:
        with TestClient(self.app) as client:
            with client.stream(
                "POST",
                "/chat/stream",
                json={
                    "message": "Look up ORD-101",
                    "user_id": "user-7",
                    "thread_id": "orders",
                },
            ) as response:
                body = "\n".join(response.iter_lines())

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertIn("event: session", body)
        self.assertIn('"thread_id": "orders"', body)
        self.assertIn("event: tool_start", body)
        self.assertIn('"name": "lookup_order"', body)
        self.assertIn('data: {"text": "Test "}', body)
        self.assertIn('data: {"text": "answer"}', body)
        self.assertIn("event: done", body)
        self.assertEqual("v2", self.agent.stream_calls[0][2])
        self.assertEqual(
            conversation_key("user-7", "orders"),
            self.agent.stream_calls[0][1]["configurable"]["thread_id"],
        )

    def test_built_react_frontend_can_be_served(self) -> None:
        with TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text(
                "<h1>ResolveFlow UI</h1>", encoding="utf-8"
            )
            app = create_app(agent=self.agent, frontend_dist_path=directory)
            with TestClient(app) as client:
                response = client.get("/")

        self.assertEqual(200, response.status_code)
        self.assertIn("ResolveFlow UI", response.text)


if __name__ == "__main__":
    unittest.main()
