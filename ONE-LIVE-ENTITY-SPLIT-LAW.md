# One Live — Identity Split + Entity Universe Law

Ratified for founder direction: 2026-09-05  
Status: **in force**. This file wins on *how a page becomes happenings* and *how people/places exist as objects*. Coverage Law still wins on catalog scope. Trust still wins on existence vs field vs mutation. Vision still wins on what 1Live is.

If a ticket hard-codes Austin Chronicle, CSS class `event|card|listing`, or “one blob is fine,” the ticket is wrong.

---

## Founder answers (locked)

| Question | Answer |
|---|---|
| Does the blob-split apply to every site and every search-result page, not just Chronicle? | **Yes.** Identity first, everywhere. |
| Do we treat venue / artist / people / group / event as distinct objects, then hunt their owned site? | **Yes.** Search and licenses find *who exists*. Owned sites become doors. Happenings attach to those objects. |
| Does that graph drive both ingestion and display? | **Yes.** Ingest writes nodes and edges. Display reads them. Strings on a card are a fallback, not the model. |

---

## 1. Four objects (never collapse these)

World-class here is a **bounded context** (Fowler): four kinds of thing, explicit relationships, no god-row.

| Object | What it is | What it is not |
|---|---|---|
| **Happening** | One instance in the world: a title, a when-if-stated, a where-if-stated | A list page. A venue. A band. |
| **Place** | A durable location: venue, park, church, museum, restaurant, hall | Tonight’s show. The Chronicle row. |
| **Actor** | A durable presenter: artist, group, company, promoter, host | The night. The ticket link. |
| **Door** | A readable source: owned site, local desk, civic calendar, claim, licensed feed | The happening itself. |

Edges (only these, at first):

- Happening **at** Place  
- Happening **by** Actor (0..n)  
- Place **has door** Door (owned calendar, ICS, `/events`)  
- Actor **has door** Door (owned site, public calendar)  
- Happening **seen via** Door (Chronicle, Do512, the owned page)

A Chronicle listing is evidence on a Happening, seen via a Door. It is not the Place and not the Actor.

---

## 2. Split law — a list is never one happening

A page (desk, search results, aggregator, venue “what’s on”) is a **list** when it declares **more than one happening identity**.

**Identity is declared by the page.** We do not guess from CSS.

### Ladder (first tier that yields ≥1 identity wins; never mix tiers on one page)

1. **Structured declaration** — JSON-LD `@type: Event` (array or graph), ICS `VEVENT`, schema.org Event microdata.  
2. **Permalink identity** — an `href` that matches a **committed identity pattern** for that host family (data, not a one-off regex in Python).  
3. **Desk selector** — `(tag, class tokens)` committed for *that* door as `listing_selectors` / identity patterns. Whole tokens, not substring `card`.  
4. **Unsplit** — stop. Zero Happenings from that page. Notes say `unsplit`. **Never emit one mashed row.**

### Forbidden

- `class` contains `event|card|listing|show|gig|happening` as a global splitter.  
- Concatenating leftover titles/venues into one Happening.  
- Using the list URL (`/EventSearch`, `/today`, a Google SERP) as `listing_url` of a single event.  
- Treating “we fetched 40 pages” as “we read 40 events.” Pages ≠ rows.  
- Search snippets as Happenings. A SERP is a **finder of URLs**, not a desk.

### Identity patterns (data)

Live in `sources/identity_patterns.json` (or the locale pack). Each pattern is:

- `host_family` (e.g. `calendar.austinchronicle.com`, `do512.com`, `eventbrite.com`)  
- `path_re` (e.g. `/event/[^/]+-\d+`, `/e/[0-9]+`, `/events/[0-9]+`)  
- `grade`: `desk_observed` only after a live page was actually read; otherwise `fixture_shape`  
- `owned`: true if that host is the Place/Actor’s own site, false if a desk/aggregator

