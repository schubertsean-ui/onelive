# Decision: first-party sources are authoritative (founder-ratified 2026-08-05)

**Founder, verbatim (session chat, on seeing valid events held):**

> "For god's sake how many times do I need to state that if something comes
> from the source site it's authoritative - no additional gating or checking
> needed. You have overengineered this and are strangling my display of valid
> events."

**What the directive resolves.** `worker/gating.py` promoted on a single
source only when its class was one of FIVE anchors (festival_feed, ticketing,
venue_calendar, claimed_upload, email_opt_in). Everything else needed two
independent sources — corroboration a venue's own website will never receive,
because only that venue publishes its own calendar. The live database's 268
sources (db-report run 31026850025, intake_funnel.sources_by_type):

| class | sources | old gate | new gate |
|---|---|---|---|
| community | 55 | hold | hold (platform, unaudited — R-081) |
| venue_calendar | 43 | PASS | PASS |
| city_calendar | 40 | hold | **PASS** |
| local_media | 29 | hold | hold (third-party, correct) |
| theater_arts | 24 | hold | **PASS** |
| gallery_museum | 20 | hold | **PASS** |
| festival_feed | 18 | PASS | PASS |
| ticketing | 10 | PASS | PASS |
| university | 9 | hold | **PASS** |
| food_culinary | 5 | hold | **PASS** |
| social / aggregators / directory / link_hub / search_benchmark | 12 | hold | hold (third-party, correct) |
| calendar_feed / claimed_upload / email_opt_in | 3 | mixed | PASS |

**73 of 268 sources could publish; 195 could not.** Worse, `theater_arts`,
`gallery_museum`, `food_culinary` and `university` are defined NOWHERE in
this repo — they were seeded straight into the database, so the gate met
classes it had never heard of and silently held them forever. That is the
`silent-yield-collapse` class again, one layer up from the date refusal.

**The rule now, stated so it generalizes:** an ANCHOR is a source publishing
an event IT ITSELF hosts — the venue's, theater's, museum's, university's,
library's, city's own calendar; the festival's own feed; the organizer's own
claimed feed. A source REPORTING on someone else's event — newspaper, social
post, aggregator, directory, blog, community platform — is third-party and
still corroborates. That is not extra gating on the source site; it is the
difference between the horse's mouth and hearsay, which is the only thing
the multi-source rule was ever for.

**An unknown class now HOLDS AND SHOUTS** (`UNCLASSIFIED SOURCE CLASS …`
warning) instead of dying quietly. Holding is the safe direction for
something whose authority nobody has decided; the loud log is what turns a
months-long invisible outage into a config fix.

**Custody note (trust-invariant adjacent, founder-owned).** This loosens the
promotion gate, which is founder-crucial by charter — and the founder is the
one directing it, verbatim, having stated it repeatedly before. Everything
else in the gate stands unchanged: trust_gate3 still ESCALATES private-RSVP,
validation errors, conflicting start times, and dedupe ambiguity; disputed
still shows; nothing publishes without passing the full gate.
