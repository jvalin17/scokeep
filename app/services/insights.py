"""Player insights engine — feature vectors, personality assignment, tips.

Computes a 10-dimension feature vector per player from game history,
applies card-count weighting, and assigns personality archetypes via
cosine similarity to pre-defined centroids.
"""

import math
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.playground import Playground
from app.models.round import Round

# Card-count weights: 1-card rounds are mostly luck
CARD_COUNT_WEIGHTS = {1: 0.2, 2: 0.5}

# EMA smoothing factor — lower = more stable, higher = more reactive
EMA_ALPHA = 0.3

# Minimum gap between top-2 centroid matches to consider assignment confident
MIN_CONFIDENCE_GAP = 0.1

# Pre-defined personality centroids (raw, normalized to unit length at module load)
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
    """Normalize a vector to unit length."""
    magnitude = math.sqrt(sum(v ** 2 for v in vec))
    if magnitude == 0:
        return vec[:]
    return [v / magnitude for v in vec]


# Centroids normalized to unit length for cosine similarity
PERSONALITY_CENTROIDS = {
    name: _normalize_to_unit(vec) for name, vec in _RAW_CENTROIDS.items()
}

FEATURE_DIMENSIONS = [
    "bid_accuracy",       # 0: weighted correct bids / total bids
    "overbid_ratio",      # 1: weighted overbids / total bids
    "underbid_ratio",     # 2: weighted underbids / total bids
    "score_variance",     # 3: stddev of per-game total scores
    "zero_bid_success",   # 4: (bid=0 & won=0) / total zero bids
    "high_card_accuracy", # 5: accuracy on 6-8 card rounds
    "low_card_accuracy",  # 6: accuracy on 1-3 card rounds (weighted)
    "tempo_first_half",   # 7: avg score per round in 1st half
    "tempo_second_half",  # 8: avg score per round in 2nd half
    "comeback_rate",      # 9: comeback wins / comeback opportunities
]


def _weight_for_cards(cards_dealt: int) -> float:
    """Return the weight for a round based on cards dealt."""
    return CARD_COUNT_WEIGHTS.get(cards_dealt, 1.0)


