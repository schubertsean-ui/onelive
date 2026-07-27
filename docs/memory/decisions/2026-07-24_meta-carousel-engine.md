# 2026-07-24 — Meta carousel engine: gate-custodied outbound marketing + the autonomy sign-off path

**Directive (founder, 2026-07-24, session `onelife-meta-carousel`):**
"configure Meta carousel options. True world class. Use our trust model
framework … human perception and data ingestion … bits, images, video,
music, humor, curiosity … positive emotions that … drive action …
Nir Eyal and Duhigg Atomic Habits ideas … structured for maximal learning
and improvement toward 100% interaction … easy for people to share …
perhaps multiple carousels … tiered toward the content categories that
have the most content … agent-driven model that pulls from OneLive data
and creates the carousels and learns and revises and reposts …
continuous measured improvement … continuously optimized for [SEO/GEO]
discovery. The goal should be to be #1 in every criteria."

**Follow-up directive (same session, mid-build):** "at some point soon I
will want the AI to do everything and remove the human from the loop. So
set up a process for me to sign off on that."

## Decisions taken (agent, within charter; founder-crucial items queued, not taken)

1. **Outbound social is an outward-facing product surface, so "AI never
   publishes" applies.** The engine (`social/carousel/`) generates,
   learns, revises, and re-proposes autonomously; RELEASE to Meta goes
   through `publish_gate` — human approval bound to a SHA-256 content
   hash, AI identities refused as approvers, current-trust-state re-check
   at release, and an import-guard test making the autonomous loop
   structurally unable to reach the publisher (promote-guard physics).
2. **The autonomy sign-off process the founder asked for is BUILT, not
   promised** (`social/carousel/autonomy.py`, spec §10): L0 (default,
   human per post) → L1 (standing approval for enumerated surface×tier)
   → L2 (full autonomy). The ONLY path up is the founder's three-step
   sign-off (evidence pack → signed decision record → PR committing
   `AUTONOMY_RATIFICATION.json`). No file = L0; malformed file = refuse
   everything (fail closed). Revocation is one commit. NO record is
   committed in this PR — the repo ships in L0.
3. **Trust selection for marketing:** feature `confirmed` freely,
   `likely` only with the uncertainty affordance, `unverified`/`disputed`
   never (selection, not hiding — product surfaces unchanged). Copy is
   verbatim event facts; the only descriptor slot requires Descriptor
   Foundry provenance; banned-claim phrases ("confirmed", scarcity
   language) are refused at generation AND re-scanned at release.
4. **Structure over guesswork for creative:** a factored Thompson-
   sampling bandit (hook type, emotion register, slide count, caption
   style, CTA, post slot, media type) with exploration floor + decay;
   interaction rate (unique interactions / reach) as north star; a
   rolling-baseline improvement ratchet with mechanical regression
   flags. Tiering follows content volume per the 22-domain taxonomy,
   with a combined long-tail carousel so nothing posts thin.
5. **Separation physics:** `social/` is a new top-level package —
   marketing reads published canonical events only and can never touch
   candidate/gating/promotion (same physics as Tastemaker separation).
6. **Zero new dependencies, zero LLM calls** in the engine (stdlib only,
   deterministic templates) — cost-discipline rule 1.

## Founder-crucial items QUEUED (never agent decisions) — spec §9
Meta app + Graph API credential minting · posting-posture ratification
(gate-custodied posting go-live) · cadence + Sentinel wiring before any
cron (R-027) · the L1/L2 autonomy ratifications themselves.

## Records
Spec: `docs/strategy/ONE_LIVE_META_CAROUSEL_ENGINE_v1.md`. Deferrals:
R-026 (live posting/metrics blocked on founder keys), R-027 (no scheduled
cycle until dead-man + budget wiring). Tests:
`tests/test_social_carousel.py` (50 at this record's writing; correction
2026-07-25 at PR #65 r2's stale-evidence nit — the suite grew with the r1
adoption and the founder listicle directive to 79, then 82 with the r2
red tests; the test file is the live count's source of truth). Session
Contract #23 in STATE.md.


## Addendum (2026-07-25, appended at PR #65 r13 — dissemination minimization)

The founder's follow-up product directive (2026-07-24, same session),
verbatim, moved HERE from STATE.md so operational docs paraphrase and
decision records hold the exact words:

"The carousels should be '5' or '7' 'blank' to experience Today or
Tonight or This Weekend and only ever show content that is to happen,
never that has happened. For example, a carousel running at 6pm would not
include shows that started before 6pm. Create a world class cadre of
actual carousel content for 5 different categories/combos of categories.
Include scenarios we've identified like date night, music and dancing,
etc - several examples of these scenarios exist in OneLive. What are the
world class practices for how many run per day? What are key metrics
we'll gather and analyze?"

---

**Codified by:** `social/` package + `tests/test_social_carousel.py`; FROZEN off-mission until v1 is live per `CLAUDE.md` mission and `docs/UNWIRED_DECISIONS.md` (founder call pending).
