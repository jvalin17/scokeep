"""Declarative title definitions — simple titles as config, not code.

Each declarative title defines:
  - key, emoji, title, desc: identity
  - metric: which GameContext field to read
  - mode: "highest" (single winner), "lowest" (single winner),
          "per_player" (all qualifying players get candidates)
  - score_fn: how to compute the candidate score from the metric value
  - detail_fn: how to format the detail string
  - threshold: minimum value to qualify (default 0 for per_player)

Complex titles that need multi-step logic live in title_patterns.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameContext:
    players: list[str]
    totals: dict[str, int]
    round_count: int
    accuracy: dict[str, float]
    bids_made: dict[str, int]
    bids_total: dict[str, int]
    zero_bids_made: dict[str, int]
    zero_bids_attempted: dict[str, int]
    overbids: dict[str, int]
    underbids: dict[str, int]
    best_bid_made: dict[str, int]
    longest_miss_streak: dict[str, int]
    longest_make_streak: dict[str, int]
    score_history: dict[str, list[int]]
    bid_sequence: dict[str, list[tuple[int, int]]]
    round_scores: dict[str, list[int]]
    cards_per_round: list[int]
    trump_per_round: list[str]
    off_by_one: dict[str, int]


def _candidate(key, emoji, title, desc, player, detail, score) -> dict:
    return {
        "key": key,
        "emoji": emoji,
        "title": title,
        "desc": desc,
        "player": player,
        "detail": detail,
        "score": float(score),
    }


# ── Metric extractors ────────────────────────────────────────────────────────
# Each returns (value, detail_str) for a player, or None if not applicable.


def _total_score(ctx, p):
    return ctx.totals[p], f"{ctx.totals[p]} pts"


def _accuracy(ctx, p):
    v = ctx.accuracy[p]
    return (v * 100, f"{v * 100:.0f}%") if v > 0 else None


def _zero_bids_made(ctx, p):
    n = ctx.zero_bids_made[p]
    return (n, f"{n} zero bids made") if n > 0 else None


def _best_bid_made(ctx, p):
    bid = ctx.best_bid_made[p]
    return (bid, f"bid {bid}") if bid > 0 else None


def _underbids(ctx, p):
    n = ctx.underbids[p]
    return (n, f"{n} underbids") if n > 0 else None


def _overbids(ctx, p):
    n = ctx.overbids[p]
    return (n, f"{n} overbids") if n > 0 else None


def _longest_miss_streak(ctx, p):
    s = ctx.longest_miss_streak[p]
    return (s, f"{s} in a row") if s > 0 else None


def _max_round_score(ctx, p):
    scores = ctx.round_scores[p]
    if not scores:
        return None
    best = max(scores)
    return (best, f"+{best} in one round") if best > 0 else None


def _min_round_score(ctx, p):
    scores = ctx.round_scores[p]
    if not scores:
        return None
    worst = min(scores)
    return (abs(worst), f"{worst} in one round") if worst < 0 else None


def _positive_round_count(ctx, p):
    count = sum(1 for s in ctx.round_scores[p] if s >= 10)
    return (count, f"scored positive in {count} rounds") if count > 0 else None


def _off_by_one(ctx, p):
    count = ctx.off_by_one[p]
    return (count, f"off by 1: {count}×") if count > 0 else None


def _zero_bids_attempted(ctx, p):
    count = ctx.zero_bids_attempted[p]
    return (count, f"bid 0: {count}×") if count > 0 else None


# ── Declarative title definitions ─────────────────────────────────────────────

DECLARATIVE_TITLES = [
    {
        "key": "champion",
        "emoji": "🏆",
        "title": "Champion",
        "desc": "Highest total score",
        "metric": _total_score,
        "mode": "highest",
        "score_weight": 100,
    },
    {
        "key": "cellar_dweller",
        "emoji": "🪣",
        "title": "Cellar Dweller",
        "desc": "Lowest total score",
        "metric": _total_score,
        "mode": "lowest",
        "score_weight": 20,
    },
    {
        "key": "sharpshooter",
        "emoji": "🎯",
        "title": "Sharpshooter",
        "desc": "Best bid accuracy",
        "metric": _accuracy,
        "mode": "per_player",
        "score_weight": 1,
    },
    {
        "key": "brick_wall",
        "emoji": "🧱",
        "title": "Brick Wall",
        "desc": "Most zero bids made",
        "metric": _zero_bids_made,
        "mode": "per_player",
        "score_weight": 15,
    },
    {
        "key": "bold_move",
        "emoji": "🎲",
        "title": "Bold Move",
        "desc": "Highest bid made",
        "metric": _best_bid_made,
        "mode": "per_player",
        "score_weight": 20,
    },
    {
        "key": "sandbagger",
        "emoji": "🏖️",
        "title": "Sandbagger",
        "desc": "Most underbids",
        "metric": _underbids,
        "mode": "per_player",
        "score_weight": 10,
    },
    {
        "key": "gambler",
        "emoji": "🎰",
        "title": "Gambler",
        "desc": "Most overbids",
        "metric": _overbids,
        "mode": "per_player",
        "score_weight": 10,
    },
    {
        "key": "cursed",
        "emoji": "😵",
        "title": "Cursed",
        "desc": "Longest miss streak",
        "metric": _longest_miss_streak,
        "mode": "per_player",
        "score_weight": 12,
    },
    {
        "key": "big_spender",
        "emoji": "💰",
        "title": "Big Spender",
        "desc": "Highest single-round score",
        "metric": _max_round_score,
        "mode": "per_player",
        "score_weight": 1,
    },
    {
        "key": "rock_bottom",
        "emoji": "🕳️",
        "title": "Rock Bottom",
        "desc": "Most negative single round",
        "metric": _min_round_score,
        "mode": "per_player",
        "score_weight": 0.5,
    },
    {
        "key": "crowd_pleaser",
        "emoji": "🎭",
        "title": "Crowd Pleaser",
        "desc": "Most rounds scoring ≥+10",
        "metric": _positive_round_count,
        "mode": "per_player",
        "score_weight": 8,
    },
    {
        "key": "heartbreaker",
        "emoji": "💔",
        "title": "Heartbreaker",
        "desc": "Most rounds off by 1",
        "metric": _off_by_one,
        "mode": "per_player",
        "score_weight": 10,
    },
    {
        "key": "humble_pie",
        "emoji": "🥧",
        "title": "Humble Pie",
        "desc": "Bid 0 the most times",
        "metric": _zero_bids_attempted,
        "mode": "per_player",
        "score_weight": 8,
    },
]


def evaluate_declarative(ctx) -> list[dict]:
    """Evaluate all declarative titles against a GameContext, return candidates."""
    candidates = []
    for defn in DECLARATIVE_TITLES:
        candidates.extend(_evaluate_one(defn, ctx))
    return candidates


def _evaluate_one(defn: dict, ctx) -> list[dict]:
    """Evaluate a single declarative title definition."""
    mode = defn["mode"]
    metric_fn = defn["metric"]
    weight = defn["score_weight"]

    if mode == "highest":
        return _eval_single_winner(defn, ctx, metric_fn, weight, reverse=True)
    elif mode == "lowest":
        return _eval_single_winner(defn, ctx, metric_fn, weight, reverse=False)
    else:  # per_player
        return _eval_per_player(defn, ctx, metric_fn, weight)


def _eval_single_winner(defn, ctx, metric_fn, weight, reverse):
    """Pick the single player with highest/lowest metric value."""
    best_player = None
    best_val = None
    best_detail = ""

    for p in ctx.players:
        result = metric_fn(ctx, p)
        if result is None:
            continue
        val, detail = result
        if best_val is None or (reverse and val > best_val) or (not reverse and val < best_val):
            best_val = val
            best_player = p
            best_detail = detail
        elif val == best_val:
            # Tiebreak: first player in roster order wins
            if ctx.players.index(p) < ctx.players.index(best_player):
                best_player = p
                best_detail = detail

    if best_player is None:
        return []
    return [
        _candidate(
            defn["key"],
            defn["emoji"],
            defn["title"],
            defn["desc"],
            best_player,
            best_detail,
            weight,
        )
    ]


def _eval_per_player(defn, ctx, metric_fn, weight):
    """Each qualifying player gets a candidate."""
    out = []
    for p in ctx.players:
        result = metric_fn(ctx, p)
        if result is None:
            continue
        val, detail = result
        score = val * weight
        if score > 0:
            out.append(
                _candidate(
                    defn["key"], defn["emoji"], defn["title"], defn["desc"], p, detail, score
                )
            )
    return out
