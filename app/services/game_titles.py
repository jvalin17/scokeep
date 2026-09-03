"""Post-game title system — thin facade over title_registry + title_patterns.

GameContext + build_context: data extraction from rounds.
evaluate_titles + select_titles: orchestration and selection.
Declarative titles: title_registry.py (13 simple titles).
Complex evaluators: title_patterns.py (27 complex titles).
"""

from __future__ import annotations

from app.services.round_utils import _iter_round_bids
from app.services.title_patterns import (
    COMPLEX_PATTERNS,
    _avg_bid_pattern,  # noqa: F401 — re-export for tests
    _variance_pattern,  # noqa: F401 — re-export for tests
)

# ── Registry (backward compat — guard tests check TITLE_REGISTRY) ────────────
# Includes both complex patterns AND wrappers for declarative titles.
from app.services.title_registry import (
    DECLARATIVE_TITLES,
    GameContext,  # noqa: F401 — re-export
    _candidate,  # noqa: F401 — re-export for tests
    _evaluate_one,
    evaluate_declarative,
)


def _make_declarative_wrapper(defn):
    """Create a function that evaluates one declarative title against a context."""

    def wrapper(ctx):
        return _evaluate_one(defn, ctx)

    wrapper.__name__ = f"_{defn['key']}"
    return wrapper


TITLE_REGISTRY: list = list(COMPLEX_PATTERNS) + [
    _make_declarative_wrapper(d) for d in DECLARATIVE_TITLES
]


def build_context(players: list[str], game_rounds) -> GameContext:
    totals: dict[str, int] = dict.fromkeys(players, 0)
    bids_made: dict[str, int] = dict.fromkeys(players, 0)
    bids_total: dict[str, int] = dict.fromkeys(players, 0)
    zero_bids_made: dict[str, int] = dict.fromkeys(players, 0)
    zero_bids_attempted: dict[str, int] = dict.fromkeys(players, 0)
    overbids: dict[str, int] = dict.fromkeys(players, 0)
    underbids: dict[str, int] = dict.fromkeys(players, 0)
    best_bid_made: dict[str, int] = dict.fromkeys(players, 0)
    miss_streak: dict[str, int] = dict.fromkeys(players, 0)
    make_streak: dict[str, int] = dict.fromkeys(players, 0)
    longest_miss_streak: dict[str, int] = dict.fromkeys(players, 0)
    longest_make_streak: dict[str, int] = dict.fromkeys(players, 0)
    score_history: dict[str, list[int]] = {p: [] for p in players}
    bid_sequence: dict[str, list[tuple[int, int]]] = {p: [] for p in players}
    round_scores: dict[str, list[int]] = {p: [] for p in players}
    cards_per_round: list[int] = []
    trump_per_round: list[str] = []
    off_by_one: dict[str, int] = dict.fromkeys(players, 0)

    seen_rounds: set = set()

    for name, bid, hand, score, rnd in _iter_round_bids(players, game_rounds):
        if id(rnd) not in seen_rounds:
            seen_rounds.add(id(rnd))
            cards_per_round.append(rnd.cards_dealt)
            trump_per_round.append(getattr(rnd, "trump", ""))

        bids_total[name] += 1
        bid_sequence[name].append((bid, hand))
        round_scores[name].append(score)
        totals[name] += score
        score_history[name].append(totals[name])

        made = bid == hand
        if made:
            bids_made[name] += 1
            make_streak[name] += 1
            miss_streak[name] = 0
            if bid > best_bid_made[name]:
                best_bid_made[name] = bid
            if bid == 0:
                zero_bids_made[name] += 1
        else:
            miss_streak[name] += 1
            make_streak[name] = 0
            if hand > bid:
                underbids[name] += 1
            else:
                overbids[name] += 1
            if abs(hand - bid) == 1:
                off_by_one[name] += 1

        if bid == 0:
            zero_bids_attempted[name] += 1

        longest_miss_streak[name] = max(longest_miss_streak[name], miss_streak[name])
        longest_make_streak[name] = max(longest_make_streak[name], make_streak[name])

    accuracy = {p: bids_made[p] / bids_total[p] if bids_total[p] > 0 else 0.0 for p in players}
    round_count = len(cards_per_round)

    return GameContext(
        players=players,
        totals=totals,
        round_count=round_count,
        accuracy=accuracy,
        bids_made=bids_made,
        bids_total=bids_total,
        zero_bids_made=zero_bids_made,
        zero_bids_attempted=zero_bids_attempted,
        overbids=overbids,
        underbids=underbids,
        best_bid_made=best_bid_made,
        longest_miss_streak=longest_miss_streak,
        longest_make_streak=longest_make_streak,
        score_history=score_history,
        bid_sequence=bid_sequence,
        round_scores=round_scores,
        cards_per_round=cards_per_round,
        trump_per_round=trump_per_round,
        off_by_one=off_by_one,
    )


# ── Selection ────────────────────────────────────────────────────────────────


def select_titles(
    candidates: list[dict], players: list[str], target: int | None = None
) -> list[dict]:
    if target is None:
        target = max(4, min(2 * len(players), 14))

    used_keys: set = set()
    covered: set = set()
    result: list[dict] = []

    def sort_key(c):
        idx = players.index(c["player"]) if c["player"] in players else 9999
        return (-c["score"], idx)

    sorted_cands = sorted(candidates, key=sort_key)

    # Phase 1: coverage — every player gets at least 1
    for p in players:
        player_cands = [c for c in sorted_cands if c["player"] == p and c["key"] not in used_keys]
        if player_cands:
            best = player_cands[0]
            result.append(best)
            used_keys.add(best["key"])
            covered.add(p)

    # Phase 2: fill up to target by score desc
    for c in sorted_cands:
        if len(result) >= target:
            break
        if c["key"] in used_keys:
            continue
        result.append(c)
        used_keys.add(c["key"])

    return result


# ── Orchestrator ─────────────────────────────────────────────────────────────


def evaluate_titles(players: list[str], game_rounds) -> list[dict]:
    if not game_rounds:
        return []
    ctx = build_context(players, game_rounds)
    if ctx.round_count == 0:
        return []

    # Collect candidates from both declarative and complex titles
    candidates: list[dict] = []
    candidates.extend(evaluate_declarative(ctx))
    for fn in COMPLEX_PATTERNS:
        candidates.extend(fn(ctx))

    return select_titles(candidates, players)
