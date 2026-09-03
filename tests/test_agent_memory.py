"""Offline tests for LangGraph conversation-memory behavior."""

import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph

from support_agent.agent import create_checkpointer, thread_config


def build_test_graph(checkpointer=None):
    """Build a deterministic graph so memory can be tested without an LLM."""

    def count_messages(state: MessagesState):
        return {"messages": [AIMessage(content=str(len(state["messages"])))]}

    builder = StateGraph(MessagesState)
    builder.add_node("count_messages", count_messages)
    builder.add_edge(START, "count_messages")
    builder.add_edge("count_messages", END)
    return builder.compile(checkpointer=checkpointer or create_checkpointer())


class AgentMemoryTests(unittest.TestCase):
    def test_same_thread_accumulates_messages(self) -> None:
        graph = build_test_graph()
        config = thread_config("conversation-a")

        graph.invoke({"messages": [("human", "first")]}, config=config)
        second = graph.invoke(
            {"messages": [("human", "second")]},
            config=config,
        )

        self.assertEqual(4, len(second["messages"]))

    def test_different_threads_are_isolated(self) -> None:
        graph = build_test_graph()

        graph.invoke(
            {"messages": [("human", "thread A")]},
            config=thread_config("conversation-a"),
        )
        thread_b = graph.invoke(
            {"messages": [("human", "thread B")]},
            config=thread_config("conversation-b"),
        )

        self.assertEqual(2, len(thread_b["messages"]))

    def test_empty_thread_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            thread_config("   ")


class DurableAgentMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_sqlite_restores_same_thread_after_saver_reopens(self) -> None:
        """Closing and reopening the saver simulates a process restart."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "conversations.db"
            config = thread_config("shared-conversation")

            async with AsyncSqliteSaver.from_conn_string(
                str(database_path)
            ) as first_saver:
                await first_saver.setup()
                first_graph = build_test_graph(checkpointer=first_saver)
                await first_graph.ainvoke(
                    {"messages": [("human", "first")]},
                    config=config,
                )

            async with AsyncSqliteSaver.from_conn_string(
                str(database_path)
            ) as second_saver:
                await second_saver.setup()
                second_graph = build_test_graph(checkpointer=second_saver)
                result = await second_graph.ainvoke(
                    {"messages": [("human", "second")]},
                    config=config,
                )

            self.assertEqual(4, len(result["messages"]))


if __name__ == "__main__":
    unittest.main()
