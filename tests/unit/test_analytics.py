"""Unit tests for analytics — career rules, awards, highlights caching."""

from app.services.analytics import (
    CAREER_RULES,
    _accumulate_game_stats,
    _best_player,
    _build_awards,
    _career_table,
    _init_career,
    _post_game_career_sweeps,
    _process_game_for_career,
)
from app.services.round_utils import _iter_round_bids


class TestIterRoundBids:
    """Shared generator that resolves player indices to names."""

    def _make_round(self, bids, hands, scores):
        class MockRound:
            def __init__(self, bids, hands_won, scores):
                self.bids = bids
                self.hands_won = hands_won
                self.scores = scores
                self.cards_dealt = 8

        return MockRound(bids, hands, scores)

    def test_yields_name_bid_hand_score(self):
        rounds = [
            self._make_round(
                {"0": 2, "1": 3},
                {"0": 2, "1": 1},
                {"0": 20, "1": -30},
            )
        ]
        results = list(_iter_round_bids(["Ravi", "Meera"], rounds))
        assert len(results) == 2
        assert results[0] == ("Ravi", 2, 2, 20, rounds[0])
        assert results[1] == ("Meera", 3, 1, -30, rounds[0])

    def test_skips_out_of_range_index(self):
        rounds = [
            self._make_round(
                {"0": 2, "5": 3},
                {"0": 2, "5": 3},
                {"0": 20, "5": 30},
            )
        ]
        results = list(_iter_round_bids(["Ravi"], rounds))
        assert len(results) == 1
        assert results[0][0] == "Ravi"

    def test_skips_none_bid_or_hand(self):
        rounds = [
            self._make_round(
                {"0": None},
                {"0": 2},
                {"0": 20},
            )
        ]
        results = list(_iter_round_bids(["Ravi"], rounds))
        assert len(results) == 0

    def test_multiple_rounds(self):
        rounds = [
            self._make_round({"0": 1}, {"0": 1}, {"0": 11}),
            self._make_round({"0": 3}, {"0": 2}, {"0": -30}),
        ]
        results = list(_iter_round_bids(["Ravi"], rounds))
        assert len(results) == 2
        assert results[0][1] == 1  # first round bid
        assert results[1][1] == 3  # second round bid


class TestCareerRulesConfig:
    """Career rules are config-driven lambdas, not hardcoded if-chains."""

    def test_four_career_rules_defined(self):
        assert len(CAREER_RULES) == 4

    def test_sniper_rule_bid_one_made(self):
        assert CAREER_RULES["sniper"](1, 1, 8) is True

    def test_sniper_rule_bid_two_not_sniper(self):
        assert CAREER_RULES["sniper"](2, 2, 8) is False

    def test_sniper_rule_bid_one_missed(self):
        assert CAREER_RULES["sniper"](1, 0, 8) is False

    def test_zero_master_rule(self):
        assert CAREER_RULES["zero_master"](0, 0, 5) is True
        assert CAREER_RULES["zero_master"](0, 1, 5) is False
        assert CAREER_RULES["zero_master"](1, 1, 5) is False

    def test_high_roller_rule(self):
        assert CAREER_RULES["high_roller"](3, 3, 8) is True
        assert CAREER_RULES["high_roller"](2, 2, 8) is False
        assert CAREER_RULES["high_roller"](3, 1, 8) is False

    def test_all_in_rule(self):
        assert CAREER_RULES["all_in"](8, 8, 8) is True
        assert CAREER_RULES["all_in"](7, 7, 8) is False
        assert CAREER_RULES["all_in"](8, 5, 8) is False

    def test_rules_are_callable(self):
        for rule_name, rule_fn in CAREER_RULES.items():
            assert callable(rule_fn), f"{rule_name} is not callable"


class TestCareerTable:
    """Career table builder sorts by count descending."""

    def test_sorted_by_count_descending(self):
        career = {
            "Ravi": {"sniper": 5},
            "Meera": {"sniper": 8},
            "Kabir": {"sniper": 2},
        }
        table = _career_table(career, "sniper")
        assert table[0]["name"] == "Meera"
        assert table[0]["count"] == 8
        assert table[1]["name"] == "Ravi"
        assert table[2]["name"] == "Kabir"

    def test_sorted_by_longest_descending(self):
        career = {
            "Ravi": {"longest_miss_streak": 3},
            "Meera": {"longest_miss_streak": 7},
        }
        table = _career_table(career, "longest_miss_streak", "longest")
        assert table[0]["name"] == "Meera"
        assert table[0]["longest"] == 7

    def test_empty_career_returns_empty_table(self):
        table = _career_table({}, "sniper")
        assert table == []


