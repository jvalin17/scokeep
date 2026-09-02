"""Career metric aggregation — combines per-game GameMetrics into a career feature vector.

Consumes GameMetrics objects (from metrics.py) and produces CareerMetrics with:
  - a 10-d feature vector (all values in [0, 1])
  - an extras dict (bidding style, consistency, trend, wins, games_played)
  - games_played count
"""

import math
from dataclasses import dataclass

# Card-count weights (matches feature_extractor.py)
_CARD_COUNT_WEIGHTS = {1: 0.2, 2: 0.5}

# Thresholds (mirrors feature_extractor.py constants)
_HIGH_CARD_THRESHOLD = 6
_LOW_CARD_THRESHOLD = 3
_MIN_ROUNDS_FOR_COMEBACK = 4
_TREND_IMPROVEMENT_THRESHOLD = 0.1
_CONSISTENCY_HIGH_THRESHOLD = 30
_CONSISTENCY_MEDIUM_THRESHOLD = 60

# Normalization caps for unbounded dims
_SCORE_STDDEV_CAP = 100.0  # dim 3: min(stddev/100, 1.0)
_TEMPO_CAP = 50.0  # dims 7,8: clamp avg-score-per-round to [-cap, cap], map to [0,1]


def _weight(cards: int) -> float:
    return _CARD_COUNT_WEIGHTS.get(cards, 1.0)


def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _normalize_tempo(raw_avg: float, cap: float = _TEMPO_CAP) -> float:
    """Map an average score (range [-cap, cap]) to [0, 1]."""
    clamped = max(-cap, min(cap, raw_avg))
    return (clamped + cap) / (2 * cap)


@dataclass
class CareerMetrics:
    feature_vector: list  # list[float], length 10, all values in [0, 1]
    extras: dict
    games_played: int


def _empty_career() -> CareerMetrics:
    return CareerMetrics(
        feature_vector=[0.0] * 10,
        extras={},
        games_played=0,
    )


def aggregate_career(player_name: str, game_metrics_list: list) -> CareerMetrics:
    """Aggregate a player's career stats from a list of GameMetrics.

    For each game where the player appears, extracts per-round bid/hand/score data
    from the player's PlayerGameMetrics alongside the game's cards_per_round list,
    then accumulates weighted accuracy, zero-bid, high/low card, tempo, and comeback stats.

    Returns CareerMetrics with:
      - feature_vector: 10-d, all values in [0, 1]
      - extras: dict with wins, games_played, bidding_style, consistency, trend, etc.
      - games_played: int
    """
    # --- Accumulators ---
    weighted_correct = 0.0
    weighted_overbids = 0.0
    weighted_underbids = 0.0
    weighted_total = 0.0

    zero_bid_attempts = 0
    zero_bid_successes = 0

    high_card_correct = 0.0
    high_card_total = 0.0
    low_card_correct = 0.0
    low_card_total = 0.0

    first_half_score_sum = 0.0
    first_half_round_count = 0
    second_half_score_sum = 0.0
    second_half_round_count = 0

    comeback_opportunities = 0
    comeback_wins = 0

    game_scores: list[float] = []

    # For extras
    games_played = 0
    wins = 0
    overbids_count = 0
    underbids_count = 0
    exact_bids_count = 0
    game_accuracies: list[float] = []

    for gm in game_metrics_list:
        if player_name not in gm.players:
            continue

        pm = gm.player_metrics.get(player_name)
        if pm is None or pm.bids_total == 0:
            continue

        cards_per_round = gm.cards_per_round  # list of ints, one per round
        bid_sequence = pm.bid_sequence  # list of (bid, hand) tuples
        round_scores = pm.round_scores  # list of ints

        # Align: player may have fewer entries than total rounds if they joined late,
        # but in normal games bid_sequence length == round_count.
        n = min(len(bid_sequence), len(cards_per_round), len(round_scores))
        if n == 0:
            continue

        halfway = n // 2
        game_total_score = 0.0
        game_correct = 0
        game_total_bids = 0

        for i in range(n):
            bid, hand = bid_sequence[i]
            score = round_scores[i]
            cards = cards_per_round[i]
            w = _weight(cards)
            made = bid == hand

            # Weighted accuracy dims 0-2
            weighted_total += w
            if made:
                weighted_correct += w
                exact_bids_count += 1
            elif bid > hand:
                weighted_overbids += w
                overbids_count += 1
            else:
                weighted_underbids += w
                underbids_count += 1

            # Zero bid
            if bid == 0:
                zero_bid_attempts += 1
                if made:
                    zero_bid_successes += 1

            # High card (6+)
            if cards >= _HIGH_CARD_THRESHOLD:
                high_card_total += 1.0
                if made:
                    high_card_correct += 1.0

            # Low card (1-3), weighted
            if cards <= _LOW_CARD_THRESHOLD:
                low_w = _weight(cards)
                low_card_total += low_w
                if made:
                    low_card_correct += low_w

            # Tempo (first / second half)
            if halfway >= 1:
                if i < halfway:
                    first_half_score_sum += score
                    first_half_round_count += 1
                else:
                    second_half_score_sum += score
                    second_half_round_count += 1

            game_total_score += score
            game_total_bids += 1
            if made:
                game_correct += 1

        games_played += 1
        game_scores.append(game_total_score)

        if gm.winner == player_name:
            wins += 1

        if game_total_bids > 0:
            game_accuracies.append(game_correct / game_total_bids)

        # Comeback: need >= MIN_ROUNDS_FOR_COMEBACK rounds in the game
        if gm.round_count >= _MIN_ROUNDS_FOR_COMEBACK:
            halfway_scores = _compute_halfway_scores(gm)
            if halfway_scores:
                halfway_leader = max(halfway_scores, key=lambda name: halfway_scores[name])
                if player_name != halfway_leader:
                    comeback_opportunities += 1
                    if gm.winner == player_name:
                        comeback_wins += 1

    if games_played == 0:
        return _empty_career()

    # --- Build feature vector ---
    # dim 3: score_variance — normalized stddev
    stddev_raw = _stddev(game_scores)
    score_variance = min(stddev_raw / _SCORE_STDDEV_CAP, 1.0)

    # dim 7/8: tempo — normalize raw avg score per round into [0, 1]
    tempo_first = _normalize_tempo(_safe_div(first_half_score_sum, first_half_round_count))
    tempo_second = _normalize_tempo(_safe_div(second_half_score_sum, second_half_round_count))

    feature_vector = [
        _safe_div(weighted_correct, weighted_total),  # 0 bid_accuracy
        _safe_div(weighted_overbids, weighted_total),  # 1 overbid_ratio
        _safe_div(weighted_underbids, weighted_total),  # 2 underbid_ratio
        score_variance,  # 3 score_variance
        _safe_div(zero_bid_successes, zero_bid_attempts),  # 4 zero_bid_success
        _safe_div(high_card_correct, high_card_total),  # 5 high_card_accuracy
        _safe_div(low_card_correct, low_card_total),  # 6 low_card_accuracy
        tempo_first,  # 7 tempo_first_half
        tempo_second,  # 8 tempo_second_half
        _safe_div(comeback_wins, comeback_opportunities),  # 9 comeback_rate
    ]

    # --- Build extras ---
    extras = _build_extras(
        wins=wins,
        games_played=games_played,
        overbids=overbids_count,
        underbids=underbids_count,
        exact_bids=exact_bids_count,
        game_scores=game_scores,
        game_accuracies=game_accuracies,
    )

    return CareerMetrics(
        feature_vector=feature_vector,
        extras=extras,
        games_played=games_played,
    )


