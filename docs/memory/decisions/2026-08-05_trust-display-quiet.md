# 2026-08-05 — Trust display returns to quiet; dead controls and handoffs ruled

## Founder directives (verbatim, 2026-08-05, on reviewing the live site post-#188)

> Remove the 'How we know" - this is not supposed to be front and center -
> its in the design canon. It should be subtle and certainly tracked
> internally but only shows that MAY be iffy should have any kind of small
> scale 'note' - notthing should take up that much real estate. Where is the
> map, the venue photos, the venue 'text box to show specials or important
> notes etc.?

> Also why is there a See Tickets that does nothing beside a link to get the
> actual tickets?
> And speaaking of external links - they should never take up the entire
> screen on a mobile device. They should operate according similar to the
> slide out so a user can alwys know where they are and easily get back to
> 1live and whatever they were looking at prior to the click on the link to
> go external

## Rulings implemented

1. **Trust display quiet again.** #188 rendered a titled "How we know" block
   on every lens tab and every detail page for EVERY confidence state — a
   drift from the ratified canon (no badges, no trust prose on solid
   listings; low-confidence = quiet marker → dismissible sheet). Restored:
   confirmed/likely render NOTHING; only unverified/disputed carry the small
   marker note with the honest sentence + source-site link; disputed stays
   open-by-default and is never hidden. Provenance remains fully tracked
   internally (payload, database, /ops unchanged). Pinned in
   `web/app/(public)/tonight/trust-quiet.test.tsx`.
2. **Dead "See tickets" control.** The unknown-price placeholder text
   rendered as a chip beside the real Get-tickets button. Price now renders
   only when actually known (lens + detail page).
3. **External handoffs keep 1live's place.** Ticket links open a NEW TAB
   (noopener, destination-labeled) — this SUPERSEDES nav canon §8's same-tab
   terminal-handoff rule; `web/qa/link-policy.test.ts` now enforces the new
   rule mechanically. Honest limit stated to the founder: a true in-app
   slide-over browser for arbitrary external sites is not possible on the
   web (ticketing sites forbid embedding via frame-ancestors); a new tab is
   the closest the platform allows — 1live stays exactly where the user
   left it.

## Deferred with the founder's question on the record (not silently)

Map embed, venue photos, and the venue specials/notes text box are REAL
feature gaps, not rendering fixes — each needs a decision or a data source
that does not exist yet (map: embed provider choice; photos: rights-clean
sourcing via claimed venues; specials: a custody path for venue-authored
text). Queued as the next cards increment with options presented to the
founder in the session report.
