# 1LIVE — Cost Matrix DRAFT v1 (for founder ratification)

**Status: PROPOSAL — every number below is illustrative until founder-ratified.**
This is the C2 deliverable of `docs/strategy/ONE_LIVE_CONVERGENCE_v1.md` §11
(founder decision 1): the asymmetric cost matrix is "the gate's value system;
it is founder voice, not agent judgment," so nothing here is live and no
number ships in code (`worker/convergence/decisions.py` refuses to run
without an explicitly loaded matrix). Once ratified, this matrix becomes a
**versioned config file on the trust path**: every change is a visible diff,
and any loosening is a gate-threshold relaxation — founder-crucial per the
charter.

Date: 2026-07-22. Consumed by: `worker/convergence/decisions.py`
(`CostMatrix.from_json`), SHADOW-ONLY until the founder ratifies coupling at
C5.

## 1. What this table means, in plain language

For every claim, the scenario engine (spec §5) estimates three probabilities:
the event isn't real at all (**fully_wrong**), it's real but a detail is
wrong (**partially_wrong**), or everything checks out (**right**). The gate
then has four possible moves, and this table says how bad each combination
of move x reality is, in a single unit of "trust damage" where **0 = the
ideal outcome** and **100 = the worst thing we can do** (send someone to a
dark room on our strongest promise). The decision rule is simply: pick the
move with the lowest probability-weighted damage. All the asymmetry the
founder asked for — phantom event >> hidden real event >> time error —
lives in these numbers and nowhere else.

Actions (spec §5): `surface_confirmed` (show with full confidence),
`surface_likely` (show, quieter framing), `hold` (don't show yet),
`flag_disputed` (show, marked disputed — never hidden).

## 2. Proposed matrix — standard events

| action \ outcome     | fully_wrong | partially_wrong | right |
|----------------------|------------:|----------------:|------:|
| `surface_confirmed`  |         100 |               6 |     0 |
| `surface_likely`     |          40 |               4 |     1 |
| `hold`               |           2 |              10 |    15 |
| `flag_disputed`      |           3 |               6 |     8 |

Each number, argued in one sentence:

- **surface_confirmed / fully_wrong = 100** — a user travels to a phantom
  event on our strongest promise: the trust catastrophe the whole product
  exists to prevent, so it anchors the scale at maximum.
- **surface_confirmed / partially_wrong = 6** — the night mostly works but
  a detail (start time, price, tag) was wrong under a confident framing:
  a real but survivable annoyance, deliberately far below any hidden-real
  cost per the founder's ordering (phantom >> hidden-real >> time error).
- **surface_confirmed / right = 0** — a real event shown confidently is
  exactly the job done right.
- **surface_likely / fully_wrong = 40** — still a phantom shown, but the
  quieter framing told the user we weren't certain, so the betrayal is
  materially smaller than a false "confirmed" while remaining the dominant
  risk of showing.
- **surface_likely / partially_wrong = 4** — a wrong detail hurts slightly
  less when we visibly under-promised.
- **surface_likely / right = 1** — showing a solid event under-confidently
  costs a little credibility and click-through, but the user still gets
  their night.
- **hold / fully_wrong = 2** — correctly keeping a phantom off the feed is
  nearly free, priced just above zero for the pipeline and admin-review
  noise it still generates.
- **hold / partially_wrong = 10** — hiding an event that was real with one
  wrong detail forfeits most of a real night out for users and audience
  for the venue.
- **hold / right = 15** — hiding a fully real event is the second-worst
  failure class (users lose the night, the venue loses its crowd, and we
  lose the reason to open the app), an order of magnitude below the
  phantom catastrophe but clearly above every detail error.
- **flag_disputed / fully_wrong = 3** — a phantom shown as disputed wastes
  some user attention but arrives pre-warned, and the disputed surface is
  doing exactly its job.
- **flag_disputed / partially_wrong = 6** — a mostly-right event under a
  dispute banner both under-serves the event and spends dispute-marker
  credibility.
- **flag_disputed / right = 8** — casting doubt on a perfectly good event
  is priced just below hiding it, because disputed-shown still beats
  hidden per the shown-never-hidden invariant, but it is not cheap.

## 3. Prominence scaling

The founder's brief scales impact by prominence (spec §5: "scaled by event
prominence"). Proposal: **two tiers**. High-prominence events (headliner
acts, high expected traffic — the concrete trigger metric is part of this
ratification) multiply every **user-facing** cell by **4**, because four
times the audience sees the same mistake; the one purely internal cell
(`hold` on a phantom — nobody outside ever sees it) stays flat.

| action \ outcome     | fully_wrong | partially_wrong | right |
|----------------------|------------:|----------------:|------:|
| `surface_confirmed`  |         400 |              24 |     0 |
| `surface_likely`     |         160 |              16 |     4 |
| `hold`               |           2 |              40 |    60 |
| `flag_disputed`      |          12 |              24 |    32 |

