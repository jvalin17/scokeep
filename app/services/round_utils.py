"""Shared round-level utilities used by analytics, game_titles, and insights."""


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


def determine_winner(players: list[str], rounds: list) -> str | None:
    """Determine the sole winner from round scores. Returns None on tie or no data."""
    if not rounds:
        return None
    totals: dict[str, int] = dict.fromkeys(players, 0)
    for rnd in rounds:
        for idx_str, score in rnd.scores.items():
            idx = int(idx_str)
            if idx < len(players):
                totals[players[idx]] += score
    if not totals:
        return None
    top_score = max(totals.values())
    leaders = [n for n, s in totals.items() if s == top_score]
    return leaders[0] if len(leaders) == 1 else None
