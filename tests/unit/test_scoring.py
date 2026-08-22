"""Tests for kachuful scoring engine.

Every branch of the scoring formula is tested:
- Bid 0 made/missed
- Bid 1 made/missed
- Bid N (2-8) made/missed
- Full round scoring (all players at once)
- Full game simulation with hand-calculated expected values
"""

import pytest

from app.services.scoring import (
    calculate_round_scores,
    kachuful_standard,
    kachuful_zeros,
)


class TestKachufulStandardSinglePlayer:
    """Each case tests one branch of the scoring formula."""

    def test_bid_zero_made(self):
        assert kachuful_standard(bid=0, actual=0) == 10

    def test_bid_zero_missed(self):
        assert kachuful_standard(bid=0, actual=2) == -10

    def test_bid_one_made(self):
        assert kachuful_standard(bid=1, actual=1) == 11

    def test_bid_one_missed_over(self):
        assert kachuful_standard(bid=1, actual=3) == -11

    def test_bid_one_missed_under(self):
        assert kachuful_standard(bid=1, actual=0) == -11

    def test_bid_two_made(self):
        assert kachuful_standard(bid=2, actual=2) == 20

    def test_bid_two_missed(self):
        assert kachuful_standard(bid=2, actual=1) == -20

    def test_bid_five_made(self):
        assert kachuful_standard(bid=5, actual=5) == 50

    def test_bid_five_missed(self):
        assert kachuful_standard(bid=5, actual=3) == -50

    def test_bid_eight_made(self):
        assert kachuful_standard(bid=8, actual=8) == 80

    def test_bid_eight_missed(self):
        assert kachuful_standard(bid=8, actual=7) == -80


class TestKachufulZerosSinglePlayer:
    """Zeros mode: bid 1 made = 10 (not 11). Bid 0 same as standard."""

    def test_bid_zero_made(self):
        assert kachuful_zeros(bid=0, actual=0) == 10

    def test_bid_zero_missed(self):
        assert kachuful_zeros(bid=0, actual=2) == -10

    def test_bid_one_made_scores_10_not_11(self):
        """Key difference: bid 1 made = 10, not 11."""
        assert kachuful_zeros(bid=1, actual=1) == 10

    def test_bid_one_missed(self):
        assert kachuful_zeros(bid=1, actual=0) == -10

    def test_bid_two_made(self):
        assert kachuful_zeros(bid=2, actual=2) == 20

    def test_bid_two_missed(self):
        assert kachuful_zeros(bid=2, actual=1) == -20

    def test_bid_five_made(self):
        assert kachuful_zeros(bid=5, actual=5) == 50

    def test_bid_eight_made(self):
        assert kachuful_zeros(bid=8, actual=8) == 80


class TestZerosRoundScoring:
    """Full round scoring with zeros formula."""

    def test_zeros_formula_via_calculate(self):
        bids = {"0": 2, "1": 0, "2": 1, "3": 1}
        hands_won = {"0": 2, "1": 0, "2": 1, "3": 0}
        scores = calculate_round_scores(bids, hands_won, "kachuful_zeros")
        # bid 2 made=20, bid 0 made=10, bid 1 made=10 (not 11!), bid 1 miss=-10
        assert scores == {"0": 20, "1": 10, "2": 10, "3": -10}


class TestCalculateRoundScores:
    """Tests for scoring all players in a round."""

    def test_four_players_mixed_results(self):
        bids = {"0": 2, "1": 0, "2": 3, "3": 1}
        hands_won = {"0": 2, "1": 0, "2": 1, "3": 1}
        scores = calculate_round_scores(bids, hands_won, "kachuful_standard")

        assert scores == {"0": 20, "1": 10, "2": -30, "3": 11}

    def test_all_players_make_their_bids(self):
        bids = {"0": 3, "1": 2, "2": 1}
        hands_won = {"0": 3, "1": 2, "2": 1}
        scores = calculate_round_scores(bids, hands_won, "kachuful_standard")

        assert scores == {"0": 30, "1": 20, "2": 11}

    def test_all_players_miss(self):
        bids = {"0": 3, "1": 0, "2": 2}
        hands_won = {"0": 1, "1": 2, "2": 0}
        scores = calculate_round_scores(bids, hands_won, "kachuful_standard")

        assert scores == {"0": -30, "1": -10, "2": -20}

    def test_unknown_formula_raises(self):
        with pytest.raises(ValueError, match="Unknown scoring formula"):
            calculate_round_scores({"0": 1}, {"0": 1}, "nonexistent")


