"""Personality assignment engine — centroids, similarity, insights.

Assigns personality archetypes to players based on feature vectors using
cosine similarity to pre-defined centroids, with normalization, shrinkage,
and smoothing for stability.

Centroid calibration: see architecture/player-insights.md for rationale.
"""

import math

# EMA smoothing factor — lower = more stable, higher = more reactive
EMA_ALPHA = 0.4

# Minimum gap between top-2 centroid matches for confident assignment
MIN_CONFIDENCE_GAP = 0.1

# Pre-defined personality centroids (raw, normalized to unit length at load)
# 9 archetypes — max pairwise cosine similarity < 0.90
_RAW_CENTROIDS = {
    "sniper": [1.0, 0.0, 0.0, 0.2, 0.6, 0.9, 0.9, 0.6, 0.6, 0.2],
    "gambler": [0.2, 1.0, 0.0, 0.7, 0.1, 0.3, 0.2, 0.7, 0.3, 0.3],
    "phoenix": [0.4, 0.2, 0.3, 0.5, 0.4, 0.4, 0.4, 0.1, 1.0, 0.9],
    "rock": [0.4, 0.1, 0.1, 0.0, 0.9, 0.4, 0.4, 0.5, 0.5, 0.1],
    "sprinter": [0.5, 0.3, 0.2, 0.5, 0.3, 0.5, 0.4, 1.0, 0.1, 0.1],
    "ghost": [0.2, 0.0, 0.6, 0.1, 1.0, 0.1, 0.5, 0.3, 0.3, 0.1],
    "reader": [0.6, 0.2, 0.1, 0.3, 0.2, 1.0, 0.2, 0.5, 0.5, 0.3],
    "surgeon": [0.5, 0.1, 0.2, 0.2, 0.4, 0.2, 1.0, 0.5, 0.5, 0.2],
    "tilter": [0.3, 0.4, 0.3, 1.0, 0.2, 0.4, 0.3, 0.8, 0.2, 0.4],
}

# Per-persona weight vectors — dimensions each archetype cares about most.
# Used in weighted cosine similarity. 2-3 dims at 1.5+, rest at 0.5-1.0.
PERSONALITY_WEIGHTS = {
    "sniper": [2.0, 0.8, 0.8, 0.5, 0.8, 1.5, 1.5, 0.7, 0.7, 0.5],
    "gambler": [0.7, 2.0, 0.5, 1.5, 0.5, 0.7, 0.5, 0.8, 0.7, 0.7],
    "phoenix": [0.7, 0.7, 0.7, 0.8, 0.7, 0.7, 0.7, 0.5, 2.0, 1.8],
    "rock": [0.8, 0.7, 0.7, 1.5, 1.5, 0.7, 0.7, 0.7, 0.7, 0.5],
    "sprinter": [0.8, 0.7, 0.7, 0.8, 0.6, 0.7, 0.7, 2.0, 1.5, 0.5],
    "ghost": [0.6, 0.5, 1.0, 0.5, 2.0, 0.5, 0.8, 0.6, 0.6, 0.5],
    "reader": [1.0, 0.7, 0.6, 0.6, 0.5, 2.0, 0.5, 0.7, 0.7, 0.7],
    "surgeon": [1.0, 0.6, 0.7, 0.5, 0.7, 0.5, 2.0, 0.7, 0.7, 0.5],
    "tilter": [0.6, 0.8, 0.8, 2.0, 0.5, 0.7, 0.6, 1.5, 0.7, 0.8],
}


def _normalize_to_unit(vec: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(v**2 for v in vec))
    if magnitude < 1e-10:
        return vec[:]
    return [v / magnitude for v in vec]


PERSONALITY_CENTROIDS = {name: _normalize_to_unit(vec) for name, vec in _RAW_CENTROIDS.items()}

