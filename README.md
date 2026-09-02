# ResolveFlow AI

An evolving customer-support agent built with LangChain, LangGraph, Azure
OpenAI, and the Model Context Protocol (MCP). The repository starts with a
small, understandable agent loop and documents the path toward a secure,
observable, production-grade service.

> Current stage: **Foundation** - working CLI agent, five tool capabilities,
> automated tests, and continuous integration.

## Why this project is interview-worthy

ResolveFlow AI demonstrates more than a chatbot. It shows how an LLM can be
placed inside a controlled workflow and grounded in purpose-built tools:

- **Agent orchestration:** LangGraph routes between model decisions and tools.
- **Tool integration:** REST, retrieval, SQLite, a delegated LLM call, and MCP.
- **Grounded answers:** policy questions use a local knowledge source instead
  of relying on model memory.
- **Safe data access:** order lookup uses a narrow, validated, parameterized
  query rather than unrestricted model-generated SQL.
- **Engineering evolution:** the [roadmap](ROADMAP.md) separates a learning
  prototype from the controls required in production.

## Architecture

```mermaid
flowchart LR
    User --> Agent[LangGraph assistant node]
    Agent -->|tool request| Tools[LangGraph ToolNode]
    Tools --> REST[REST API]
    Tools --> RAG[Policy retrieval]
    Tools --> DB[(SQLite)]
    Tools --> LLM[Azure OpenAI]
    Tools --> MCP[MCP server]
    REST --> Agent
    RAG --> Agent
    DB --> Agent
    LLM --> Agent
    MCP --> Agent
    Agent -->|final response| User
```

The model selects a capability, LangGraph executes it, and the tool result is
returned to the model before it produces a grounded response.

## Quick start

Prerequisites: Python 3.11+ and access to an Azure OpenAI chat deployment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill in the three Azure values in `.env`, then run:

```powershell
python -m support_agent.agent --list-tools
python -m support_agent.agent
```

Example prompts:

```text
Look up ORD-101 and tell me whether its product has a warranty.
Can an unused product be returned after 20 days?
What are the human support hours in India?
```

Run the offline test suite (no API key or network call required):

```powershell
python -m unittest discover -s tests -v
```

## Repository map

```text
support_agent/                  Main agent package
  agent.py                      LangGraph workflow and CLI
  local_tools.py                REST, retrieval, LLM, and database tools
  mcp_server.py                 Local MCP server over stdio
  knowledge_base.md             Example support policies
tests/                          Offline unit tests
simple_langgraph.py             API-key-free introductory graph
azure_langchain_langgraph.py    Introductory Azure OpenAI graph
ROADMAP.md                      Prototype-to-production plan
```

For a detailed explanation of every capability and design tradeoff, see the
[support agent walkthrough](support_agent/README.md).

## Security notes

- Secrets are loaded from `.env`, which is excluded from Git.
- `.env.example` contains placeholders only.
- Database access is read-only at the tool boundary and uses parameterized SQL.
- All included customer and order data is fictional demonstration data.

This is an educational foundation, not yet a production deployment. See the
[roadmap](ROADMAP.md) for the missing authentication, authorization,
observability, evaluation, resilience, and deployment controls.
