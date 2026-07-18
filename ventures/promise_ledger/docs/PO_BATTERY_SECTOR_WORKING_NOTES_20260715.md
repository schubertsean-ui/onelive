<!-- Complete po-battery working notes for the FINANCIALS beachhead decision
(founder decided 2026-07-15: "Financial"). Generator output committed at
PO_BATTERY_SECTOR_20260715.txt (seed 20260715, random word "anchor"). Every
operator P1-P8.6, >=2 named movement techniques per provocation (PRIN/DIFF/
MOM/POS/SPEC). Provocations are stimuli, never facts; the harvest feeds the
sector build plan through the normal gates. Compiled 2026-07-15. -->

# Po battery — financials beachhead (founder-decided; battery run post-decision per charter)

**Statement:** "The promise ledger launches with FINANCIALS (banks and financial institutions) as its beachhead sector."

**Step 0 assumptions:** banks' promises live in earnings releases · guidance language is the promise type that matters · the sector's density/cadence advantages (memo) outweigh its whitespace disadvantage (Marvin/Visible Alpha adjacency) · US-listed banks ≈ the sector · investors are the reader.

## P1 ESCAPE
- **Po: banks' promises are NOT in earnings releases.** PRIN: bank commitments also live in capital plans (CCAR/stress-test announcements), dividend/buyback declarations, branch/layoff announcements, and merger integration timelines — all 8-K/PR material, all datable. DIFF: this widens the claim taxonomy beyond guidance — the exact differentiation the memo demanded vs Marvin/Visible Alpha (they track guidance numbers; nobody tracks "we will complete the integration by Q2" or "we will return $X to shareholders"). → **H-S1: bank claim taxonomy = guidance + capital-return promises + integration/timeline promises + regulatory-remediation commitments.**
- **Po: cadence regularity doesn't exist.** SPEC: true for crisis periods — banks go quiet or off-cycle exactly when it matters (2023 regionals). MOM: simulating March-2023-style stress — silence detection fires on missed cadence during stress = the product's highest-value alert. → **H-S2: stress-period silence is the killer demo; backtest silence detection against the 2023 regional-bank window.**
- **Po: the reader is not an investor.** PRIN: bank supervisors and bank COUNTERPARTIES read bank promises professionally; treasury/credit teams at corporates assess bank strength. → parked for phase 2 (buyer expansion), consistent with analysis §6.

## P2 REVERSAL
- **Po: the sector launches the ledger** (banks as the first *issuer-side* users). DIFF: banks have the most process-driven IR teams — the pre-flight linter (H5) may land fastest here. Parked to phase 2 per sprint sequencing.
- **Po: financials is the LAST sector.** POS (of the reversal): forces the honest reading of the memo's caveat — financials has the least whitespace. Movement: what makes it defensible anyway? The claim types in H-S1 that incumbents don't track + the archive depth (banks have the deepest 8-K history). → **H-S3: differentiation checklist committed before build — every financials feature must name what Marvin/Visible Alpha DON'T do.**

## P3 EXAGGERATION
- **Po 10,000× up: every bank promise ever, all 4,000+ US banks.** PRIN: coverage SLO should be defined on a NAMED universe — start with the ~130 banks above $10B assets (stress-test + SEC-reporting overlap), guarantee completeness there. → **H-S4: universe = named list, committed, versioned.**
- **Po 1/10,000 down: one promise per bank.** DIFF: the one promise per bank that matters most is the capital-return commitment (buyback/dividend) — measurable, dated, universally watched. → **H-S5: capital-return promises = the golden-set's first claim class (cleanest fulfillment observables: subsequent 8-Ks/10-Qs report actual buybacks).**

