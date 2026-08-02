# 1LIVE — Growth Loops & Design-Tool Stack v1

**Status: PROPOSAL** — nothing here is license to build. Every loop design must
clear the full po battery + Friction attack (charter: Thinking tools §1, Friction
Agent) and the design brief's white-hat reflection test (§6) before any
implementation. PostHog adoption is a NEW SERVICE = **founder-crucial** — the
founder decides and mints the key, at Step 9, never the agent.

Provenance: researched and delivered to the founder in chat 2026-07-22
(founder request: "Research the best site design tools that a world class
app/site would use given our vision … and most important the user experience
and the Nir Eyal and other experts methods and practices that make the site one
that people want to use over and over … I want this to be one of the fastest
growing sites ever created."). Text below is the delivered research, verbatim
except this header and the chat-only framing lines. Web sources linked inline
were live as of 2026-07-22.

---

## The starting point: half of this is already ratified canon

The design brief (§6, "Behavioral Architecture") already encodes Nir Eyal's full
Hook cycle, Thaler/Sunstein choice architecture, Loewenstein's curiosity-gap
theory, and a synthesis of the most-returned-to products ever built (Wordle's
daily edition, Duolingo's compounding investment, the shareable artifact) — each
constrained by the white-hat reflection test. 1Live holds a structural
advantage most apps fake: **tonight is a genuinely new edition every day**. The
variable reward is real, so the Hook needs no manufacturing. What the canon
*doesn't* yet cover is the acquisition half — how users create users. That's
where "fastest-growing" actually lives.

## Growth methods: loops, not funnels

The modern consensus ([Reforge: "Growth Loops are the New Funnels"](https://www.reforge.com/blog/growth-loops),
[Ortto](https://ortto.com/learn/growth-loops/),
[Ward van Gasteren](https://growwithward.com/growth-loops/)) is that
fast-growing products are built as self-reinforcing loops where usage *produces*
new users. The nightlife-adjacent proof is **Partiful**: ~400% year-over-year
growth to millions of users
([CNBC](https://www.cnbc.com/2025/04/19/meet-partiful-the-gen-z-party-planning-staple-thats-taking-on-apple.html),
[Sacra](https://sacra.com/c/partiful/),
[ainvest](https://www.ainvest.com/news/rise-partiful-gen-app-disrupting-social-event-planning-outpacing-apple-2504/))
— powered by one loop: *the invite is the acquisition unit*. Every party planned
recruits every guest.

1Live has four native loops, three already ratified in some form:

1. **The plan-share loop (the Partiful analog, strongest).** The ratified Group
   Plans P0 share card: "who's in tonight?" sent to friends who aren't users
   yet. One fan planning a night recruits 2–6 people at the exact moment of
   highest intent. This should be treated as *the* growth engine.
2. **The artifact loop.** The Wordle lesson, already in the brief (§6.D5): a
   beautiful, compact share card of a show or a night — social marketing without
   discovery ever becoming social-driven.
3. **The supply-side loop.** Venues and artists who claim listings promote their
   own pages — every claimed venue is an unpaid distribution channel with a
   poster in its window.
4. **The seeding loop.** Partiful's ambassador program ($100/month to hosts) is
   the paid-cold-start version; the Tastemaker layer is the organic version.
   (This crosses into the founder's "demand/marketing later" bucket — noted,
   not designed here.)

Two evidence-based rules for when these get built
([Consumer App Growth Playbook](https://getresidualthoughts.substack.com/p/the-consumer-app-growth-playbook),
[Kasva](https://www.kasva.io/post/how-to-drive-acquisition-with-growth-loops)):
fire the share prompt at **peak delight** (after a great night, after a plan
comes together — never at signup), and reward referrals with **status or
feature unlocks, not cash** — cash referrals attract users who churn;
referred-by-a-friend-at-the-right-moment users retain best. Both rules pass the
reflection test cleanly. One addition to the canon worth adopting: the
**peak-end rule** (Kahneman) — design the *end* of the night (a morning-after
"your night" memory card) since that's what memory keeps and what gets shared.

## Tools: a deliberately short list

The honest answer for *this* product is lean — we already own a Next.js
codebase, in-repo comps, and a testing harness most startups dream of.
Why-this-not-that, per layer:

- **Design/comps: stay in-repo (current approach), Figma optional.**
  [Figma](https://uxcel.com/blog/best-product-design-tools-to-add-to-your-toolkit-in-2026)
  remains the industry default for team-scale design systems — but the team is
  one founder plus the agent, and the comps are already living HTML judged by a
  rubric and tests, which is *closer* to production truth than Figma files.
  Adopt Figma only if human designers join.
  [Framer](https://quadiz.com/2026/03/18/figma-vs-framer/) publishes marketing
  sites, not products — irrelevant to /tonight, possibly useful later for a
  landing page.
- **Motion/signature element: [Rive](https://www.trulycritic.com/blog/best-design-tool-2026)**
  — state-machine animations shipped as tiny files, GPU-accelerated. This is
  *the* tool for making the chosen signature element (Doorlight glow / Pulse
  line / Edition masthead) feel alive at 60fps without hurting the LCP≤2.5s
  budget. Worth adopting at Step 9 polish; free tier first.
- **Analytics / flags / experiments / session replay:
  [PostHog](https://www.luckyorange.com/comparisons/posthog-vs-amplitude)** —
  one tool covering all four, event-priced (generous free tier), open-source
  and self-hostable, which fits both the cost discipline and the privacy
  posture. [Amplitude](https://www.ideaplan.io/compare/amplitude-vs-posthog) is
  the ML-heavier enterprise alternative (and just absorbed
  [Statsig](https://userlifecycle.com/compare/statsig-vs-posthog)) — more power
  than needed at 10–100× the eventual price. Growth loops are engineering
  disciplines: you can't tune the 48-hour activation moment or referral timing
  without event analytics, so this is the one genuinely *new* tool worth
  adopting at launch. **New service = founder-crucial: the founder decides and
  mints the key, when we reach Step 9.**
- **Everything else already exists in-repo**: accessibility and
  visual-regression gates in the harness, Playwright, and the evaluator
  pipeline. No purchases needed.

## Adoption gates (what must happen before any of this builds)

1. Founder ratifies this doc (or the parts of it) — PROPOSAL ≠ license to build.
2. Each loop design runs the full po battery + Friction attack pre-work before
   implementation (charter requirement for design-direction/ideation moments).
3. Every share/referral surface passes the brief's reflection test and trust
   display rules; no loop may touch the candidate/gating/promotion pipeline.
4. PostHog (or any analytics): founder decision + founder-minted key + spend
   cap first, at Step 9 — logged as a decision record when it happens.
