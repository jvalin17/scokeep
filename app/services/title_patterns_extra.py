"""Extra title pattern functions — bid style, card-range accuracy, streaks, mirrors.

Auto-registers into COMPLEX_PATTERNS from title_patterns.py on import.
Separated for module size: these patterns are independent of the rank-trajectory
patterns in the main file.
"""

from __future__ import annotations

from app.services.title_patterns import (
    COMPLEX_PATTERNS,
    _avg_bid_pattern,
    _halfway,
    _variance_pattern,
)
from app.services.title_registry import GameContext, _candidate


def _extra_pattern(fn):
    """Register a pattern function into the shared COMPLEX_PATTERNS list."""
    COMPLEX_PATTERNS.append(fn)
    return fn


@_extra_pattern
def _conservative(ctx: GameContext) -> list[dict]:
    return _avg_bid_pattern(
        ctx, "conservative", "🛡️", "Conservative", "Lowest average bid", highest=False
    )


@_extra_pattern
def _daredevil(ctx: GameContext) -> list[dict]:
    return _avg_bid_pattern(
        ctx, "daredevil", "🤸", "Daredevil", "Highest average bid", highest=True
    )


@_extra_pattern
def _rollercoaster(ctx: GameContext) -> list[dict]:
    return _variance_pattern(
        ctx, "rollercoaster", "🎢", "Rollercoaster", "Highest score variance", highest=True
    )


@_extra_pattern
def _metronome(ctx: GameContext) -> list[dict]:
    if ctx.round_count < 3:
        return []
    return _variance_pattern(
        ctx, "metronome", "⏱️", "Metronome", "Lowest score variance", highest=False
    )


@_extra_pattern
def _trump_master(ctx: GameContext) -> list[dict]:
    out = []
    for player in ctx.players:
        made = 0
        total = 0
        for (bid, hand), cards in zip(ctx.bid_sequence[player], ctx.cards_per_round, strict=False):
            if 6 <= cards <= 8:
                total += 1
                if bid == hand:
                    made += 1
        if total >= 2 and made > 0:
            pct = made / total
            out.append(
                _candidate(
                    "trump_master",
                    "♠️",
                    "Trump Master",
                    "Best accuracy on 6-8 card rounds",
                    player,
                    f"{made} of {total} bids correct on high-card rounds",
                    pct * 100,
                )
            )
    return out


@_extra_pattern
def _minimalist(ctx: GameContext) -> list[dict]:
    out = []
    for player in ctx.players:
        made = 0
        total = 0
        for (bid, hand), cards in zip(ctx.bid_sequence[player], ctx.cards_per_round, strict=False):
            if 1 <= cards <= 3:
                total += 1
                if bid == hand:
                    made += 1
        if total >= 2:
            pct = made / total
            out.append(
                _candidate(
                    "minimalist",
                    "✨",
                    "Minimalist",
                    "Best accuracy on 1-3 card rounds",
                    player,
                    f"{made} of {total} bids correct on low-card rounds",
                    pct * 100,
                )
            )
    return out


@_extra_pattern
def _mirror(ctx: GameContext) -> list[dict]:
    if len(ctx.players) < 2:
        return []
    out = []
    for i, player_a in enumerate(ctx.players):
        for j, player_b in enumerate(ctx.players):
            if j <= i:
                continue
            shared = sum(
                1
                for s1, s2 in zip(
                    ctx.round_scores[player_a],
                    ctx.round_scores[player_b],
                    strict=False,
                )
                if s1 == s2
            )
            if shared >= 3:
                out.append(
                    _candidate(
                        "mirror",
                        "🪞",
                        "Mirror",
                        f"Same score as {player_b} in 3+ rounds",
                        player_a,
                        f"{shared} matching rounds",
                        35,
                    )
                )
                out.append(
                    _candidate(
                        "mirror",
                        "🪞",
                        "Mirror",
                        f"Same score as {player_a} in 3+ rounds",
                        player_b,
                        f"{shared} matching rounds",
                        35,
                    )
                )
    return out


@_extra_pattern
def _lucky_seven(ctx: GameContext) -> list[dict]:
    out = []
    for player in ctx.players:
        count = sum(1 for score in ctx.round_scores[player] if score in (10, 11))
        if count >= 7:
            out.append(
                _candidate(
                    "lucky_seven",
                    "🍀",
                    "Lucky Seven",
                    "Scored +10 or +11 in 7+ rounds",
                    player,
                    f"{count} rounds",
                    45,
                )
            )
    return out


@_extra_pattern
def _last_laugh(ctx: GameContext) -> list[dict]:
    half = _halfway(ctx)
    if half < 1 or ctx.round_count < 2:
        return []
    out = []
    first_half = {p: sum(ctx.round_scores[p][:half]) for p in ctx.players}
    second_half = {p: sum(ctx.round_scores[p][half:]) for p in ctx.players}
    worst_first = min(ctx.players, key=lambda p: (first_half[p], ctx.players.index(p)))
    best_second = max(ctx.players, key=lambda p: (second_half[p], -ctx.players.index(p)))
    if worst_first == best_second:
        out.append(
            _candidate(
                "last_laugh",
                "😏",
                "Last Laugh",
                "Worst 1st half, best 2nd half",
                worst_first,
                f"{first_half[worst_first]}→{second_half[worst_first]}",
                50,
            )
        )
    return out


@_extra_pattern
def _survivor(ctx: GameContext) -> list[dict]:
    out = []
    for player in ctx.players:
        scores = ctx.round_scores[player]
        played_all = len(scores) == ctx.round_count
        if played_all and ctx.totals[player] > 0 and all(s < 20 for s in scores):
            out.append(
                _candidate(
                    "survivor",
                    "🛟",
                    "Survivor",
                    "Played all rounds, positive total, no huge score",
                    player,
                    f"{ctx.totals[player]} pts steady",
                    15,
                )
            )
    return out
