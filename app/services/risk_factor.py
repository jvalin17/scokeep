"""Position × cards × bid risk for Last Game awards.

claim_risk at bid time; paid_risk only on exact make.
Safe bets (bid 0 / tiny ambition) get near-zero credit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.title_registry import GameContext

RISKY_MAKE_THRESHOLD = 0.35
CLUTCH_MIN_CARDS = 5
PRESSURE_COOKER_MIN_PRESSURE = 0.5
SAFE_AMBITION = 0.25


def claim_risk(*, bid: int, cards: int, rank: int, num_players: int) -> float:
    """Risk of the bid claim before outcome.

    rank: 1 = current leader … N = last (before this round).
    """
    if cards <= 0 or bid <= 0:
        return 0.0
    ambition = bid / cards
    denom = max(num_players - 1, 1)
    pressure = (rank - 1) / denom
    return ambition * (0.35 + 0.65 * pressure)


def paid_risk(*, bid: int, hands: int, cards: int, rank: int, num_players: int) -> float:
    """Risk credit only when the bid is made exactly."""
    if bid != hands:
        return 0.0
    return claim_risk(bid=bid, cards=cards, rank=rank, num_players=num_players)


def _ranks_before_round(ctx: GameContext, round_index: int) -> dict[str, int]:
    """Rank (1=best) entering round_index (0-based). Round 0: roster order as tie-break."""
    if round_index <= 0:
        # Everyone tied at 0 — stable roster order → Alice rank 1, etc.
        return {player: index + 1 for index, player in enumerate(ctx.players)}
    prev = round_index - 1
    scores = {
        player: (ctx.score_history[player][prev] if prev < len(ctx.score_history[player]) else 0)
        for player in ctx.players
    }
    # Higher score = better rank; roster order breaks ties
    ordered = sorted(
        ctx.players,
        key=lambda player: (-scores[player], ctx.players.index(player)),
    )
    return {player: ordered.index(player) + 1 for player in ctx.players}


def compute_game_risk(ctx: GameContext) -> dict[str, dict]:
    """Per-player aggregates and per-round paid risk lists.

    Returns:
      {
        player: {
          total_paid_risk, max_paid_risk, risky_makes,
          pressure_risky_makes,  # paid_risk >= threshold AND pressure >= 0.5
          rounds: [{round_index, claim_risk, paid_risk, pressure, ambition, cards, bid}],
        }
      }
    """
    num_players = len(ctx.players)
    result: dict[str, dict] = {}
    for player in ctx.players:
        result[player] = {
            "total_paid_risk": 0.0,
            "max_paid_risk": 0.0,
            "risky_makes": 0,
            "pressure_risky_makes": 0,
            "rounds": [],
        }

    for round_index, cards in enumerate(ctx.cards_per_round):
        ranks = _ranks_before_round(ctx, round_index)
        for player in ctx.players:
            if round_index >= len(ctx.bid_sequence[player]):
                continue
            bid, hands = ctx.bid_sequence[player][round_index]
            rank = ranks[player]
            ambition = (bid / cards) if cards > 0 else 0.0
            denom = max(num_players - 1, 1)
            pressure = (rank - 1) / denom
            claimed = claim_risk(bid=bid, cards=cards, rank=rank, num_players=num_players)
            paid = paid_risk(bid=bid, hands=hands, cards=cards, rank=rank, num_players=num_players)
            entry = result[player]
            entry["rounds"].append(
                {
                    "round_index": round_index,
                    "claim_risk": claimed,
                    "paid_risk": paid,
                    "pressure": pressure,
                    "ambition": ambition,
                    "cards": cards,
                    "bid": bid,
                }
            )
            entry["total_paid_risk"] += paid
            if paid > entry["max_paid_risk"]:
                entry["max_paid_risk"] = paid
            if paid >= RISKY_MAKE_THRESHOLD:
                entry["risky_makes"] += 1
                if pressure >= PRESSURE_COOKER_MIN_PRESSURE:
                    entry["pressure_risky_makes"] += 1

    return result
