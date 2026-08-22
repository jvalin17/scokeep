"""Player insights orchestrator — computes and stores personality insights.

Coordinates feature extraction, personality assignment, and storage.
Algorithm details: see architecture/player-insights.md.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.playground import Playground
from app.models.round import Round
from app.services.feature_extractor import (
    CARD_COUNT_WEIGHTS,
    FEATURE_DIMENSIONS,
    compute_accuracy_by_cards,
    compute_feature_vector,
    compute_player_extras,
)
from app.services.personality_engine import (
    EMA_ALPHA,
    GROWTH_TEMPLATES,
    MIN_CONFIDENCE_GAP,
    PERSONALITY_CENTROIDS,
    PERSONALITY_META,
    STRENGTH_TEMPLATES,
    assign_personalities_unique,
    assign_personality,
    cosine_similarity,
    ema_update,
    generate_insights,
    james_stein_shrink,
    min_max_normalize,
)

# Minimum games before personality is assigned
MIN_GAMES_FOR_PERSONALITY = 3

# Re-export for backward compatibility with tests
__all__ = [
    "CARD_COUNT_WEIGHTS",
    "EMA_ALPHA",
    "FEATURE_DIMENSIONS",
    "GROWTH_TEMPLATES",
    "MIN_CONFIDENCE_GAP",
    "MIN_GAMES_FOR_PERSONALITY",
    "PERSONALITY_CENTROIDS",
    "PERSONALITY_META",
    "STRENGTH_TEMPLATES",
    "assign_personalities_unique",
    "assign_personality",
    "compute_accuracy_by_cards",
    "backfill_meta",
    "compute_feature_vector",
    "compute_insights",
    "compute_player_extras",
    "cosine_similarity",
    "ema_update",
    "generate_insights",
    "james_stein_shrink",
    "min_max_normalize",
]


def backfill_meta(insights_blob: dict | None) -> dict | None:
    """Add personality meta to cached blobs that lack it."""
    if not insights_blob:
        return insights_blob
    for data in insights_blob.get("players", {}).values():
        if data.get("personality") and "meta" not in data:
            data["meta"] = PERSONALITY_META.get(data["personality"], {})
    return insights_blob


class _GameWithRounds:
    """Lightweight game wrapper that carries pre-loaded rounds."""

    def __init__(self, game, rounds):
        self.players = game.players
        self.winner = self._determine_winner(game.players, rounds)
        self.rounds = rounds

    @staticmethod
    def _determine_winner(players, rounds):
        totals = dict.fromkeys(players, 0)
        for rnd in rounds:
            for idx_str, score in rnd.scores.items():
                idx = int(idx_str)
                if idx < len(players):
                    totals[players[idx]] += score
        return max(totals, key=lambda n: totals[n]) if totals else None


async def compute_insights(db: AsyncSession, playground_id: int) -> dict | None:
    """Full pipeline: compute and store insights for all players."""
    playground = await db.get(Playground, playground_id)
    if not playground:
        return None

    games, rounds_by_game = await _load_game_data(db, playground_id)
    if not games:
        return None

    wrapped_games = [_GameWithRounds(g, rounds_by_game.get(g.id, [])) for g in games]

    player_game_counts = _count_player_games(wrapped_games)
    all_players = set(player_game_counts.keys())
    existing_players = (playground.insights or {}).get("players", {})

    raw_vectors = _compute_raw_vectors(all_players, player_game_counts, wrapped_games)
    if not raw_vectors:
        return await _store_unlock_only(db, playground, all_players, player_game_counts)

    insights_blob = _assemble_blob(
        raw_vectors,
        player_game_counts,
        existing_players,
        all_players,
        wrapped_games,
        games,
        rounds_by_game,
    )
    playground.insights = insights_blob
    await db.commit()
    return insights_blob


def _compute_raw_vectors(all_players, player_game_counts, wrapped_games):
    """Compute feature vectors for players with enough games."""
    return {
        name: compute_feature_vector(name, wrapped_games)
        for name in all_players
        if player_game_counts[name] >= MIN_GAMES_FOR_PERSONALITY
    }


def _assemble_blob(
    raw_vectors,
    player_game_counts,
    existing_players,
    all_players,
    wrapped_games,
    games,
    rounds_by_game,
):
    """Build the full insights blob from vectors and assignments."""
    smoothed_vectors = _normalize_shrink_smooth(
        raw_vectors,
        player_game_counts,
        existing_players,
    )
    assignments = assign_personalities_unique(smoothed_vectors)
    players_data = _build_player_data(
        all_players,
        player_game_counts,
        assignments,
        smoothed_vectors,
        existing_players,
        wrapped_games,
    )
    return {
        "version": 1,
        "computed_at": datetime.now(UTC).isoformat(),
        "players": players_data,
        "highlights": _compute_cached_highlights(games, rounds_by_game),
        "total_games": len(games),
    }


async def _load_game_data(db: AsyncSession, playground_id: int):
    """Load all finished games and their scored rounds."""
    games_result = await db.execute(
        select(Game)
        .where(Game.playground_id == playground_id, Game.status == "finished")
        .order_by(Game.started_at)
    )
    games = list(games_result.scalars().all())
    if not games:
        return [], {}

    game_ids = [g.id for g in games]
    rounds_result = await db.execute(
        select(Round)
        .where(Round.game_id.in_(game_ids), Round.status == "scored")
        .order_by(Round.game_id, Round.round_num)
    )
    rounds_by_game: dict[int, list] = {}
    for rnd in rounds_result.scalars().all():
        rounds_by_game.setdefault(rnd.game_id, []).append(rnd)

    return games, rounds_by_game


def _count_player_games(games: list) -> dict[str, int]:
    """Count games played per player across all games."""
    counts: dict[str, int] = {}
    for game in games:
        for name in game.players:
            counts[name] = counts.get(name, 0) + 1
    return counts


def _normalize_shrink_smooth(
    raw_vectors: dict[str, list[float]],
    player_game_counts: dict[str, int],
    existing_players: dict,
) -> dict[str, list[float]]:
    """Pipeline: min-max normalize → James-Stein shrink → EMA smooth."""
    normalized = min_max_normalize(raw_vectors)

    num_dims = len(FEATURE_DIMENSIONS)
    population_mean = [0.0] * num_dims
    for vec in normalized.values():
        for i in range(num_dims):
            population_mean[i] += vec[i]
    for i in range(num_dims):
        population_mean[i] /= len(normalized)

    smoothed = {}
    for name, norm_vec in normalized.items():
        shrunk = james_stein_shrink(
            norm_vec,
            population_mean,
            player_game_counts[name],
        )
        stored = None
        if name in existing_players and existing_players[name].get("feature_vector"):
            stored = existing_players[name]["feature_vector"]
        smoothed[name] = ema_update(shrunk, stored)

    return smoothed


async def _store_unlock_only(db, playground, all_players, player_game_counts):
    """Store unlock progress for players without enough games."""
    players_data = {
        name: {
            "personality": None,
            "games_analyzed": player_game_counts.get(name, 0),
            "unlock_at": MIN_GAMES_FOR_PERSONALITY,
        }
        for name in all_players
    }
    insights_blob = {
        "version": 1,
        "computed_at": datetime.now(UTC).isoformat(),
        "players": players_data,
    }
    playground.insights = insights_blob
    await db.commit()
    return insights_blob


def _build_player_data(
    all_players,
    player_game_counts,
    assignments,
    smoothed_vectors,
    existing_players,
    games,
):
    """Build the full player data dict for the insights blob."""
    return {
        name: _build_single_player(
            name,
            player_game_counts.get(name, 0),
            assignments,
            smoothed_vectors,
            existing_players,
            games,
        )
        for name in all_players
    }


def _build_single_player(
    name,
    games_played,
    assignments,
    smoothed_vectors,
    existing_players,
    games,
):
    """Build data for one player — either unlock progress or full insights."""
    if games_played < MIN_GAMES_FOR_PERSONALITY:
        return {
            "personality": None,
            "games_analyzed": games_played,
            "unlock_at": MIN_GAMES_FOR_PERSONALITY,
        }

    assignment = assignments[name]
    previous = _detect_evolution(name, assignment, existing_players)
    assigned_at = _resolve_assigned_at(name, assignment, existing_players)

    personality_key = assignment["personality"]
    meta = PERSONALITY_META.get(personality_key, {})

    return {
        "personality": personality_key,
        "meta": meta,
        "previous_personality": previous,
        "confidence": assignment["confidence"],
        "confidence_gap": assignment["confidence_gap"],
        "feature_vector": [round(v, 4) for v in smoothed_vectors[name]],
        "accuracy_by_cards": compute_accuracy_by_cards(name, games),
        "insights": generate_insights(smoothed_vectors[name], assignment["personality"]),
        "extras": compute_player_extras(name, games),
        "games_analyzed": games_played,
        "assigned_at": assigned_at,
    }


def _detect_evolution(name, assignment, existing_players):
    """Check if personality changed from previous computation."""
    if name not in existing_players:
        return None
    old = existing_players[name].get("personality")
    if old and old != assignment["personality"]:
        return old
    return None


def _resolve_assigned_at(name, assignment, existing_players):
    """Keep original assigned_at if personality unchanged."""
    if name in existing_players:
        old_data = existing_players[name]
        same = old_data.get("personality") == assignment["personality"]
        if same and old_data.get("assigned_at"):
            return old_data["assigned_at"]
    return datetime.now(UTC).isoformat()


def _compute_cached_highlights(games, rounds_by_game):
    """Compute highlights for caching in insights blob."""
    from app.services.analytics import AnalyticsService

    highlights = AnalyticsService._calc_highlights(games, rounds_by_game)
    last_game = AnalyticsService._calc_last_game_awards(
        games,
        rounds_by_game,
    )
    highlights["last_game"] = last_game
    return highlights