# Global priors for z-score normalization (domain knowledge + staging data)
GLOBAL_PRIORS = [
    (0.50, 0.20),  # 0: bid_accuracy
    (0.35, 0.15),  # 1: overbid_ratio
    (0.40, 0.20),  # 2: underbid_ratio
    (0.50, 0.25),  # 3: score_variance
    (0.60, 0.20),  # 4: zero_bid_success
    (0.50, 0.20),  # 5: high_card_accuracy
    (0.50, 0.20),  # 6: low_card_accuracy
    (0.50, 0.20),  # 7: tempo_first_half
    (0.50, 0.20),  # 8: tempo_second_half
    (0.30, 0.20),  # 9: comeback_rate
]

PRIOR_WEIGHT = 5

# Minimum observations before using playground-specific calibration
WELFORD_MIN_COUNT = 20


def welford_update(state: dict, vec: list[float]) -> dict:
    """Online update of running mean and M2 (sum of squared deviations).

    Welford's algorithm — numerically stable single-pass.
    State: {"count": int, "mean": list[float], "m2": list[float]}
    """
    count = state["count"] + 1
    mean = list(state["mean"])
    m2 = list(state["m2"])
    for i in range(len(vec)):
        delta = vec[i] - mean[i]
        mean[i] += delta / count
        delta2 = vec[i] - mean[i]
        m2[i] += delta * delta2
    return {"count": count, "mean": mean, "m2": m2}


def welford_variance(state: dict) -> list[float]:
    """Compute population variance from Welford state."""
    if state["count"] < 2:
        return [0.0] * len(state["mean"])
    return [m2 / state["count"] for m2 in state["m2"]]


def adaptive_z_normalize(
    vectors: dict[str, list[float]],
    calibration: dict | None,
) -> dict[str, list[float]]:
    """Normalize using playground-specific stats when available (count >= 20).

    Falls back to global_z_normalize when calibration is None or count < threshold.
    """
    if not calibration or calibration.get("count", 0) < WELFORD_MIN_COUNT:
        return global_z_normalize(vectors)

    if not vectors:
        return {}

    cal_mean = calibration["mean"]
    variances = welford_variance(calibration)
    num_dims = len(cal_mean)

    result = {}
    for player, vec in vectors.items():
        normalized = []
        for i in range(min(len(vec), num_dims)):
            sd = math.sqrt(variances[i]) if variances[i] > 0 else 0.0
            if sd > 1e-10:
                z = (vec[i] - cal_mean[i]) / sd
                val = 1.0 / (1.0 + math.exp(-z))
            else:
                val = 0.5
            normalized.append(round(val, 6))
        result[player] = normalized
    return result


def global_z_normalize(vectors: dict[str, list[float]]) -> dict[str, list[float]]:
    """Normalize each dimension against fixed global priors, not other players."""
    if not vectors:
        return {}
    num_dims = len(GLOBAL_PRIORS)
    result = {}
    for player, vec in vectors.items():
        normalized = []
        for i in range(min(len(vec), num_dims)):
            mean, sd = GLOBAL_PRIORS[i]
            if sd > 0:
                z = (vec[i] - mean) / sd
                val = 1.0 / (1.0 + math.exp(-z))
            else:
                val = 0.5
            normalized.append(round(val, 6))
        result[player] = normalized
    return result


def bayesian_shrink(
    player_vector: list[float],
    games_played: int,
) -> list[float]:
    """Shrink toward fixed prior using empirical Bayes.

    At games_played=3: 37.5% observation, 62.5% prior.
    At games_played=5: 50/50.
    At games_played=10: 67% observation, 33% prior.
    """
    weight = games_played / (games_played + PRIOR_WEIGHT)
    prior_value = 0.5
    return [round(prior_value + weight * (v - prior_value), 6) for v in player_vector]


