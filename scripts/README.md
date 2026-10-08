# Utility Scripts

Run scripts from the repository root. These are development and maintenance
tools; the application starts with `python -m agent_platform`.

## Application Validation

| Scripts | Purpose |
| --- | --- |
| `check_platform_ci.py`, `check_platform_coverage.py` | Lint, types, regression tests and coverage gates; full CI needs disposable PostgreSQL. |
| `check_chat_ui.py`, `check_question_attachment_ui.py` | Chat and attachment browser QA with Fake runtimes. |
| `check_platform_ui.py`, `check_platform_m5_ui.py` | Trace workspace browser checks. |
| `smoke_platform*.py`, `smoke_chat_history.py`, `smoke_redis_restart.py` | API, tools, persistence and recovery smoke checks. |
| `mcp_failure_fixture.py`, `platform_m6_native_fixture.py` | Tool and deployment fixtures. |

Check each script's arguments before running. Use free ports and isolated
storage. Browser checks must not submit to the existing real-model service.
Attachment tests import `pdf_file` from `smoke_platform_m5.py`;
`smoke_platform_m4.py` imports the M3 client fixture.

## Optional Demo Servers

`serve_platform_m4_demo.py`, `serve_platform_m5_demo.py`, and
`serve_chat_rag_demo.py` provide separate demo configurations.
RAG demos do not enable reference attachments in the normal chat interface.

## Strategy And Skill Maintenance

- `build_strategy_embeddings.py`, `build_lexical_strategy_index.py`,
  `append_additional_strategy_embeddings.py`, and
  `sync_formula_guidance_strategy_embeddings.py` maintain strategy indexes.
- `query_strategy_index.py`, `query_strategy_with_client.py`, and
  `batch_query_strategy_with_client.py` inspect retrieval.
- `translate_*.py`, `merge_and_embed_translated_skill_modules.py`,
  `batch_pdf_to_chinese_latex_argos.py`, and `assemble_*translation*.py`
  prepare skill resources. Some modify resources or call models.
- `probe_intern_chat_request.py` is an explicit live-client diagnostic and can
  consume model quota.

The active English skill source is `skill2_en/`; `skill2/` provides the
per-category fallback. Resource-maintenance scripts are not startup commands.
The release includes lexical strategy resources only. Embedding/translation
maintenance requires separately supplied source material, optional dependencies,
and frozen local model weights; original datasets, arrays, and translation
checkpoints are not shipped. For normal chat, no embedding build is needed.
Maintenance scripts that previously used the JSONL runner's environment loader
now use `scripts/local_env.py`. It optionally reads the root `.env` when invoked
and preserves existing environment variables; it is not a backend startup hook.

## Removed Competition Tooling

The JSONL runner, competition contract tests, local validation-output scripts,
answer-comparison evaluator, and labelled-RAG evaluator were removed when the
repository became a standalone application. Functional tests and browser QA
remain.

Keep generated inputs, outputs, logs, and screenshots in ignored local
directories. Do not stage them with source changes.
