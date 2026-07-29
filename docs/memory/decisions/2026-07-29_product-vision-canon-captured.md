Founder supplied the full ONE LIVE product vision + governance principles (2026-07-29) — captured as canon at `docs/strategy/ONE_LIVE_PRODUCT_VISION_AND_PRINCIPLES_v1.md` for content work and future functionality builds. Read it before designing any net-new surface.

## What it contains (retrieval pointers)

- **Governance canon (binding):** Core Principles (no pay-to-rank; artist
  sovereignty + 70% splits; social validates never defines; amplification/
  livestreaming opt-in & separate; no artist-level data resale without consent;
  aggregate insights only; permission-first AV), the **Artist Bill of Rights**,
  **Venue Principles**, **Platform Rules**, and **Red Lines** (pay-to-rank /
  non-aggregate data resale = dissolution).
- **Future surfaces (directional, each a separately-gated build):** Night Out
  Experiences (curated chains + open tables beyond Resy/OpenTable), the
  Matching Moat (availability slots + score-based matching), Transportation/
  surge integration, **AV in-ride suggestions** (opt-in, permission-first),
  opt-in **livestreaming** (15-min free → Stripe paywall; private sessions),
  and **Heartbeat Analytics** (aggregate city flows; premium/city dashboards).
- **Directional technical notes** ("not gospel"): normalize/dedupe (rapidfuzz
  >80%), confidence/SXSW mode (threshold 2.2, 2 independent sources, overrides
  lock), /tonight distribution, social-as-weak-signal (weight 0.2,
  validate_with_social).

## Why this matters for future work

- Several principles are ALREADY enforced trust invariants (no-pay-to-rank,
  social-validates-never-defines, disputed-shown, AI-never-publishes). The doc
  reaffirms them; it does not change any gate.
- The net-new surfaces (AV, livestreaming, matching, transport, analytics)
  introduce money, new services, and data surfaces — so each is founder-crucial
  at build time and must carry the 70% split, consent-gated data, and
  aggregate-only commitments from day one.
- Nothing here is live; nothing here relaxes an existing gate. It is the
  reference for design decisions, not an instruction to build now.
