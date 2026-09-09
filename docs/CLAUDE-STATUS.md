# Claude is not the builder (2026-09-09)

Diagnosed:
- @claude on an issue: compare API 404.
- @claude from this chat: job often skipped (association) or dies in 0.5s is_error $0.
- workflow_dispatch: green in 4s with log line `Context prompt: NO PROMPT` then `No trigger found, skipping remaining steps`. The action never ran a model.

Fix: Grok writes Ticket A on PR #279. Claude.yml stays for later. Do not wait on Claude for populate.
