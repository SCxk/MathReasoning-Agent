# MathReasoning-Agent Backend

FastAPI provides sessions, asynchronous reasoning tasks, SSE progress, history,
question attachments, and static frontend serving. The default runtime is a Fake
demo. Real solving uses LangGraphRuntime with a trusted client provider.

## Local Startup

Follow the root README to install dependencies and build `client/`.
For a demo without model calls:

```powershell
python -m agent_platform --port 8010
```

Open `http://127.0.0.1:8010/chat/`. API documentation is at `/docs`;
`/trace-viewer` is a separate diagnostic workspace.

For real solving, set `INTERN_API_KEY` in the backend environment and use
`--runtime langgraph --client-provider deployment_bootstrap:provided_client
--client-identity intern/intern-s2-preview/local-v1 --function-calling off`.
Use the complete Redis/question-directory command in the root README for
persistent history and question uploads. API keys never belong in the browser.

## Runtime And Persistence

- `create_app(store=..., runtime=...)` accepts explicit storage/runtime adapters.
- The default process-local store loses records when the process exits.
- RedisTaskStore requires AOF with `appendfsync always`; readiness refuses an
  unavailable or incorrectly configured Redis instead of silently falling back.
- Checkpoints persist at workflow node boundaries and bind to code, configuration,
  tool, and model identities. Incompatible interrupted tasks require an explicit
  operator decision; finished history remains readable.
- Generation fences prevent old executions from overwriting cancelled or resumed
  tasks. Cancelling a task does not forcibly terminate an uncooperative model call.
- Traces and responses are sanitized; public APIs do not expose full prompts,
  private checkpoints, model credentials, or private storage paths.

The default workflow is profile, retrieval, plan, solve, tool checks, audit,
optional repair, and finalization. Solver audit and repair are application
behavior. No offline benchmark or reference-answer evaluator is included.

## HTTP Surface

| Route | Purpose |
| --- | --- |
| `GET /health/live`, `GET /health/ready` | Liveness and dependency/runtime capabilities |
| `POST /v1/sessions`, `GET /v1/sessions` | Create a session and list paginated history |
| `GET /v1/sessions/{id}/tasks` | Paginated task history |
| `POST /v1/sessions/{id}/tasks` | Submit a question with an idempotency key |
| `GET /v1/sessions/{id}/tasks/{task_id}` | Current status and accepted public answer |
| Task event, trace, cancel, and resume routes | Progress replay and lifecycle controls |
| Question batch routes | Parse, explicitly start, track, retry, and export questions |

Use the generated OpenAPI at `/docs` for complete route and request schemas.
Answer styles are `auto`, `answer`, `brief`, and `detailed`; proofs retain
necessary public proof steps. Missing steps are reported rather than invented.

PDF/Markdown question uploads require `--question-dir`. Uploading parses only;
explicit send starts sequential solving. Limits are 20 MiB/file and 24,000
characters/question. OCR, scanned/image-only PDF recovery, Word input, and
account-based access isolation are not implemented.

## Strategy Resources And Optional Document RAG

The release includes the ordinary chat workflow's lexical strategy metadata and
checked index under `strategy_data/`, plus English/Chinese skill handbooks.
Model weights, dense embedding arrays, raw source datasets, and translation
intermediates are excluded.

Normal chat explicitly selects no reference documents and does not require an
embedding model. Optional document APIs and the Trace workspace can use RAG:

```powershell
python -m pip install -r requirements-platform-m5.txt
# Append to a local backend launch command after preparing frozen offline weights:
# --rag-dir local_state/chat_rag --embedding-model-dir <local-model-directory>
```

The encoder does not download weights at startup. RAG uses session-scoped
PDF/Markdown ingestion, dense/sparse retrieval, and bounded passage output.
Use one API owner per document directory. Refer to the retained model card
under `strategyrag/Qwen3-Embedding-0.6B/README.md` for the optional encoder.

## Distributed Deployment

Docker Compose provides PostgreSQL, Redis, Qdrant, migration, API, Celery normal
and recovery workers, and Prometheus. It starts with a Fake runtime by default.

```powershell
$env:MATHS_DB_PASSWORD = "<URL-safe-deployment-password>"
docker compose up --build --wait
```

The API binds to `127.0.0.1:8004`; Prometheus binds to `127.0.0.1:9094`.
Change `MATHS_API_PORT` and `MATHS_METRICS_PORT` if needed. Named volumes hold
persistent data. Do not remove volumes containing records you need.

A real container deployment needs `MATHS_RUNTIME=langgraph`, a trusted
`MATHS_CLIENT_PROVIDER`, a versioned `MATHS_CLIENT_IDENTITY`, and explicit
provider-secret passthrough via an operator-owned Compose override or secret
mechanism. The included bootstrap is packaged in the runtime image; credentials
are not. `compose.rag.yaml` additionally mounts operator-provided integration
code and frozen model weights for optional RAG.

The runtime image contains lexical strategy resources and skill materials.
Its allow-listed build context excludes Git history, private data, model weights,
local environments, and frontend dependencies/build outputs.

PostgreSQL is authoritative for distributed tasks and events; Redis Streams
provide delivery/replay caching. A dedicated recovery worker reserves capacity.
Metrics expose finite-label operations and task states, without claiming answer
accuracy or measured real-model recovery guarantees.

## Validation And Boundaries

```powershell
python -m pip install -r requirements-platform-dev.txt
python -m pytest -q
python scripts/check_platform_ci.py
```

Full CI requires a dedicated disposable PostgreSQL supplied through
`MATHS_TEST_DATABASE_URL`. Without it, database integration tests skip and
the complete coverage gate may fail. Browser QA requires Playwright and an
installed browser; it uses isolated Fake backends and must never submit to an
existing real-model service.

The application is currently local and single-user. Public authentication and
per-account ownership are not implemented. Docker/remote infrastructure and
real-model answer quality require separate validation; local deterministic tests
do not establish those properties.
