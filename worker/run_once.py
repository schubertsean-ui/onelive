"""Orchestrator entrypoint — drives worker.orchestrator.run_loop.

Default (no flags) mode is a smoke test: a stub AI provider (no model call)
over a single in-memory source, so the loop itself — fetch, sensor, extract,
gate3, promote/escalate, replay logging — is genuinely exercised end to end
without a live database or an Anthropic key. The one thing it does need is
network for the fetch step: the stub source points at a tiny, stable public
URL (fetch_url is HTTP-only, so a local file:// path is not an option). Only
that fetch step touches the network; sensors, extract, gate3, and replay run
identically regardless of which URL is fetched.

`--real` additionally requires ONELIVE_DB_DSN and an Anthropic API key to be
configured (it swaps in ClaudeProvider and expects real `source` rows from
the DB); it is guarded behind the flag specifically so importing this module,
or running it with no flags, never requires network or DB configuration.

This file legitimately calls worker.orchestrator.run_loop, which itself calls
worker.promote.promote_candidate; run_once.py is on the PROMOTE_IMPORT_ALLOWLIST
in tools/trust_gate.py (transitively exercising the promote path is the whole
point of a smoke test for the orchestrator).
"""
import argparse
import os
import sys

# Make the repo root importable when this file is invoked directly as a
# script (`python worker/run_once.py`), where Python puts this file's own
# directory — not the repo root — at sys.path[0], so `import ai` / `import
# worker` would otherwise fail. Mirrors tests/conftest.py's identical fix for
# the identical reason. A no-op when already run as `python -m worker.run_once`
# or under pytest (repo root already on sys.path in both cases).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.bedrock_provider import BedrockProvider
from worker.orchestrator import run_loop

# A tiny, stable public endpoint used only for the offline smoke path so
# `python worker/run_once.py` demonstrates a real fetch->sensor->extract->
# gate3 loop with zero configuration. httpbin's /html endpoint returns a
# small, stable static HTML page with real, non-trivial text content (well
# above the sensor's minimum length) and is not rate-limited for single GETs.
_SMOKE_SOURCE = {
    "source_id": None,
    "name": "smoke_stub_source",
    "url": "https://httpbin.org/html",
    "source_class": "social",
}


def _run_stub() -> int:
    ai = BedrockProvider(client=None, model_id="stub")
    report = run_loop(ai=ai, sources=[_SMOKE_SOURCE], sxsw_mode=False, promote=False)
    print("RunReport:")
    print(f"  run_id:   {report.run_id}")
    print(f"  started:  {report.started}")
    print(f"  finished: {report.finished}")
    print(f"  counts:   {report.counts}")
    for r in report.results:
        print(f"  - {r.source_name}: stage={r.stage_reached} decision={r.decision} detail={r.detail}")
    return 0


def _run_real() -> int:
    # Imported lazily, inside the guarded branch, so importing run_once.py
    # (or running its stub path) never requires anthropic/psycopg2 network
    # configuration — only `--real` pays that cost.
    from ai.claude_provider import ClaudeProvider
    from worker.candidate_store import db as candidate_db

    dsn = os.getenv("ONELIVE_DB_DSN")
    if not dsn:
        print("ERROR: --real requires ONELIVE_DB_DSN to be set.", file=sys.stderr)
        return 1

    ai = ClaudeProvider()
    with candidate_db() as conn:
        with conn.cursor() as cur:
            cur.execute("select source_id, name, url, source_class from source where active = true")
            rows = cur.fetchall()
    sources = [
        {"source_id": str(sid), "name": name, "url": url, "source_class": source_class}
        for (sid, name, url, source_class) in rows
    ]
    if not sources:
        print("ERROR: no active sources found in the `source` table.", file=sys.stderr)
        return 1

    report = run_loop(ai=ai, sources=sources, sxsw_mode=False, promote=False, dsn=dsn)
    print("RunReport:")
    print(f"  run_id:   {report.run_id}")
    print(f"  counts:   {report.counts}")
    for r in report.results:
        print(f"  - {r.source_name}: stage={r.stage_reached} decision={r.decision} detail={r.detail}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OneLive orchestrator loop once.")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use ClaudeProvider and real `source` rows from ONELIVE_DB_DSN instead of the offline stub.",
    )
    args = parser.parse_args()
    return _run_real() if args.real else _run_stub()


if __name__ == "__main__":
    raise SystemExit(main())
