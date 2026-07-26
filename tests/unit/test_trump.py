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
    """Cards per round: alternating sets (8→1, 1→8, 8→1, ...)."""

    def test_set_1_round_1_is_8_cards(self):
        assert get_cards_for_round(1) == 8

    def test_set_1_round_8_is_1_card(self):
        assert get_cards_for_round(8) == 1

    def test_set_2_round_9_is_1_card_ascending(self):
        """Set 2 ascends: starts at 1."""
        assert get_cards_for_round(9) == 1

    def test_set_2_round_16_is_8_cards(self):
        """Set 2 ascends: ends at 8."""
        assert get_cards_for_round(16) == 8

    def test_set_3_round_17_is_8_cards_descending(self):
        """Set 3 descends again: starts at 8."""
        assert get_cards_for_round(17) == 8

    def test_full_set_1_sequence(self):
        """Set 1 (odd) = 8,7,6,5,4,3,2,1."""
        expected = [8, 7, 6, 5, 4, 3, 2, 1]
        actual = [get_cards_for_round(r) for r in range(1, 9)]
        assert actual == expected

    def test_full_set_2_sequence(self):
        """Set 2 (even) = 1,2,3,4,5,6,7,8."""
        expected = [1, 2, 3, 4, 5, 6, 7, 8]
        actual = [get_cards_for_round(r) for r in range(9, 17)]
        assert actual == expected

    def test_three_sets_sequence(self):
        """3 sets = 8→1, 1→8, 8→1."""
        set_desc = [8, 7, 6, 5, 4, 3, 2, 1]
        set_asc = [1, 2, 3, 4, 5, 6, 7, 8]
        expected = set_desc + set_asc + set_desc
        actual = [get_cards_for_round(r) for r in range(1, 25)]
        assert actual == expected

    def test_custom_rounds_per_set(self):
        """Support custom set sizes (e.g., 5 rounds per set: 5,4,3,2,1 then 1,2,3,4,5)."""
        expected_set1 = [5, 4, 3, 2, 1]
        actual_set1 = [get_cards_for_round(r, rounds_per_set=5) for r in range(1, 6)]
        assert actual_set1 == expected_set1
        expected_set2 = [1, 2, 3, 4, 5]
        actual_set2 = [get_cards_for_round(r, rounds_per_set=5) for r in range(6, 11)]
        assert actual_set2 == expected_set2
