"""Unit tests for analytics — career rules, awards, highlights caching."""


from app.services.analytics import (
    CAREER_RULES,
    _accumulate_game_stats,
    _best_player,
    _build_awards,
    _career_table,
    _iter_round_bids,
)


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
        rounds = [self._make_round(
            {"0": 2, "1": 3}, {"0": 2, "1": 1}, {"0": 20, "1": -30},
        )]
        results = list(_iter_round_bids(["Ravi", "Meera"], rounds))
        assert len(results) == 2
        assert results[0] == ("Ravi", 2, 2, 20, rounds[0])
        assert results[1] == ("Meera", 3, 1, -30, rounds[0])

    def test_skips_out_of_range_index(self):
        rounds = [self._make_round(
            {"0": 2, "5": 3}, {"0": 2, "5": 3}, {"0": 20, "5": 30},
        )]
        results = list(_iter_round_bids(["Ravi"], rounds))
        assert len(results) == 1
        assert results[0][0] == "Ravi"

    def test_skips_none_bid_or_hand(self):
        rounds = [self._make_round(
            {"0": None}, {"0": 2}, {"0": 20},
        )]
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
                {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30},
            ),
            self._make_round(
                {"0": 1, "1": 4}, {"0": 1, "1": 2}, {"0": 11, "1": -40},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["totals"]["Ravi"] == 31
        assert stats["totals"]["Meera"] == -10

    def test_overbid_underbid_counted(self):
        rounds = [
            self._make_round(
                {"0": 5, "1": 1}, {"0": 2, "1": 3}, {"0": -50, "1": -10},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["overbids"]["Ravi"] == 1
        assert stats["underbids"]["Meera"] == 1

    def test_zero_bids_tracked(self):
        rounds = [
            self._make_round(
                {"0": 0, "1": 5}, {"0": 0, "1": 5}, {"0": 10, "1": 50},
            ),
        ]
        stats = _accumulate_game_stats(["Ravi", "Meera"], rounds)
        assert stats["zero_bids_made"]["Ravi"] == 1
        assert stats["zero_bids_made"]["Meera"] == 0

    def test_best_bid_tracked(self):
        rounds = [
            self._make_round(
                {"0": 5, "1": 2}, {"0": 5, "1": 2}, {"0": 50, "1": 20},
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
            "mvp", "sharpshooter", "brick_wall", "bold_move",
            "cursed", "sandbagger", "gambler",
        }
        assert set(awards.keys()) == expected_keys
