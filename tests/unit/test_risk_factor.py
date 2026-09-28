"""Risk factor: position × cards × bid — fixtures are synthetic (factory)."""

from app.services.risk_factor import (
    RISKY_MAKE_THRESHOLD,
    claim_risk,
    compute_game_risk,
    paid_risk,
)
from app.services.title_registry import GameContext


def _ctx(
    players,
    bid_sequence,
    score_history,
    cards_per_round,
    round_scores=None,
):
    """Minimal GameContext for risk tests."""
    totals = {p: score_history[p][-1] if score_history[p] else 0 for p in players}
    return GameContext(
        players=players,
        totals=totals,
        round_count=len(cards_per_round),
        accuracy=dict.fromkeys(players, 0.5),
        bids_made=dict.fromkeys(players, 0),
        bids_total={p: len(cards_per_round) for p in players},
        zero_bids_made=dict.fromkeys(players, 0),
        zero_bids_attempted=dict.fromkeys(players, 0),
        overbids=dict.fromkeys(players, 0),
        underbids=dict.fromkeys(players, 0),
        best_bid_made=dict.fromkeys(players, 0),
        longest_miss_streak=dict.fromkeys(players, 0),
        longest_make_streak=dict.fromkeys(players, 0),
        score_history=score_history,
        bid_sequence=bid_sequence,
        round_scores=round_scores or {p: [0] * len(cards_per_round) for p in players},
        cards_per_round=cards_per_round,
        trump_per_round=[""] * len(cards_per_round),
        off_by_one=dict.fromkeys(players, 0),
    )


def test_nil_exact_zero_risk():
    """Bid 0 exact → ambition 0 → claim_risk 0 and paid_risk 0."""
    assert claim_risk(bid=0, cards=8, rank=4, num_players=4) == 0.0
    assert paid_risk(bid=0, hands=0, cards=8, rank=4, num_players=4) == 0.0


def test_trailing_high_bid_outranks_safe():
    """Last place bid 5/8 made beats leader bid 1/8 made."""
    trailing = paid_risk(bid=5, hands=5, cards=8, rank=4, num_players=4)
    leading_safe = paid_risk(bid=1, hands=1, cards=8, rank=1, num_players=4)
    assert trailing > leading_safe
    assert trailing >= RISKY_MAKE_THRESHOLD
    assert leading_safe < RISKY_MAKE_THRESHOLD


def test_miss_pays_zero():
    """Claim risk exists but miss → paid_risk 0."""
    claimed = claim_risk(bid=5, cards=8, rank=4, num_players=4)
    assert claimed > 0
    assert paid_risk(bid=5, hands=3, cards=8, rank=4, num_players=4) == 0.0


def test_compute_game_risk_aggregates():
    """Two players: safe nils vs one pressure make."""
    # Round 0: both start equal (rank 1 for both after sort — Alice first in roster).
    # After R0 Alice +30 Bob +10 → Alice leads.
    # Round 1 (8 cards): Alice bid 0/0 (safe), Bob bid 4/4 while trailing.
    players = ["Alice", "Bob"]
    cards = [8, 8]
    bid_sequence = {
        "Alice": [(0, 0), (0, 0)],
        "Bob": [(1, 1), (4, 4)],
    }
    # cumulative after each round
    score_history = {
        "Alice": [30, 40],
        "Bob": [11, 51],
    }
    ctx = _ctx(players, bid_sequence, score_history, cards)
    agg = compute_game_risk(ctx)
    assert agg["Alice"]["total_paid_risk"] < agg["Bob"]["total_paid_risk"]
    assert agg["Bob"]["risky_makes"] >= 1
    assert agg["Alice"]["risky_makes"] == 0
