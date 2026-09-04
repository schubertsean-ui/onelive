# Reading one public desk end to end — Chronicle EventSearch

**What you are about to see.** We treat this desk as ONE door and walk its list
from the first page to the last, turning each card into one of our rows. Three
tables follow: which pages opened (and why one did not), what the desk calls its
categories against what we call ours, and how many of those happenings we
already hold. Nothing here was published, promoted, or shown to anybody — this
is a measurement, not an ingest.

Session Contract #62, 2026-09-04. Commands are printed above every number so any
of them can be re-derived rather than trusted.

## The honest headline: the live desk was not reachable from this build

Two independent attempts, both refused by our own network before the desk was
ever asked:

```
$ curl -sS -o /dev/null -w '%{http_code}' \
    "https://calendar.austinchronicle.com/austin/EventSearch?sortType=date&v=g"
curl: (56) CONNECT tunnel failed, response 403

$ curl -sS "$HTTPS_PROXY/__agentproxy/status"      # the proxy's own record
"recentRelayFailures": [{ "kind": "connect_rejected",
  "detail": "gateway answered 403 to CONNECT (policy denial or upstream failure)",
  "host": "calendar.austinchronicle.com:443" }]
```

The WebFetch path answered the same way (`EGRESS_BLOCKED`,
`calendar.austinchronicle.com`). Per the proxy's own instructions an organisation
policy denial is reported, never retried or routed around, so this session did
not attempt a third path.

**This is our block, not the desk's.** The desk never refused us — we never
reached it. The walker records that distinction rather than flattening it:

```
$ python3 tools/desk_coverage.py --door austin-chronicle-eventsearch --real --max-pages 3
Stopped because: `fetch_error`  <- the desk's list may continue past this

| door | page | url | status | rows | new | blocked_reason |
|---|---|---|---|---|---|---|
| `austin-chronicle-eventsearch` | 1 | https://calendar.austinchronicle.com/austin/EventSearch?sortType=date&v=g | — | 0 | 0 | fetch failed: ProxyError: HTTPSConnectionPool(host='calendar.austinchronicle.com', port=443): Max retries exceeded ... (Caused by ProxyError('Unable to connect to proxy', |
```

Note what did NOT happen: the door was not demoted to class D. A wall
(401/402/403/407/429 from the desk, or a redirect onto a sign-in page) is class D
through the ingest loop's own authority; our proxy failing to connect is a
failure of ours, and treating it as the desk's would permanently shrink coverage
over a network problem (ONE-LIVE-OPERATING-LAW, effectiveness rule 4: "403/404 on
a start URL is triage").

**So every count below is a FIXTURE count**, from committed synthetic pages that
carry the desk's SHAPE (pagination, JSON-LD + HTML cards, category links, listings
with no date). They prove the machinery. They measure no live desk, and the pass
the founder named — order of magnitude against the desk's live list — cannot be
computed from this sandbox. The one command that computes it is committed and
above; it needs a run where egress to that host is allowed.

| number | live | fixture |
|---|---|---|
| pages walked | **unknown — never reached** | 3 |
| rows the desk printed | **unknown — never reached** | 18 |
| unique happenings | **unknown — never reached** | 17 |

## 1-3. The three tables (fixture run)

```
$ python3 tools/desk_coverage.py --door austin-chronicle-eventsearch
```

# Desk coverage — `austin-chronicle-eventsearch` (local_desk, via Austin Chronicle) — FIXTURE walk

Start: https://desk.example/EventSearch?sortType=date&v=g
Mapping: austin-chronicle (68 committed rows)
Stopped because: `no_next_link`

## 1. Pages

