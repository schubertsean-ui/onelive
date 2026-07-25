"""Proof tests for the HELD-OUT (hidden) brain memory eval (brain/eval/held_out.py).

Greppable summary: these tests prove the held-out set does the four jobs that
make it a trustworthy anti-gaming gate:

  1. DISJOINTNESS — the held-out questions share NO question text and NO gold
     answer with the visible benchmark (brain/eval/benchmark.py). If they
     overlapped, optimizing the visible set would leak into the hidden one and
     the split would be a fiction.
  2. IT MEASURES — the live brain meets its recorded held-out floor (the eval
     actually runs the real brain-backed read surface and scores it).
  3. IT CAN GO RED — a PLANTED regression (a read surface that drops a hop, a
     time-blind read, a fabricating read, a damaged corpus) drops the relevant
     category below floor. A gate that cannot fail proves nothing.
  4. OVERFITTING IS CAUGHT — an answerer that MEMORIZES the visible set's gold
     answers scores a perfect pass on the VISIBLE set but FAILS the held-out
     set. This is the whole point of a dev/test split: a self-optimizing agent
     that overfits the dev questions cannot fake a held-out improvement.

Pure-logic, deterministic: no database, no network, no LLM, no spend.
"""
from brain.eval.benchmark import (
    BENCHMARK,  # the VISIBLE (dev) set
    CATEGORIES,
    ENTITY_RESOLUTION,
    KNOWLEDGE_UPDATE,
    MULTI_HOP,
    SINGLE_FACT,
    all_questions as visible_questions,
)
from brain.eval.harness import Answer, BrainAnswerer, run_benchmark
from brain.eval.held_out import (
    all_held_out_questions,
    held_out_baselines,
    run_held_out,
)


def _floors() -> dict:
    return held_out_baselines()["categories"]


def _gold_values(questions) -> set:
    """Every concrete gold answer string a question set expects (single values
    and both sides of every dispute). Abstentions carry no value."""
    vals = set()
    for q in questions:
        if q.gold.value is not None:
            vals.add(q.gold.value)
        for v in (q.gold.values or ()):
            vals.add(v)
    return vals


# --- 1. DISJOINTNESS: the split is real --------------------------------------
def test_held_out_questions_are_text_disjoint_from_visible():
    visible = {q.text for q in visible_questions()}
    held = {q.text for q in all_held_out_questions()}
    overlap = visible & held
    assert not overlap, (
        f"held-out shares question TEXT with the visible set: {sorted(overlap)} "
        f"— a leaked question means overfitting the dev set carries over.")


def test_held_out_gold_answers_are_disjoint_from_visible():
    visible = _gold_values(visible_questions())
    held = _gold_values(all_held_out_questions())
    overlap = visible & held
    assert not overlap, (
        f"held-out shares GOLD ANSWERS with the visible set: {sorted(overlap)} "
        f"— a memorized visible answer must not be a correct held-out answer.")


def test_held_out_covers_all_six_categories_with_enough_questions():
    counts = {c: 0 for c in CATEGORIES}
    for q in all_held_out_questions():
        counts[q.category] += 1
    assert set(counts) == set(CATEGORIES)
    for cat, n in counts.items():
        assert n >= 4, f"held-out category {cat} has only {n} questions (need >= 4)"


# --- 2. IT MEASURES: the live brain meets its recorded held-out floor ---------
def test_live_brain_meets_every_held_out_floor():
    report = run_held_out()
    floors = _floors()
    for cat in CATEGORIES:
        acc = report.per_category[cat].accuracy
        base = float(floors[cat])
        assert acc + 1e-9 >= base, (
            f"held-out {cat} regressed: {acc:.4f} < floor {base:.4f}")


def test_held_out_reuses_the_same_deterministic_scorer():
    # Two runs are byte-for-byte identical (deterministic, no clock/network).
    a = run_held_out()
    b = run_held_out()
    assert a.overall_accuracy == b.overall_accuracy
    assert [(r.id, r.correct) for r in a.results] == \
           [(r.id, r.correct) for r in b.results]
    # And the same provenance/abstention properties the visible harness reports.
    assert a.provenance_citation_rate == 1.0


# --- 3. IT CAN GO RED: planted regressions drop the category below floor ------
class _DropHopAnswerer(BrainAnswerer):
    def multi_hop(self, g, sid, path):
        from brain.eval.harness import multi_hop as real_multi_hop
        # Traverse ONE fewer edge than asked — a genuine reasoning regression.
        return real_multi_hop(g, sid, path[:-1]) if len(path) > 1 \
            else Answer.unknown()


def test_planted_read_surface_regression_makes_held_out_multi_hop_red():
    floors = _floors()
    report = run_held_out(answerer=_DropHopAnswerer())
    acc = report.per_category[MULTI_HOP].accuracy
    assert acc < float(floors[MULTI_HOP]), (
        "dropping a hop must drop held-out multi_hop below its floor — a gate "
        "that cannot fail is worthless")


class _TimeBlindAnswerer(BrainAnswerer):
    def as_of(self, g, sid, pred, date):
        from brain.eval.harness import current_value as real_current
        # Ignore the queried instant; answer with today's value.
        return real_current(g, sid, pred)


