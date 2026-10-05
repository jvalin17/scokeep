"""Unit tests for Scoresheet round lock helpers."""

from app.services.scoresheet import apply_round, scores_dict_for_players


def test_scores_dict_for_players_maps_indices():
    players = ["Maria", "Diego", "Priya"]
    by_index = {"0": 10, "1": 20, "2": -5}
    named = scores_dict_for_players(players, by_index)
    assert named == {"Maria": 10, "Diego": 20, "Priya": -5}


def test_apply_named_round_into_totals():
    players = ["Maria", "Diego"]
    totals = {"Maria": 0, "Diego": 0}
    named = scores_dict_for_players(players, {"0": 12, "1": 8})
    assert apply_round(totals, named) == {"Maria": 12, "Diego": 8}
