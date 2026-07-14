CI forwards unset variables as EMPTY STRINGS — treat present-but-empty env as misconfiguration and fail closed, never as "use the default" or "uncapped".

Bit us twice in one day: (1) `OPENAI_REVIEW_MODEL: ${{ vars.… }}` arrived as
`""` and `env.get(name, default)` kept the empty string → `"model": ""` →
undiagnosable HTTP 400 from OpenAI (PR #11 round 1); (2) an empty
`ONELIVE_MAX_SOURCES_PER_RUN` initially meant "uncapped" — a fail-open budget
guard (PR #12 round 2, caught by the evaluator).

Rule now applied everywhere: `os.environ.get(X)` then branch — `None` =
genuinely unset (default/allowed), `""` = raise/exit loud. For anything
guard-like (budgets, allowlists), 0/negative/garbage also fails closed.
Reference implementations: `tools/adversarial_review.py` (model/base-url),
`worker/run_once.py` `_resolve_source_cap`, `tools/model_router.py`.
