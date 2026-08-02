# 1LIVE — Verification Engine (v1, design of record)

**Status:** Design of record, founder-directed 2026-07-31 ("Yes do it and build
… get this in production and live"). Supersedes the corroboration-count framing
in earlier notes. This is the trust-critical core; it ships in reviewed stages
with the safeguards PROVEN before the auto-publish switch flips — never a raw
switch-flip on unproven code.

## 1. The principle (founder, verbatim intent)

**An event is true only if it traces to a first-party AUTHORITY** — the venue's,
artist's, or group's own source. Verification is *provenance to an authority*, not
counting sources.

- A first-party authority (venue's own calendar/site/account, artist's own page/
  account, organizer's own page) is trusted **as accurate, full stop** — the only
  extra check is a spoof/odd-page sniff.
- Tying an event to the venue/artist/group **is** verification — "as good as we
  can do."
- A **weak signal** — an individual/third-party on social who is *not* the
  authority — is not trusted on its face. It triggers a **cascade to reach the
  authority**, not a publish.
- Social media **can** verify alone when it is the entity's *own* account
  (first-party), or when independent social corroboration stands in for an
  unreachable authority page.

## 2. The Verification Cascade (the decision, in order)

1. **Source is itself an authority** (venue/artist/group's own page/account) →
   **VERIFIED & publish.** Only guard: spoof/odd-page check.
2. **Weak signal → resolve to authority.** Identify the claimed venue/artist,
   fetch *their* own source, confirm the event is there → **VERIFIED.**
3. **Authority unreachable (blocked / no page) → seek a second independent
   validation** (another independent social signal/mention) → **VALIDATED** at the
   appropriate level.
4. **None of the above → HOLD (do not publish), and LOG WHY** (authority blocked?
   no page found? no second signal?). The held queue is the **to-do list for
   extending validation coverage** — we learn from every non-publish.

This makes "unverified junk on the feed" structurally hard: a thing publishes only
if it is tied to an authority (directly or by resolution); everything else holds.

## 3. Chosen architecture — grounded hybrid (Registry + Agent)

Two world-class poles were analyzed (2026-07-31): a **deterministic authority
registry + rules cascade** (max trust/auditability/low cost, capped recall) and an
**agentic verification layer** (max recall/differentiation, AI-judgment risk). The
founder-selected design is the **grounded hybrid**:

- **The Registry is the authority of record.** Every venue/artist/group linked to
  its *official* sources, each with a machine-checkable BASIS (a first-party feed
  we already ingest; DNS/TLS domain ownership; a verified handle; a crosswalk to
  Wikidata/MusicBrainz/official links). Authoritative sources publish directly —
  fast, free, provable.
- **The Agent runs only the cascade on WEAK signals** — the long-tail recall. But
  **the agent never publishes on its own say-so**: it must return a *citation to a
  registered (or freshly domain/handle-verified) authority*, and a **deterministic
  check ratifies** that the citation (a) genuinely is that authority and (b)
  actually contains the event. The AI *finds* evidence; a non-AI rule *confirms*
  it. A deterministic authority stays in the loop — "AI never publishes without
  the gate" in the strong sense, not a loophole.
- **Every agent resolution becomes registry data** (append-only, auditable): a new
  verified handle/page is recorded, so the system **learns from every decision**,
  per-event cost falls as more resolves deterministically, and the identity graph
  compounds into the moat.
- **The escaped-error rate governs the agent** with auto-throttle to human review
  if accuracy slips — so a "bunch of errors" self-limits.

Why the hybrid over either pole: the registry alone caps coverage at what we can
hand-register (never the comprehensive cultural site); the agent alone puts AI
judgment on the trust-critical path (the "obviously wrong at scale" risk). The
hybrid gets **registry-grade trust on the published item** *and* **agentic reach on
discovery**, because the agent's job is reduced from "decide" to "find authority
evidence a rule can verify."

## 4. The hinge: authoritative identity

Nothing in the cascade works until we can *establish* that a page/account is the
entity's own — that `mohawkaustin.com` is Mohawk, a handle is really the artist.
That is identity resolution (the geo/identity backbone, ONE_LIVE_GEO_IDENTITY_v1.md
#110): opaque entity ids + an external crosswalk (Wikidata/GeoNames/MusicBrainz/
official links) + append-only provenance. It is a PREREQUISITE, built first.

## 5. Build sequence (each stage is a reviewed PR; live in stages)

1. **Authority + provenance classification core** (this PR) — PURE decision logic:
   classify a source as authoritative (and for which entity, on what basis) vs
   weak, and the cascade DECISION (verified / validated / hold + reason) from
   provenance + resolution inputs. No network, no publish; fully unit-tested.
2. **Identity/authority registry** — the entity↔official-source store + the
   deterministic basis checks (first-party category, domain ownership, crosswalk
   seed).
3. **Active resolution + second-signal fetchers** — the cascade's network steps
   (fetch the authority page/account; find an independent second signal), run on
   CI, grounded so the agent's citations are deterministically ratified.
4. **Held-and-learn loop** — every non-publish logged with its failure reason,
   feeding registry/connector expansion.
5. **Escaped-error metric + auto-throttle**, then **the promoter** — the thin last
   step that publishes ONLY what the cascade verified, fail-closed behind the
   ratification flag, adversarially reviewed. Live only after the safeguards above
   are proven, with proof shown to the founder.

## 6. Trust invariants (unchanged, reinforced)

`disputed` shown-never-hidden; never fabricate an event; RLS fail-closed; no
pay-to-rank. The promote-import allowlist stays the structural control — the
promoter is added to it only under the founder-directed reversal, flag-fail-closed,
reviewed, and the reviewer rulebook (#121) now judges it on real validation, not a
human click. Publishing stays reversible: any published event auto-retracts/
disputes the instant contradicting evidence appears.
