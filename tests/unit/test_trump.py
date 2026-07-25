"""Tests for trump rotation and cards-per-round utilities.

Fixtures are synthetic — designed to cover rotation boundaries and multi-set games.
"""

from app.utils.trump import TRUMP_ORDER, get_cards_for_round, get_trump_for_round


class TestGetTrumpForRound:
    """Trump rotates: spades → diamonds → clubs → hearts, repeating."""

    def test_round_1_is_spades(self):
        assert get_trump_for_round(1) == "spades"

    def test_round_2_is_diamonds(self):
        assert get_trump_for_round(2) == "diamonds"

    def test_round_3_is_clubs(self):
        assert get_trump_for_round(3) == "clubs"

    def test_round_4_is_hearts(self):
        assert get_trump_for_round(4) == "hearts"

    def test_round_5_wraps_to_spades(self):
        assert get_trump_for_round(5) == "spades"

    def test_full_24_round_rotation(self):
        """3 sets × 8 rounds = 24 rounds. Trump repeats every 4."""
        expected = TRUMP_ORDER * 6  # 4 suits × 6 = 24
        actual = [get_trump_for_round(r) for r in range(1, 25)]
        assert actual == expected


class TestGetCardsForRound:
    """Cards per round: 8,7,6,5,4,3,2,1 per set."""

    def test_set_1_round_1_is_8_cards(self):
        assert get_cards_for_round(1) == 8

    def test_set_1_round_8_is_1_card(self):
        assert get_cards_for_round(8) == 1

    def test_set_2_round_9_resets_to_8(self):
        assert get_cards_for_round(9) == 8

    def test_set_2_round_16_is_1_card(self):
        assert get_cards_for_round(16) == 1

    def test_full_set_sequence(self):
        """One set = 8,7,6,5,4,3,2,1."""
        expected = [8, 7, 6, 5, 4, 3, 2, 1]
        actual = [get_cards_for_round(r) for r in range(1, 9)]
        assert actual == expected

    def test_three_sets_sequence(self):
        """3 sets = 24 rounds, pattern repeats."""
        one_set = [8, 7, 6, 5, 4, 3, 2, 1]
        expected = one_set * 3
        actual = [get_cards_for_round(r) for r in range(1, 25)]
        assert actual == expected

    def test_custom_rounds_per_set(self):
        """Support custom set sizes (e.g., 5 rounds per set: 5,4,3,2,1)."""
        expected = [5, 4, 3, 2, 1]
        actual = [get_cards_for_round(r, rounds_per_set=5) for r in range(1, 6)]
        assert actual == expected
