"""Shared test fixtures for unit tests."""


class MockRound:
    """Mock round object for testing game logic without a database."""

    def __init__(self, bids, hands_won, scores, cards_dealt=8, trump_suit="spades"):
        self.bids = bids
        self.hands_won = hands_won
        self.scores = scores
        self.cards_dealt = cards_dealt
        self.trump_suit = trump_suit
