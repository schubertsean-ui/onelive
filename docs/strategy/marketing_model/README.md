# Marketing Research & AI Agent Model — deliverable sources

**Status:** committed 2026-08-01 at founder direction ("update the repo and canon
as appropriate"). These scripts are the source of truth for the founder-facing
deliverable **Marketing Research & AI Agent Model v1** (27-page PDF, delivered
in-conversation 2026-08-01; ~7 MB, not committed — regenerable below). The
CONTENT they encode follows canon: the five-part communication framework
(WHAT · HOW · WHY · WHY THAT WHY MATTERS · EXPECTED OUTCOMES), the 23-segment
taxonomy, the engagement/behavioral architecture (design brief v2.4 §3/§6),
the Tier-2 monetization scoping, and the agent-surfaces inventory
(`../ONE_LIVE_AGENT_SURFACES_v1.md`).

## Regenerate

Requires: `matplotlib`, `weasyprint`, `pypdf` (pure-Python; no network).

```bash
cd docs/strategy/marketing_model
python make_glance.py      # flow_glance.png, flow_highlevel.png
python make_story.py       # storyboards: bar/winery/artist/promo + onboardloop
python make_why.py         # flow_fanout.png (demand engine grid)
python make_factory.py     # flow_factory1.png, flow_factory2.png
python make_model.py       # flow_model.png (the OneLive engine)
python make_friendly.py    # phone_bar/winery/artist.png (reads build_paper.py)
python make_casestudy.py   # cs_*.png  (Continental Club case study artifacts)
python make_kit2.py        # cs_kit.png (engagement carousel) + cs_channels.png
python build_model.py      # -> Marketing_Research_and_AI_Agent_Model_v1.pdf
```

Run order matters only in the last three lines (`make_kit2.py` overwrites the
`cs_kit.png` that `make_casestudy.py` emits — intentional; `build_model.py`
consumes all PNGs). `build_paper.py` is the 23-category content module
(single source for category briefs; canonical text lives in
`../ONE_LIVE_CATEGORY_RESEARCH_23_v1.md`).

## Design system

`DESIGN_PHILOSOPHY.md` ("Filled Frame") governs the visual language: full-bleed
card grids, no empty lanes, type sized for print at arm's length, actor hues
(blue owner / orange agent / green world / yellow tap), venue-brand colors only
inside mocked artifacts. Page aspect ≈ 0.70 (Letter-landscape full-bleed).

## Case-study data caveat (R-025)

`make_casestudy.py` encodes REAL public data on The Continental Club gathered
2026-08-01 via search-index snapshots (sandbox network policy blocked direct
fetches). Per `docs/RECORD.md` R-025 the read must be re-run as a direct crawl
before any partner-facing use. Nothing was published anywhere; the venue is not
affiliated. See `../ONE_LIVE_CASE_STUDY_CONTINENTAL_v1.md`.
