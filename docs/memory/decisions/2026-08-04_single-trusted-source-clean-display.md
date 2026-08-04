# Decision: a single TRUSTWORTHY source publishes as 'likely', displayed CLEAN — founder ruling (2026-08-04)

**Founder, verbatim (on being shown the auto-publish policy's single-source treatment):**
> "If it's trustworthy why require a second source? This is a misinterpretation when we
> were talking about incorporating social media. Trustworthy is trustworthy, it is isn't.
> If it is, publish without the uncertainty marker."

**The correction.** The auto-publish policy had mapped a single trustworthy non-anchor
source (gate HOLD) to `unverified` + the quiet uncertainty marker. The founder rules that
treatment a mis-carry from the social-media sourcing discussion: source reliability is
already enforced upstream (a source graded below the 0.35 threshold never publishes at
all — it goes to human review), so a source that clears that bar is trusted, full stop.

**What changed (both halves of the same ruling):**
1. `worker/publish_policy.py` — HOLD now publishes at **`likely`** (was `unverified`).
   `likely` fits its own definition: one credible source, not yet corroborated. The tier
   ladder stays coherent: anchor/corroborated PASS → confirmed; single trusted → likely;
   below-threshold → human review, never published.
2. `web/lib/trust.ts` — **`likely` displays CLEAN**: no marker, no caveat surface, same
   as confirmed; its details sheet keeps honest provenance ("Reported by X. Times and
   prices can change; the venue's own page and the ticket link are the last word") with
   no doubt language. `web/lib/share.ts` inherits automatically (caveats key off the
   surface flag) — a shared 'likely' event carries no ⚠ line.

**What did NOT change.** The 4-state confidence model stands (unverified/likely/
confirmed/disputed — no reversion to 3-state). `unverified` (the degrade-target for
unknown states and any legacy single-source rows) keeps its quiet marker; `disputed`
stays shown-never-hidden with its marker; fabrication risk and gate-ESCALATE still never
auto-publish; the no-badge rule is untouched (clean display means NO chrome, not a
"verified" claim). Tests updated to pin the new contract (trust.test.ts,
share.test.ts, test_publish_policy.py); UI canon §8 annotated.

**Tradeoff, stated.** A single miskeyed listing from a trusted source now reads with the
same visual confidence as a corroborated one; the compensations are the reliability
grade (outcome-driven — a source that burns us drops below threshold and loses
auto-publish entirely), the venue-last-word line on every listing, and disputed's
unconditional visibility.
