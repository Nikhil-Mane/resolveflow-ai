# Learning Progress

This file records the current learning state for future sessions. Update it
whenever a concept or implementation milestone is completed.

## Preferred learning workflow

For every new topic:

1. Explain the concept before changing code.
2. Give a simple practical example and execution flow.
3. Explain why the concept is used.
4. Explain reasonable alternatives.
5. Explain what happens when the concept is not used.
6. Wait for confirmation that the concept is understood.
7. Implement it in the existing `support_agent` project.
8. Run tests and explain exactly which files and code changed.

Do not create a separate tutorial project unless explicitly requested.

## Completed concepts

- LangChain chat-model abstraction with Azure OpenAI and `.env` configuration
- LangChain `@tool`, tool schemas, `bind_tools()`, and model-driven tool choice
- REST API tool: `get_public_todo`
- Basic lexical RAG tool: `search_support_policies`
- Delegated normal-LLM tool: `answer_general_question`
- Narrow parameterized SQLite tool: `lookup_order`
- Local MCP server over `stdio`: `get_support_hours`
- Multi-tool questions and tool-result synthesis
- LangGraph `StateGraph`, `MessagesState`, nodes, edges, and `ToolNode`
- Conditional routing with `tools_condition`
- Agent loop from assistant to tools and back to assistant
- Process-local memory with `InMemorySaver`
- Durable local memory with `AsyncSqliteSaver`
- Checkpoints, `thread_id`, thread isolation, and restart persistence
- User-scoped conversation keys using `user_id` plus `thread_id`
- FastAPI application factory and lifespan resource management
- Pydantic API request and response validation
- `GET /health` and `POST /chat`
- Per-thread asynchronous request locking
- Server-Sent Events and `Content-Type: text/event-stream`
- LangGraph `astream_events()`
- `POST /chat/stream` with session, tool, token, completion, and error events
- Client-disconnection handling during streaming
- Difference between SSE, WebSocket, and WebRTC
- Offline unit tests, fake-agent dependency injection, and CI basics
- Organized FastAPI package under `support_agent/api/`
- React component state, TypeScript contracts, and Vite development workflow
- Browser Fetch `ReadableStream` integration with POST-based SSE
- FastAPI serving of the built React frontend

## Current implementation

The existing project contains:

```text
support_agent/
|-- api/
|   |-- __init__.py
|   |-- app.py
|   `-- schemas.py
|-- agent.py
|-- config.py
|-- local_tools.py
|-- mcp_server.py
|-- knowledge_base.md
`-- README.md

tests/
|-- test_agent_memory.py
|-- test_api.py
`-- test_local_tools.py
```

Current HTTP endpoints:

```text
GET  /health
POST /chat
POST /chat/stream
```

The latest verified test suite contains 15 passing tests.

## Next concept

**Structured LangGraph state**

Explain how explicit fields such as `user_id`, `selected_order`,
`retrieved_policies`, `tools_used`, `workflow_status`, and `errors` differ from
keeping all information only in `MessagesState`. Do not implement it until the
concept has been explained and confirmed.

## Pending topics

Recommended order:

1. Structured LangGraph state
2. Structured tool/domain response models
3. Structured configuration and startup validation
4. Timeouts, retries, error categories, and graceful fallbacks
5. Production RAG with embeddings, hybrid search, citations, and evaluation
6. Authentication, authorization, and tenant isolation
7. Human approval for sensitive or write operations
8. LangSmith or OpenTelemetry tracing and quality evaluation
9. Production Postgres/Cosmos checkpoint storage
10. Docker, deployment, monitoring, and rollback
11. Locked dependencies, linting, formatting, typing, and pre-commit hooks

## Important current limitations

- `user_id` is caller-supplied namespacing, not authentication.
- SQLite checkpointing is intended for local development, not distributed
  production workers.
- RAG uses lexical matching rather than embeddings or hybrid retrieval.
- Database tools use fictional sample data and do not perform identity checks.
- Streaming improves responsiveness but does not make model or tool execution
  faster.
- Production security, observability, evaluation, resilience, and deployment
  controls remain pending.

See `support_agent/README.md` for the implementation walkthrough and
`ROADMAP.md` for the production milestones.
