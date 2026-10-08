# MathReasoning-Agent Architecture

## Request Flow

The React client calls FastAPI session/task endpoints. TaskService owns task
admission, cancellation, history, and progress events. LangGraphRuntime routes
the staged solver through profile, retrieval, planning, solving, checks, audit,
repair when needed, and finalization. StagedAdapter bridges the graph to shared
reasoning modules and sanitized public answer rendering.

Model clients are supplied by trusted backend bootstrap code. Reasoning nodes
use the provided chat interface; the browser never receives model credentials.

## Ownership

| Directory | Responsibility |
| --- | --- |
| `client/` | Chat UI, Markdown/math rendering, progress and history |
| `agent_platform/` | API, runtime integration, task lifecycle, persistence |
| `reasoning_agent/` | Shared solver logic, prompts, parsing, numerical checks |
| `skill2_en/`, `skill2/` | English skill handbooks and Chinese fallback |
| `strategy_data/` | Verified lexical strategy resources |
| `deploy/` | Redis and monitoring configuration |
| `scripts/`, `tests/` | Maintenance and deterministic verification |

## State

The Fake demo uses process memory. Local durable chat uses a dedicated Redis
configured with AOF/always and a private question-file directory. Optional
distributed deployment uses PostgreSQL as the task/event authority, Redis for
delivery and capacity coordination, and Celery normal/recovery workers.

Checkpoints validate workflow/source/config/model identity before recovery.
SSE progress can replay persisted events. Generation fencing prevents obsolete
executions from replacing cancelled or resumed task results.

## Release Boundary

The release includes source, tests, deployment configuration, skill handbooks,
and lexical runtime resources. It excludes Git history, credentials, local
conversations, question datasets, evaluation artifacts, model weights, dense
embedding arrays, dependency directories, and generated frontend builds.

Normal chat does not use reference-document RAG. Optional RAG adapters require
separately supplied offline model files. Solver audit/repair remain part of
answer generation. No benchmark runner or competition entrypoint is included.