class TestFullGameSimulation:
    """Simulate a 1-set game (8 rounds) with 4 players.

    Hand-calculated expected scores verified manually.
    All values are synthetic (factory) — designed to cover all formula branches.
    """

    GAME_DATA = [
        # (round, bids, hands_won, expected_round_scores, expected_cumulative)
        (
            1,
            {"0": 2, "1": 0, "2": 1, "3": 3},
            {"0": 2, "1": 0, "2": 1, "3": 3},
            {"0": 20, "1": 10, "2": 11, "3": 30},
            {"0": 20, "1": 10, "2": 11, "3": 30},
        ),
        (
            2,
            {"0": 0, "1": 3, "2": 2, "3": 0},
            {"0": 1, "1": 3, "2": 2, "3": 0},
            {"0": -10, "1": 30, "2": 20, "3": 10},
            {"0": 10, "1": 40, "2": 31, "3": 40},
        ),
        (
            3,
            {"0": 1, "1": 1, "2": 0, "3": 2},
            {"0": 1, "1": 0, "2": 0, "3": 2},
            {"0": 11, "1": -11, "2": 10, "3": 20},
            {"0": 21, "1": 29, "2": 41, "3": 60},
        ),
        (
            4,
            {"0": 0, "1": 0, "2": 0, "3": 5},
            {"0": 0, "1": 0, "2": 0, "3": 5},
            {"0": 10, "1": 10, "2": 10, "3": 50},
            {"0": 31, "1": 39, "2": 51, "3": 110},
        ),
        (
            5,
            {"0": 1, "1": 2, "2": 0, "3": 1},
            {"0": 0, "1": 2, "2": 1, "3": 1},
            {"0": -11, "1": 20, "2": -10, "3": 11},
            {"0": 20, "1": 59, "2": 41, "3": 121},
        ),
        (
            6,
            {"0": 0, "1": 1, "2": 1, "3": 0},
            {"0": 0, "1": 1, "2": 0, "3": 1},
            {"0": 10, "1": 11, "2": -11, "3": -10},
            {"0": 30, "1": 70, "2": 30, "3": 111},
        ),
        (
            7,
            {"0": 1, "1": 0, "2": 0, "3": 1},
            {"0": 1, "1": 0, "2": 0, "3": 1},
            {"0": 11, "1": 10, "2": 10, "3": 11},
            {"0": 41, "1": 80, "2": 40, "3": 122},
        ),
        (
            8,
            {"0": 0, "1": 0, "2": 0, "3": 1},
            {"0": 0, "1": 0, "2": 0, "3": 1},
            {"0": 10, "1": 10, "2": 10, "3": 11},
            {"0": 51, "1": 90, "2": 50, "3": 133},
        ),
    ]

    def test_round_scores_match_hand_calculated(self):
        for round_num, bids, hands_won, expected_scores, _ in self.GAME_DATA:
            scores = calculate_round_scores(bids, hands_won, "kachuful_standard")
            assert scores == expected_scores, f"Round {round_num} scores wrong"

    def test_cumulative_scores_match_hand_calculated(self):
        cumulative = {"0": 0, "1": 0, "2": 0, "3": 0}
        for round_num, bids, hands_won, _, expected_cumulative in self.GAME_DATA:
            round_scores = calculate_round_scores(bids, hands_won, "kachuful_standard")
            for player_index in cumulative:
                cumulative[player_index] += round_scores[player_index]
            assert cumulative == expected_cumulative, f"Cumulative after round {round_num} wrong"

    def test_final_winner_is_player_3(self):
        """Player 3 should win with 133 points."""
        cumulative = {"0": 0, "1": 0, "2": 0, "3": 0}
        for _, bids, hands_won, _, _ in self.GAME_DATA:
            round_scores = calculate_round_scores(bids, hands_won, "kachuful_standard")
            for player_index in cumulative:
                cumulative[player_index] += round_scores[player_index]

        winner = max(cumulative, key=cumulative.get)
        assert winner == "3"
        assert cumulative["3"] == 133
