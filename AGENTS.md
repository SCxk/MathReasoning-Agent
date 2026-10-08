# Repository Guidelines

## Application Structure

This repository is a standalone math reasoning Web application. The backend
entrypoints are `python -m agent_platform` for local use and
`python -m agent_platform.deployment` for distributed deployments.
`client/` contains the React/TypeScript frontend. `agent_platform/` owns HTTP,
SSE, task orchestration, attachments, persistence, and presentation.
`reasoning_agent/` supplies shared reasoning code, prompts, parsers, and tools.
The Web workflow uses StagedAdapter and LangGraphRuntime directly.

The competition submission entrypoint, JSONL runner, and offline evaluation
tools were removed. Do not recreate them unless explicitly requested.

Shared code under `reasoning_agent/custom/`, `custom2/`, and `action_graph/`
is still imported by the backend. Resolve actual dependencies before removing
historical implementations. Preserve solver audit, verification, and repair:
these are application behavior, not offline evaluation.

## Development

Use Python 3.11 and Node.js >=22.12. Install backend dependencies with
`pip install -r requirements.txt`; install development tools with
`pip install -r requirements-platform-dev.txt`.
The optional local embedding/RAG dependencies are in
`requirements-platform-m5.txt`.

Build the frontend with `npm ci` and `npm run build` inside `client/`.
Run `python -m agent_platform --port 8010` for a Fake demo without model calls.
For real solving, use the explicit langgraph client-provider command in README.
Keep the existing client injection boundary: model clients are constructed in
trusted application bootstrap code, never inside reasoning nodes or the browser.

Run `python -m pytest -q`, then `npm test` and `npm run build` in `client/`.
The full CI script is `python scripts/check_platform_ci.py`; PostgreSQL tests
require a dedicated disposable `MATHS_TEST_DATABASE_URL`. No live model call
is needed for deterministic regression tests.

## Code And API Contracts

Use Python 3, four-space indentation, snake_case functions/modules and
PascalCase classes. Prefer small modules and typed interfaces.
Preserve HTTP/SSE contracts, task idempotency, cancellation, history isolation,
checkpoint validation, and answer rendering when refactoring.
Keep task responses, traces, errors, and checkpoints JSON-safe and sanitized.
Never expose prompts, raw private model responses, credentials, or local paths.

Do not hardcode fallback behavior for specific problems, answers, constants,
keywords, metadata indices, or judge examples. Fallbacks must derive from the
current problem, accepted reasoning state, and declared protocol constraints.

## Data, Secrets, And Local Services

Keep credentials in backend environment variables such as `INTERN_API_KEY`.
Do not put secrets in source files, frontend bundles, or `VITE_*` variables.
The default deployment is local and single-user; do not claim public
authentication or multi-user ownership is implemented.

Preserve `local_state/`, Redis data, question files, and existing chat history.
Do not stop or restart shared services during cleanup or tests.
Use isolated ports, storage namespaces, and disposable databases for smoke tests.

Do not stage or commit datasets, reference answers, generated outputs, logs,
raw responses, caches, local environments, or model weights. This includes
`sample_data/`, `sample_outputs/`, `val_outputs/`, `outputs/`,
`run_outputs/`, and `local_state/`. Existing tracked artifacts need a
separate reviewed publishing cleanup; ignore rules alone do not untrack them.
Preserve required strategy corpora and skill handbooks unless replacing their
runtime dependencies.

## Commits And Documentation

Inspect `git status` and the staged file list before committing.
Never use `git add .` in place of reviewing source/config/test changes.
Use conventional messages such as `fix:`, `docs:`, and `refactor:`.
Do not commit or push unless requested.

README and this file describe the current application. The release does not
include old handoff notes or historical validation records. Current architecture
is documented in docs/ARCHITECTURE.md. Keep setup instructions aligned with dependencies.
Report checks run and real limitations; do not invent accuracy or performance.
