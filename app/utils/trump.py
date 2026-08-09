"""Trump rotation and round sequence utilities."""

TRUMP_ORDER = ["spades", "diamonds", "clubs", "hearts"]
ROUNDS_PER_SET = 8
DECK_SIZE = 52


def max_cards_for_players(player_count: int) -> int:
    """Max cards per round = floor(deck_size / players)."""
    return DECK_SIZE // player_count


def get_trump_for_round(round_num: int) -> str:
    """Get trump suit for a given round number (1-based)."""
    return TRUMP_ORDER[(round_num - 1) % len(TRUMP_ORDER)]


def get_cards_for_round(round_num: int, rounds_per_set: int = ROUNDS_PER_SET) -> int:
    """Get number of cards dealt for a given round.

    Pattern alternates: odd sets descend (8→1), even sets ascend (1→8).
    """
    position_in_set = (round_num - 1) % rounds_per_set
    set_number = (round_num - 1) // rounds_per_set  # 0-based
    if set_number % 2 == 0:
        # Odd sets (1st, 3rd, ...): descend 8→1
        return rounds_per_set - position_in_set
    else:
        # Even sets (2nd, 4th, ...): ascend 1→8
        return position_in_set + 1
