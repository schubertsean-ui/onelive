# Founder escalation — should we extract events from image-only sources?

**Date:** 2026-07-29
**Status:** OPEN — awaiting founder decision
**Why this is an interrupt (not an agent decision):** it touches three
founder-crucial triggers at once — the certified extraction harness (a trust
invariant), possible new spend, and possible new services. CLAUDE.md forbids me
from starting it on my own.
**Trigger:** a review of the open-source project *PixelRAG* against our
ingestion pipeline (full write-up: `docs/memory/decisions/2026-07-29_pixelrag-visual-ingestion-assessment.md`).

---

## The one thing I need from you

**Do you want 1Live to start capturing events that appear only inside an
image** — a gig poster, a PDF flyer, an Instagram flyer, or a venue calendar
that is really just a picture — **which we cannot read today?** Pick one:

1. **Yes, scope it** — I'll run the full Friction/adversarial pass and come
   back with a concrete plan + cost estimate before any code.
2. **Not now** — I log it as a known gap and we revisit after go-live.
3. **Tell me more first** — ask anything below and I'll answer before you choose.

Nothing has been built. This is a go/no-go on *investigating*, not on shipping.

---

## Plain-language background

Right now 1Live reads events as **text**. When a venue lists shows as words on
a web page, we read them fine — and if the page is built by JavaScript, we
already open it in a real browser to get that text (`render_fetch.py`).

But some sources put the event **only in a picture**: a concert flyer saved as
a JPEG, a PDF calendar, an Instagram post. To us today, those pages look empty —
there are no words to read, so the event silently never enters the pipeline. I
verified this: our extraction code has no ability to "look at" an image, and our
browser step deliberately throws images away to run fast.

I reviewed PixelRAG because it is built around exactly this "read the picture,
not the text" idea.

## Why this, not that

- **Why not just adopt PixelRAG?** It solves the *opposite* problem. PixelRAG
  is a *search engine* — "find the document that looks like this" across a big
  library. We do not have a search problem; we already know which pages to
  fetch. We have an *extraction* problem — pull the band, date, and venue out.
  Adopting it would also mean standing up a new AI model on a rented GPU plus a
  new database, i.e. a new monthly bill and a new service to babysit.
- **Why the alternative I'd recommend instead:** we already run a real browser
  (for the JavaScript pages) and we already pay for a Claude model that can look
  at images. So the cheap path is: take a screenshot with the browser we already
  have, and ask the Claude model we already pay for to read the event off it —
  producing the *exact same* structured result our text path produces. **No new
  service, no new database, no new model to host.**

## Tradeoffs — honestly

- **What gets better:** we stop missing the flyer-only / PDF-only long tail —
  often the smaller, more interesting independent shows.
- **What the cost is:** reading an image costs more per source than reading
  text, so this must stay a *fallback* — used only when the text path finds
  nothing, never on every page — to respect our cost discipline. I would build
  in a hard per-run cap, same as we do for text extraction today.
- **What risk remains:** it is a change to the **certified extraction harness**,
  which is trust-critical. It cannot ship on a green build alone — it must pass
  your attended golden exam like any extraction change. That is a feature, not a
  delay to route around.
- **What I am NOT proposing:** no new vendor, no PixelRAG dependency, no image
  storage build-out beyond what we already have for Tastemaker photos.

## If you want more before deciding

- The full technical assessment (why PixelRAG is the wrong tool, what I
  inspected to confirm the gap):
  `docs/memory/decisions/2026-07-29_pixelrag-visual-ingestion-assessment.md`
- PixelRAG itself: https://github.com/StarTrail-org/PixelRAG
- The browser step that already throws images away (the code I'd extend):
  `worker/fetch/render_fetch.py`
- The extraction step a screenshot would feed into:
  `worker/ai_extract.py`

## What happens on each answer

- **Yes** → I write the plan to `docs/FRICTION_LOG.md`, have the independent
  (non-Claude) evaluator attack it, size the per-source cost, and return with a
  go/no-go plan. Still zero code until you approve the plan.
- **Not now** → I record it as an OPEN gap with a revisit trigger and move on.
- **More info** → reply with your questions here.
