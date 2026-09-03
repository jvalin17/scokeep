"""Complex title pattern functions for the post-game title system."""

from __future__ import annotations

import statistics
from collections import Counter

from app.services.title_registry import GameContext, _candidate

# ── Registry ────────────────────────────────────────────────────────────────

COMPLEX_PATTERNS: list = []


def title_pattern(fn):
    COMPLEX_PATTERNS.append(fn)
    return fn


# ── Helpers ───────────────────────────────────────────────────────────────────


def _halfway(ctx: GameContext) -> int:
    return ctx.round_count // 2


def _rank_at(ctx: GameContext, idx: int) -> dict[str, int]:
    """Return rank (1=best) of each player at a given score_history index."""
    scores = {
        p: ctx.score_history[p][idx] if idx < len(ctx.score_history[p]) else 0 for p in ctx.players
    }
    sorted_players = sorted(ctx.players, key=lambda p: scores[p], reverse=True)
    return {p: sorted_players.index(p) + 1 for p in ctx.players}


def _avg_bid_pattern(ctx: GameContext, key, emoji, title, desc, highest=True) -> list[dict]:
    """Return one candidate per player for avg bid; winner is highest or lowest."""
    candidates = []
    for p in ctx.players:
        bids = [b for b, _ in ctx.bid_sequence[p]]
        if not bids:
            continue
        avg = sum(bids) / len(bids)
        # Score must be > 0 per contract; negate avg for lowest-wins ranking
        score = avg if highest else max(0.01, 1.0 / (avg + 0.01))
        candidates.append(_candidate(key, emoji, title, desc, p, f"avg bid {avg:.1f}", score))
    return candidates


def _variance_pattern(ctx: GameContext, key, emoji, title, desc, highest=True) -> list[dict]:
    """Return one candidate per player for score variance; winner is highest or lowest."""
    candidates = []
    for p in ctx.players:
        scores = ctx.round_scores[p]
        if len(scores) < 2:
            continue
        var = statistics.variance(scores)
        if highest and var <= 0:
            continue
        # Score must be > 0 per contract; negate variance for lowest-wins ranking
        score = var if highest else max(0.01, 1.0 / (var + 0.01))
        detail = f"scores swung widely ({var:.0f} variance)"
        candidates.append(_candidate(key, emoji, title, desc, p, detail, score))
    return candidates


# ── Pattern functions ─────────────────────────────────────────────────────────


@title_pattern
def _underdog(ctx: GameContext) -> list[dict]:
    half = _halfway(ctx)
    if half < 1 or ctx.round_count < 2:
        return []
    mid_ranks = _rank_at(ctx, half - 1)
    end_ranks = _rank_at(ctx, ctx.round_count - 1)
    n = len(ctx.players)
    half_n = n / 2
    out = []
    for p in ctx.players:
        mid_r = mid_ranks[p]
        end_r = end_ranks[p]
        if mid_r > half_n and end_r <= half_n:
            climbed = mid_r - end_r
            if climbed > 0:
                out.append(
                    _candidate(
                        "underdog",
                        "🐕",
                        "Underdog",
                        "Climbed from bottom half to top half",
                        p,
                        f"+{climbed} positions",
                        climbed * 15,
                    )
                )
    return out


@title_pattern
def _landslide(ctx: GameContext) -> list[dict]:
    if len(ctx.players) < 2:
        return []
    sorted_totals = sorted(ctx.totals.values(), reverse=True)
    margin = sorted_totals[0] - sorted_totals[1]
    if margin < 20:
        return []
    winner = max(ctx.players, key=lambda p: (ctx.totals[p], -ctx.players.index(p)))
    return [
        _candidate(
            "landslide", "🏔️", "Landslide", "Won by ≥20 pts", winner, f"+{margin} margin", margin / 2
        )
    ]


