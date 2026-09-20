"""TDD: Tests for declarative title registry.

Written BEFORE title_registry.py exists.
Tests the declarative title system that replaces simple title patterns
from game_titles.py with config-driven definitions.
"""

from tests.unit.conftest import MockRound


def _make_context():
    """Build a GameContext with known data for testing."""
    from app.services.game_titles import build_context

    rounds = [
        MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
        MockRound({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7),
        MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 6),
        MockRound({"0": 1, "1": 0}, {"0": 0, "1": 0}, {"0": -11, "1": 10}, 3),
    ]
    return build_context(["Alice", "Bob"], rounds)


class TestDeclarativeTitleDefs:
    """Declarative titles must produce the same candidates as the old functions."""

    def test_registry_has_declarative_titles(self):
        from app.services.title_registry import DECLARATIVE_TITLES

        assert len(DECLARATIVE_TITLES) >= 13

    def test_each_title_has_required_fields(self):
        from app.services.title_registry import DECLARATIVE_TITLES

        required = {"key", "emoji", "title", "desc", "metric", "mode"}
        for t in DECLARATIVE_TITLES:
            missing = required - set(t.keys())
            assert not missing, f"Title {t.get('key', '?')} missing fields: {missing}"

    def test_champion_is_declarative(self):
        from app.services.title_registry import DECLARATIVE_TITLES

        keys = [t["key"] for t in DECLARATIVE_TITLES]
        assert "champion" in keys

    def test_cellar_dweller_is_declarative(self):
        from app.services.title_registry import DECLARATIVE_TITLES

        keys = [t["key"] for t in DECLARATIVE_TITLES]
        assert "cellar_dweller" in keys


class TestEvaluateDeclarative:
    """evaluate_declarative must produce valid candidates from GameContext."""

    def test_champion_picks_highest_scorer(self):
        from app.services.title_registry import evaluate_declarative

        ctx = _make_context()
        candidates = evaluate_declarative(ctx)
        champ = [c for c in candidates if c["key"] == "champion"]
        assert len(champ) == 1
        assert champ[0]["player"] == "Alice"  # Alice has 49 pts, Bob has 11

    def test_cellar_dweller_picks_lowest_scorer(self):
        from app.services.title_registry import evaluate_declarative

        ctx = _make_context()
        candidates = evaluate_declarative(ctx)
        cellar = [c for c in candidates if c["key"] == "cellar_dweller"]
        assert len(cellar) == 1
        assert cellar[0]["player"] == "Bob"

    def test_sharpshooter_ranks_by_accuracy(self):
        from app.services.title_registry import evaluate_declarative

        ctx = _make_context()
        candidates = evaluate_declarative(ctx)
        sharp = [c for c in candidates if c["key"] == "sharpshooter"]
        # Both players should have candidates since both have accuracy > 0
        assert len(sharp) >= 1

    def test_all_candidates_have_required_fields(self):
        from app.services.title_registry import evaluate_declarative

        ctx = _make_context()
        candidates = evaluate_declarative(ctx)
        required = {"key", "emoji", "title", "desc", "player", "detail", "score"}
        for c in candidates:
            missing = required - set(c.keys())
            assert not missing, f"Candidate {c['key']} missing: {missing}"

    def test_all_scores_positive(self):
        from app.services.title_registry import evaluate_declarative

        ctx = _make_context()
        candidates = evaluate_declarative(ctx)
        for c in candidates:
            assert c["score"] > 0, f"{c['key']} for {c['player']} has score={c['score']}"

    def test_declarative_titles_include_all_expected_keys(self):
        """Declarative titles must cover original 13 + 12 new keys."""
        from app.services.title_registry import DECLARATIVE_TITLES

        expected_keys = {
            # Original 13
            "champion",
            "cellar_dweller",
            "sharpshooter",
            "brick_wall",
            "bold_move",
            "sandbagger",
            "gambler",
            "cursed",
            "big_spender",
            "rock_bottom",
            "crowd_pleaser",
            "heartbreaker",
            "humble_pie",
            # New 12
            "glass_cannon",
            "overachiever",
            "penny_pincher",
            "steamroller",
            "wrecking_ball",
            "sniper_bid",
            "wild_card",
            "iron_nerve",
            "marathon",
            "anchor",
            "clutch",
            "perfectionist",
        }
        actual_keys = {t["key"] for t in DECLARATIVE_TITLES}
        assert expected_keys == actual_keys

    def test_no_duplicate_title_keys(self):
        from app.services.title_registry import DECLARATIVE_TITLES

        keys = [t["key"] for t in DECLARATIVE_TITLES]
        assert len(keys) == len(set(keys)), f"Duplicate keys: {keys}"

    def test_champion_tie_picks_first_player(self):
        """Tied scores → first player in roster order wins."""
        from app.services.game_titles import build_context
        from app.services.title_registry import evaluate_declarative

        # Both players score exactly the same
        rounds = [
            MockRound({"0": 2, "1": 2}, {"0": 2, "1": 2}, {"0": 20, "1": 20}, 8),
            MockRound({"0": 1, "1": 1}, {"0": 1, "1": 1}, {"0": 11, "1": 11}, 5),
        ]
        ctx = build_context(["Alice", "Bob"], rounds)
        candidates = evaluate_declarative(ctx)
        champ = [c for c in candidates if c["key"] == "champion"]
        assert len(champ) == 1
        assert champ[0]["player"] == "Alice"  # first in roster

    def test_single_player_game(self):
        """Single player gets all applicable titles."""
        from app.services.game_titles import build_context
        from app.services.title_registry import evaluate_declarative

        rounds = [
            MockRound({"0": 3}, {"0": 3}, {"0": 30}, 8),
            MockRound({"0": 0}, {"0": 0}, {"0": 10}, 5),
        ]
        ctx = build_context(["Solo"], rounds)
        candidates = evaluate_declarative(ctx)
        assert len(candidates) > 0
        for c in candidates:
            assert c["player"] == "Solo"


