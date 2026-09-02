# ResolveFlow AI: Production Roadmap

The project will evolve in small, demonstrable stages. Each stage should end
with tests, documentation, and a runnable demo so the Git history tells a clear
engineering story.

## Stage 1 - Foundation (current)

- [x] LangGraph model-tool loop
- [x] REST, policy retrieval, LLM, SQLite, and MCP capabilities
- [x] Environment-based secret handling
- [x] Offline unit tests and GitHub Actions CI
- [x] Architecture and setup documentation

## Stage 2 - Reliable application

- [ ] Move to a `src/` package and locked dependency workflow
- [ ] Add structured configuration and startup validation
- [ ] Introduce typed domain models and structured tool responses
- [ ] Add timeouts, retries, error categories, and graceful fallbacks
- [ ] Add conversation checkpointing and session identifiers
- [ ] Expose the graph through a FastAPI service with health endpoints
- [ ] Add linting, formatting, type checking, and pre-commit hooks

## Stage 3 - Production RAG and quality

- [ ] Replace lexical matching with embeddings plus hybrid retrieval
- [ ] Add chunk metadata, source citations, and confidence thresholds
- [ ] Create a versioned evaluation dataset for routing and answer quality
- [ ] Measure groundedness, retrieval recall, latency, and token cost
- [ ] Add prompt-injection and unsafe-tool-use regression tests
- [ ] Trace graph runs with OpenTelemetry or LangSmith

## Stage 4 - Security and operations

- [ ] Add identity, per-customer authorization, and tenant isolation
- [ ] Store secrets in Azure Key Vault using managed identity
- [ ] Add rate limits, audit logs, PII redaction, and retention controls
- [ ] Require human approval for sensitive or write operations
- [ ] Containerize the service and add deployment manifests
- [ ] Add CI security scans, staged deployment, and rollback support
- [ ] Define service-level objectives, dashboards, and alerts

## Suggested interview demo

1. Start with a policy question to show grounded retrieval.
2. Ask about `ORD-101` plus its warranty to demonstrate multi-tool routing.
3. Show the LangGraph loop and explain why the model never receives arbitrary
   database access.
4. Run the offline test suite and CI workflow.
5. Pick one roadmap item and explain its risk, tradeoff, and acceptance test.
