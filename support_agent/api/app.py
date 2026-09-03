"""FastAPI application factory for the existing LangGraph support agent."""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from support_agent.agent import (
    DEFAULT_MEMORY_DB_PATH,
    build_agent,
    thread_config,
    used_tool_names,
)
from support_agent.api.schemas import ChatRequest, ChatResponse, HealthResponse


LOGGER = logging.getLogger(__name__)


def conversation_key(user_id: str, thread_id: str) -> str:
    """Namespace a client thread so different users cannot collide by accident."""

    return f"user:{user_id}:thread:{thread_id}"


def current_turn_tool_names(messages: list[Any]) -> list[str]:
    """Return tool names requested after the most recent human message."""

    last_human_index = 0
    for index, message in enumerate(messages):
        if getattr(message, "type", None) == "human":
            last_human_index = index
    return used_tool_names(messages[last_human_index:])


def encode_sse(event: str, data: dict[str, Any]) -> str:
    """Encode one JSON payload using the Server-Sent Events wire format."""

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(
    *,
    agent: Any | None = None,
    tools: list[Any] | None = None,
    memory_db_path: str | Path = DEFAULT_MEMORY_DB_PATH,
    frontend_dist_path: str | Path | None = None,
) -> FastAPI:
    """Create the web application, with optional dependencies for offline tests."""

    supplied_agent = agent
    supplied_tools = tools or []
    database_path = Path(memory_db_path).expanduser().resolve()
    frontend_path = Path(frontend_dist_path).resolve() if frontend_dist_path else (
        Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.thread_locks = defaultdict(asyncio.Lock)

        if supplied_agent is not None:
            application.state.agent = supplied_agent
            application.state.tools = supplied_tools
            yield
            return

        database_path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(
            str(database_path)
        ) as checkpointer:
            await checkpointer.setup()
            loaded_agent, loaded_tools = await build_agent(checkpointer=checkpointer)
            application.state.agent = loaded_agent
            application.state.tools = loaded_tools
            yield

    application = FastAPI(
        title="ResolveFlow AI Support Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.post("/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        public_thread_id = payload.thread_id or f"thread-{uuid.uuid4().hex[:12]}"
        internal_thread_id = conversation_key(payload.user_id, public_thread_id)
        config = thread_config(internal_thread_id)

        # One process can serve different threads concurrently, while requests
        # for the same thread are ordered to avoid conflicting checkpoints.
        lock = request.app.state.thread_locks[internal_thread_id]
        try:
            async with lock:
                result = await request.app.state.agent.ainvoke(
                    {"messages": [("human", payload.message)]},
                    config=config,
                )
        except Exception as error:
            LOGGER.exception("Agent invocation failed")
            raise HTTPException(
                status_code=503,
                detail="The support agent is temporarily unavailable.",
            ) from error

        messages = result["messages"]
        return ChatResponse(
            answer=messages[-1].text,
            user_id=payload.user_id,
            thread_id=public_thread_id,
            tools_used=current_turn_tool_names(messages),
        )

    @application.post(
        "/chat/stream",
        response_class=StreamingResponse,
        responses={
            200: {
                "content": {"text/event-stream": {}},
                "description": "Server-Sent Events containing agent progress",
            }
        },
    )
    async def stream_chat(payload: ChatRequest, request: Request) -> StreamingResponse:
        public_thread_id = payload.thread_id or f"thread-{uuid.uuid4().hex[:12]}"
        internal_thread_id = conversation_key(payload.user_id, public_thread_id)
        config = thread_config(internal_thread_id)

        async def event_stream() -> AsyncIterator[str]:
            tool_names: list[str] = []
            yield encode_sse(
                "session",
                {
                    "user_id": payload.user_id,
                    "thread_id": public_thread_id,
                },
            )

            lock = request.app.state.thread_locks[internal_thread_id]
            try:
                async with lock:
                    async for event in request.app.state.agent.astream_events(
                        {"messages": [("human", payload.message)]},
                        config=config,
                        version="v2",
                    ):
                        if await request.is_disconnected():
                            return

                        event_type = event.get("event")
                        event_name = event.get("name", "unknown")
                        if event_type == "on_tool_start":
                            if event_name not in tool_names:
                                tool_names.append(event_name)
                            yield encode_sse("tool_start", {"name": event_name})
                        elif event_type == "on_tool_end":
                            yield encode_sse("tool_end", {"name": event_name})
                        elif event_type == "on_chat_model_stream":
                            metadata = event.get("metadata", {})
                            if metadata.get("langgraph_node") != "assistant":
                                continue
                            chunk = event.get("data", {}).get("chunk")
                            text = getattr(chunk, "text", "")
                            if text:
                                yield encode_sse("token", {"text": text})

                yield encode_sse("done", {"tools_used": tool_names})
            except asyncio.CancelledError:
                LOGGER.info(
                    "Streaming client disconnected from thread %s",
                    internal_thread_id,
                )
                raise
            except Exception:
                LOGGER.exception("Streaming agent invocation failed")
                yield encode_sse(
                    "error",
                    {"message": "The support agent is temporarily unavailable."},
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    if frontend_path.is_dir():
        application.mount(
            "/",
            StaticFiles(directory=frontend_path, html=True),
            name="frontend",
        )

    return application


app = create_app()