def test_planted_time_blind_regression_makes_held_out_knowledge_update_red():
    floors = _floors()
    report = run_held_out(answerer=_TimeBlindAnswerer())
    acc = report.per_category[KNOWLEDGE_UPDATE].accuracy
    assert acc < float(floors[KNOWLEDGE_UPDATE]), (
        "ignoring bi-temporal validity must drop held-out knowledge_update "
        "below its floor")


class _FabricatingAnswerer(BrainAnswerer):
    def single_fact(self, g, sid, pred):
        real = super().single_fact(g, sid, pred)
        if real.is_unknown():
            return Answer(value="(fabricated)", sources=["source:made-up"])
        return real

    def via_alias(self, g, alias, pred):
        real = super().via_alias(g, alias, pred)
        if real.is_unknown():
            return Answer(value="(fabricated)", sources=["source:made-up"])
        return real


def test_planted_fabrication_regression_makes_held_out_abstention_red():
    from brain.eval.benchmark import ABSTENTION
    floors = _floors()
    honest = run_held_out()
    fabricating = run_held_out(answerer=_FabricatingAnswerer())
    assert honest.per_category[ABSTENTION].accuracy >= float(floors[ABSTENTION])
    assert fabricating.per_category[ABSTENTION].accuracy < float(floors[ABSTENTION]), (
        "fabricating an answer to an unanswerable held-out question must score "
        "wrong")


def _break_resolution(g, keymap, scenario):
    if scenario.id != "held_aliases":
        return
    # Reverse the alias merge via the brain's own reversible primitive; the
    # surface forms can no longer reach the canonical entity's facts.
    g.unresolve(keymap["axelrad"])


def test_planted_corpus_regression_makes_held_out_entity_resolution_red():
    floors = _floors()
    report = run_held_out(mutate=_break_resolution)
    acc = report.per_category[ENTITY_RESOLUTION].accuracy
    assert acc < float(floors[ENTITY_RESOLUTION]), (
        "breaking resolution must drop held-out entity_resolution below floor")


# --- 4. OVERFITTING IS CAUGHT: memorizing the visible set fails the held-out --
class _VisibleMemorizingAnswerer(BrainAnswerer):
    """Overfits the VISIBLE (dev) set perfectly: it returns the exact gold
    answer for every visible query, keyed by the query's structure, and abstains
    on anything it never saw. This is the strongest form of dev-set overfitting.
    On the visible set it scores 1.0; on the DISJOINT held-out set none of its
    memorized keys match, so it collapses — which is exactly what the split must
    catch."""

    def __init__(self):
        self._table = {}
        for scenario in BENCHMARK:  # the VISIBLE set only
            for q in scenario.questions:
                self._table[self._key(q.query)] = self._memorize(q.gold)

    @staticmethod
    def _key(query):
        return (query.op, query.subject, query.predicate, tuple(query.path),
                query.alias, query.as_of_date)

    @staticmethod
    def _memorize(gold) -> Answer:
        if gold.unknown:
            return Answer.unknown()
        if gold.disputed:
            return Answer(values=list(gold.values or ()), disputed=True,
                                 sources=["source:memorized"])
        return Answer(value=gold.value, sources=["source:memorized"])

    def answer(self, g, keymap, q):
        # Note: the runner passes the Query (q), not the human question text —
        # so this memorizer is keyed on query structure, the most an optimizing
        # agent could realistically capture. Anything unseen -> abstain.
        return self._table.get(self._key(q), Answer.unknown())


def test_memorizing_visible_set_passes_visible_but_fails_held_out():
    floors = _floors()
    mem = _VisibleMemorizingAnswerer()

    # (a) It DOES overfit the visible set — a perfect dev score, so a naive
    #     "did the score go up?" check on the visible set alone would be fooled.
    visible_report = run_benchmark(answerer=mem)
    for cat in CATEGORIES:
        assert visible_report.per_category[cat].accuracy == 1.0, (
            f"memorizer should reproduce the visible gold for {cat}")

    # (b) But it FAILS the held-out set: every answerable category collapses
    #     below its floor, because no memorized (visible) query key matches a
    #     held-out query — the disjoint split defeats the overfit.
    held_report = run_held_out(answerer=mem)
    answerable = [SINGLE_FACT, MULTI_HOP, KNOWLEDGE_UPDATE, ENTITY_RESOLUTION]
    for cat in answerable:
        assert held_report.per_category[cat].accuracy < float(floors[cat]), (
            f"a visible-set memorizer must fall below the held-out floor for "
            f"{cat} — overfitting the dev set must NOT pass the test set")
    # Categories with no abstention-style questions collapse all the way to 0
    # (a blanket-abstain memorizer only ever scores an abstention right).
    for cat in (SINGLE_FACT, MULTI_HOP, ENTITY_RESOLUTION):
        assert held_report.per_category[cat].accuracy == 0.0, (
            f"a visible-set memorizer must score 0 on held-out {cat}")
    # Overall held-out accuracy is far below the (1.0) floor: overfitting caught.
    assert held_report.overall_accuracy < 0.5
