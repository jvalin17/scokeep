"""Pluggable scoring engine for card games.

Each formula takes a bid and actual hands won, returns points.
Formulas are registered in SCORING_FORMULAS dict.
"""


def kachuful_standard(bid: int, actual: int) -> int:
    """Kachuful standard scoring.

    Bid 0 made = 10, Bid 1 made = 11, Bid N≥2 made = N×10.
    Miss = same value negated.
    """
    if bid == actual:
        if bid == 0:
            return 10
        elif bid == 1:
            return 11
        else:
            return bid * 10
    else:
        if bid == 0:
            return -10
        elif bid == 1:
            return -11
        else:
            return -(bid * 10)


def kachuful_zeros(bid: int, actual: int) -> int:
    """Kachuful zeros scoring.

    Same as standard but bid 1 made = 10 (not 11).
    Bid 0 and 1 are treated equally: made = 10, missed = -10.
    Bid N≥2 made = N×10, missed = -(N×10).
    """
    if bid == actual:
        if bid <= 1:
            return 10
        return bid * 10
    else:
        if bid <= 1:
            return -10
        return -(bid * 10)


SCORING_FORMULAS = {
    "kachuful_standard": kachuful_standard,
    "kachuful_zeros": kachuful_zeros,
}


def calculate_round_scores(
    bids: dict[str, int],
    hands_won: dict[str, int],
    formula_name: str,
) -> dict[str, int]:
    """Calculate scores for all players in a round."""
    if formula_name not in SCORING_FORMULAS:
        raise ValueError(f"Unknown scoring formula: {formula_name}")

    formula = SCORING_FORMULAS[formula_name]
    return {
        player_index: formula(bid=bids[player_index], actual=hands_won[player_index])
        for player_index in bids
    }
