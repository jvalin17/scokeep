"""Trump rotation and round sequence utilities."""

TRUMP_ORDER = ["spades", "diamonds", "clubs", "hearts"]
ROUNDS_PER_SET = 8


def get_trump_for_round(round_num: int) -> str:
    """Get trump suit for a given round number (1-based)."""
    return TRUMP_ORDER[(round_num - 1) % len(TRUMP_ORDER)]


def get_cards_for_round(round_num: int, rounds_per_set: int = ROUNDS_PER_SET) -> int:
    """Get number of cards dealt for a given round.

    Pattern: 8,7,6,5,4,3,2,1 repeating per set.
    """
    position_in_set = (round_num - 1) % rounds_per_set
    return rounds_per_set - position_in_set