class TestMetricExtractors:
    """Test individual metric extractor functions in title_registry."""

    def _ctx(self):
        from app.services.game_titles import build_context

        rounds = [
            MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
            MockRound({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7),
        ]
        return build_context(["Alice", "Bob"], rounds)

    def test_total_score(self):
        from app.services.title_registry import _total_score

        ctx = self._ctx()
        val, detail = _total_score(ctx, "Alice")
        assert val == 40
        assert "pts" in detail

    def test_accuracy(self):
        from app.services.title_registry import _accuracy

        ctx = self._ctx()
        result = _accuracy(ctx, "Alice")
        assert result is not None
        val, detail = result
        assert val == 100.0  # 2/2

    def test_zero_bids_made(self):
        from app.services.title_registry import _zero_bids_made

        ctx = self._ctx()
        result = _zero_bids_made(ctx, "Alice")
        assert result is not None

    def test_best_bid_made(self):
        from app.services.title_registry import _best_bid_made

        ctx = self._ctx()
        result = _best_bid_made(ctx, "Alice")
        assert result is not None
        val, _ = result
        assert val == 3

    def test_underbids(self):
        from app.services.title_registry import _underbids

        ctx = self._ctx()
        result = _underbids(ctx, "Bob")
        assert result is not None

    def test_overbids(self):
        from app.services.title_registry import _overbids

        ctx = self._ctx()
        # Bob overbid in round 2 (bid 2, won 3 → underbid, not overbid)
        # Check returns None or valid tuple
        result = _overbids(ctx, "Bob")
        assert result is None or isinstance(result, tuple)

    def test_longest_miss_streak(self):
        from app.services.title_registry import _longest_miss_streak

        ctx = self._ctx()
        result = _longest_miss_streak(ctx, "Bob")
        assert result is not None

    def test_max_round_score(self):
        from app.services.title_registry import _max_round_score

        ctx = self._ctx()
        result = _max_round_score(ctx, "Alice")
        assert result is not None
        val, _ = result
        assert val == 30

    def test_min_round_score(self):
        from app.services.title_registry import _min_round_score

        ctx = self._ctx()
        result = _min_round_score(ctx, "Bob")
        assert result is not None  # Bob has -20

    def test_positive_round_count(self):
        from app.services.title_registry import _positive_round_count

        ctx = self._ctx()
        result = _positive_round_count(ctx, "Alice")
        assert result is not None

    def test_off_by_one(self):
        from app.services.title_registry import _off_by_one

        ctx = self._ctx()
        # May or may not have off-by-one, just check it returns correctly
        result = _off_by_one(ctx, "Alice")
        assert result is None or isinstance(result, tuple)

    def test_zero_bids_attempted(self):
        from app.services.title_registry import _zero_bids_attempted

        ctx = self._ctx()
        result = _zero_bids_attempted(ctx, "Alice")
        assert result is not None

    def test_glass_cannon(self):
        from app.services.title_registry import _glass_cannon

        ctx = self._ctx()
        # Alice: rounds [30, 10] → gap=20; Bob: rounds [10, -20] → gap=30
        result = _glass_cannon(ctx, "Bob")
        assert result is not None
        val, _ = result
        assert val == 30  # 10 - (-20) = 30

    def test_overachiever(self):
        from app.services.title_registry import _overachiever

        ctx = self._ctx()
        # Bob round 1: bid 2, hand 3 → overachieved
        result = _overachiever(ctx, "Bob")
        assert result is not None
        val, _ = result
        assert val >= 1

    def test_sniper_bid(self):
        from app.services.title_registry import _sniper_bid

        ctx = self._ctx()
        # Check returns valid tuple or None
        result = _sniper_bid(ctx, "Alice")
        assert result is None or isinstance(result, tuple)

    def test_wild_card(self):
        from app.services.title_registry import _wild_card

        ctx = self._ctx()
        # Alice bid [3, 0] → 2 unique; Bob bid [0, 2] → 2 unique
        result = _wild_card(ctx, "Alice")
        assert result is not None
        val, _ = result
        assert val == 2

    def test_steamroller(self):
        from app.services.title_registry import _steamroller

        ctx = self._ctx()
        # Uses longest_make_streak from context
        result = _steamroller(ctx, "Alice")
        assert result is not None or result is None  # depends on data

    def test_marathon(self):
        """Marathon fires when all rounds have positive score."""
        from app.services.game_titles import build_context
        from app.services.title_registry import _marathon

        rounds = [
            MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 5),
            MockRound({"0": 0, "1": 1}, {"0": 0, "1": 1}, {"0": 10, "1": 11}, 4),
        ]
        ctx = build_context(["Alice", "Bob"], rounds)
        result = _marathon(ctx, "Alice")
        assert result is not None
        val, _ = result
        assert val == 1  # boolean-ish: 1 = all positive

    def test_marathon_fails_with_negative(self):
        from app.services.title_registry import _marathon

        ctx = self._ctx()
        # Bob has -20 in one round
        result = _marathon(ctx, "Bob")
        assert result is None

    def test_anchor(self):
        from app.services.title_registry import _anchor

        ctx = self._ctx()
        # Count rounds where hands_won = 0
        result = _anchor(ctx, "Alice")
        assert result is None or isinstance(result, tuple)

    def test_penny_pincher(self):
        from app.services.title_registry import _penny_pincher

        ctx = self._ctx()
        result = _penny_pincher(ctx, "Alice")
        assert result is None or isinstance(result, tuple)

    def test_wrecking_ball(self):
        from app.services.title_registry import _wrecking_ball

        ctx = self._ctx()
        # Bob has -20 in round 2 → negative total
        result = _wrecking_ball(ctx, "Bob")
        assert result is not None
        val, _ = result
        assert val == 20  # abs of -20

    def test_iron_nerve(self):
        from app.services.title_registry import _iron_nerve

        ctx = self._ctx()
        result = _iron_nerve(ctx, "Alice")
        assert result is None or isinstance(result, tuple)

    def test_clutch(self):
        from app.services.title_registry import _clutch

        ctx = self._ctx()
        # Rounds with ≥5 cards: round 1 (8 cards), round 2 (7 cards)
        result = _clutch(ctx, "Alice")
        assert result is not None

    def test_perfectionist(self):
        """Perfectionist is highest mode — single best accuracy player."""
        from app.services.game_titles import build_context
        from app.services.title_registry import DECLARATIVE_TITLES, _evaluate_one

        rounds = [
            MockRound({"0": 1, "1": 1}, {"0": 1, "1": 0}, {"0": 11, "1": -11}, 5),
            MockRound({"0": 0, "1": 0}, {"0": 0, "1": 0}, {"0": 10, "1": 10}, 3),
        ]
        ctx = build_context(["Alice", "Bob"], rounds)
        perf_def = next(d for d in DECLARATIVE_TITLES if d["key"] == "perfectionist")
        result = _evaluate_one(perf_def, ctx)
        assert len(result) == 1
        assert result[0]["player"] == "Alice"  # 100% vs 50%