Note what scaling does and doesn't change: because (almost) all losses
scale together, the *chosen action* at a given belief barely moves — but
the **Value of Information** scales with the losses while fetch costs
don't, so a high-prominence event justifies roughly four times as much
re-verification spend. That is the founder's "verify harder when it
matters more," falling out of the arithmetic instead of a special rule.

## 4. Worked example 1 — thin evidence: the engine chooses the quiet framing

A claim's scenario pass returns P(fully_wrong)=0.05,
P(partially_wrong)=0.15, P(right)=0.80. `decide()` computes every action's
expected loss as sum of P(outcome) x cost(action, outcome), standard tier:

| action              | fully_wrong term | partially_wrong term | right term | expected loss |
|---------------------|-----------------:|---------------------:|-----------:|--------------:|
| `surface_confirmed` | 0.05 x 100 = 5.00 | 0.15 x 6 = 0.90 | 0.80 x 0 = 0.00 | **5.90** |
| `surface_likely`    | 0.05 x 40 = 2.00 | 0.15 x 4 = 0.60 | 0.80 x 1 = 0.80 | **3.40** |
| `hold`              | 0.05 x 2 = 0.10 | 0.15 x 10 = 1.50 | 0.80 x 15 = 12.00 | **13.60** |
| `flag_disputed`     | 0.05 x 3 = 0.15 | 0.15 x 6 = 0.90 | 0.80 x 8 = 6.40 | **7.45** |

Argmin: **`surface_likely` at 3.40**. Read the rationale straight off the
rows: at 5% phantom risk, "confirmed" is carrying 5.00 points of phantom
exposure on its own, while holding an 80%-real event throws away 12.00
points of real nights — the quiet framing is the honest middle and the
arithmetic says so.

## 5. Worked example 2 — strong corroboration: the engine commits

After two independent confirmations, the same claim resolves to
P(fully_wrong)=0.005, P(partially_wrong)=0.035, P(right)=0.96:

| action              | fully_wrong term | partially_wrong term | right term | expected loss |
|---------------------|-----------------:|---------------------:|-----------:|--------------:|
| `surface_confirmed` | 0.005 x 100 = 0.500 | 0.035 x 6 = 0.210 | 0.96 x 0 = 0.000 | **0.710** |
| `surface_likely`    | 0.005 x 40 = 0.200 | 0.035 x 4 = 0.140 | 0.96 x 1 = 0.960 | **1.300** |
| `hold`              | 0.005 x 2 = 0.010 | 0.035 x 10 = 0.350 | 0.96 x 15 = 14.400 | **14.760** |
| `flag_disputed`     | 0.005 x 3 = 0.015 | 0.035 x 6 = 0.210 | 0.96 x 8 = 7.680 | **0.015 + 0.210 + 7.680 = 7.905** |

Argmin: **`surface_confirmed` at 0.710**. Note the crossover is purely a
consequence of the ratified numbers — at 96% right, the residual phantom
exposure (0.500) is finally cheaper than the under-claiming tax
(`surface_likely`'s 0.960 on the right-outcome row). Where exactly that
crossover sits IS the value judgment being ratified here.

## 6. The same numbers price a re-fetch (VoI, for context)

From example 1's position (best action `surface_likely`, expected loss
3.40): a perfect venue-site check that resolves the claim outright would
land us in `hold` when it's a phantom (loss 2), `surface_likely` when a
detail is off (loss 4), `surface_confirmed` when right (loss 0), for an
expected post-fetch loss of 0.05 x 2 + 0.15 x 4 + 0.80 x 0 = 0.70. Gross
value of the fetch: 3.40 - 0.70 = 2.70 trust points; at a fetch priced 0.5
the net is +2.20 — fetch. The identical claim at example 2's beliefs has a
prior loss of only 0.710 and a perfect fetch is worth at most 0.710 - (
0.005 x 2 + 0.035 x 4 + 0.96 x 0) = 0.56 gross, net +0.06 — barely worth
one cheap fetch and nothing more. This is spec §5's "a claim at 0.99
belief buys nothing from a re-fetch" behavior, priced by the same table.

## 7. What ratification means

1. The founder edits/approves the two tables above (any numbers, any
   scale — only the *ratios* drive decisions; the unit is arbitrary) and
   the prominence tier trigger.
2. The ratified matrix lands as a versioned JSON config consumed via
   `CostMatrix.from_json` — on the trust path, where every later change is
   a reviewed diff and any loosening is founder-crucial.
3. Until both happen, the convergence engine stays SHADOW-ONLY (spec §11):
   it logs what it *would* decide; the count-based gate keeps deciding.
