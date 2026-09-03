"""Interactive five-capability agent built with LangChain and LangGraph."""

import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

# When this file is run directly from inside support_agent, Python only adds
# that folder to sys.path. Add the project root so package imports also work.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from support_agent.config import create_model
from support_agent.local_tools import build_local_tools


MCP_SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"
DEFAULT_MEMORY_DB_PATH = Path(__file__).resolve().parent / "conversations.db"

SYSTEM_PROMPT = """You are a small educational customer-support agent.
Use the available tools instead of inventing factual results.
- Use get_public_todo for a numbered sample REST todo.
- Use search_support_policies for returns, refunds, shipping, or warranties.
- Use answer_general_question for general knowledge or explanations.
- Use lookup_order for sample order IDs such as ORD-101.
- Use get_support_hours for regional human-support hours through MCP.
You may call more than one tool when a question needs multiple sources.
After tools return, provide a short answer and mention which source types you used.
Use plain ASCII punctuation in the final answer.
"""


def create_checkpointer() -> InMemorySaver:
    """Create process-local storage for short-term conversation memory."""

    return InMemorySaver()


def thread_config(thread_id: str) -> dict[str, dict[str, str]]:
    """Build the LangGraph configuration that identifies one conversation."""

    if not thread_id.strip():
        raise ValueError("thread_id must not be empty")
    return {"configurable": {"thread_id": thread_id}}


async def build_agent(checkpointer: Any | None = None) -> tuple[Any, list[Any]]:
    """Load all tools and compile the LangGraph agent loop."""

    model = create_model()
    local_tools = build_local_tools(model)

    mcp_client = MultiServerMCPClient(
        {
            "sample_support": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [str(MCP_SERVER_PATH)],
            }
        }
    )
    mcp_tools = await mcp_client.get_tools()
    all_tools = [*local_tools, *mcp_tools]
    model_with_tools = model.bind_tools(all_tools)

    async def call_model(state: MessagesState) -> dict[str, list[Any]]:
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("assistant", call_model)
    builder.add_node("tools", ToolNode(all_tools))
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "assistant")
    # Tests and library callers can omit a saver and receive process-local memory.
    if checkpointer is None:
        checkpointer = create_checkpointer()
    return builder.compile(checkpointer=checkpointer), all_tools


def used_tool_names(messages: list[Any]) -> list[str]:
    """Collect tool names requested by the model for learning/debug output."""

    names: list[str] = []
    for message in messages:
        for call in getattr(message, "tool_calls", []):
            name = call.get("name")
            if name and name not in names:
                names.append(name)
    return names


async def run_cli(agent: Any, tools: list[Any], args: argparse.Namespace) -> None:
    """Run the interactive prompt using one compiled agent/checkpointer."""

    if args.list_tools:
        print("Available tools:")
        for loaded_tool in tools:
            print(f"- {loaded_tool.name}: {loaded_tool.description}")
        return

    thread_id = args.thread_id
    memory_type = "in-memory" if args.in_memory else f"SQLite ({args.memory_db})"
    print("Five-capability support agent with conversation memory.")
    print("Commands: /new starts a new conversation; exit stops the program.")
    print(f"Memory: {memory_type}")
    print(f"Thread: {thread_id}")
    while True:
        try:
            question = input("\nYou: ").strip()
        except EOFError:
            break
        if question.lower() in {"exit", "quit"}:
            break
        if question.lower() == "/new":
            thread_id = f"support-{uuid.uuid4().hex[:8]}"
            print(f"Started a new conversation. Thread: {thread_id}")
            continue
        if not question:
            continue

        config = thread_config(thread_id)
        result = await agent.ainvoke(
            {"messages": [("human", question)]},
            config=config,
        )
        names = used_tool_names(result["messages"])
        print(f"Tools used: {', '.join(names) if names else 'none'}")
        print(f"Agent: {result['messages'][-1].text}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="load the agent, print its tool names, and exit",
    )
    parser.add_argument(
        "--thread-id",
        default="support-session",
        help="conversation-memory ID (default: support-session)",
    )
    parser.add_argument(
        "--memory-db",
        default=str(DEFAULT_MEMORY_DB_PATH),
        help="SQLite checkpoint database used for durable conversation memory",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="use process-local memory instead of durable SQLite checkpoints",
    )
    args = parser.parse_args()

    if args.in_memory:
        agent, tools = await build_agent()
        await run_cli(agent, tools, args)
        return

    memory_db_path = Path(args.memory_db).expanduser().resolve()
    memory_db_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(memory_db_path)) as checkpointer:
        await checkpointer.setup()
        agent, tools = await build_agent(checkpointer=checkpointer)
        await run_cli(agent, tools, args)


if __name__ == "__main__":
    asyncio.run(main())
