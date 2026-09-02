"""Shared round-level utilities used by analytics and game_titles."""


def _iter_round_bids(players, game_rounds):
    """Yield (name, bid, hand, score, rnd) for each valid player bid."""
    for rnd in game_rounds:
        for idx_str in rnd.bids:
            idx = int(idx_str)
            if idx >= len(players):
                continue
            bid = rnd.bids.get(idx_str)
            hand = rnd.hands_won.get(idx_str)
            if bid is None or hand is None:
                continue
            score = rnd.scores.get(idx_str, 0)
            yield players[idx], bid, hand, score, rnd
