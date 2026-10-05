"""Scoresheet scoring vectors — apply, undo, high/low rank.

Requirements: multi-game Scoresheet play + Winner setting.
Fixtures are synthetic (factory) — Scoresheet engine not yet wired to API.
"""

from app.services.scoresheet import apply_round, rank_players, undo_round


def test_apply_round_and_undo_round():
    totals = {"Ab": 0, "Cd": 0, "Ef": 0}
    round_one = {"Ab": 20, "Cd": 0, "Ef": 40}
    after_one = apply_round(totals, round_one)
    assert after_one == {"Ab": 20, "Cd": 0, "Ef": 40}

    round_two = {"Ab": 10, "Cd": 30, "Ef": 5}
    after_two = apply_round(after_one, round_two)
    assert after_two == {"Ab": 30, "Cd": 30, "Ef": 45}

    undone = undo_round(after_two, round_two)
    assert undone == {"Ab": 20, "Cd": 0, "Ef": 40}


def test_rank_players_highest_and_lowest():
    totals = {"Ab": 30, "Cd": 30, "Ef": 45}
    high = rank_players(totals, lowest_wins=False)
    assert high[0] == "Ef"
    assert set(high[1:]) == {"Ab", "Cd"}

    low = rank_players(totals, lowest_wins=True)
    assert low[-1] == "Ef"
    assert low[0] in {"Ab", "Cd"}


def test_apply_preserves_missing_players_as_zero_delta():
    totals = {"Ab": 5, "Cd": 5}
    updated = apply_round(totals, {"Ab": 3})
    assert updated == {"Ab": 8, "Cd": 5}


def test_undo_does_not_go_below_when_key_missing_from_round():
    totals = {"Ab": 10, "Cd": 0}
    undone = undo_round(totals, {"Ab": 10})
    assert undone == {"Ab": 0, "Cd": 0}


def test_apply_and_undo_negative_scores():
    """Allow negatives On — signed round deltas apply and undo cleanly."""
    totals = {"Alice": 10, "Bob": 0}
    round_scores = {"Alice": -5, "Bob": 12}
    after = apply_round(totals, round_scores)
    assert after == {"Alice": 5, "Bob": 12}
    assert undo_round(after, round_scores) == totals
