# Member preferences & connections v1 — save your taste, favorite anything, connect your music (PROPOSAL)

Greppable summary: founder-directed (2026-07-15: "a formal build option for
people to save their preferences or connect their playlists or 'favorite'
artists or venues or bars or restaurants or museums or schools or
auditoriums or theaters or comedy clubs or… any entertainment venue").
Three phases by cost/consent weight: P1 anonymous on-device preferences
(no account, pre-launch-safe) · P2 account favorites for artists + ANY
place (extensible venue-type taxonomy) · P3 playlist/library connections
(Spotify/Apple Music OAuth — new services, FOUNDER-CRUCIAL at build).
Personalization is a LENS, never a GATE: the honest full feed is always
one tap away, nothing is hidden, recommendations carry provenance and are
never for sale. STATUS: PROPOSAL for ratification; P1 has no blockers.

## The venue-type taxonomy (the founder's "or… any entertainment venue")

`place_type` becomes an extensible config vocabulary, favoritable from day
one even where 1Live doesn't yet LIST that type's events: music venue ·
bar · restaurant (incl. supper clubs — Broken Spoke is all three) · dance
hall · theater · auditorium/PAC · museum · gallery · school/university
venue · comedy club · outdoor/park stage · church/community hall · …
(config rows, never code). Honesty note: favoriting a comedy club works
the moment P2 ships; comedy LISTINGS remain out of content scope until the
founder expands it (voice persona #20's demand log is the evidence stream
for when).

## Phases

### P1 — "My defaults" (on-device, no account, buildable at Step 9)
Saved genres, neighborhoods, price preference, radius, day habits — stored
on the device (localStorage), applied as the default lens on open ("your
scene: jazz + east side" chip visible + one tap to full feed). Zero
credentials, zero PII server-side, works behind the stealth gate. This is
the brief's "identity, gently" (§6.D7) with zero privacy surface.

### P2 — Favorites (account layer via existing Clerk)
Heart any artist or any PLACE (full place_type vocabulary). Favorites
power: "your artists playing this week," venue-first views, and later
notifications (a separate consent + timing decision). Server-side personal
data begins here → §13 privacy engineering applies from the first row
(data map entry, DSAR/delete = purge, favorites never sold or shared,
never used to rank the public feed).

### P3 — Connections (Spotify / Apple Music)
OAuth into the fan's library: followed/top artists matched against
upcoming lineups — "12 artists you listen to are playing Austin this
month" is the strongest retention surface this product can own, and both
platforms expose exactly the needed read scopes (Spotify Web API
top/followed artists; Apple MusicKit library). COSTS: developer-program
registration, OAuth apps, secret custody, review processes = new services
+ credentials = FOUNDER-CRUCIAL when built. Privacy: read-only minimal
scopes, matching happens server-side against our lineup data, library
contents are never stored wholesale, disconnect = purge derived data.

## Trust screens (the rules that make this 1Live and not an ad platform)

1. **Lens, never gate:** personalization re-orders and highlights; it
   never removes. The full chronological feed stays one visible tap away;
   disputed/uncertain display rules are identical under every lens.
2. **Provenance on every recommendation:** "because you favorited Sahara
   Lounge" / "because Culebra Canyon is in your library" — no black-box
   'for you'; the reflection test (§6) applies to every personalized row.
3. **Never for sale, never leaked:** preference and connection data plays
   no role in what ANYONE ELSE sees, is never sold, and never feeds a
   pay-to-reach surface. Discovery integrity outranks growth mechanics.
4. **Tastemaker separation unchanged:** favorites are structured
   preference data; they never touch the event candidate/gating pipeline.

## Disposition

P1 → Step 9 build scope (small, no decisions needed beyond this doc's
ratification). P2 → post-launch, first account-layer PR (privacy map in
the same PR). P3 → founder-crucial service decision when P2 usage earns
it. Genre preferences reference the taxonomy proposal (ratify that first
or together).