| door | page | url | status | rows | new | blocked_reason |
|---|---|---|---|---|---|---|
| `austin-chronicle-eventsearch` | 1 | https://desk.example/EventSearch?sortType=date&v=g | 200 | 7 | 7 | — |
| `austin-chronicle-eventsearch` | 2 | https://desk.example/EventSearch?sortType=date&v=g&page=2 | 200 | 7 | 6 | — |
| `austin-chronicle-eventsearch` | 3 | https://desk.example/EventSearch?sortType=date&v=g&page=3 | 200 | 4 | 4 | — |

3 page(s) opened, 3 read, 0 blocked. 18 row(s) printed, 17 unique happening(s) (1 repeat(s) across pages, 1 card(s) read twice on one page and merged, 1 block(s) with no title). 13 carry a date the page stated; 4 have an honest hole on the clock.

## 2. Categories — their label, our kind

| desk category (their label) | our kind | rows | evidence |
|---|---|---|---|
| 2151678 | `art` | 1 | desk_id_cited |
| Farmers Market | `market` | 1 | language_rule |
| Food & Drink | `food` | 1 | language_rule |
| Galleries | `art` | 1 | language_rule |
| Improv | `comedy` | 1 | language_rule |
| Kids & Family | `family` | 1 | language_rule |
| Live Music | `music` | 1 | language_rule |
| Movies | `film` | 1 | language_rule |
| Nature | `outdoors` | 1 | language_rule |
| Public Meetings | `civic` | 1 | language_rule |
| Readings | `literary` | 1 | language_rule |
| Sports | `sport` | 1 | language_rule |
| Theatre | `theater` | 1 | language_rule |
| Workshops | `class` | 1 | language_rule |
| _(no mapped category stated)_ | `other` | 3 | door scope / default |

**Unmapped (1)**, stated by the desk and not in the committed table — these rows kept the door's kind, and the table is completed from these words, never from memory: `Psychogeography`

## 3. Coverage

| scope | on_desk | in_store | gap | reason |
|---|---|---|---|---|
| kind `other` | 3 | — | — | see TOTAL |
| kind `art` | 2 | — | — | see TOTAL |
| kind `civic` | 1 | — | — | see TOTAL |
| kind `class` | 1 | — | — | see TOTAL |
| kind `comedy` | 1 | — | — | see TOTAL |
| kind `family` | 1 | — | — | see TOTAL |
| kind `film` | 1 | — | — | see TOTAL |
| kind `food` | 1 | — | — | see TOTAL |
| kind `literary` | 1 | — | — | see TOTAL |
| kind `market` | 1 | — | — | see TOTAL |
| kind `music` | 1 | — | — | see TOTAL |
| kind `outdoors` | 1 | — | — | see TOTAL |
| kind `sport` | 1 | — | — | see TOTAL |
| kind `theater` | 1 | — | — | see TOTAL |
| **TOTAL (this desk)** | **17** | **unverified** | **unverified** | ONELIVE_DB_DSN is not set in this environment, so the store was never asked — `unverified`, never 0 |
| _fixture run_ | — | — | — | counts above are from committed shape fixtures, not from the live desk |

`in_store` is only ever filled for the TOTAL row: a stored candidate carries a title and a time, not one of our kinds, so a per-kind store count would be inferred rather than counted.

**Fixture run.** SYNTHETIC shape fixtures for the paginating desk walk. These are NOT a saved copy of any live page: egress to the real desk is denied from the build sandbox (CONNECT 403 at the proxy, 2026-09-04), and every title, venue and date here is invented for the test. What is faithful is the SHAPE — JSON-LD plus HTML cards, a rel=next link on page 1, a text 'Next' anchor on page 2, no next link on page 3, one listing repeated across pages 1 and 2, two listings with no date in markup, and one untitled block. Counts derived from these files are fixture counts and every table that prints them says so.

This tool wrote nothing: no candidate, no promotion, no user-visible row. Reading a desk does not change the catalog — wiring these rows into the pipeline is a separate, named step.

## The committed mapping table — their category, our kind

