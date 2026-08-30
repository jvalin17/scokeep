"""Selection algorithm invariant tests with Hypothesis."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.game_titles import evaluate_titles, select_titles
from tests.guards.fixtures import (
    PLAYERS_2,
    PLAYERS_4,
    PLAYERS_8,
    all_missed_game,
    eight_player_game,
    full_game_4p,
)


def _make_candidate(key, player, score):
    return {
        "key": key,
        "emoji": "T",
        "title": "Test",
        "desc": "Test",
        "player": player,
        "detail": "test",
        "score": float(score),
    }


class TestSelectionInvariants:
    def test_every_player_covered_4p(self):
        titles = evaluate_titles(PLAYERS_4, full_game_4p())
        for p in PLAYERS_4:
            assert p in {t["player"] for t in titles}, f"'{p}' missing"

    def test_every_player_covered_8p(self):
        titles = evaluate_titles(PLAYERS_8, eight_player_game())
        for p in PLAYERS_8:
            assert p in {t["player"] for t in titles}, f"'{p}' missing"

    def test_every_player_covered_2p(self):
        titles = evaluate_titles(
            PLAYERS_2,
            [
                __import__("tests.guards.fixtures", fromlist=["make_round"]).make_round(
                    {"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8, "spades"
                ),
                __import__("tests.guards.fixtures", fromlist=["make_round"]).make_round(
                    {"0": 0, "1": 2}, {"0": 0, "1": 2}, {"0": 10, "1": 20}, 7, "hearts"
                ),
            ],
        )
        for p in PLAYERS_2:
            assert p in {t["player"] for t in titles}

    def test_no_duplicate_keys(self):
        titles = evaluate_titles(PLAYERS_4, full_game_4p())
        keys = [t["key"] for t in titles]
        assert len(keys) == len(set(keys))

    def test_deterministic(self):
        r1 = evaluate_titles(PLAYERS_4, full_game_4p())
        r2 = evaluate_titles(PLAYERS_4, full_game_4p())
        assert r1 == r2

    def test_count_respects_target(self):
        titles = evaluate_titles(PLAYERS_4, full_game_4p())
        assert len(titles) <= max(10, len(PLAYERS_4) + 2)

    def test_all_missed_still_works(self):
        titles = evaluate_titles(PLAYERS_4, all_missed_game())
        for p in PLAYERS_4:
            assert p in {t["player"] for t in titles}

    def test_empty_returns_empty(self):
        assert evaluate_titles(PLAYERS_4, []) == []


class TestSelectAlgorithm:
    def test_coverage_first(self):
        candidates = [
            _make_candidate("t1", "Alice", 100),
            _make_candidate("t2", "Alice", 90),
            _make_candidate("t3", "Bob", 10),
        ]
        result = select_titles(candidates, ["Alice", "Bob"], target=2)
        assert {"Alice", "Bob"} == {t["player"] for t in result}

    def test_no_duplicate_keys_in_output(self):
        candidates = [
            _make_candidate("t1", "Alice", 100),
            _make_candidate("t1", "Bob", 90),
            _make_candidate("t2", "Bob", 80),
        ]
        result = select_titles(candidates, ["Alice", "Bob"], target=2)
        assert len({t["key"] for t in result}) == len(result)

    def test_fewer_than_target(self):
        result = select_titles([_make_candidate("t1", "Alice", 100)], ["Alice"], target=10)
        assert len(result) == 1


class TestHypothesisInvariants:
    @given(data=st.data())
    @settings(max_examples=100, deadline=2000)
    def test_coverage_always_holds(self, data):
        players = data.draw(
            st.lists(
                st.from_regex(r"[a-z]{3,6}", fullmatch=True), min_size=2, max_size=6, unique=True
            )
        )
        candidates = [_make_candidate(f"auto_{p}", p, 50 + i) for i, p in enumerate(players)]
        for i in range(data.draw(st.integers(min_value=0, max_value=15))):
            p = data.draw(st.sampled_from(players))
            candidates.append(
                _make_candidate(f"extra_{i}", p, data.draw(st.floats(min_value=1, max_value=200)))
            )
        result = select_titles(candidates, players)
        for p in players:
            assert p in {t["player"] for t in result}, f"'{p}' missing"
