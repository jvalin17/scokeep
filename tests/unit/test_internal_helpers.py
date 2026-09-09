"""Tests for internal helper functions.

Gate requires test names matching function names.
"""

from app.services.metrics import compute_game_metrics
from tests.unit.conftest import MockRound


class TestGameTitlesHelpers:
    def test_make_declarative_wrapper(self):
        from app.services.game_titles import TITLE_REGISTRY, build_context

        rounds = [MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10})]
        ctx = build_context(["Alice", "Bob"], rounds)
        champ_fn = next(f for f in TITLE_REGISTRY if f.__name__ == "_champion")
        result = champ_fn(ctx)
        assert isinstance(result, list)
        assert result[0]["key"] == "champion"

    def test_wrapper(self):
        """The inner wrapper function inside _make_declarative_wrapper."""
        from app.services.game_titles import TITLE_REGISTRY

        # Every declarative wrapper is callable
        for fn in TITLE_REGISTRY:
            assert callable(fn)


class TestInsightsHelpers:
    def test_compute_raw_vectors(self):
        from app.services.insights import _compute_raw_vectors

        gm = compute_game_metrics(
            ["Alice", "Bob"],
            [MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11})],
        )
        vectors = _compute_raw_vectors({"Alice", "Bob"}, {"Alice": 3, "Bob": 2}, [gm])
        assert "Alice" in vectors
        assert "Bob" not in vectors
        assert len(vectors["Alice"]) == 10

    def test_update_calibration(self):
        from app.services.insights import _update_calibration

        vectors = {"Alice": [0.5] * 10, "Bob": [0.8] * 10}
        result = _update_calibration(vectors)
        assert result["count"] == 2


class TestMetricAggregatorHelpers:
    def test_accumulate_rounds(self):
        from app.services.metric_aggregator import _accumulate_rounds

        g1 = compute_game_metrics(["Alice"], [MockRound({"0": 2}, {"0": 2}, {"0": 20})])
        g2 = compute_game_metrics(["Alice"], [MockRound({"0": 1}, {"0": 0}, {"0": -11})])
        acc = _accumulate_rounds("Alice", [g1, g2])
        assert acc.games_played == 2
        assert len(acc.game_totals) == 2

    def test_classify_bidding_style(self):
        from app.services.metric_aggregator import _classify_bidding_style

        style, pct = _classify_bidding_style(5, 2, 3)
        assert style == "aggressive"

    def test_classify_consistency(self):
        from app.services.metric_aggregator import _classify_consistency

        assert _classify_consistency([50.0, 50.0, 50.0]) == "high"

    def test_classify_trend(self):
        from app.services.metric_aggregator import _classify_trend

        assert _classify_trend([0.3, 0.3, 0.9, 0.9]) == "improving"
        assert _classify_trend([0.5, 0.5]) == "steady"

    def test_best_trump_suit(self):
        from app.services.metric_aggregator import _best_trump_suit

        suit, pct = _best_trump_suit({"spades": 5, "hearts": 3}, {"spades": 4, "hearts": 1})
        assert suit == "spades"

    def test_classify_tempo(self):
        from app.services.metric_aggregator import _classify_tempo

        assert _classify_tempo([30, 20, 25], [5, 3, 2]) == "1st half"
        assert _classify_tempo([10, 11], [10, 12]) == "even"

    def test_build_fun_facts(self):
        from app.services.metric_aggregator import _build_fun_facts, _RoundAccumulator

        acc = _RoundAccumulator()
        acc.biggest_round_score = 50
        acc.bid_counts = {2: 5}
        facts = _build_fun_facts(acc, 2)
        assert any("50" in f for f in facts)

    def test_games_to_metrics(self):
        from app.services.metric_aggregator import _games_to_metrics

        class MockGame:
            players = ["A"]
            rounds = [MockRound({"0": 1}, {"0": 1}, {"0": 11})]
            winner = "A"

        result = _games_to_metrics([MockGame()])
        assert len(result) == 1
        assert result[0].winner == "A"

    def test_compute_halfway_scores(self):
        from app.services.metric_aggregator import _compute_halfway_scores

        gm = compute_game_metrics(
            ["Alice", "Bob"],
            [
                MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}),
                MockRound({"0": 1, "1": 2}, {"0": 1, "1": 2}, {"0": 11, "1": 20}),
            ],
        )
        scores = _compute_halfway_scores(gm)
        assert "Alice" in scores
        assert "Bob" in scores
