# Decision: Today-density is the live defect; duplicates founder-caught (2026-08-05)

**Founder, verbatim (session chat, looking at the live /tonight Today tab):**

> "THe number of events showing on the live site for today is worse than
> paltry - 11 items. What gives? Fix this. I want every event loaded asap"

and, with screenshots:

> "worse there are apparent duplicates"

**What the screenshots prove (founder-supplied evidence, 2026-08-05 ~19:00 CT):**
1. **Cross-source duplicates**: "O.A.R., Gavin DeGraw, Lisa Loeb" at ACL
   Live at The Moody Theater, Wed Aug 5 6:30 PM, rendered TWICE with
   differing genre lines ("Rock · Alternative Rock" vs "Alternative ·
   Alternative Rock") — the same show imported through two providers
   (ticketing + the venue's own structured feed). The licensed lane dedupes
   per-provider by external id; NO cross-provider collapse existed.
   "Summer Stock Austin" appears 4× across two venues/two times — venue
   records disagree across sources; not blindly collapsible.
2. **Non-event rows**: "Apply: Fall ESL classes" (a registration deadline)
   and "Ice Age in the Wild" (an all-day exhibition running May–Aug) render
   as Today events from university/localist feeds — import-lane quality gap,
   named here, fixed in the import lane with data in hand (not by an
   editorial display filter).
3. **Thin supply is the root**: today's licensed window holds ~19 events;
   the discovered lane's 1,363 published events include ZERO upcoming
   (db-report 31026850025) — the engine's whole contribution to Today is
   currently nothing. Already the named next-engine-bottleneck.

**Actions (this session, in order):** display-layer cross-source duplicate
collapse (identical venue+start+title; richest record kept; disputed rows
NEVER collapse — shown-never-hidden outranks tidiness; collapsed count
logged, never silent) → db_scope_report gains a date-distribution and
duplicate-detection section so the supply lever is chosen from evidence →
fresh licensed/structured import dispatches. The upcoming-discovered fix
follows the evidence, not a guess.