@title_pattern
def _photo_finish(ctx: GameContext) -> list[dict]:
    if len(ctx.players) < 2:
        return []
    sorted_players = sorted(ctx.players, key=lambda p: ctx.totals[p], reverse=True)
    if abs(ctx.totals[sorted_players[0]] - ctx.totals[sorted_players[1]]) > 5:
        return []
    return [
        _candidate(
            "photo_finish",
            "📸",
            "Photo Finish",
            "Top 2 within 5 pts",
            sorted_players[0],
            f"{ctx.totals[sorted_players[0]]} pts",
            30,
        ),
        _candidate(
            "photo_finish",
            "📸",
            "Photo Finish",
            "Top 2 within 5 pts",
            sorted_players[1],
            f"{ctx.totals[sorted_players[1]]} pts",
            30,
        ),
    ]


@title_pattern
def _perfect_game(ctx: GameContext) -> list[dict]:
    if ctx.round_count < 4:
        return []
    out = []
    for p in ctx.players:
        if ctx.bids_total[p] >= 4 and ctx.bids_made[p] == ctx.bids_total[p]:
            out.append(
                _candidate(
                    "perfect_game",
                    "⭐",
                    "Perfect Game",
                    "100% accuracy, min 4 rounds",
                    p,
                    f"{ctx.bids_made[p]}/{ctx.bids_total[p]}",
                    95,
                )
            )
    return out


@title_pattern
def _nearly_perfect(ctx: GameContext) -> list[dict]:
    if ctx.round_count < 4:
        return []
    out = []
    for p in ctx.players:
        total = ctx.bids_total[p]
        missed = total - ctx.bids_made[p]
        if total >= 4 and missed == 1:
            out.append(
                _candidate(
                    "nearly_perfect",
                    "🌟",
                    "Nearly Perfect",
                    "Missed exactly 1 bid",
                    p,
                    f"{ctx.bids_made[p]}/{total}",
                    80,
                )
            )
    return out