# Single source of truth for personality display — served via API to frontend
PERSONALITY_META = {
    "sniper": {
        "name": "The Sniper",
        "tagline": "Calls the shot. Makes the shot.",
        "color": "#1B5E20",
        "icon": "🎯",
    },
    "gambler": {
        "name": "The Gambler",
        "tagline": "Goes big. Sometimes it pays off.",
        "color": "#E65100",
        "icon": "🎲",
    },
    "phoenix": {
        "name": "The Phoenix",
        "tagline": "Rises when it matters most.",
        "color": "#BF360C",
        "icon": "🔥",
    },
    "rock": {
        "name": "The Rock",
        "tagline": "Steady hands. No surprises.",
        "color": "#37474F",
        "icon": "🪨",
    },
    "sprinter": {
        "name": "The Sprinter",
        "tagline": "Out of the gate like lightning.",
        "color": "#0D47A1",
        "icon": "⚡",
    },
    "ghost": {
        "name": "The Ghost",
        "tagline": "Bids nothing. Wins everything.",
        "color": "#4A148C",
        "icon": "👻",
    },
    "reader": {
        "name": "The Reader",
        "tagline": "More cards, more to read.",
        "color": "#006064",
        "icon": "📖",
    },
    "surgeon": {
        "name": "The Surgeon",
        "tagline": "Precision cuts. No wasted moves.",
        "color": "#3E2723",
        "icon": "🔬",
    },
    "tilter": {
        "name": "The Tilter",
        "tagline": "Hot or cold. Never lukewarm.",
        "color": "#FF6F00",
        "icon": "🎢",
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


def ema_update(
    new_vector: list[float],
    stored_vector: list[float] | None,
    alpha: float = EMA_ALPHA,
) -> list[float]:
    """Exponential moving average for feature vector smoothing."""
    if stored_vector is None:
        return new_vector[:]
    return [alpha * new_vector[i] + (1 - alpha) * stored_vector[i] for i in range(len(new_vector))]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 for near-zero vectors."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    magnitude_a = math.sqrt(sum(a**2 for a in vec_a))
    magnitude_b = math.sqrt(sum(b**2 for b in vec_b))
    if magnitude_a < 1e-10 or magnitude_b < 1e-10:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def weighted_cosine_similarity(
    vec_a: list[float],
    vec_b: list[float],
    weights: list[float],
) -> float:
    """Weighted cosine similarity: each dimension scaled by weight before comparison."""
    wa = [a * w for a, w in zip(vec_a, weights, strict=True)]
    wb = [b * w for b, w in zip(vec_b, weights, strict=True)]
    dot_product = sum(a * b for a, b in zip(wa, wb, strict=True))
    mag_a = math.sqrt(sum(a**2 for a in wa))
    mag_b = math.sqrt(sum(b**2 for b in wb))
    if mag_a < 1e-10 or mag_b < 1e-10:
        return 0.0
    return dot_product / (mag_a * mag_b)


def assign_personality(
    vector: list[float],
    excluded: set[str] | None = None,
) -> dict:
    """Assign personality archetype using per-persona weighted cosine similarity."""
    available = {
        name: centroid
        for name, centroid in PERSONALITY_CENTROIDS.items()
        if not excluded or name not in excluded
    }
    if not available:
        available = PERSONALITY_CENTROIDS

    similarities = {
        name: weighted_cosine_similarity(vector, centroid, PERSONALITY_WEIGHTS[name])
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
    """Compute weighted similarity scores for all player-personality pairs."""
    matches = []
    for player_name, vector in vectors.items():
        for personality_name, centroid in PERSONALITY_CENTROIDS.items():
            score = weighted_cosine_similarity(
                vector, centroid, PERSONALITY_WEIGHTS[personality_name]
            )
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
            n: c
            for n, c in PERSONALITY_CENTROIDS.items()
            if n not in taken and n != personality_name
        }
        second_score = (
            max(
                weighted_cosine_similarity(
                    vectors[player_name], c, PERSONALITY_WEIGHTS[n]
                )
                for n, c in remaining.items()
            )
            if remaining
            else 0.0
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
