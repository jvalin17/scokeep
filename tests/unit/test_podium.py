"""The Podium — weighted finish standing (base place + margin).

Fixtures are synthetic (factory).
"""

from app.services.podium import (
    MARGIN_SCALE,
    build_podium_table,
    init_podium_player,
    place_points,
    record_game,
)


def test_last_place_gets_positive_base():
    totals = {"0": 100, "1": 50, "2": 10}
    names = ["A", "B", "C"]
    pts = place_points(totals, names)
    assert pts["C"] >= 1.0
    assert pts["A"] > pts["B"] > pts["C"]


def test_large_gap_boosts_leader():
    crush = place_points({"0": 200, "1": 10, "2": 5}, ["A", "B", "C"])
    tight = place_points({"0": 52, "1": 50, "2": 48}, ["A", "B", "C"])
    assert crush["A"] - crush["B"] > tight["A"] - tight["B"]
    assert crush["A"] > tight["A"]


def test_tight_finish_small_margin():
    pts = place_points({"0": 51, "1": 50, "2": 49}, ["A", "B", "C"])
    assert pts["A"] < 3 + MARGIN_SCALE
    assert abs(pts["A"] - pts["B"]) < 2.0


def test_all_tied_pure_base():
    pts = place_points({"0": 40, "1": 40, "2": 40}, ["A", "B", "C"])
    assert pts["A"] == 3.0
    assert pts["B"] == 2.0
    assert pts["C"] == 1.0


def test_standing_average():
    podium = {
        "A": init_podium_player(),
        "B": init_podium_player(),
    }
    record_game(podium, {"0": 100, "1": 10}, ["A", "B"])
    record_game(podium, {"0": 20, "1": 80}, ["A", "B"])
    table = build_podium_table(podium)
    assert table[0]["games_count"] == 2
    assert table[0]["standing"] == round(
        podium[table[0]["player"]]["points_sum"] / 2,
        2,
    )
    assert "places" in table[0]
    assert sum(table[0]["places"].values()) == 2
