"""Post-game title system for Judgement/Kachuful score tracker."""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass

from app.services.analytics import _iter_round_bids

# ── Registry ────────────────────────────────────────────────────────────────

TITLE_REGISTRY: list = []


def title_pattern(fn):
    TITLE_REGISTRY.append(fn)
    return fn


# ── Context ──────────────────────────────────────────────────────────────────


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


# ── Helpers ───────────────────────────────────────────────────────────────────


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


def _rank_players(ctx: GameContext, key_fn, reverse=True) -> list[str]:
    return sorted(ctx.players, key=lambda p: (key_fn(p), -ctx.players.index(p)), reverse=reverse)


def _halfway(ctx: GameContext) -> int:
    return ctx.round_count // 2


def _rank_at(ctx: GameContext, idx: int) -> dict[str, int]:
    """Return rank (1=best) of each player at a given score_history index."""
    scores = {
        p: ctx.score_history[p][idx] if idx < len(ctx.score_history[p]) else 0 for p in ctx.players
    }
    sorted_players = sorted(ctx.players, key=lambda p: scores[p], reverse=True)
    return {p: sorted_players.index(p) + 1 for p in ctx.players}


# ── select_titles ─────────────────────────────────────────────────────────────


def select_titles(
    candidates: list[dict], players: list[str], target: int | None = None
) -> list[dict]:
    if target is None:
        target = max(10, len(players) + 2)

    used_keys: set = set()
    covered: set = set()
    result: list[dict] = []

    # Sort candidates: score desc, then player index asc for tiebreak
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


# ── evaluate_titles ───────────────────────────────────────────────────────────


def evaluate_titles(players: list[str], game_rounds) -> list[dict]:
    if not game_rounds:
        return []
    ctx = build_context(players, game_rounds)
    if ctx.round_count == 0:
        return []

    candidates: list[dict] = []
    for fn in TITLE_REGISTRY:
        candidates.extend(fn(ctx))

    return select_titles(candidates, players)


# ── Pattern functions ─────────────────────────────────────────────────────────


@title_pattern
def _champion(ctx: GameContext) -> list[dict]:
    best = max(ctx.players, key=lambda p: (ctx.totals[p], -ctx.players.index(p)))
    return [
        _candidate(
            "champion",
            "🏆",
            "Champion",
            "Highest total score",
            best,
            f"{ctx.totals[best]} pts",
            100,
        )
    ]


@title_pattern
def _sharpshooter(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        acc = ctx.accuracy[p]
        if acc > 0:
            out.append(
                _candidate(
                    "sharpshooter",
                    "🎯",
                    "Sharpshooter",
                    "Best bid accuracy",
                    p,
                    f"{acc * 100:.0f}%",
                    acc * 100,
                )
            )
    return out


@title_pattern
def _brick_wall(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        n = ctx.zero_bids_made[p]
        if n > 0:
            out.append(
                _candidate(
                    "brick_wall",
                    "🧱",
                    "Brick Wall",
                    "Most zero bids made",
                    p,
                    f"{n} zero bids made",
                    n * 15,
                )
            )
    return out


@title_pattern
def _bold_move(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        bid = ctx.best_bid_made[p]
        if bid > 0:
            out.append(
                _candidate(
                    "bold_move", "🎲", "Bold Move", "Highest bid made", p, f"bid {bid}", bid * 20
                )
            )
    return out


@title_pattern
def _sandbagger(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        n = ctx.underbids[p]
        if n > 0:
            out.append(
                _candidate(
                    "sandbagger", "🏖️", "Sandbagger", "Most underbids", p, f"{n} underbids", n * 10
                )
            )
    return out


@title_pattern
def _gambler(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        n = ctx.overbids[p]
        if n > 0:
            out.append(
                _candidate("gambler", "🎰", "Gambler", "Most overbids", p, f"{n} overbids", n * 10)
            )
    return out


@title_pattern
def _cursed(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        s = ctx.longest_miss_streak[p]
        if s > 0:
            out.append(
                _candidate(
                    "cursed", "😵", "Cursed", "Longest miss streak", p, f"{s} in a row", s * 12
                )
            )
    return out


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
def _cellar_dweller(ctx: GameContext) -> list[dict]:
    worst = min(ctx.players, key=lambda p: (ctx.totals[p], ctx.players.index(p)))
    return [
        _candidate(
            "cellar_dweller",
            "🪣",
            "Cellar Dweller",
            "Lowest total score",
            worst,
            f"{ctx.totals[worst]} pts",
            20,
        )
    ]


@title_pattern
def _big_spender(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        scores = ctx.round_scores[p]
        if not scores:
            continue
        best = max(scores)
        if best > 0:
            out.append(
                _candidate(
                    "big_spender",
                    "💰",
                    "Big Spender",
                    "Highest single-round score",
                    p,
                    f"+{best} in one round",
                    float(best),
                )
            )
    return out


@title_pattern
def _rock_bottom(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        scores = ctx.round_scores[p]
        if not scores:
            continue
        worst = min(scores)
        if worst < 0:
            out.append(
                _candidate(
                    "rock_bottom",
                    "🕳️",
                    "Rock Bottom",
                    "Most negative single round",
                    p,
                    f"{worst} in one round",
                    abs(worst) / 2,
                )
            )
    return out


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
        candidates.append(_candidate(key, emoji, title, desc, p, f"variance {var:.1f}", score))
    return candidates


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
def _crowd_pleaser(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        count = sum(1 for s in ctx.round_scores[p] if s >= 10)
        if count > 0:
            out.append(
                _candidate(
                    "crowd_pleaser",
                    "🎭",
                    "Crowd Pleaser",
                    "Most rounds scoring ≥+10",
                    p,
                    f"{count} rounds ≥+10",
                    count * 8,
                )
            )
    return out


@title_pattern
def _heartbreaker(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        count = ctx.off_by_one[p]
        if count > 0:
            out.append(
                _candidate(
                    "heartbreaker",
                    "💔",
                    "Heartbreaker",
                    "Most rounds off by 1",
                    p,
                    f"off by 1: {count}×",
                    count * 10,
                )
            )
    return out


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
                    f"{made}/{total} on big rounds",
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
                    f"{made}/{total} on small rounds",
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
def _humble_pie(ctx: GameContext) -> list[dict]:
    out = []
    for p in ctx.players:
        count = ctx.zero_bids_attempted[p]
        if count > 0:
            out.append(
                _candidate(
                    "humble_pie",
                    "🥧",
                    "Humble Pie",
                    "Bid 0 the most times",
                    p,
                    f"bid 0: {count}×",
                    count * 8,
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
