"""TDD: Tests for wiring title engine to GameMetrics.

Written BEFORE implementation. build_context_from_metrics should produce
the same GameContext as build_context but consuming GameMetrics instead
of raw rounds.
"""

from app.services.metrics import compute_game_metrics
from tests.unit.conftest import MockRound


def _make_rounds():
    return [
        MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
        MockRound({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7),
        MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 6),
        MockRound({"0": 1, "1": 0}, {"0": 0, "1": 0}, {"0": -11, "1": 10}, 3),
    ]


class TestBuildContextFromMetrics:
    def test_build_context_from_metrics_exists(self):
        from app.services.game_titles import build_context_from_metrics

        assert callable(build_context_from_metrics)

    def test_produces_same_totals(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        assert ctx_new.totals == ctx_old.totals

    def test_produces_same_accuracy(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        for p in players:
            assert abs(ctx_new.accuracy[p] - ctx_old.accuracy[p]) < 0.01

    def test_produces_same_bids_made(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        assert ctx_new.bids_made == ctx_old.bids_made

    def test_produces_same_round_count(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        assert ctx_new.round_count == ctx_old.round_count

    def test_produces_same_streaks(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        assert ctx_new.longest_make_streak == ctx_old.longest_make_streak
        assert ctx_new.longest_miss_streak == ctx_old.longest_miss_streak

    def test_produces_same_off_by_one(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        assert ctx_new.off_by_one == ctx_old.off_by_one

    def test_score_history_matches(self):
        from app.services.game_titles import build_context, build_context_from_metrics

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        ctx_old = build_context(players, rounds)
        ctx_new = build_context_from_metrics(gm)

        assert ctx_new.score_history == ctx_old.score_history


class TestFillStateFromPlayerMetrics:
    def test_fill_state_from_player_metrics(self):
        from app.services.game_titles import _fill_state_from_player_metrics, _init_context_state

        rounds = _make_rounds()
        gm = compute_game_metrics(["Alice", "Bob"], rounds)
        state = _init_context_state(["Alice", "Bob"])
        _fill_state_from_player_metrics(state, "Alice", gm.player_metrics["Alice"], gm)
        assert state["bids_made"]["Alice"] > 0
        assert state["totals"]["Alice"] != 0


class TestEvaluateFromContext:
    def test_evaluate_from_context(self):
        from app.services.game_titles import _evaluate_from_context, build_context

        rounds = _make_rounds()
        ctx = build_context(["Alice", "Bob"], rounds)
        result = _evaluate_from_context(ctx, ["Alice", "Bob"])
        assert isinstance(result, list)
        assert len(result) > 0


class TestEvaluateTitlesFromMetrics:
    def test_evaluate_titles_from_metrics_exists(self):
        from app.services.game_titles import evaluate_titles_from_metrics

        assert callable(evaluate_titles_from_metrics)

    def test_produces_titles(self):
        from app.services.game_titles import evaluate_titles_from_metrics

        rounds = _make_rounds()
        gm = compute_game_metrics(["Alice", "Bob"], rounds)
        titles = evaluate_titles_from_metrics(gm)
        assert isinstance(titles, list)
        assert len(titles) > 0

    def test_same_titles_as_old_path(self):
        from app.services.game_titles import (
            evaluate_titles,
            evaluate_titles_from_metrics,
        )

        rounds = _make_rounds()
        players = ["Alice", "Bob"]
        gm = compute_game_metrics(players, rounds)

        old_titles = evaluate_titles(players, rounds)
        new_titles = evaluate_titles_from_metrics(gm)

        old_keys = {t["key"] for t in old_titles}
        new_keys = {t["key"] for t in new_titles}
        assert old_keys == new_keys