Chronicle `/event/{slug}-{id}` is **one row in that table**, not a special case in the reader. Do512, Eventbrite, Localist, a church `/calendar/event/123`, a search result whose URL already matches a pattern — same code path.

### Mash test (must be able to fail)

Given HTML with two `/event/foo-1` and `/event/bar-2` links, `read()` returns **two** Happenings with those listing URLs.  
Given a list page with **no** identity and a giant text blob, `read()` returns **zero** Happenings and `unsplit` in notes.  
A test that accepts the blob as one row is a defect.

Live evidence 2026-09-05 (desk-ingest #3/#4 on master): Chronicle opened 40 pages, emitted **1** row titled a concatenation (“Promoted Events Back To The Ranch…”), key `url:https://www.austinchronicle.com`. That is the mash this law forbids. Do not `--write` that.

---

## 3. Entity law — names become objects, then we hunt doors

### 3.1 Extract, don’t invent

From each Happening (and from licenses, civic lists, search hits):

- Place name + locality as **stated**  
- Actor names as **stated**  
- Happening title as **stated**

If the page did not name a Place, Place is a hole. Do not invent “Austin” as the venue. Do not split a title into a fake band.

### 3.2 Resolve (fail-closed merge)

Same Place only when: same locale **and** (same listing_url host path **or** same normalized name + same street **or** an official id).  
Ambiguous (“Mohawk” vs a different Mohawk) → **two Places**. Never merge on name alone.  
Same rule for Actors.

Brain `Entity` (venue/artist) already exists as memory. Product catalog Places/Actors are the durable store the feed reads. Do not confuse the two: brain does not publish.

### 3.3 Universe vs Tonight

Vision lock, restated as mechanism:

| Input | Writes | Does not write |
|---|---|---|
| License / TABC / civic registry / search “who exists here” | Place / Actor (universe) | Happenings on Tonight |
| Local desk / owned calendar / ICS / JSON-LD / claim | Happenings **and** fills Place/Actor holes | Fake dates |
| One unofficial social post | Hunt trigger | A Happening (Trust: not enough to exist alone) |

Search is a **finder of official URLs**, never a publisher.

### 3.4 Owned-site hunt (the combination)

For each Place or Actor **without** an official Door:

1. Public search query: `"{name}" {locale} official` / site / calendar — cheapest finder first.  
2. Candidate URLs only. No login, no paywall, no bot-bust. One knock.  
3. Keep a URL as **owned door** only with **same-page evidence**: name on the page matches the entity; or NAP (name/address/phone) matches; or the domain is the name they print.  
4. Ambiguous or 403 → Door class D / unknown. Queue claim. Do not guess.  
5. When an owned door is kept: it is the **best door** for that entity’s calendar. Desk listings stay as `via [desk]` and attach to the same Happening. Official fills holes; it does not delete the desk row.

This is how “we learn from Chronicle, then go direct” stays honest: Chronicle remains a trusted door; the owned site is a second door on the same Happening and the Place’s own door for the next tick.

Subscribe-inbox / membership: only after public door failed, mail actually carries a schedule, cap per locale (Vision). Not a hunt of hundreds of thousands of logins.

---

## 4. Ingestion model (spine)

Generalize the spine. Specialize the door. Combine evidence.

```
Universe tick (bounded)     List tick (bounded)           Field tick
licenses/civic/search  →  Place, Actor                  (no Tonight)
desk / SERP URLs       →  SPLIT identities → Happenings
                         attach at Place, by Actor
owned-site hunt        →  Door on Place/Actor
fetch best door        →  fields (when, place, actors)  same-page only
gate                   →  label (via, disputed, TBA)
view                   →  /tonight reads Happenings + Place + Actor
```

**Least costly method first:** pattern split and JSON-LD before any model call. Hunt and extract only on new or changed identities. Skip-unchanged / 304 on refresh. T-minus on Happenings that already have `start_time`. No category weighting. Caps are per **tick**, never “this source class is out of scope.”

**Unsplit is a coverage defect on that door**, not a reason to mash. Next ticket is a pattern or a claim, not a blob publish.

---

## 5. Display model (what the person sees)

The card is a Happening. It is **decidable in one look** because Place and Actor are objects:

- Who — Actor names, one-line from **owned materials** when we have them (Spark / sample), never invented bio  
- What — Happening title  
- When — as stated; hole stays a hole; no invented day  
- Where — Place name, short address, small map of **that Place**  
- Via — Door that stated it (`via Austin Chronicle`, `via Stubb’s`)  
- Next step — link to ticket or owned page (their shop, not ours)  
- Adjacent — other Happenings **at the same Place** that window (graph edge, not a related-string guess)

A mashed blob cannot do any of this. That is why split is a display requirement, not a parser nicety.

Trust copy: ordinary rows presumed listed by a trusted door — no per-row “verified” stamp. Path (b) only (independent people, no official word) wears the at-a-glance warning on card **and** detail. Disputed stays shown.

Privacy: Place/Actor/Happening are catalog. Night-out plans stay on device. Heartbeat is aggregates on locale × period × category, never itineraries.

---

## 6. CTO execution (how we build this without wandering)

Bar: WORLD_CLASS.md §0–§5 + this file. Small CLs. Tests that can fail. Disk is truth.

### Sequence (one ticket at a time; do not skip)

| Ticket | What ships | Must not |
|---|---|---|
| **A — this law** | This file at repo root. Pointer in CLAUDE.md. | No worker change. No `--write`. |
| **B — identity split** | Pattern table + `desk_read` / list walk uses ladder §2. Mash test red on master, green on the PR. Live dry ingest: Chronicle rows ≈ events on the page, each `listing_url` is `/event/…`, zero mash titles. | No Chronicle-only function. No class-substring splitter. No smoke of `ai_extract.py` unless wiring demands it and founder says. No `--write` until the table is honest. |
| **C — Place/Actor from listings** | Happening rows attach Place/Actor ids from **stated** names; fail-closed resolve. Display can show Place as a link even if hunt has not run. | No owned-site HTTP yet. No merge on name-only. |
| **D — owned-site hunt** | Finder job, budgeted, one knock, owned-door evidence rules §3.4. | No login. No publishing from search snippets. No telling a venue “we have your calendar.” |
| **E — display consumes graph** | Card/detail/adjacent from Place/Actor, not concatenated list text. | No Tonight redesign-as-scope-creep; only what the graph already enables. |

### Operating rules for agents

- Chronicle is the **proving ground**, not the product fence. Patterns learned there go in the **table**, then the same spine reads Do512, civic, owned sites, search-found URLs.  
- If live HTML ≠ fixture: the live page wins; upgrade `grade` to `desk_observed`; do not silently keep fixture selectors.  
- Unsplit + 403 are **our** failures or **their** wall — labeled. Never “empty calendar.”  
- Branch `grok/chronicle-event-href-rows` was a stub accident (2026-09-05). **Do not merge it.** Split ships as ticket B on a clean branch from master.  
- `--write` only after a dry ingest table a human would recognize as individual events.

### Bottleneck (named, 2026-09-05)

Not GitHub login. Not “can we fetch Chronicle.”  
**Split:** GitHub Actions already reads 40 Chronicle pages and mashes them into 1 row. Do512 is a 403 wall on the runner (class D / claim).  
Until ticket B is green, more desks and more write runs only publish blobs.

---

## 7. What “done” looks like for CAPCOG proving ground

Not “music only.” Not “every category designed.”

- Happenings on Tonight are **individual**, each with a real listing URL or a stated hole.  
- Places and Actors in the universe grow from desks **and** licenses/search, bucketed (fetch / follow / claim / mail / blocked / unknown).  
- Owned doors appear where public evidence supports them; desks still credit `via`.  
- A friend opening Tonight can decide: who, where, when, via, next step — then leave.

Friends stay off until the list itself has moved (Vision). Ticket B is what moves the list.
