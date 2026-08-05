# Decision: scheduled ingest cap raised 10 → 30 — founder-directed (2026-08-04)

**Founder, verbatim (on being shown the 10-per-pass rotation and the freshness
table):**
> "Make sure this isn't too restrictive causing us to miss things"

**The change.** ingest.yml's scheduled MAX_SOURCES goes from 10 to 30 (both the
validation and execution expressions — they must agree). Effect: every source
is checked roughly every **3 hours** instead of every ~9, at 72 passes/day ×
30 = 2,160 slots/day over the 268-source catalog. This is a deliberate spend
escalation under the charter's cost-discipline rule ("escalate spend
deliberately, never silently") — the founder direction is the escalation
reason, recorded here.

**What still bounds cost.** The per-pass ceiling remains fail-loud-required on
every scheduled run; unchanged pages still terminate at the conditional fetch
(no AI tokens); the sensor still rejects junk pre-AI; the ANTHROPIC console
cap ($500/mo, alert at $280) remains the hard backstop; cost-per-verified-
event is measured from live data. Revisit with real numbers after ~48h of
extraction uptime; the queued adaptive-cadence build supersedes fixed caps.

**Tradeoff, stated.** Worst-case AI exposure per pass triples (30 changed
pages max, vs 10). The dead-man + Sentry alarms and the console cap are the
compensations; the founder chose freshness.
