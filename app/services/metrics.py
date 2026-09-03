"""Shared metric computation layer for game analytics."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.round_utils import _iter_round_bids


@dataclass
class PlayerGameMetrics:
    player: str
    total_score: int = 0
    rounds_played: int = 0
    bids_made: int = 0
    bids_total: int = 0
    overbids: int = 0
    underbids: int = 0
    off_by_one: int = 0
    zero_bids_attempted: int = 0
    zero_bids_made: int = 0
    longest_make_streak: int = 0
    longest_miss_streak: int = 0
    best_bid_made: int = 0
    round_scores: list = field(default_factory=list)
    score_cumulative: list = field(default_factory=list)
    bid_sequence: list = field(default_factory=list)


@dataclass
class GameMetrics:
    players: list[str]
    round_count: int
    player_metrics: dict[str, PlayerGameMetrics]
    totals: dict[str, int]
    winner: str | None
    cards_per_round: list[int]
    trump_per_round: list[str]


def compute_game_metrics(players: list[str], game_rounds: list) -> GameMetrics:
    """Compute unified per-player stats from a list of game rounds."""
    if not game_rounds:
        return GameMetrics(
            players=players,
            round_count=0,
            player_metrics={},
            totals={},
            winner=None,
            cards_per_round=[],
            trump_per_round=[],
        )

    # Initialize per-player state
    pm = {p: PlayerGameMetrics(player=p) for p in players}
    current_make_streak = dict.fromkeys(players, 0)
    current_miss_streak = dict.fromkeys(players, 0)

    # Track round-level data (ordered, deduped by rnd object identity)
    seen_rounds = []
    seen_round_ids = set()

    for name, bid, hand, score, rnd in _iter_round_bids(players, game_rounds):
        m = pm[name]

        # Per-round stats
        m.rounds_played += 1
        m.bids_total += 1
        m.total_score += score
        m.round_scores.append(score)
        m.score_cumulative.append((m.score_cumulative[-1] if m.score_cumulative else 0) + score)
        m.bid_sequence.append((bid, hand))

        made = bid == hand

        if made:
            m.bids_made += 1
            current_make_streak[name] += 1
            current_miss_streak[name] = 0
            m.longest_make_streak = max(m.longest_make_streak, current_make_streak[name])
            if bid > m.best_bid_made:
                m.best_bid_made = bid
        else:
            current_make_streak[name] = 0
            current_miss_streak[name] += 1
            m.longest_miss_streak = max(m.longest_miss_streak, current_miss_streak[name])
            diff = hand - bid
            if diff > 0:
                m.underbids += 1
            else:
                m.overbids += 1
            if abs(diff) == 1:
                m.off_by_one += 1

        if bid == 0:
            m.zero_bids_attempted += 1
            if made:
                m.zero_bids_made += 1

        # Track round order
        rnd_id = id(rnd)
        if rnd_id not in seen_round_ids:
            seen_round_ids.add(rnd_id)
            seen_rounds.append(rnd)

    totals = {p: pm[p].total_score for p in players}

    # Determine winner (None if tied)
    winner = None
    if totals:
        max_score = max(totals.values())
        top = [p for p, s in totals.items() if s == max_score]
        if len(top) == 1:
            winner = top[0]

    return GameMetrics(
        players=players,
        round_count=len(seen_rounds),
        player_metrics=pm,
        totals=totals,
        winner=winner,
        cards_per_round=[r.cards_dealt for r in seen_rounds],
        trump_per_round=[r.trump_suit for r in seen_rounds],
    )
