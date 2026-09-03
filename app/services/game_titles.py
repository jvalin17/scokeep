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
    """Build a GameContext by iterating all rounds once."""
    state = _init_context_state(players)
    seen_rounds: set = set()

    for name, bid, hand, score, rnd in _iter_round_bids(players, game_rounds):
        if id(rnd) not in seen_rounds:
            seen_rounds.add(id(rnd))
            state["cards_per_round"].append(rnd.cards_dealt)
            state["trump_per_round"].append(getattr(rnd, "trump", ""))

        _process_context_bid(state, name, bid, hand, score)

    return _finalize_context(players, state)


def _init_context_state(players: list[str]) -> dict:
    """Initialize all accumulator dicts for build_context."""
    return {
        "totals": dict.fromkeys(players, 0),
        "bids_made": dict.fromkeys(players, 0),
        "bids_total": dict.fromkeys(players, 0),
        "zero_bids_made": dict.fromkeys(players, 0),
        "zero_bids_attempted": dict.fromkeys(players, 0),
        "overbids": dict.fromkeys(players, 0),
        "underbids": dict.fromkeys(players, 0),
        "best_bid_made": dict.fromkeys(players, 0),
        "miss_streak": dict.fromkeys(players, 0),
        "make_streak": dict.fromkeys(players, 0),
        "longest_miss_streak": dict.fromkeys(players, 0),
        "longest_make_streak": dict.fromkeys(players, 0),
        "score_history": {p: [] for p in players},
        "bid_sequence": {p: [] for p in players},
        "round_scores": {p: [] for p in players},
        "cards_per_round": [],
        "trump_per_round": [],
        "off_by_one": dict.fromkeys(players, 0),
    }


def _update_bid_result(state: dict, name: str, bid: int, hand: int):
    """Update state for whether a bid was made or missed."""
    if bid == hand:
        state["bids_made"][name] += 1
        state["make_streak"][name] += 1
        state["miss_streak"][name] = 0
        if bid > state["best_bid_made"][name]:
            state["best_bid_made"][name] = bid
        if bid == 0:
            state["zero_bids_made"][name] += 1
    else:
        state["miss_streak"][name] += 1
        state["make_streak"][name] = 0
        if hand > bid:
            state["underbids"][name] += 1
        else:
            state["overbids"][name] += 1
        if abs(hand - bid) == 1:
            state["off_by_one"][name] += 1


def _process_context_bid(state: dict, name: str, bid: int, hand: int, score: int):
    """Process one bid result into the context state."""
    state["bids_total"][name] += 1
    state["bid_sequence"][name].append((bid, hand))
    state["round_scores"][name].append(score)
    state["totals"][name] += score
    state["score_history"][name].append(state["totals"][name])

    _update_bid_result(state, name, bid, hand)

    if bid == 0:
        state["zero_bids_attempted"][name] += 1
    state["longest_miss_streak"][name] = max(
        state["longest_miss_streak"][name], state["miss_streak"][name]
    )
    state["longest_make_streak"][name] = max(
        state["longest_make_streak"][name], state["make_streak"][name]
    )


def _finalize_context(players: list[str], state: dict) -> GameContext:
    """Build the final GameContext from accumulated state."""
    accuracy = {
        p: state["bids_made"][p] / state["bids_total"][p] if state["bids_total"][p] > 0 else 0.0
        for p in players
    }
    return GameContext(
        players=players,
        totals=state["totals"],
        round_count=len(state["cards_per_round"]),
        accuracy=accuracy,
        bids_made=state["bids_made"],
        bids_total=state["bids_total"],
        zero_bids_made=state["zero_bids_made"],
        zero_bids_attempted=state["zero_bids_attempted"],
        overbids=state["overbids"],
        underbids=state["underbids"],
        best_bid_made=state["best_bid_made"],
        longest_miss_streak=state["longest_miss_streak"],
        longest_make_streak=state["longest_make_streak"],
        score_history=state["score_history"],
        bid_sequence=state["bid_sequence"],
        round_scores=state["round_scores"],
        cards_per_round=state["cards_per_round"],
        trump_per_round=state["trump_per_round"],
        off_by_one=state["off_by_one"],
    )