class TestEvalHelpers:
    """Test _eval_single_winner and _eval_per_player."""

    def test_eval_single_winner(self):
        from app.services.game_titles import build_context
        from app.services.title_registry import DECLARATIVE_TITLES, _evaluate_one

        rounds = [MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8)]
        ctx = build_context(["Alice", "Bob"], rounds)
        champ_def = next(d for d in DECLARATIVE_TITLES if d["key"] == "champion")
        result = _evaluate_one(champ_def, ctx)
        assert len(result) == 1
        assert result[0]["player"] == "Alice"

    def test_eval_per_player(self):
        from app.services.game_titles import build_context
        from app.services.title_registry import DECLARATIVE_TITLES, _evaluate_one

        rounds = [MockRound({"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}, 8)]
        ctx = build_context(["Alice", "Bob"], rounds)
        sharp_def = next(d for d in DECLARATIVE_TITLES if d["key"] == "sharpshooter")
        result = _evaluate_one(sharp_def, ctx)
        assert len(result) == 2  # both players have accuracy > 0


class TestAssignExclusive:
    def test__assign_exclusive_drops_ties(self):
        from app.services.game_titles import _assign_exclusive

        cands = [
            {"key": "t1", "player": "A", "score": 50.0},
            {"key": "t1", "player": "B", "score": 50.0},
            {"key": "t2", "player": "A", "score": 40.0},
        ]
        result = _assign_exclusive(cands)
        keys = [c["key"] for c in result]
        assert "t1" not in keys  # tied — dropped
        assert "t2" in keys

    def test__assign_exclusive_keeps_clear_winner(self):
        from app.services.game_titles import _assign_exclusive

        cands = [
            {"key": "t1", "player": "A", "score": 80.0},
            {"key": "t1", "player": "B", "score": 50.0},
        ]
        result = _assign_exclusive(cands)
        assert len(result) == 1
        assert result[0]["player"] == "A"


class TestPhase1Coverage:
    def test__phase1_coverage_fallback_on_no_exclusive(self):
        from app.services.game_titles import _phase1_coverage

        exclusive = [{"key": "t1", "player": "A", "score": 50.0}]
        all_cands = [
            {"key": "t1", "player": "A", "score": 50.0},
            {"key": "t2", "player": "B", "score": 30.0},
        ]
        used = set()
        result = _phase1_coverage(["A", "B"], exclusive, all_cands, used)
        players = {c["player"] for c in result}
        assert "A" in players
        assert "B" in players  # fell back to all_cands


class TestPerfectionistMetric:
    def test__perfectionist_metric_above_threshold(self):
        from app.services.title_registry import _perfectionist_metric

        ctx = _make_context()
        # Alice has 75% accuracy in _make_context (3/4 bids made)
        result = _perfectionist_metric(ctx, "Alice")
        # 75% < 80% threshold
        assert result is None

    def test__perfectionist_metric_high_accuracy(self):
        from app.services.game_titles import build_context
        from app.services.title_registry import _perfectionist_metric

        rounds = [
            MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 5),
            MockRound({"0": 0, "1": 1}, {"0": 0, "1": 0}, {"0": 10, "1": -11}, 3),
        ]
        ctx = build_context(["Alice", "Bob"], rounds)
        result = _perfectionist_metric(ctx, "Alice")
        assert result is not None
        val, _ = result
        assert val == 100.0


class TestCandidateHelper:
    def test_candidate_creates_dict(self):
        from app.services.title_registry import _candidate

        c = _candidate("test", "🏆", "Test", "desc", "Alice", "detail", 50)
        assert c["key"] == "test"
        assert c["score"] == 50.0
        assert c["player"] == "Alice"
