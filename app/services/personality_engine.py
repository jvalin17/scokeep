"""Personality assignment engine — centroids, similarity, insights.

Assigns personality archetypes to players based on feature vectors using
cosine similarity to pre-defined centroids, with normalization, shrinkage,
and smoothing for stability.

Centroid calibration: see architecture/player-insights.md for rationale.
"""

import math

# EMA smoothing factor — lower = more stable, higher = more reactive
EMA_ALPHA = 0.3

# Minimum gap between top-2 centroid matches for confident assignment
MIN_CONFIDENCE_GAP = 0.1

# Pre-defined personality centroids (raw, normalized to unit length at load)
_RAW_CENTROIDS = {
    "sniper":       [1.0, 0.0, 0.0, 0.3, 0.5, 0.8, 0.8, 0.5, 0.5, 0.3],
    "gambler":      [0.3, 1.0, 0.0, 0.7, 0.1, 0.4, 0.2, 0.6, 0.4, 0.3],
    "phoenix":      [0.5, 0.3, 0.3, 0.5, 0.4, 0.5, 0.5, 0.2, 0.9, 0.6],
    "rock":         [0.6, 0.3, 0.3, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.3],
    "sprinter":     [0.5, 0.3, 0.3, 0.5, 0.4, 0.5, 0.5, 0.9, 0.2, 0.2],
    "ghost":        [0.5, 0.0, 0.3, 0.3, 1.0, 0.4, 0.5, 0.5, 0.5, 0.3],
    "architect":    [0.6, 0.3, 0.2, 0.4, 0.3, 1.0, 0.2, 0.5, 0.5, 0.3],
    "minimalist":   [0.6, 0.2, 0.3, 0.4, 0.5, 0.2, 1.0, 0.5, 0.5, 0.3],
    "comeback_kid": [0.4, 0.3, 0.3, 0.6, 0.3, 0.5, 0.5, 0.2, 0.7, 1.0],
    "wildcard":     [0.4, 0.5, 0.5, 1.0, 0.3, 0.4, 0.4, 0.5, 0.5, 0.4],
}


def _normalize_to_unit(vec: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(v ** 2 for v in vec))
    if magnitude < 1e-10:
        return vec[:]
    return [v / magnitude for v in vec]


PERSONALITY_CENTROIDS = {
    name: _normalize_to_unit(vec) for name, vec in _RAW_CENTROIDS.items()
}

# Single source of truth for personality display — served via API to frontend
PERSONALITY_META = {
    "sniper": {
        "name": "The Sniper", "tagline": "Calls the shot. Makes the shot.",
        "color": "#1B5E20", "icon": "🎯",
    },
    "gambler": {
        "name": "The Gambler", "tagline": "Goes big. Sometimes it pays off.",
        "color": "#E65100", "icon": "🎲",
    },
    "phoenix": {
        "name": "The Phoenix", "tagline": "Slow start? That's the plan.",
        "color": "#BF360C", "icon": "🔥",
    },
    "rock": {
        "name": "The Rock", "tagline": "Steady hands. No surprises.",
        "color": "#37474F", "icon": "🪨",
    },
    "sprinter": {
        "name": "The Sprinter", "tagline": "Out of the gate like lightning.",
        "color": "#0D47A1", "icon": "⚡",
    },
    "ghost": {
        "name": "The Ghost", "tagline": "Bids nothing. Wins everything.",
        "color": "#4A148C", "icon": "👻",
    },
    "architect": {
        "name": "The Architect", "tagline": "More cards, more to build.",
        "color": "#006064", "icon": "🏗️",
    },
    "minimalist": {
        "name": "The Minimalist", "tagline": "Less is more. Always.",
        "color": "#3E2723", "icon": "✨",
    },
    "comeback_kid": {
        "name": "The Comeback Kid", "tagline": "Don't count them out.",
        "color": "#880E4F", "icon": "🦅",
    },
    "wildcard": {
        "name": "The Wildcard", "tagline": "You never know what you get.",
        "color": "#FF6F00", "icon": "🃏",
    },
}

# Insight templates indexed by feature dimension (0-9)
STRENGTH_TEMPLATES = [
    "Calls the shot. Makes the shot.",
    "Bold bids, bold player.",
    "Reads the hand. Never overcommits.",
    "Unpredictable. That's the weapon.",
    "The invisible hand. Bids nothing, loses nothing.",
    "Give them more cards, they build more.",
    "Less is more. Always.",
    "Out of the gate like lightning.",
    "Second halves are your territory.",
    "Don't count them out. Ever.",
]

GROWTH_TEMPLATES = [
    "Sharpening the aim could change everything.",
    "Pulling back occasionally might surprise everyone.",
    "A bigger bid now and then could pay off.",
    "A little more chaos could keep them guessing.",
    "The zero bid is an untapped weapon.",
    "Big hands are your next frontier.",
    "Small hands have hidden potential.",
    "Starting strong could set the tone.",
    "Keeping that energy late could be deadly.",
    "Comebacks are waiting to happen.",
]


