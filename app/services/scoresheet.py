"""Scoresheet scoring helpers — direct per-player scores (no bids/trump).

Used by unit vectors now; wired into round/API slabs later.
"""

from __future__ import annotations


def apply_round(totals: dict[str, int], round_scores: dict[str, int]) -> dict[str, int]:
    """Return new totals after adding one completed round's per-player scores."""
    updated = dict(totals)
    for name, score in round_scores.items():
        updated[name] = updated.get(name, 0) + int(score)
    return updated


def scores_dict_for_players(
    players: list[str], scores_by_index: dict[str, int] | dict[int, int]
) -> dict[str, int]:
    """Map player-index scores to display-name keys for ranking helpers."""
    named: dict[str, int] = {}
    for index, name in enumerate(players):
        key = str(index)
        if key in scores_by_index:
            named[name] = int(scores_by_index[key])
        elif index in scores_by_index:
            named[name] = int(scores_by_index[index])
    return named


def undo_round(totals: dict[str, int], round_scores: dict[str, int]) -> dict[str, int]:
    """Roll back one completed round from cumulative totals."""
    updated = dict(totals)
    for name, score in round_scores.items():
        updated[name] = updated.get(name, 0) - int(score)
    return updated


def rank_players(totals: dict[str, int], *, lowest_wins: bool = False) -> list[str]:
    """Order player names by total. Highest first unless lowest_wins."""
    return sorted(
        totals.keys(),
        key=lambda name: totals[name],
        reverse=not lowest_wins,
    )