class TestBestPlayer:
    """Helper to find player with highest value."""

    def test_finds_highest(self):
        result = _best_player({"Ravi": 5, "Meera": 3}, "count")
        assert result["name"] == "Ravi"
        assert result["count"] == 5

    def test_returns_none_when_all_zero(self):
        result = _best_player({"Ravi": 0, "Meera": 0}, "count")
        assert result is None

    def test_returns_none_for_empty_dict(self):
        result = _best_player({}, "count")
        assert result is None


class TestAccumulateGameStats:
    """Raw stat accumulation from game rounds."""

    def _make_round(self, bids, hands, scores):
        class MockRound:
            def __init__(self, bids, hands_won, scores):
                self.bids = bids
                self.hands_won = hands_won
                self.scores = scores

        return MockRound(bids, hands, scores)

    def test_totals_accumulated(self):
        rounds = [
            self._make_round(
                {"0": 2, "1": 3},
                {"0": 2, "1": 3},
                {"0": 20, "1": 30},
            ),
            self._make_round(
                {"0": 1, "1": 4},
                {"0": 1, "1": 2},
                {"0": 11, "1": -40},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["totals"]["Ravi"] == 31
        assert stats["totals"]["Meera"] == -10

    def test_overbid_underbid_counted(self):
        rounds = [
            self._make_round(
                {"0": 5, "1": 1},
                {"0": 2, "1": 3},
                {"0": -50, "1": -10},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["overbids"]["Ravi"] == 1
        assert stats["underbids"]["Meera"] == 1

    def test_zero_bids_tracked(self):
        rounds = [
            self._make_round(
                {"0": 0, "1": 5},
                {"0": 0, "1": 5},
                {"0": 10, "1": 50},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["zero_bids_made"]["Ravi"] == 1
        assert stats["zero_bids_made"]["Meera"] == 0

    def test_best_bid_tracked(self):
        rounds = [
            self._make_round(
                {"0": 5, "1": 2},
                {"0": 5, "1": 2},
                {"0": 50, "1": 20},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["best_bid"]["Ravi"] == 5


class TestBuildAwards:
    """Award dicts built from accumulated stats."""

    def test_mvp_is_highest_scorer(self):
        stats = {
            "totals": {"Ravi": 50, "Meera": 30},
            "bids_made": {"Ravi": 3, "Meera": 2},
            "bids_total": {"Ravi": 4, "Meera": 4},
            "zero_bids_made": {"Ravi": 0, "Meera": 1},
            "overbids": {"Ravi": 1, "Meera": 0},
            "underbids": {"Ravi": 0, "Meera": 1},
            "best_bid": {"Ravi": 5},
            "longest_miss": {"Ravi": 1, "Meera": 2},
        }
        awards = _build_awards(stats)
        assert awards["mvp"]["name"] == "Ravi"
        assert awards["mvp"]["score"] == 50

    def test_sharpshooter_best_accuracy(self):
        stats = {
            "totals": {"Ravi": 50, "Meera": 30},
            "bids_made": {"Ravi": 2, "Meera": 4},
            "bids_total": {"Ravi": 4, "Meera": 4},
            "zero_bids_made": {"Ravi": 0, "Meera": 0},
            "overbids": {"Ravi": 0, "Meera": 0},
            "underbids": {"Ravi": 0, "Meera": 0},
            "best_bid": {},
            "longest_miss": {"Ravi": 0, "Meera": 0},
        }
        awards = _build_awards(stats)
        assert awards["sharpshooter"]["name"] == "Meera"
        assert awards["sharpshooter"]["accuracy"] == 100

    def test_all_award_keys_present(self):
        stats = {
            "totals": {"Ravi": 10},
            "bids_made": {"Ravi": 1},
            "bids_total": {"Ravi": 2},
            "zero_bids_made": {"Ravi": 0},
            "overbids": {"Ravi": 1},
            "underbids": {"Ravi": 0},
            "best_bid": {},
            "longest_miss": {"Ravi": 1},
        }
        awards = _build_awards(stats)
        expected_keys = {
            "mvp",
            "sharpshooter",
            "brick_wall",
            "bold_move",
            "cursed",
            "sandbagger",
            "gambler",
        }
        assert set(awards.keys()) == expected_keys


class TestNewCareerAwards:
    """TDD: failing tests for 10 new career award categories."""

    def _make_round(self, bids, hands, scores, cards=8):
        class R:
            def __init__(self, b, h, s, c):
                self.bids = b
                self.hands_won = h
                self.scores = s
                self.cards_dealt = c

        return R(bids, hands, scores, cards)

    def _run_career(self, players, game_rounds, settings=None):
        """Run career tracking on one game, return career dict."""
        from app.services.analytics import (
            _init_career,
            _process_game_for_career,
        )

        class FakeGame:
            def __init__(self, p, s):
                self.players = p
                self.settings = s or {"rounds_per_set": 8}
                self.id = 1

        career = _init_career(set(players))
        game = FakeGame(players, settings)
        _process_game_for_career(game, {1: game_rounds}, career)
        return career

    def test_hot_hand_tracks_positive_streak(self):
        """Longest streak of consecutive made bids."""
        rounds = [
            self._make_round({"0": 1}, {"0": 1}, {"0": 11}),
            self._make_round({"0": 2}, {"0": 2}, {"0": 20}),
            self._make_round({"0": 0}, {"0": 0}, {"0": 10}),
            self._make_round({"0": 1}, {"0": 0}, {"0": -11}),  # miss
        ]
        career = self._run_career(["A"], rounds)
        assert career["A"]["longest_positive_streak"] == 3

    def test_biggest_bid_made(self):
        """Track highest bid successfully made."""
        rounds = [
            self._make_round({"0": 5}, {"0": 5}, {"0": 50}),
            self._make_round({"0": 2}, {"0": 2}, {"0": 20}),
        ]
        career = self._run_career(["A"], rounds)
        assert career["A"]["biggest_bid_made"] == 5

    def test_set_champion_tracks_best_set(self):
        """Best set score across all sets."""
        # 2-round set, player scores 30 + 11 = 41 in set 1
        rounds = [
            self._make_round({"0": 3}, {"0": 3}, {"0": 30}),
            self._make_round({"0": 1}, {"0": 1}, {"0": 11}),
        ]
        career = self._run_career(["A"], rounds, {"rounds_per_set": 2})
        assert career["A"]["best_set_score"] == 41

    def test_set_disaster_tracks_worst_set(self):
        """Worst negative set score."""
        rounds = [
            self._make_round({"0": 3}, {"0": 0}, {"0": -30}),
            self._make_round({"0": 2}, {"0": 0}, {"0": -20}),
        ]
        career = self._run_career(["A"], rounds, {"rounds_per_set": 2})
        assert career["A"]["worst_set_score"] == -50

    def test_comeback_king_tracks_deficit_recovery(self):
        """Largest recovery = final_score - min_cumulative."""
        # Round 1: -30, Round 2: +50 → cumulative: -30, +20
        # Recovery = 20 - (-30) = 50
        rounds = [
            self._make_round({"0": 3}, {"0": 0}, {"0": -30}),
            self._make_round({"0": 5}, {"0": 5}, {"0": 50}),
        ]
        career = self._run_career(["A"], rounds)
        assert career["A"]["biggest_comeback"] == 50

    def test_sweep_tracks_games_won(self):
        """Winner of the game gets games_won incremented."""
        rounds = [
            self._make_round({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}),
        ]
        career = self._run_career(["A", "B"], rounds)
        assert career["A"]["games_won"] == 1
        assert career["B"]["games_won"] == 0

    def test_iron_wall_tracks_zero_bid_streak(self):
        """Longest streak of successful zero bids."""
        rounds = [
            self._make_round({"0": 0}, {"0": 0}, {"0": 10}),
            self._make_round({"0": 0}, {"0": 0}, {"0": 10}),
            self._make_round({"0": 0}, {"0": 0}, {"0": 10}),
            self._make_round({"0": 1}, {"0": 1}, {"0": 11}),  # non-zero bid
        ]
        career = self._run_career(["A"], rounds)
        assert career["A"]["longest_zero_streak"] == 3

    def test_heartbreaker_counts_off_by_one(self):
        """Count rounds where |bid - hand| == 1."""
        rounds = [
            self._make_round({"0": 2}, {"0": 3}, {"0": -20}),  # off by 1
            self._make_round({"0": 1}, {"0": 0}, {"0": -11}),  # off by 1
            self._make_round({"0": 3}, {"0": 1}, {"0": -30}),  # off by 2
        ]
        career = self._run_career(["A"], rounds)
        assert career["A"]["off_by_one_total"] == 2

    def test_triple_crown_same_best_accuracy_and_score(self):
        """Player with both best accuracy AND highest score gets triple crown."""
        rounds = [
            self._make_round({"0": 3, "1": 0}, {"0": 3, "1": 2}, {"0": 30, "1": -10}),
            self._make_round({"0": 2, "1": 1}, {"0": 2, "1": 0}, {"0": 20, "1": -11}),
        ]
        career = self._run_career(["A", "B"], rounds)
        assert career["A"]["triple_crowns"] == 1
        assert career["B"]["triple_crowns"] == 0

    def test_career_tables_include_new_awards(self):
        """_career_tables must include all 10 new award keys."""
        from app.services.analytics import _career_tables, _init_career

        career = _init_career({"A"})
        tables = _career_tables(career)
        new_keys = [
            "hot_hand",
            "biggest_bid",
            "set_champion",
            "set_disaster",
            "comeback_king",
            "sweep",
            "iron_wall",
            "heartbreaker",
            "triple_crown",
        ]
        for key in new_keys:
            assert key in tables, f"Missing career table: {key}"


class TestCheckSetScores:
    """Test _check_set_scores helper."""

    def test_updates_best_set_score(self):
        from app.services.analytics import _check_set_scores

        career = {"A": {"best_set_score": 0, "worst_set_score": 0}}
        _check_set_scores(["A"], {"A": 41}, career)
        assert career["A"]["best_set_score"] == 41

    def test_updates_worst_set_score_only_if_negative(self):
        from app.services.analytics import _check_set_scores

        career = {"A": {"best_set_score": 0, "worst_set_score": 0}}
        _check_set_scores(["A"], {"A": -30}, career)
        assert career["A"]["worst_set_score"] == -30

    def test_positive_score_does_not_set_worst(self):
        from app.services.analytics import _check_set_scores

        career = {"A": {"best_set_score": 0, "worst_set_score": 0}}
        _check_set_scores(["A"], {"A": 20}, career)
        assert career["A"]["worst_set_score"] == 0


class TestEmptyHighlightsSchema:
    """empty_highlights must include all career table keys."""

    def test_empty_highlights_has_all_career_keys(self):
        from app.services.analytics import AnalyticsService, _career_tables, _init_career

        # Get the actual career table keys
        career = _init_career({"test"})
        tables = _career_tables(career)
        expected_keys = set(tables.keys())

        # Get empty_highlights career keys (from the method's fallback)
        # We need to check the hardcoded dict matches
        import inspect

        source = inspect.getsource(AnalyticsService.get_playground_stats)
        for key in expected_keys:
            assert f'"{key}"' in source, f"empty_highlights missing career key: {key}"


class TestCareerAccumulatesAcrossGames:
    """Career stats must accumulate correctly across multiple games."""

    def _make_round(self, bids, hands, scores, cards=8):
        class R:
            def __init__(self, b, h, s, c):
                self.bids = b
                self.hands_won = h
                self.scores = s
                self.cards_dealt = c

        return R(bids, hands, scores, cards)

    def test_career_accumulates_across_games(self):
        """Career stats must accumulate across multiple games."""

        class FakeGame:
            def __init__(self, pid, players, settings):
                self.id = pid
                self.players = players
                self.settings = settings

        players = ["A", "B"]
        career = _init_career(set(players))

        # Game 1: A makes bid 3, B bids 0
        rounds1 = [self._make_round({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10})]
        game1 = FakeGame(1, players, {"rounds_per_set": 8})
        _process_game_for_career(game1, {1: rounds1}, career)

        # Game 2: A makes bid 2, B bids 0
        rounds2 = [self._make_round({"0": 2, "1": 0}, {"0": 2, "1": 0}, {"0": 20, "1": 10})]
        game2 = FakeGame(2, players, {"rounds_per_set": 8})
        _process_game_for_career(game2, {2: rounds2}, career)

        # A should have accumulated: total_rounds=2, games_won=2, biggest_bid=3
        assert career["A"]["total_rounds_played"] == 2
        assert career["A"]["games_won"] == 2
        assert career["A"]["biggest_bid_made"] == 3  # max across games, not sum

        # B: total_rounds=2
        assert career["B"]["total_rounds_played"] == 2


class TestPostGameCareerSweeps:
    """Test the extracted _post_game_career_sweeps helper."""

    def test_sweep_awards_sole_winner(self):

        career = _init_career({"A", "B"})
        _post_game_career_sweeps(
            ["A", "B"],
            game_totals={"A": 50, "B": 30},
            game_bids_made={"A": 2, "B": 1},
            game_bids_total={"A": 2, "B": 2},
            cumulative={"A": [20, 50], "B": [10, 30]},
            career=career,
        )
        assert career["A"]["games_won"] == 1
        assert career["B"]["games_won"] == 0

    def test_comeback_tracks_deficit_recovery(self):

        career = _init_career({"A"})
        # Was at -30 after R1, recovered to +20 at R2. Recovery = 20 - (-30) = 50
        _post_game_career_sweeps(
            ["A"],
            game_totals={"A": 20},
            game_bids_made={"A": 1},
            game_bids_total={"A": 2},
            cumulative={"A": [-30, 20]},
            career=career,
        )
        assert career["A"]["biggest_comeback"] == 50

    def test_triple_crown_requires_sole_leader_both(self):

        career = _init_career({"A", "B"})
        _post_game_career_sweeps(
            ["A", "B"],
            game_totals={"A": 50, "B": 30},
            game_bids_made={"A": 2, "B": 1},
            game_bids_total={"A": 2, "B": 2},
            cumulative={"A": [20, 50], "B": [10, 30]},
            career=career,
        )
        assert career["A"]["triple_crowns"] == 1
