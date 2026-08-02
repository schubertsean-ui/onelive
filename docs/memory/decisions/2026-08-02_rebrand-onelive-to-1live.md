# 2026-08-02 — Rebrand: OneLive → 1Live

**Founder, verbatim (2026-08-02):** "Change all 'OneLive' to '1Live' /
Everywhere, in these last 2 documents and in the repo and in the canon"

## Executed now (this docs-armed session)

- **Both deliverables** — every builder in `docs/strategy/marketing_model/`
  swept (figure text and page copy), all figures re-rendered, both PDFs
  rebuilt; the customer document's filename becomes
  `1Live_Customer_Story_v1.pdf`.
- **Living canon** — brand-name occurrences swept in all living docs:
  `docs/strategy/**`, operating docs (OPERATING_RULES, WORLD_CLASS,
  MODEL_ROUTING, TESTS, KAIZEN policy), review personas, skills, hats,
  design docs, living memory (RED_CLASSES, entities/gotchas), research
  notes, TODOS.md. Rules: `OneLive` → `1Live`; the spaced all-caps brand
  `ONE LIVE` → `1LIVE`.

## Deliberately preserved (with reasons)

1. **Historical, append-only records keep their original text** — past
   changelog entries, session arcs, Kaizen ledger rows, decision records,
   RECORD.md rows, founder-digest/friction logs. They are records of what
   was said and done when the brand was OneLive; rewriting them would
   falsify verbatim quotes and history. All NEW entries use 1Live.
2. **Machine identifiers stay** until their owners change them: the GitHub
   repo name (`onelive`), deployment URLs, the Supabase project ref, env
   var names (`ONELIVE_DB_DSN`, `ONELIVE_APPROVAL_KEY`), and `ONE_LIVE_*`
   FILENAMES (renaming ~50 canon files breaks every cross-reference —
   held as an optional follow-up sweep, R-065).
3. **Runtime code and CLAUDE.md** — the session is docs-armed; the web
   app's user-facing brand (`web/components/BrandMark.tsx` and ~50 other
   runtime files) and the CLAUDE.md charter text are the code-armed
   remainder, recorded as **R-065** with the trigger "next code-armed
   session, before any user-facing deploy". STATE.md is additionally
   frozen by the R-023 arming classification (any STATE.md edit fails
   trust-gate until the next smoke-evidence refresh) and is listed in
   R-065 rather than edited here.


## Addendum (2026-08-02, later the same day) — founder confirmations + one-pager

**Founder, verbatim:** "All fine. The agent function remains unchanged.
They do keep it. / And yes it needs to be 1Live everywhere - that is the
name and brand name."

1. **Exit behavior confirmed unchanged.** The earlier copy directive
   removed the SLOGAN only; customers do keep everything the agent builds.
   The near-identical phrases flagged at execution ("Your exit" tile,
   "no lock-in by design", "stop after any step") STAY. The keep-it-forever
   fact is now required client-facing content (it anchors the one-pager's
   bottom band).
2. **1Live everywhere ratified as the name and brand name.** The R-065
   remainder (runtime strings, CLAUDE.md, STATE.md, filename sweep, infra
   renames) now carries explicit founder authorization — no further
   founder input needed except the founder-owned infra renames themselves
   (repo name, URLs, Supabase ref, env vars), which stay on the R-065
   one-list ask. Historical records still keep original text (facts of
   the OneLive era; unchanged by this ratification).
3. **Client-facing one-pager commissioned and built** ("entirely outside
   in ... Minimal text. Max images. Use the entire page."):
   `make_onepager.py` → `1Live_Agent_One_Pager_v1.pdf` (single full-bleed
   Letter-landscape page: problem pictograms, six-step icon strip, value
   tiles, the no-dashboard text-thread vignette, and the YOURS. FOREVER.
   band — "belongs to you, whether or not you ever do more marketing with
   1Live"). Honesty line included (connections in build, statuses reported
   truthfully); worked-example numbers in the vignette are the C-11
   ILLUSTRATIVE composites.


## Addendum 2 (2026-08-02) — identifiers stay, by decision

**Founder, verbatim:** "Leave as-is for now. Any long term concern if
remain like that?"

DECIDED: the R-065 infra items stay as-is — GitHub repo name, deployment
URLs, Supabase ref, env-var names (`ONELIVE_DB_DSN`, `ONELIVE_APPROVAL_KEY`
— these intentionally KEEP their exact names; renaming them is churn with
custody risk and any future "consistency" rename is a defect, not a fix),
and the `ONE_LIVE_*.md` filenames (optional sweep remains available).
Assessment delivered in-conversation: no functional or customer-facing
concern EXCEPT the go-live rule now bound to R-065 — a customer must never
see a "onelive" URL, so the production custom 1Live domain (founder
purchase; trademark check advised) fronts the site before launch. New
canon files use the `1LIVE_` prefix; searches must cover both prefixes.
Mechanical guard added: check_artifacts.py fails any deliverable builder
that reintroduces the old brand spelling.


## Addendum 3 (2026-08-02) — one-pager copy directives

**Founder, verbatim:** "Remove this: whether or not you ever do more
marketing with 1Live. / Re: NO DASHBOARD. - put 1Live as Sender and You
as sender in appropriate mssgs / This is too simplistic and not always
relevant: Great night, invisible ... Change it to: People Want A Great
Night Out / don't be hard to find or worse, invisible / Change 'Five
sites, zero hours' to Multiple Sites. (Almost) No Time."

Executed in make_onepager.py: bottom band now reads "belongs to you."
(the keep-forever FACT stands via YOURS. FOREVER.; the qualifier clause
is removed); thread bubbles carry 1Live/You sender labels; problem card 1
recast outside-in ("People Want A Great Night Out / Don't be hard to
find — or worse, invisible", chalkboard icon replaced by a phone-with-pin);
card 2 head is "Multiple Sites. (Almost) No Time." Visual QA re-run
(thread overflow from the added labels caught and fixed before delivery).


## Addendum 4 (2026-08-02) — production domain secured; you-vs-1Live emphasis

**Founder, verbatim:** "I already have the domain 1Live.co - thru GoDaddy /
This chain and the colors don't emphasize the limited work the user does -
make it more obvious what they do using a combo of color scheme, design
and words and image. ... ie they hardly do anything but it's important -
1live does the work"

1. **Production domain: 1Live.co (GoDaddy, founder-held).** The R-065
   go-live condition is now SATISFIABLE with an owned asset: wire
   1Live.co as the production custom domain (DNS at GoDaddy → Vercel) in
   the deploy/code-armed session — no customer ever sees a onelive URL.
2. **One-pager HOW IT WORKS rebuilt as a two-lane weight contrast:** a
   thin light-blue YOU lane (three tiny chips: paste one link · choose
   your channels · tap approve — "that's all, ≈ minutes") feeding a thick
   saturated-orange 1LIVE lane (VERIFIES · BUILDS · PUBLISHES · MEASURES ·
   IMPROVES). Headline: "YOU: A FEW TAPS. 1LIVE: ALL THE WORK." The visual
   weight itself carries the founder's point: the customer hardly does
   anything, and what they do is decisive.