@title_pattern
def _zero_hero(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        if ctx.zero_bids_attempted[p] >= 3 and ctx.zero_bids_made[p] == ctx.zero_bids_attempted[p]:
            out.append(
                _candidate(
                    "zero_hero",
                    "👻",
                    "Zero Hero",
                    "Bid 0 three+ times and made all",
                    p,
                    f"{ctx.zero_bids_made[p]} zeros made",
                    60,
                )
            )
    return out


@title_pattern
def _high_roller(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        bid = ctx.best_bid_made[p]
        if bid >= 4:
            out.append(
                _candidate(
                    "high_roller",
                    "🎰",
                    "High Roller",
                    "Made a bid of 4+",
                    p,
                    f"bid {bid} made",
                    bid * 18,
                )
            )
    return out


@title_pattern
def _all_in(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        for (bid, hand), cards in zip(ctx.bid_sequence[p], ctx.cards_per_round, strict=False):
            if bid == cards and bid == hand:
                out.append(
                    _candidate(
                        "all_in",
                        "🃏",
                        "All In",
                        "Bid = cards dealt and made it",
                        p,
                        f"bid {bid} on {cards} cards",
                        55,
                    )
                )
                break
    return out


@title_pattern
def _fortune_teller(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        best = 0
        cur = 0
        for bid, hand in ctx.bid_sequence[p]:
            if bid == hand:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        if best >= 3:
            out.append(
                _candidate(
                    "fortune_teller",
                    "🔮",
                    "Fortune Teller",
                    "3+ consecutive correct bids",
                    p,
                    f"{best} in a row",
                    best * 18,
                )
            )
    return out


@title_pattern
def _scatterbrain(ctx: GameContext) -> list[dict]:
    if ctx.round_count < 4:
        return []
    out = []
    for p in ctx.players:
        seq = [b for b, _ in ctx.bid_sequence[p]]
        if len(seq) < 4:
            continue
        if all(seq[i] != seq[i + 1] for i in range(len(seq) - 1)):
            out.append(
                _candidate(
                    "scatterbrain",
                    "🤪",
                    "Scatterbrain",
                    "Never bid same twice in a row",
                    p,
                    f"{len(seq)} rounds",
                    25,
                )
            )
    return out


@title_pattern
def _one_trick(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        bids = [b for b, _ in ctx.bid_sequence[p]]
        if not bids:
            continue
        most_common_bid, count = Counter(bids).most_common(1)[0]
        if count >= 4:
            out.append(
                _candidate(
                    "one_trick",
                    "🐴",
                    "One Trick",
                    "Same bid 4+ times",
                    p,
                    f"bid {most_common_bid} × {count}",
                    30,
                )
            )
    return out


@title_pattern
def _hot_streak(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        best = 0
        cur = 0
        for s in ctx.round_scores[p]:
            if s > 0:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        if best >= 4:
            out.append(
                _candidate(
                    "hot_streak",
                    "🔥",
                    "Hot Streak",
                    "4+ consecutive positive rounds",
                    p,
                    f"{best} in a row",
                    best * 12,
                )
            )
    return out


@title_pattern
def _ice_cold(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        best = 0
        cur = 0
        for s in ctx.round_scores[p]:
            if s < 0:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        if best >= 3:
            out.append(
                _candidate(
                    "ice_cold",
                    "🥶",
                    "Ice Cold",
                    "3+ consecutive negative rounds",
                    p,
                    f"{best} in a row",
                    best * 10,
                )
            )
    return out


@title_pattern
def _comeback_king(ctx: GameContext) -> list[dict]:
    half = _halfway(ctx)
    if half < 1 or ctx.round_count < 2:
        return []
    mid_ranks = _rank_at(ctx, half - 1)
    end_ranks = _rank_at(ctx, ctx.round_count - 1)
    n = len(ctx.players)
    out = []
    for p in ctx.players:
        if mid_ranks[p] == n and end_ranks[p] <= 2:
            out.append(
                _candidate(
                    "comeback_king",
                    "👑",
                    "Comeback King",
                    "Last place at halfway, top 2 at end",
                    p,
                    f"rank {n}→{end_ranks[p]}",
                    70,
                )
            )
    return out


@title_pattern
def _slow_starter(ctx: GameContext) -> list[dict]:
    half = _halfway(ctx)
    if half < 1 or ctx.round_count < 2:
        return []
    out = []
    for p in ctx.players:
        mid_total = ctx.score_history[p][half - 1] if half - 1 < len(ctx.score_history[p]) else 0
        end_total = ctx.totals[p]
        if mid_total < 0 and end_total > 0:
            out.append(
                _candidate(
                    "slow_starter",
                    "🐢",
                    "Slow Starter",
                    "Negative at halfway, positive at end",
                    p,
                    f"{mid_total}→{end_total}",
                    40,
                )
            )
    return out


@title_pattern
def _fast_fade(ctx: GameContext) -> list[dict]:
    half = _halfway(ctx)
    if half < 1 or ctx.round_count < 2:
        return []
    mid_ranks = _rank_at(ctx, half - 1)
    end_ranks = _rank_at(ctx, ctx.round_count - 1)
    n = len(ctx.players)
    half_n = n / 2
    out = []
    for p in ctx.players:
        if mid_ranks[p] == 1 and end_ranks[p] > half_n:
            out.append(
                _candidate(
                    "fast_fade",
                    "💨",
                    "Fast Fade",
                    "Led at halfway, bottom half at end",
                    p,
                    f"rank 1→{end_ranks[p]}",
                    25,
                )
            )
    return out


@title_pattern
def _closer(ctx: GameContext) -> list[dict]:
    third = max(1, ctx.round_count // 3)
    out = []
    for p in ctx.players:
        final_scores = ctx.round_scores[p][-third:]
        if not final_scores:
            continue
        avg = sum(final_scores) / len(final_scores)
        if avg > 0:
            out.append(
                _candidate(
                    "closer",
                    "🔒",
                    "Closer",
                    "Best avg score in final third",
                    p,
                    f"avg {avg:.1f} last {third} rounds",
                    avg * 2,
                )
            )
    return out


@title_pattern
def _conservative(ctx: GameContext) -> list[dict]:
    return _avg_bid_pattern(
        ctx, "conservative", "🛡️", "Conservative", "Lowest average bid", highest=False
    )


@title_pattern
def _daredevil(ctx: GameContext) -> list[dict]:
    return _avg_bid_pattern(
        ctx, "daredevil", "🤸", "Daredevil", "Highest average bid", highest=True
    )


@title_pattern
def _rollercoaster(ctx: GameContext) -> list[dict]:
    return _variance_pattern(
        ctx, "rollercoaster", "🎢", "Rollercoaster", "Highest score variance", highest=True
    )


@title_pattern
def _metronome(ctx: GameContext) -> list[dict]:
    if ctx.round_count < 3:
        return []
    return _variance_pattern(
        ctx, "metronome", "⏱️", "Metronome", "Lowest score variance", highest=False
    )


@title_pattern
def _trump_master(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        made = 0
        total = 0
        for (bid, hand), cards in zip(ctx.bid_sequence[p], ctx.cards_per_round, strict=False):
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
                    p,
                    f"{made} of {total} bids correct on high-card rounds",
                    pct * 100,
                )
            )
    return out


@title_pattern
def _minimalist(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        made = 0
        total = 0
        for (bid, hand), cards in zip(ctx.bid_sequence[p], ctx.cards_per_round, strict=False):
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
                    p,
                    f"{made} of {total} bids correct on low-card rounds",
                    pct * 100,
                )
            )
    return out


@title_pattern
def _mirror(ctx: GameContext) -> list[dict]:
    if len(ctx.players) < 2:
        return []
    out = []
    for i, p in enumerate(ctx.players):
        for j, q in enumerate(ctx.players):
            if j <= i:
                continue
            shared = sum(
                1
                for s1, s2 in zip(ctx.round_scores[p], ctx.round_scores[q], strict=False)
                if s1 == s2
            )
            if shared >= 3:
                out.append(
                    _candidate(
                        "mirror",
                        "🪞",
                        "Mirror",
                        f"Same score as {q} in 3+ rounds",
                        p,
                        f"{shared} matching rounds",
                        35,
                    )
                )
                out.append(
                    _candidate(
                        "mirror",
                        "🪞",
                        "Mirror",
                        f"Same score as {p} in 3+ rounds",
                        q,
                        f"{shared} matching rounds",
                        35,
                    )
                )
    return out


@title_pattern
def _lucky_seven(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        count = sum(1 for s in ctx.round_scores[p] if s in (10, 11))
        if count >= 7:
            out.append(
                _candidate(
                    "lucky_seven",
                    "🍀",
                    "Lucky Seven",
                    "Scored +10 or +11 in 7+ rounds",
                    p,
                    f"{count} rounds",
                    45,
                )
            )
    return out


@title_pattern
def _last_laugh(ctx: GameContext) -> list[dict]:
    half = _halfway(ctx)
    if half < 1 or ctx.round_count < 2:
        return []
    out = []
    first_half_scores = {p: sum(ctx.round_scores[p][:half]) for p in ctx.players}
    second_half_scores = {p: sum(ctx.round_scores[p][half:]) for p in ctx.players}
    worst_first = min(ctx.players, key=lambda p: (first_half_scores[p], ctx.players.index(p)))
    best_second = max(ctx.players, key=lambda p: (second_half_scores[p], -ctx.players.index(p)))
    if worst_first == best_second:
        out.append(
            _candidate(
                "last_laugh",
                "😏",
                "Last Laugh",
                "Worst 1st half, best 2nd half",
                worst_first,
                f"{first_half_scores[worst_first]}→{second_half_scores[worst_first]}",
                50,
            )
        )
    return out


@title_pattern
def _survivor(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        scores = ctx.round_scores[p]
        if len(scores) == ctx.round_count and ctx.totals[p] > 0 and all(s < 20 for s in scores):
            out.append(
                _candidate(
                    "survivor",
                    "🛟",
                    "Survivor",
                    "Played all rounds, positive total, no huge score",
                    p,
                    f"{ctx.totals[p]} pts steady",
                    15,
                )
            )
    return out