## P4 DISTORTION
- **Po: fulfillment happens before the promise.** PRIN: banks pre-announce then confirm (buyback authorized → executed quarterly) — the ledger models promise CHAINS, not single events. → schema already supports via lifecycle REITERATED/MODIFIED; taxonomy note added.
- **Po: the regulator promises, the bank grades.** SPEC: consent-order remediation commitments are bank promises TO regulators with public milestones — a claim class with enforcement-grade observability. → folded into H-S1.

## P5 WISHFUL
- **Po: every bank promise self-reports its outcome.** Capital-return promises nearly DO (subsequent filings report actuals) — that's why H-S5 leads. PRIN: prefer claim classes whose fulfillment is reported in structured filings (buybacks, dividends, CET1 targets) — verdicts can reach `confirmed` from XBRL facts later, not narrative judgment.
- **Po: zero wrong verdicts ever.** MOM: founder's cap applies — financials launch keeps verdicts ≤ `likely` until golden-set precision is proven (memo's graduated-confidence resolution, now policy). → **H-S6: verdict cap = launch policy, revisited only on eval evidence.**

## P6 ABSURD
- **Po: the banks sue the ledger.** SPEC: financials = the most litigious, most compliance-heavy issuers; the never-verbatim/evidence-linked/4-state design is load-bearing here, not optional. POS: also the sector where the "receipts" posture wins trust fastest.
- **Po: the Fed subscribes.** PRIN: SupTech demand (analysis appendix G) is realest in banking supervision — a phase-2 door, evidence already gathered.

## P7 RANDOM ENTRY — "anchor"
- anchor holds through storms → the ledger's value peaks in volatility; build the stress-window backtest (reinforces H-S2). (PRIN, SPEC)
- anchor drags → a promise quietly renegotiated ("we now expect…") = MODIFIED lifecycle events chained — drift detection over successive guidance revisions. → **H-S7: guidance-drift view (how far has the promise moved from its original?).** (DIFF, MOM)
- anchor chain links → promise chains (P4 convergence). (PRIN)
- anchor tattoo (commitment symbol) → public commitment device: banks WANT credit for kept promises — verified-issuer door (H4) strongest in financials. (POS)
- weighing anchor = departure → coverage of exits (branch closures, market exits) — promises to STOP doing things are claims too. (DIFF)

## P8 RANDOM × OPERATOR
- **8.1 escape (anchorless ship):** no fixed universe — drift to wherever promises are densest. Rejected for launch (H-S4 wins); noted as a discovery mode for phase 2. (PRIN, SPEC)
- **8.2 reversal (the sea anchors the ship):** the ENVIRONMENT (rates, Fed policy) anchors bank promises — context enrichment: attach the rate regime at promise time to each claim record. → **H-S8: macro-context field on financial claims (cheap: FRED date join).** (DIFF, POS)
- **8.3 exaggeration (a thousand anchors):** every sentence anchored = over-extraction; H7's materiality editorial guards. (PRIN)
- **8.4 distortion (anchor before the ship):** taxonomy seeded before ingestion — pre-seed from bank-analyst frameworks (capital, credit, NIM guidance, efficiency targets). → feeds sprint step 9 taxonomy. (PRIN, MOM)
- **8.5 wishful (anchor that never rusts):** claims never staling — the maturity calendar keeps every financial promise ticking; zombie-promise report for banks ("the oldest unmet efficiency target in banking"). (POS)
- **8.6 absurd (the anchor steers):** the ledger drives bank behavior — success metric: banks start citing their own kept-promise record. Long-run; noted. (SPEC)

## Harvest → sector build inputs
H-S1 claim taxonomy (guidance + capital-return + integration/timeline + remediation) · H-S2 stress-window silence backtest (2023 regionals) · H-S3 differentiation checklist vs Marvin/Visible Alpha before build · H-S4 named universe (~130 banks >$10B) · H-S5 capital-return promises = first golden-set class · H-S6 verdict cap ≤ likely at launch (policy) · H-S7 guidance-drift view · H-S8 macro-context field. All converge through the normal gates; friction attack = evaluator on this PR.
