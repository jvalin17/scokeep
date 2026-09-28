"""The Podium — per-game place points with margin, career standing averages.

Base: place p of N gets (N - p + 1) — last earns 1, never 0.
Margin: adjacent score gaps share MARGIN_SCALE points by gap/span.
"""

from __future__ import annotations

MARGIN_SCALE = 3.0


def init_podium_player() -> dict:
    return {
        "points_sum": 0.0,
        "game_count": 0,
        "places": {},  # str(place) -> count
    }


def place_points(totals_by_index: dict[str, int], player_names: list[str]) -> dict[str, float]:
    """Compute podium points for one finished game.

    totals_by_index: {"0": score, "1": score, ...} keyed by seat index string.
    player_names: roster in seat order.
    """
    num_players = len(player_names)
    if num_players == 0:
        return {}

    ranked_indices = sorted(
        range(num_players),
        key=lambda index: (-int(totals_by_index.get(str(index), 0)), index),
    )
    scores = [int(totals_by_index.get(str(index), 0)) for index in ranked_indices]
    span = max(scores) - min(scores) if scores else 0

    points = dict.fromkeys(player_names, 0.0)
    for place, index in enumerate(ranked_indices, start=1):
        name = player_names[index]
        points[name] = float(num_players - place + 1)

    if span > 0:
        for position in range(num_players - 1):
            better_index = ranked_indices[position]
            gap = scores[position] - scores[position + 1]
            if gap <= 0:
                continue
            bonus = (gap / span) * MARGIN_SCALE
            points[player_names[better_index]] += bonus

    return points


def places_from_totals(totals_by_index: dict[str, int], player_names: list[str]) -> dict[str, int]:
    """Map player name → finish place (1 = best)."""
    num_players = len(player_names)
    ranked_indices = sorted(
        range(num_players),
        key=lambda index: (-int(totals_by_index.get(str(index), 0)), index),
    )
    return {player_names[index]: place for place, index in enumerate(ranked_indices, start=1)}


def record_game(
    podium: dict[str, dict],
    totals_by_index: dict[str, int],
    player_names: list[str],
) -> None:
    """Score one finished game into the podium accumulators."""
    points = place_points(totals_by_index, player_names)
    places = places_from_totals(totals_by_index, player_names)
    accumulate_podium(podium, points, player_names, places)


def accumulate_podium(
    podium: dict[str, dict],
    points: dict[str, float],
    player_names: list[str],
    places: dict[str, int],
) -> None:
    """Add one game's points/places into career podium accumulators."""
    for name in player_names:
        if name not in podium:
            podium[name] = init_podium_player()
        entry = podium[name]
        entry["points_sum"] += float(points.get(name, 0.0))
        entry["game_count"] += 1
        place = places.get(name)
        if place is not None:
            key = str(place)
            entry["places"][key] = entry["places"].get(key, 0) + 1


def build_podium_table(podium: dict[str, dict]) -> list[dict]:
    """Sorted standing board: highest average first."""
    rows = []
    for player, entry in podium.items():
        games = entry["game_count"]
        if games < 1:
            continue
        standing = round(entry["points_sum"] / games, 2)
        places = {int(k): v for k, v in entry["places"].items()}
        rows.append(
            {
                "player": player,
                "standing": standing,
                "games_count": games,
                "places": places,
            }
        )
    rows.sort(key=lambda row: (-row["standing"], -row["games_count"], row["player"]))
    return rows