def compute_feature_vector(player_name: str, games: list) -> list[float]:
    """Compute a 10-dimension feature vector for a player across all games.

    Args:
        player_name: The player to compute for.
        games: List of game objects with .players, .rounds, .winner attributes.

    Returns:
        List of 10 floats, one per FEATURE_DIMENSIONS entry.
    """
    # Accumulators for weighted metrics
    weighted_correct = 0.0
    weighted_overbids = 0.0
    weighted_underbids = 0.0
    weighted_total = 0.0

    # Zero-bid tracking
    zero_bid_attempts = 0
    zero_bid_successes = 0

    # High/low card accuracy
    high_card_correct = 0.0
    high_card_total = 0.0
    low_card_correct = 0.0
    low_card_total = 0.0

    # Tempo tracking
    first_half_score_sum = 0.0
    first_half_round_count = 0
    second_half_score_sum = 0.0
    second_half_round_count = 0

    # Comeback tracking
    comeback_opportunities = 0
    comeback_wins = 0

    # Per-game scores for variance
    game_scores = []

    for game in games:
        if player_name not in game.players:
            continue

        player_index = game.players.index(player_name)
        player_idx_str = str(player_index)
        rounds = game.rounds
        total_rounds_in_game = len(rounds)
        halfway = total_rounds_in_game // 2

        game_total_score = 0
        halfway_scores = {}  # player_name → score at halfway

        for name in game.players:
            halfway_scores[name] = 0

        for round_idx, rnd in enumerate(rounds):
            bid = rnd.bids.get(player_idx_str)
            hand = rnd.hands_won.get(player_idx_str)
            score = rnd.scores.get(player_idx_str, 0)

            if bid is None or hand is None:
                continue

            weight = _weight_for_cards(rnd.cards_dealt)
            made = bid == hand

            # Weighted accuracy (dims 0, 1, 2)
            weighted_total += weight
            if made:
                weighted_correct += weight
            elif bid > hand:
                weighted_overbids += weight
            else:  # bid < hand
                weighted_underbids += weight

            # Zero-bid success (dim 4)
            if bid == 0:
                zero_bid_attempts += 1
                if hand == 0:
                    zero_bid_successes += 1

            # High-card accuracy (dim 5): 6-8 cards
            if rnd.cards_dealt >= 6:
                high_card_total += 1.0
                if made:
                    high_card_correct += 1.0

            # Low-card accuracy (dim 6): 1-3 cards (weighted)
            if rnd.cards_dealt <= 3:
                low_weight = _weight_for_cards(rnd.cards_dealt)
                low_card_total += low_weight
                if made:
                    low_card_correct += low_weight

            # Tempo (dims 7, 8)
            if round_idx < halfway:
                first_half_score_sum += score
                first_half_round_count += 1
            else:
                second_half_score_sum += score
                second_half_round_count += 1

            # Track all player scores at halfway for comeback detection
            game_total_score += score

        # Update halfway scores for all players in this game
        for rnd_idx, rnd in enumerate(rounds):
            if rnd_idx >= halfway:
                break
            for idx_str, score_val in rnd.scores.items():
                idx = int(idx_str)
                if idx < len(game.players):
                    halfway_scores[game.players[idx]] += score_val

        game_scores.append(game_total_score)

        # Comeback detection (dim 9)
        if total_rounds_in_game >= 2:
            halfway_leader = max(halfway_scores, key=lambda n: halfway_scores[n])
            if player_name != halfway_leader:
                comeback_opportunities += 1
                if game.winner == player_name:
                    comeback_wins += 1

    # Build the 10-dimension vector
    vector = [0.0] * 10

    # Dim 0: bid_accuracy
    vector[0] = weighted_correct / weighted_total if weighted_total > 0 else 0.0

    # Dim 1: overbid_ratio
    vector[1] = weighted_overbids / weighted_total if weighted_total > 0 else 0.0

    # Dim 2: underbid_ratio
    vector[2] = weighted_underbids / weighted_total if weighted_total > 0 else 0.0

    # Dim 3: score_variance (stddev of per-game totals)
    if len(game_scores) >= 2:
        mean_score = sum(game_scores) / len(game_scores)
        variance = sum((s - mean_score) ** 2 for s in game_scores) / len(game_scores)
        vector[3] = math.sqrt(variance)
    else:
        vector[3] = 0.0

    # Dim 4: zero_bid_success
    vector[4] = zero_bid_successes / zero_bid_attempts if zero_bid_attempts > 0 else 0.0

    # Dim 5: high_card_accuracy
    vector[5] = high_card_correct / high_card_total if high_card_total > 0 else 0.0

    # Dim 6: low_card_accuracy
    vector[6] = low_card_correct / low_card_total if low_card_total > 0 else 0.0

    # Dim 7: tempo_first_half (avg score per round)
    vector[7] = first_half_score_sum / first_half_round_count if first_half_round_count > 0 else 0.0

    # Dim 8: tempo_second_half (avg score per round)
    if second_half_round_count > 0:
        vector[8] = second_half_score_sum / second_half_round_count

    # Dim 9: comeback_rate
    vector[9] = comeback_wins / comeback_opportunities if comeback_opportunities > 0 else 0.0

    return vector


def min_max_normalize(vectors: dict[str, list[float]]) -> dict[str, list[float]]:
    """Min-max normalize feature vectors across all players in a room.

    Each dimension is scaled to [0, 1] based on the room's min/max.
    Single player: all dimensions set to 0.5.
    All players same value on a dimension: set to 0.5.

    Args:
        vectors: {player_name: [10 floats]}

    Returns:
        {player_name: [10 normalized floats]}
    """
    players = list(vectors.keys())
    if not players:
        return {}

    num_dims = len(next(iter(vectors.values())))

    if len(players) == 1:
        return {players[0]: [0.5] * num_dims}

    # Compute min/max per dimension
    dim_mins = [float("inf")] * num_dims
    dim_maxs = [float("-inf")] * num_dims
    for vec in vectors.values():
        for dim_index in range(num_dims):
            if vec[dim_index] < dim_mins[dim_index]:
                dim_mins[dim_index] = vec[dim_index]
            if vec[dim_index] > dim_maxs[dim_index]:
                dim_maxs[dim_index] = vec[dim_index]

    result = {}
    for name, vec in vectors.items():
        normalized = []
        for dim_index in range(num_dims):
            span = dim_maxs[dim_index] - dim_mins[dim_index]
            if span == 0:
                normalized.append(0.5)
            else:
                normalized.append(
                    (vec[dim_index] - dim_mins[dim_index]) / span
                )
        result[name] = normalized

    return result


