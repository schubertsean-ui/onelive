# Signal-acquisition specs — po battery working notes (2026-07-22)

Battery: full P1–P8.6, seed 20260723 (arbitrary reproducibility seed, not a date), random word "windmill", target
statement = the three-part signal-acquisition expansion (ingest inbox ·
social composite enrichment · non-music). Provocations are stimuli,
never facts; harvest converges through the normal gates. ≥2 movement
techniques applied per provocation (principle-extraction and
moment-to-moment used throughout; special-circumstances where noted).

## Harvest (traceable)

- **H1 (P3 exaggeration-down, 1 newsletter)** — per-sender YIELD
  LIFECYCLE: subscriptions are sources; events-per-message is tracked
  and a barren subscription is unsubscribed, logged. → Ingest Inbox
  spec, Governance §2.
- **H2 (P1 escape, "enrichment converges" negated)** — dossier
  COMPLETENESS SCORE with a diminishing-returns stop: enrichment halts
  when marginal expected info gain drops below threshold; prevents
  infinite polishing of one artist while the tail starves. → Social
  Composite spec (enhancement loop control).
- **H3 (P2 reversal, "artists ingest us")** — REPLY-TO-CLAIM: a venue
  answering its own newsletter's ingest copy bootstraps the claimed
  channel. Parked as P2 product feature with consent design. → Ingest
  Inbox spec, Governance §3.
- **H4 (P3 exaggeration-up, 100k/day)** — inbox as ROUTING not storage:
  address-per-subscription; queue-based classify-at-receipt; mailbox
  never becomes an accidental database. → Ingest Inbox spec, Option B.
- **H5 (P4 distortion, enrich-before-ingest)** — PRE-ENRICHMENT STUBS:
  first sighting of an unknown artist/venue creates a dossier stub and
  queues enrichment BETWEEN ingest cycles (off the hot path), so the
  second sighting lands corroboration-ready. → Social Composite spec.
- **H6 (P5 wishful, "every artist publishes a perfect feed")** — the
  partial reality is schema.org/MusicEvent JSON-LD embedded in venue
  pages: parse STRUCTURED DATA FIRST, LLM extraction second — cheaper
  and higher-confidence where present; and our claimed channel should
  EMIT the same standard. → Social Composite spec + pipeline note.
- **H7 (P7 windmill: turns to face the wind)** — YIELD-WEIGHTED
  ADAPTIVE CADENCE ("wind vane"): crawl/enrichment attention re-points
  toward sources whose recent yield is rising (extends
  least-recently-attempted rotation with a yield weight; ceiling-capped
  so the tail is never starved). → Social Composite spec (learning
  loop) + future run_once enhancement.
- **H8 (P8.4 windmill+distortion: the miller pays the wind)** —
  ATTRIBUTION GOODWILL LOOP: every surfaced event visibly credits and
  links its venue/artist sources; being in OneLive should feel like
  free distribution, making sources WANT to feed us (newsletters,
  uploads, claims). → both specs, display posture.
- **H9 (P2 caution)** — PER-SOURCE COMPLIANCE FIELD: each API source
  row carries its license/ToS posture (display allowed? cache allowed?
  attribution required?) and the pipeline refuses to surface fields
  whose license doesn't permit it — compliance as data, not memory. →
  Social Composite spec.
- **H10 (P6 absurd, "the building tweets its lineup")** — soft ACTIVITY
  signals (e.g. Google Places popular-times, venue-hours changes) as
  corroboration-adjacent context, never event assertions. → Social
  Composite spec (signal tiers).

Dead ends logged (battery convention): P8.2 (wind grinds the miller)
produced only role-swap noise; P5 second wish (fans hand-deliver
lineups) collapses into the existing community-sighting channel idea
(global-sensing doc H9) — no new candidate.