def min_max_normalize(vectors: dict[str, list[float]]) -> dict[str, list[float]]:
    """Min-max normalize feature vectors across all players in a room."""
    players = list(vectors.keys())
    if not players:
        return {}

    num_dims = len(next(iter(vectors.values())))

    if len(players) == 1:
        return {players[0]: [0.5] * num_dims}

    dim_mins = [float("inf")] * num_dims
    dim_maxs = [float("-inf")] * num_dims
    for vec in vectors.values():
        for i in range(num_dims):
            if vec[i] < dim_mins[i]:
                dim_mins[i] = vec[i]
            if vec[i] > dim_maxs[i]:
                dim_maxs[i] = vec[i]

    result = {}
    for name, vec in vectors.items():
        normalized = []
        for i in range(num_dims):
            span = dim_maxs[i] - dim_mins[i]
            normalized.append((vec[i] - dim_mins[i]) / span if span > 0 else 0.5)
        result[name] = normalized
    return result


def james_stein_shrink(
    player_vector: list[float],
    population_mean: list[float],
    games_played: int,
) -> list[float]:
    """Apply James-Stein shrinkage toward population mean."""
    num_dims = len(player_vector)
    diff_squared_sum = sum(
        (player_vector[i] - population_mean[i]) ** 2
        for i in range(num_dims)
    )

    if diff_squared_sum < 1e-10 or games_played == 0:
        return player_vector[:]

    raw_shrinkage = 1.0 - (num_dims - 2) / (games_played * diff_squared_sum)
    shrinkage_factor = max(0.0, min(1.0, raw_shrinkage))

    return [
        population_mean[i] + shrinkage_factor * (player_vector[i] - population_mean[i])
        for i in range(num_dims)
    ]


def ema_update(
    new_vector: list[float],
    stored_vector: list[float] | None,
    alpha: float = EMA_ALPHA,
) -> list[float]:
    """Exponential moving average for feature vector smoothing."""
    if stored_vector is None:
        return new_vector[:]
    return [
        alpha * new_vector[i] + (1 - alpha) * stored_vector[i]
        for i in range(len(new_vector))
    ]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 for near-zero vectors."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    magnitude_a = math.sqrt(sum(a ** 2 for a in vec_a))
    magnitude_b = math.sqrt(sum(b ** 2 for b in vec_b))
    if magnitude_a < 1e-10 or magnitude_b < 1e-10:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def assign_personality(
    vector: list[float],
    excluded: set[str] | None = None,
) -> dict:
    """Assign personality archetype based on cosine similarity to centroids."""
    available = {
        name: centroid for name, centroid in PERSONALITY_CENTROIDS.items()
        if not excluded or name not in excluded
    }
    if not available:
        available = PERSONALITY_CENTROIDS

    similarities = {
        name: cosine_similarity(vector, centroid)
        for name, centroid in available.items()
    }
    sorted_matches = sorted(similarities.items(), key=lambda x: -x[1])
    top_name, top_score = sorted_matches[0]
    second_score = sorted_matches[1][1] if len(sorted_matches) > 1 else 0.0

    return {
        "personality": top_name,
        "confidence": round(top_score, 4),
        "confidence_gap": round(top_score - second_score, 4),
    }


def assign_personalities_unique(
    vectors: dict[str, list[float]],
) -> dict[str, dict]:
    """Draft-style assignment: each player gets a unique personality."""
    if not vectors:
        return {}

    all_matches = _compute_all_matches(vectors)
    results = _draft_assign(all_matches, vectors)

    # Fallback for >10 players
    for player_name, vector in vectors.items():
        if player_name not in results:
            results[player_name] = assign_personality(vector)

    return results


def _compute_all_matches(vectors: dict[str, list[float]]) -> list[tuple]:
    """Compute similarity scores for all player-personality pairs."""
    matches = []
    for player_name, vector in vectors.items():
        for personality_name, centroid in PERSONALITY_CENTROIDS.items():
            score = cosine_similarity(vector, centroid)
            matches.append((score, player_name, personality_name))
    matches.sort(key=lambda x: -x[0])
    return matches


def _draft_assign(
    all_matches: list[tuple],
    vectors: dict[str, list[float]],
) -> dict[str, dict]:
    """Assign personalities greedily — best match first, then remove."""
    assigned: set[str] = set()
    taken: set[str] = set()
    results: dict[str, dict] = {}

    for score, player_name, personality_name in all_matches:
        if player_name in assigned or personality_name in taken:
            continue

        remaining = {
            n: c for n, c in PERSONALITY_CENTROIDS.items()
            if n not in taken and n != personality_name
        }
        second_score = (
            max(cosine_similarity(vectors[player_name], c) for c in remaining.values())
            if remaining else 0.0
        )

        results[player_name] = {
            "personality": personality_name,
            "confidence": round(score, 4),
            "confidence_gap": round(score - second_score, 4),
        }
        assigned.add(player_name)
        taken.add(personality_name)

        if len(assigned) == len(vectors):
            break

    return results


def generate_insights(vector: list[float], personality: str) -> list[str]:
    """Generate 1 strength + 1 growth tip from the feature vector."""
    ranked = sorted(range(len(vector)), key=lambda i: -vector[i])
    strength_dim = ranked[0]
    growth_dim = ranked[-1]
    if growth_dim == strength_dim:
        growth_dim = ranked[-2] if len(ranked) > 1 else ranked[0]

    return [
        STRENGTH_TEMPLATES[strength_dim],
        GROWTH_TEMPLATES[growth_dim],
    ]