def james_stein_shrink(
    player_vector: list[float],
    population_mean: list[float],
    games_played: int,
) -> list[float]:
    """Apply James-Stein shrinkage toward population mean.

    Shrinkage is proportional to 1/games_played — fewer games means
    more shrinkage toward the average. With many games, the player's
    raw vector dominates.

    Args:
        player_vector: Player's normalized feature vector (10 floats).
        population_mean: Average vector across all players (10 floats).
        games_played: Number of games this player has completed.

    Returns:
        Shrunk feature vector (10 floats).
    """
    num_dims = len(player_vector)

    # Compute squared distance from mean
    diff_squared_sum = sum(
        (player_vector[i] - population_mean[i]) ** 2
        for i in range(num_dims)
    )

    # James-Stein shrinkage factor
    # shrinkage = 1 - (d - 2) / (n * ||x - mean||^2)
    # where d = dimensions, n = games_played
    if diff_squared_sum == 0 or games_played == 0:
        return player_vector[:]

    raw_shrinkage = 1.0 - (num_dims - 2) / (games_played * diff_squared_sum)
    # Clamp to [0, 1] — negative shrinkage means data is too close to mean
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
    """Exponential moving average update for feature vector smoothing.

    First computation (no stored vector): returns new_vector as-is.
    Subsequent: blends alpha * new + (1 - alpha) * stored.

    Args:
        new_vector: Freshly computed feature vector.
        stored_vector: Previously stored vector, or None if first time.
        alpha: Blending factor (0.3 default — 30% new, 70% stored).

    Returns:
        Smoothed feature vector.
    """
    if stored_vector is None:
        return new_vector[:]
    return [
        alpha * new_vector[i] + (1 - alpha) * stored_vector[i]
        for i in range(len(new_vector))
    ]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns 0.0 for zero vectors (instead of NaN).
    """
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    magnitude_a = math.sqrt(sum(a ** 2 for a in vec_a))
    magnitude_b = math.sqrt(sum(b ** 2 for b in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def assign_personality(
    vector: list[float],
    excluded: set[str] | None = None,
) -> dict:
    """Assign a personality archetype based on cosine similarity to centroids.

    Args:
        vector: Player's processed feature vector (10 floats).
        excluded: Set of personality names already taken (for unique assignment).

    Returns:
        {personality, confidence, confidence_gap}
    """
    available = {
        name: centroid for name, centroid in PERSONALITY_CENTROIDS.items()
        if not excluded or name not in excluded
    }
    # Fallback: if all excluded (more players than personalities), use full set
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
    """Draft-style assignment: each player gets a unique personality.

    Players are assigned in order of strongest match first.
    Once a personality is taken, it's removed from the pool.
    If there are more players than personalities (>10), duplicates allowed.

    Args:
        vectors: {player_name: processed feature vector}

    Returns:
        {player_name: {personality, confidence, confidence_gap}}
    """
    if not vectors:
        return {}

    # Compute all similarities: (score, player, personality)
    all_matches = []
    for player_name, vector in vectors.items():
        for personality_name, centroid in PERSONALITY_CENTROIDS.items():
            score = cosine_similarity(vector, centroid)
            all_matches.append((score, player_name, personality_name))

    # Sort by score descending — strongest matches assigned first
    all_matches.sort(key=lambda x: -x[0])

    assigned_players: set[str] = set()
    taken_personalities: set[str] = set()
    results: dict[str, dict] = {}

    for score, player_name, personality_name in all_matches:
        if player_name in assigned_players:
            continue
        if personality_name in taken_personalities:
            continue

        # Compute confidence gap against remaining personalities
        remaining = {
            name: centroid for name, centroid in PERSONALITY_CENTROIDS.items()
            if name not in taken_personalities and name != personality_name
        }
        second_score = 0.0
        if remaining:
            second_score = max(
                cosine_similarity(vectors[player_name], c)
                for c in remaining.values()
            )

        results[player_name] = {
            "personality": personality_name,
            "confidence": round(score, 4),
            "confidence_gap": round(score - second_score, 4),
        }
        assigned_players.add(player_name)
        taken_personalities.add(personality_name)

        if len(assigned_players) == len(vectors):
            break

    # Fallback: any unassigned players (more than 10) get best available
    for player_name, vector in vectors.items():
        if player_name not in assigned_players:
            results[player_name] = assign_personality(vector)

    return results


# Insight templates — indexed by FEATURE_DIMENSIONS order (0-9)
STRENGTH_TEMPLATES = [
    "Calls the shot. Makes the shot.",                  # 0: bid_accuracy
    "Bold bids, bold player.",                          # 1: overbid_ratio
    "Reads the hand. Never overcommits.",               # 2: underbid_ratio (conservative)
    "Unpredictable. That's the weapon.",                # 3: score_variance (high)
    "The invisible hand. Bids nothing, loses nothing.", # 4: zero_bid_success
    "Give them more cards, they build more.",           # 5: high_card_accuracy
    "Less is more. Always.",                            # 6: low_card_accuracy
    "Out of the gate like lightning.",                  # 7: tempo_first_half
    "Second halves are your territory.",                # 8: tempo_second_half
    "Don't count them out. Ever.",                      # 9: comeback_rate
]

GROWTH_TEMPLATES = [
    "Sharpening the aim could change everything.",      # 0: bid_accuracy
    "Pulling back occasionally might surprise everyone.", # 1: overbid_ratio
    "A bigger bid now and then could pay off.",         # 2: underbid_ratio
    "A little more chaos could keep them guessing.",    # 3: score_variance
    "The zero bid is an untapped weapon.",              # 4: zero_bid_success
    "Big hands are your next frontier.",                # 5: high_card_accuracy
    "Small hands have hidden potential.",               # 6: low_card_accuracy
    "Starting strong could set the tone.",              # 7: tempo_first_half
    "Keeping that energy late could be deadly.",        # 8: tempo_second_half
    "Comebacks are waiting to happen.",                 # 9: comeback_rate
]


def generate_insights(vector: list[float], personality: str) -> list[str]:
    """Generate 1 strength + 1 growth tip from the feature vector.

    Strength: dimension where player scores highest.
    Growth: dimension where player has most room to improve.
    Never picks the same dimension for both.

    Args:
        vector: Player's processed feature vector (10 floats).
        personality: Assigned personality name.

    Returns:
        [strength_text, growth_text]
    """
    # Rank dimensions by value (highest first)
    ranked = sorted(range(len(vector)), key=lambda i: -vector[i])

    # Strength: highest dimension
    strength_dim = ranked[0]

    # Growth: lowest dimension, but not the same as strength
    # Search from the bottom of the ranking
    growth_dim = ranked[-1]
    if growth_dim == strength_dim:
        growth_dim = ranked[-2] if len(ranked) > 1 else ranked[0]

    return [
        STRENGTH_TEMPLATES[strength_dim],
        GROWTH_TEMPLATES[growth_dim],
    ]


def compute_accuracy_by_cards(player_name: str, games: list) -> dict:
    """Compute bid accuracy breakdown by cards dealt.

    Returns raw accuracy (no weighting) for each card count the player
    has encountered. Shown on the card back.

    Args:
        player_name: Player to compute for.
        games: List of game objects with .players, .rounds.

    Returns:
        {"8": {"pct": 90, "rounds": 9}, "5": {"pct": 50, "rounds": 6}, ...}
    """
    by_cards: dict[int, dict] = {}  # cards_dealt → {correct, total}

    for game in games:
        if player_name not in game.players:
            continue
        player_idx_str = str(game.players.index(player_name))

        for rnd in game.rounds:
            bid = rnd.bids.get(player_idx_str)
            hand = rnd.hands_won.get(player_idx_str)
            if bid is None or hand is None:
                continue

            cards = rnd.cards_dealt
            if cards not in by_cards:
                by_cards[cards] = {"correct": 0, "total": 0}
            by_cards[cards]["total"] += 1
            if bid == hand:
                by_cards[cards]["correct"] += 1

    result = {}
    for cards, data in sorted(by_cards.items()):
        pct = round(data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
        result[str(cards)] = {"pct": pct, "rounds": data["total"]}

    return result


TRUMP_SUITS = ["spades", "diamonds", "clubs", "hearts"]
TRUMP_SYMBOLS = {"spades": "♠", "diamonds": "♦", "clubs": "♣", "hearts": "♥"}


def compute_player_extras(player_name: str, games: list) -> dict:
    """Compute additional stats for the player card.

    Returns dict with: signature_round, wins, games_played, best_trump,
    trend, fun_facts, favorite_bid, total_rounds, biggest_round_score,
    kryptonite (worst card count).
    """
    wins = 0
    games_played = 0
    total_rounds = 0
    biggest_round_score = 0
    bid_counts: dict[int, int] = {}
    trump_correct: dict[str, int] = {}
    trump_total: dict[str, int] = {}
    zero_bid_streak = 0
    max_zero_streak = 0
    game_accuracies: list[float] = []  # per-game accuracy for trend

    for game in games:
        if player_name not in game.players:
            continue
        player_idx_str = str(game.players.index(player_name))
        games_played += 1
        if game.winner == player_name:
            wins += 1

        game_correct = 0
        game_total = 0

        for rnd in game.rounds:
            bid = rnd.bids.get(player_idx_str)
            hand = rnd.hands_won.get(player_idx_str)
            score = rnd.scores.get(player_idx_str, 0)
            if bid is None or hand is None:
                continue

            total_rounds += 1
            made = bid == hand

            # Biggest round score
            if score > biggest_round_score:
                biggest_round_score = score

            # Favorite bid
            bid_counts[bid] = bid_counts.get(bid, 0) + 1

            # Trump suit performance
            trump = rnd.trump_suit if hasattr(rnd, "trump_suit") else None
            if trump:
                trump_lower = trump.lower()
                trump_total[trump_lower] = trump_total.get(trump_lower, 0) + 1
                if made:
                    trump_correct[trump_lower] = trump_correct.get(trump_lower, 0) + 1

            # Zero bid streak
            if bid == 0 and made:
                zero_bid_streak += 1
                if zero_bid_streak > max_zero_streak:
                    max_zero_streak = zero_bid_streak
            elif bid == 0 and not made:
                zero_bid_streak = 0

            # Per-game accuracy
            game_total += 1
            if made:
                game_correct += 1

        if game_total > 0:
            game_accuracies.append(game_correct / game_total)

    # Signature round (best card count from accuracy_by_cards — computed separately)
    # Kryptonite (worst card count) — also from accuracy_by_cards

    # Best trump suit
    best_trump = None
    best_trump_pct = 0
    for suit in TRUMP_SUITS:
        total = trump_total.get(suit, 0)
        if total >= 2:  # need at least 2 rounds to be meaningful
            correct = trump_correct.get(suit, 0)
            pct = correct / total
            if pct > best_trump_pct:
                best_trump_pct = pct
                best_trump = suit

    # Trend (compare first half of games vs second half accuracy)
    trend = "steady"
    if len(game_accuracies) >= 4:
        mid = len(game_accuracies) // 2
        first_half_avg = sum(game_accuracies[:mid]) / mid
        second_half_avg = sum(game_accuracies[mid:]) / (len(game_accuracies) - mid)
        diff = second_half_avg - first_half_avg
        if diff > 0.1:
            trend = "improving"
        elif diff < -0.1:
            trend = "declining"

    # Favorite bid
    favorite_bid = None
    if bid_counts:
        favorite_bid = max(bid_counts, key=lambda b: bid_counts[b])

    # Fun facts
    fun_facts = []
    if biggest_round_score >= 40:
        fun_facts.append(f"Scored +{biggest_round_score} in a single round")
    if max_zero_streak >= 3:
        fun_facts.append(f"Nailed {max_zero_streak} zero bids in a row")
    if favorite_bid is not None and favorite_bid >= 4:
        fun_facts.append(f"Loves bidding {favorite_bid}")
    elif favorite_bid == 0:
        fun_facts.append("Favorite bid: zero")
    highest_bid = max(bid_counts.keys()) if bid_counts else 0
    if highest_bid >= 6:
        fun_facts.append(f"Once bid {highest_bid}")

    return {
        "wins": wins,
        "games_played": games_played,
        "total_rounds": total_rounds,
        "best_trump": TRUMP_SYMBOLS.get(best_trump) if best_trump else None,
        "best_trump_pct": round(best_trump_pct * 100) if best_trump else None,
        "trend": trend,
        "favorite_bid": favorite_bid,
        "biggest_round_score": biggest_round_score,
        "fun_facts": fun_facts,
    }


# Minimum games before personality is assigned
MIN_GAMES_FOR_PERSONALITY = 3

# Personality display metadata
PERSONALITY_META = {
    "sniper":       {"name": "The Sniper",       "tagline": "Calls the shot. Makes the shot."},
    "gambler":      {"name": "The Gambler",       "tagline": "Goes big. Sometimes it pays off."},
    "phoenix":      {"name": "The Phoenix",       "tagline": "Slow start? That's the plan."},
    "rock":         {"name": "The Rock",          "tagline": "Steady hands. No surprises."},
    "sprinter":     {"name": "The Sprinter",      "tagline": "Out of the gate like lightning."},
    "ghost":        {"name": "The Ghost",         "tagline": "Bids nothing. Wins everything."},
    "architect":    {"name": "The Architect",    "tagline": "More cards, more to build."},
    "minimalist":   {"name": "The Minimalist",   "tagline": "Less is more. Always."},
    "comeback_kid": {"name": "The Comeback Kid", "tagline": "Don't count them out."},
    "wildcard":     {"name": "The Wildcard",     "tagline": "You never know what you get."},
}


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
    """Full pipeline: compute and store insights for all players in a playground.

    Called after every game finishes. Loads all historical data,
    computes feature vectors, normalizes, shrinks, smooths, assigns
    personalities, generates insights, and stores in playground.insights.

    Returns the insights dict, or None if no finished games.
    """
    # Load playground
    playground = await db.get(Playground, playground_id)
    if not playground:
        return None

    # Load all finished games + rounds
    games_result = await db.execute(
        select(Game)
        .where(Game.playground_id == playground_id, Game.status == "finished")
        .order_by(Game.started_at)
    )
    db_games = list(games_result.scalars().all())
    if not db_games:
        return None

    game_ids = [g.id for g in db_games]
    rounds_result = await db.execute(
        select(Round)
        .where(Round.game_id.in_(game_ids), Round.status == "scored")
        .order_by(Round.game_id, Round.round_num)
    )
    all_rounds = list(rounds_result.scalars().all())

    # Group rounds by game
    rounds_by_game: dict[int, list] = {}
    for rnd in all_rounds:
        rounds_by_game.setdefault(rnd.game_id, []).append(rnd)

    # Build game wrappers with rounds attached
    games = [
        _GameWithRounds(g, rounds_by_game.get(g.id, []))
        for g in db_games
    ]

    # Find all players across all games
    all_players: set[str] = set()
    player_game_counts: dict[str, int] = {}
    for game in games:
        for name in game.players:
            all_players.add(name)
            player_game_counts[name] = player_game_counts.get(name, 0) + 1

    # Load existing insights for EMA
    existing_insights = playground.insights or {}
    existing_players = existing_insights.get("players", {})

    # Step 1: Compute raw feature vectors
    raw_vectors = {}
    for name in all_players:
        if player_game_counts.get(name, 0) >= MIN_GAMES_FOR_PERSONALITY:
            raw_vectors[name] = compute_feature_vector(name, games)

    if not raw_vectors:
        # No players with enough games — store unlock progress only
        players_data = {}
        for name in all_players:
            players_data[name] = {
                "personality": None,
                "games_analyzed": player_game_counts.get(name, 0),
                "unlock_at": MIN_GAMES_FOR_PERSONALITY,
            }
        insights_blob = {
            "computed_at": datetime.now(UTC).isoformat(),
            "players": players_data,
        }
        playground.insights = insights_blob
        await db.commit()
        return insights_blob

    # Step 2: Min-max normalize
    normalized = min_max_normalize(raw_vectors)

    # Step 3: Compute population mean
    num_dims = len(FEATURE_DIMENSIONS)
    population_mean = [0.0] * num_dims
    for vec in normalized.values():
        for i in range(num_dims):
            population_mean[i] += vec[i]
    for i in range(num_dims):
        population_mean[i] /= len(normalized)

    # Step 4: Shrink + EMA for each eligible player
    smoothed_vectors = {}
    for name in normalized:
        games_played = player_game_counts.get(name, 0)
        shrunk = james_stein_shrink(
            normalized[name], population_mean, games_played,
        )
        stored_vector = None
        if name in existing_players and existing_players[name].get("feature_vector"):
            stored_vector = existing_players[name]["feature_vector"]
        smoothed_vectors[name] = ema_update(shrunk, stored_vector)

    # Step 5: Unique personality assignment (draft-style)
    assignments = assign_personalities_unique(smoothed_vectors)

    # Step 6: Build player data
    players_data = {}
    for name in all_players:
        games_played = player_game_counts.get(name, 0)

        if games_played < MIN_GAMES_FOR_PERSONALITY:
            players_data[name] = {
                "personality": None,
                "games_analyzed": games_played,
                "unlock_at": MIN_GAMES_FOR_PERSONALITY,
            }
            continue

        assignment = assignments[name]

        # Detect evolution
        previous_personality = None
        if name in existing_players:
            old_personality = existing_players[name].get("personality")
            if old_personality and old_personality != assignment["personality"]:
                previous_personality = old_personality

        # Generate insights
        insights = generate_insights(
            smoothed_vectors[name], assignment["personality"],
        )

        # Accuracy by cards
        accuracy = compute_accuracy_by_cards(name, games)

        # Signature round + kryptonite from accuracy data
        signature_round = None
        kryptonite = None
        if accuracy:
            valid = {k: v for k, v in accuracy.items() if v["rounds"] >= 2}
            if valid:
                signature_round = max(valid, key=lambda k: valid[k]["pct"])
                kryptonite = min(valid, key=lambda k: valid[k]["pct"])
                if signature_round == kryptonite:
                    kryptonite = None

        # Extra stats
        extras = compute_player_extras(name, games)

        # Determine assigned_at
        assigned_at = datetime.now(UTC).isoformat()
        if name in existing_players:
            old = existing_players[name]
            if old.get("personality") == assignment["personality"] and old.get("assigned_at"):
                assigned_at = old["assigned_at"]

        players_data[name] = {
            "personality": assignment["personality"],
            "previous_personality": previous_personality,
            "confidence": assignment["confidence"],
            "confidence_gap": assignment["confidence_gap"],
            "feature_vector": [round(v, 4) for v in smoothed_vectors[name]],
            "accuracy_by_cards": accuracy,
            "insights": insights,
            "signature_round": signature_round,
            "kryptonite": kryptonite,
            "extras": extras,
            "games_analyzed": games_played,
            "assigned_at": assigned_at,
        }

    insights_blob = {
        "computed_at": datetime.now(UTC).isoformat(),
        "players": players_data,
    }
    playground.insights = insights_blob
    await db.commit()
    return insights_blob