def _compute_halfway_scores(gm) -> dict:
    """Compute cumulative player scores at the halfway point of a GameMetrics game.

    Uses each player's round_scores list and the game's round_count.
    """
    halfway = gm.round_count // 2
    if halfway == 0:
        return {}

    result = {}
    for player_name in gm.players:
        pm = gm.player_metrics.get(player_name)
        if pm is None:
            result[player_name] = 0
        else:
            result[player_name] = sum(pm.round_scores[:halfway])
    return result


def _build_extras(
    wins: int,
    games_played: int,
    overbids: int,
    underbids: int,
    exact_bids: int,
    game_scores: list[float],
    game_accuracies: list[float],
) -> dict:
    """Compute the extras dict."""
    # Bidding style
    total_bids = overbids + underbids + exact_bids
    if total_bids == 0:
        bidding_style = "balanced"
    elif overbids > underbids:
        bidding_style = "aggressive"
    elif underbids > overbids:
        bidding_style = "conservative"
    else:
        bidding_style = "balanced"

    # Consistency based on stddev of game totals
    stddev = _stddev([float(s) for s in game_scores])
    if stddev < _CONSISTENCY_HIGH_THRESHOLD:
        consistency = "high"
    elif stddev < _CONSISTENCY_MEDIUM_THRESHOLD:
        consistency = "medium"
    else:
        consistency = "low"

    # Trend: compare accuracy of first half vs second half of career games
    trend = "steady"
    if len(game_accuracies) >= _MIN_ROUNDS_FOR_COMEBACK:
        mid = len(game_accuracies) // 2
        first_avg = sum(game_accuracies[:mid]) / mid
        second_avg = sum(game_accuracies[mid:]) / (len(game_accuracies) - mid)
        diff = second_avg - first_avg
        if diff > _TREND_IMPROVEMENT_THRESHOLD:
            trend = "improving"
        elif diff < -_TREND_IMPROVEMENT_THRESHOLD:
            trend = "declining"

    return {
        "wins": wins,
        "games_played": games_played,
        "bidding_style": bidding_style,
        "consistency": consistency,
        "trend": trend,
    }
