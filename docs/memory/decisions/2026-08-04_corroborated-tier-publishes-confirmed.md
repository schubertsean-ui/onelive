# Decision: the corroborated tier publishes as CONFIRMED — founder ruling (2026-08-04)

**Founder, verbatim (on being shown the auto-publish tier sentence "An event
corroborated by 2+ independent sources (or one anchor source like a ticketing
API) publishes automatically as confirmed/likely"):**
> "Just 'confirmed' - remove 'likely'"

**The ruling.** Corroboration by 2+ independent sources (3 in sxsw_mode) earns the
same label an anchor source does: **confirmed**. The old ladder reserved
'confirmed' for anchors and gave corroborated events 'likely' — after today's
earlier ruling (a single trustworthy source publishes at 'likely', displayed
clean), that left 'likely' meaning two different things. This ruling completes
the coherent ladder:

| evidence | confidence | display |
|---|---|---|
| anchor source OR 2+ independent sources (3 in SXSW mode) | confirmed | clean |
| one trustworthy source (gate HOLD, reliability above threshold) | likely | clean (ruling earlier today) |
| below reliability threshold / gate ESCALATE / fabrication risk | — | human review, never auto-published |
| moderation dispute | disputed | shown-never-hidden, marked |

**What changed.** `worker/confidence.py::derive_confidence`'s corroborated branch
returns 'confirmed' (was 'likely'); it now never returns 'likely' — that state is
assigned exclusively by the publish policy's single-trusted-source path. This is
the single source of truth for corroboration→confidence, so the change flows
identically to human-custodied promotion (`worker/promote.py`), triangulation
(`worker/triangulate.py`), and auto-publish (`worker/publish_policy.py`) — the
label states what the evidence is, not which custody mode published it. Tests
re-pinned: test_gates.py (incl. a new never-returns-likely guard),
test_publish_policy.py, test_triangulate.py.

**What did NOT change.** The 4-state model stands (no reversion to 3-state —
'likely' remains a live state, populated by single-trusted-source publishes).
Corroboration thresholds unchanged (2, or 3 in sxsw_mode; independence rules
untouched). Reliability threshold, ESCALATE handling, fabrication-risk handling,
disputed's shown-never-hidden rule, and the no-badge display rule all unchanged.
Existing rows keep their stored confidence; the ladder applies from promotion
time forward.

**Tradeoff, stated.** Two independent non-anchor sources can both be wrong the
same way (e.g. both syndicating one bad listing); the independence rules in
triangulation (distinct source classes) are the compensation, and disputed
remains unconditionally visible if evidence later contradicts.