# ── Selection ────────────────────────────────────────────────────────────────


def _phase1_coverage(players: list[str], sorted_cands: list[dict], used_keys: set) -> list[dict]:
    """Give every player at least one title (coverage pass)."""
    result = []
    for p in players:
        player_cands = [c for c in sorted_cands if c["player"] == p and c["key"] not in used_keys]
        if player_cands:
            best = player_cands[0]
            result.append(best)
            used_keys.add(best["key"])
    return result


def _phase2_fill(sorted_cands: list[dict], used_keys: set, result: list[dict], target: int) -> None:
    """Fill remaining slots up to target by score descending."""
    for c in sorted_cands:
        if len(result) >= target:
            break
        if c["key"] not in used_keys:
            result.append(c)
            used_keys.add(c["key"])


def select_titles(
    candidates: list[dict], players: list[str], target: int | None = None
) -> list[dict]:
    if target is None:
        target = max(4, min(2 * len(players), 14))

    def sort_key(c):
        idx = players.index(c["player"]) if c["player"] in players else 9999
        return (-c["score"], idx)

    sorted_cands = sorted(candidates, key=sort_key)
    used_keys: set = set()
    result = _phase1_coverage(players, sorted_cands, used_keys)
    _phase2_fill(sorted_cands, used_keys, result, target)
    return result


# ── Orchestrator ─────────────────────────────────────────────────────────────


def evaluate_titles(players: list[str], game_rounds) -> list[dict]:
    if not game_rounds:
        return []
    ctx = build_context(players, game_rounds)
    if ctx.round_count == 0:
        return []

    return _evaluate_from_context(ctx, players)


def build_context_from_metrics(gm) -> GameContext:
    """Build a GameContext from a GameMetrics object (shared pipeline)."""
    players = gm.players
    state = _init_context_state(players)

    for player in players:
        pm = gm.player_metrics.get(player)
        if pm is None:
            continue
        _fill_state_from_player_metrics(state, player, pm, gm)

    return _finalize_context(players, state)


def _fill_state_from_player_metrics(state, player, pm, gm):
    """Copy PlayerGameMetrics fields into context state dict."""
    state["bids_made"][player] = pm.bids_made
    state["bids_total"][player] = pm.bids_total
    state["zero_bids_made"][player] = pm.zero_bids_made
    state["zero_bids_attempted"][player] = pm.zero_bids_attempted
    state["overbids"][player] = pm.overbids
    state["underbids"][player] = pm.underbids
    state["best_bid_made"][player] = pm.best_bid_made
    state["longest_miss_streak"][player] = pm.longest_miss_streak
    state["longest_make_streak"][player] = pm.longest_make_streak
    state["off_by_one"][player] = pm.off_by_one
    state["total_rounds"] = gm.round_count
    state["totals"][player] = pm.total_score
    state["round_scores"][player] = list(pm.round_scores)
    state["bid_sequence"][player] = list(pm.bid_sequence)
    state["score_history"][player] = list(pm.score_cumulative)
    state["cards_per_round"] = list(gm.cards_per_round)
    state["trump_per_round"] = list(gm.trump_per_round)


def evaluate_titles_from_metrics(gm) -> list[dict]:
    """Evaluate titles from a GameMetrics object (shared pipeline path)."""
    if gm.round_count == 0:
        return []
    ctx = build_context_from_metrics(gm)
    return _evaluate_from_context(ctx, gm.players)


def _evaluate_from_context(ctx: GameContext, players: list[str]) -> list[dict]:
    """Collect candidates from declarative + complex titles and select."""
    candidates: list[dict] = []
    candidates.extend(evaluate_declarative(ctx))
    for fn in COMPLEX_PATTERNS:
        candidates.extend(fn(ctx))
    return select_titles(candidates, players)
