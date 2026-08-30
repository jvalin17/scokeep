"""Shared MockRound factories and edge-case datasets for guard tests."""


class MockRound:
    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit=None):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit


def make_round(bids, hands, scores, cards_dealt=8, trump_suit=None):
    return MockRound(bids, hands, scores, cards_dealt, trump_suit)


PLAYERS_2 = ["Alice", "Bob"]
PLAYERS_4 = ["Alice", "Bob", "Charlie", "Diana"]
PLAYERS_8 = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]


def empty_rounds():
    return []


def full_game_4p():
    """4-player, 8-round game with diverse outcomes."""
    return [
        make_round(
            {"0": 2, "1": 0, "2": 1, "3": 3},
            {"0": 2, "1": 0, "2": 1, "3": 3},
            {"0": 20, "1": 10, "2": 11, "3": 30},
            8,
            "spades",
        ),
        make_round(
            {"0": 0, "1": 3, "2": 2, "3": 0},
            {"0": 1, "1": 3, "2": 2, "3": 0},
            {"0": -10, "1": 30, "2": 20, "3": 10},
            7,
            "hearts",
        ),
        make_round(
            {"0": 1, "1": 1, "2": 0, "3": 2},
            {"0": 1, "1": 0, "2": 0, "3": 2},
            {"0": 11, "1": -11, "2": 10, "3": 20},
            6,
            "diamonds",
        ),
        make_round(
            {"0": 0, "1": 0, "2": 0, "3": 5},
            {"0": 0, "1": 0, "2": 0, "3": 5},
            {"0": 10, "1": 10, "2": 10, "3": 50},
            5,
            "clubs",
        ),
        make_round(
            {"0": 1, "1": 2, "2": 0, "3": 1},
            {"0": 0, "1": 2, "2": 1, "3": 1},
            {"0": -11, "1": 20, "2": -10, "3": 11},
            4,
            "spades",
        ),
        make_round(
            {"0": 0, "1": 1, "2": 1, "3": 0},
            {"0": 0, "1": 1, "2": 0, "3": 1},
            {"0": 10, "1": 11, "2": -11, "3": -10},
            3,
            "hearts",
        ),
        make_round(
            {"0": 1, "1": 0, "2": 0, "3": 1},
            {"0": 1, "1": 0, "2": 0, "3": 1},
            {"0": 11, "1": 10, "2": 10, "3": 11},
            2,
            "diamonds",
        ),
        make_round(
            {"0": 0, "1": 0, "2": 0, "3": 1},
            {"0": 0, "1": 0, "2": 0, "3": 1},
            {"0": 10, "1": 10, "2": 10, "3": 11},
            1,
            "clubs",
        ),
    ]


def all_missed_game():
    """Every player misses every bid."""
    return [
        make_round(
            {"0": 3, "1": 0, "2": 2, "3": 1},
            {"0": 1, "1": 2, "2": 0, "3": 5},
            {"0": -30, "1": -10, "2": -20, "3": -10},
            8,
        ),
        make_round(
            {"0": 0, "1": 3, "2": 1, "3": 2},
            {"0": 2, "1": 1, "2": 3, "3": 1},
            {"0": -10, "1": -30, "2": -11, "3": -20},
            7,
        ),
    ]


def eight_player_game():
    """8 players, 3 rounds."""
    return [
        make_round(
            {str(i): i % 3 for i in range(8)},
            {str(i): i % 3 for i in range(8)},
            {str(i): (i % 3) * 10 + (1 if i % 3 == 1 else 0) for i in range(8)},
            8,
        ),
        make_round(
            {str(i): (i + 1) % 4 for i in range(8)},
            {str(i): (i + 1) % 4 for i in range(8)},
            {str(i): ((i + 1) % 4) * 10 + (1 if (i + 1) % 4 == 1 else 0) for i in range(8)},
            7,
        ),
        make_round(
            {str(i): i % 2 for i in range(8)},
            {str(i): i % 2 for i in range(8)},
            {str(i): 10 + (i % 2) for i in range(8)},
            6,
        ),
    ]
