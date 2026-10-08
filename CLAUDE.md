# Development Guidance

This repository is a standalone math reasoning Web application.
Read `AGENTS.md` for current development, data, security, and commit rules,
and `README.md` for setup and launch commands.

The React frontend is in `client/`; the FastAPI backend is in
`agent_platform/`. LangGraphRuntime and StagedAdapter reuse shared modules
under `reasoning_agent/`. Model connection code belongs in the trusted backend
bootstrap, with credentials supplied by environment variables.

Competition entrypoints and offline benchmark runners have been removed.
Solver verification and repair remain part of real application behavior.
Preserve local chat history and existing services when working on the project.

Run deterministic Python tests and frontend tests/build after relevant changes.
Historical handoff/design documents describe previous milestones and must not
override current instructions.