`sources/kind_maps/austin-chronicle.json`, 68 rows, validated at load
time against this locale's own kind vocabulary
(`sources/locale_packs/us-tx-capcog.json` -> `query_grammar.kinds`). A mapping
that names a kind we do not have is a load ERROR, not a dropped row: their labels
map INTO our vocabulary and never extend it. Anything unmapped lands on `other`,
and the reader PRINTS what it could not map so this table is completed from the
desk's own words rather than from anyone's memory of its taxonomy.

| our kind | desk labels this table maps to it | rows | evidence |
|---|---|---|---|
| `art` | Art, Arts, Visual Art, Visual Arts, Gallery, Galleries, Exhibition, Exhibitions | 8 | language_rule |
| `film` | Film, Films, Movies, Cinema, Screening, Screenings | 6 | language_rule |
| `literary` | Literary, Literature, Books, Readings, Poetry, Author Events | 6 | language_rule |
| `market` | Market, Markets, Farmers Market, Farmers Markets, Flea Market, Craft Fair | 6 | language_rule |
| `class` | Class, Classes, Workshop, Workshops, Lessons | 5 | language_rule |
| `family` | Family, Kids, Kids & Family, Children, All Ages | 5 | language_rule |
| `food` | Food, Food & Drink, Drink, Dining, Culinary | 5 | language_rule |
| `outdoors` | Outdoors, Outdoor, Nature, Hiking, Parks | 5 | language_rule |
| `civic` | Civic, Government, City Council, Public Meetings | 4 | language_rule |
| `comedy` | Comedy, Standup, Stand-Up Comedy, Improv | 4 | language_rule |
| `music` | Music, Live Music, Concert, Concerts | 4 | language_rule |
| `theater` | Theater, Theatre, Plays, Stage | 4 | language_rule |
| `sport` | Sport, Sports, Athletics | 3 | language_rule |
| `other` | Other, Miscellaneous | 2 | language_rule |
| `art` | section id `2151678` | 1 | desk_id_cited |

Read the evidence column strictly:

* `desk_id_cited` — the desk's own section id, cited to a committed door URL in
  the locale pack. That door is graded `found_unverified`, so this row inherits
  that standing and is re-checked on the first authorized live read.
* `language_rule` — an ordinary English category word that NAMES one of our
  kinds ("movies" -> `film`). It is a statement about OUR vocabulary applied to
  whatever text a desk prints. **It is not a claim that this desk prints it.**
  There are no `desk_observed` rows yet, because nobody has read the live page.

Deliberately NOT mapped, so they surface as unmapped instead of being guessed:
labels that name something we have no kind for (a dance listing is not
`theater` by our vocabulary), and anything whose reading depends on the desk's
own conventions.

## What this changes on the live site

Nothing, yet — and that is stated rather than glossed. This PR adds a reader, a
mapping and a report. It writes no candidate, promotes nothing, and touches no
consumer surface. Reading a desk becomes coverage only when these rows are
wired to the candidate path, which is a separate, named step and is not in this
ticket.

Three files already recorded (R-105, PR #222) would hide these rows if they were
wired forward today: `api/public.py` (the city stamp, and the NULL `start_time`
filter that drops every honest hole on the clock) and `worker/gating.py`
(`ANCHOR_CLASSES` has no class for a local desk of this kind).

## The exact next desk after merge

`do512-today` — `https://do512.com/events/today`, door type `marketplace`,
public, HTML, graded `catalogued` in the pack. It is the founder's own signalled
next ("Do not start Do512 in this PR"), it is the widest general-audience list in
the locale after this one, and it exercises the one branch this desk did not: a
marketplace sits in the corroboration tier downstream, so its rows exist on the
same terms but are graded differently at promote time.

Runner-up if that door turns out to wall: `showlist-austin`
(`https://austin.showlists.net/`, `local_desk`, public, HTML) — a plain single
list, the cheapest possible second proof that the walker is not shaped around one
desk's markup.
