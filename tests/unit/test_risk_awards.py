"""Last Game risk awards — synthetic fixtures (factory).

Safe fat-hand exacts must lose to real paid-risk makes.
Simple titles must not appear on Last Game.
"""

from app.services.game_titles import (
    LAST_GAME_EXCLUDED_KEYS,
    evaluate_titles,
    select_titles,
)
from app.services.title_patterns_risk import _clutch_risk
from tests.unit.conftest import MockRound


def _ctx_from_rounds(players, rounds):
    from app.services.game_titles import build_context

    return build_context(players, rounds)


def test_safe_bet_clutch_loses_to_risky_make():
    """Trailing bid-5/8 make beats leader's safe 0/1 exacts for Ice in the Veins."""
    players = ["Lala", "Masood"]
    # R1: Masood leads (safe). R2: Lala trails and nails bid 5/8.
    rounds = [
        MockRound(
            {"0": 0, "1": 2},
            {"0": 0, "1": 2},
            {"0": 10, "1": 20},
            8,
        ),
        MockRound(
            {"0": 5, "1": 0},
            {"0": 5, "1": 0},
            {"0": 50, "1": 10},
            8,
        ),
        MockRound(
            {"0": 1, "1": 1},
            {"0": 1, "1": 1},
            {"0": 11, "1": 11},
            7,
        ),
        MockRound(
            {"0": 0, "1": 0},
            {"0": 0, "1": 0},
            {"0": 10, "1": 10},
            6,
        ),
    ]
    ctx = _ctx_from_rounds(players, rounds)
    candidates = _clutch_risk(ctx)
    by_player = {c["player"]: c for c in candidates}
    assert "Lala" in by_player
    if "Masood" in by_player:
        assert by_player["Lala"]["score"] > by_player["Masood"]["score"]


def test_last_game_excludes_simple_titles():
    players = ["Alice", "Bob"]
    rounds = [
        MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
        MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 7),
        MockRound({"0": 0, "1": 2}, {"0": 0, "1": 2}, {"0": 10, "1": 20}, 6),
        MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 5),
    ]
    titles = evaluate_titles(players, rounds)
    keys = {t["key"] for t in titles}
    assert "champion" not in keys
    assert "brick_wall" not in keys
    assert "daredevil" not in keys
    assert "rollercoaster" not in keys
    for key in keys:
        assert key not in LAST_GAME_EXCLUDED_KEYS


def test_max_per_player_cap():
    """Dominant player cannot vacuum all fill slots."""
    players = ["Alice", "Bob", "Charlie"]
    candidates = []
    for index in range(8):
        candidates.append(
            {
                "key": f"a_{index}",
                "emoji": "T",
                "title": "Test",
                "desc": "Test",
                "player": "Alice",
                "detail": "x",
                "score": 100.0 - index,
            }
        )
    candidates.append(
        {
            "key": "b_only",
            "emoji": "T",
            "title": "Test",
            "desc": "Test",
            "player": "Bob",
            "detail": "x",
            "score": 10.0,
        }
    )
    candidates.append(
        {
            "key": "c_only",
            "emoji": "T",
            "title": "Test",
            "desc": "Test",
            "player": "Charlie",
            "detail": "x",
            "score": 9.0,
        }
    )
    result = select_titles(candidates, players, target=6)
    # max_per_player = ceil(6/3) = 2
    counts = {}
    for item in result:
        counts[item["player"]] = counts.get(item["player"], 0) + 1
    assert counts.get("Alice", 0) <= 2
    assert "Bob" in counts
    assert "Charlie" in counts


def test_ice_in_the_veins_display_name():
    players = ["Alice", "Bob"]
    rounds = [
        MockRound({"0": 1, "1": 3}, {"0": 1, "1": 3}, {"0": 11, "1": 30}, 8),
        MockRound({"0": 4, "1": 0}, {"0": 4, "1": 0}, {"0": 40, "1": 10}, 8),
    ]
    ctx = _ctx_from_rounds(players, rounds)
    candidates = _clutch_risk(ctx)
    assert candidates
    assert candidates[0]["title"] == "Ice in the Veins"
