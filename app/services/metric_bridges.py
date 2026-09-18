"""Bridge functions — accept game objects, convert to GameMetrics internally.

These adapt the raw game-object API (used by insights.py) to the GameMetrics API
used by the core aggregator. Also houses the accuracy-by-cards computation which
is independent of the career aggregation pipeline.
"""

from typing import Any

from app.services.metric_aggregator import (
    aggregate_career,
    compute_display_extras,
)
from app.services.metrics import compute_game_metrics


def _games_to_metrics(games: list[Any]) -> list[Any]:
    """Convert game-like objects (with .players and .rounds) to GameMetrics."""
    result = []
    for game in games:
        game_metrics = compute_game_metrics(game.players, game.rounds)
        if hasattr(game, "winner") and game.winner is not None:
            game_metrics.winner = game.winner
        result.append(game_metrics)
    return result


def compute_feature_vector(player_name: str, games: list[Any]) -> list[float]:
    """Bridge: compute 10-d feature vector from game objects."""
    return aggregate_career(player_name, _games_to_metrics(games)).feature_vector


def compute_player_extras(player_name: str, games: list[Any]) -> dict[str, Any]:
    """Bridge: compute display extras dict from game objects."""
    return compute_display_extras(player_name, _games_to_metrics(games))


def compute_accuracy_by_cards_metrics(
    player_name: str, game_metrics_list: list[Any],
) -> dict[str, dict[str, int]]:
    """Compute bid accuracy breakdown by card count from GameMetrics objects."""
    by_cards: dict[int, dict[str, int]] = {}

    for game_metrics in game_metrics_list:
        if player_name not in game_metrics.players:
            continue
        player_metrics = game_metrics.player_metrics.get(player_name)
        if player_metrics is None:
            continue

        count = min(len(player_metrics.bid_sequence), len(game_metrics.cards_per_round))
        for i in range(count):
            bid, hand = player_metrics.bid_sequence[i]
            cards = game_metrics.cards_per_round[i]
            if cards not in by_cards:
                by_cards[cards] = {"correct": 0, "total": 0}
            by_cards[cards]["total"] += 1
            if bid == hand:
                by_cards[cards]["correct"] += 1

    return {
        str(cards): {
            "pct": round(data["correct"] / data["total"] * 100) if data["total"] > 0 else 0,
            "rounds": data["total"],
        }
        for cards, data in sorted(by_cards.items())
    }


def compute_accuracy_by_cards(
    player_name: str, games: list[Any],
) -> dict[str, dict[str, int]]:
    """Bridge: compute accuracy-by-cards from game objects."""
    return compute_accuracy_by_cards_metrics(player_name, _games_to_metrics(games))
