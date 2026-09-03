"""Career metric aggregation — combines per-game GameMetrics into a career feature vector.

Consumes GameMetrics objects (from metrics.py) and produces CareerMetrics with:
  - a 10-d feature vector (all values in [0, 1])
  - an extras dict (bidding style, consistency, trend, wins, games_played)
  - games_played count

Also provides bridge functions (compute_feature_vector, compute_player_extras,
compute_accuracy_by_cards_from_games) that accept raw game objects for backward
compatibility — these convert to GameMetrics internally.
"""

import math
from dataclasses import dataclass, field

from app.services.metrics import compute_game_metrics

# Card-count weights (shared with metrics.py)
_CARD_COUNT_WEIGHTS = {1: 0.2, 2: 0.5}

# Thresholds
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


# ── Shared classification helpers ─────────────────────────────────────────────


def _classify_bidding_style(overbids: int, underbids: int, exact_bids: int) -> tuple[str, int]:
    """Return (bidding_style_label, overbid_pct_int)."""
    total = overbids + underbids + exact_bids
    if total == 0:
        return "balanced", 0
    overbid_pct = round(overbids / total * 100)
    if overbids > underbids:
        return "aggressive", overbid_pct
    if underbids > overbids:
        return "conservative", overbid_pct
    return "balanced", overbid_pct


def _classify_consistency(game_scores: list[float]) -> str:
    """Return 'high', 'medium', or 'low' based on score stddev."""
    stddev = _stddev([float(s) for s in game_scores])
    if stddev < _CONSISTENCY_HIGH_THRESHOLD:
        return "high"
    if stddev < _CONSISTENCY_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _classify_trend(game_accuracies: list[float]) -> str:
    """Return 'improving', 'declining', or 'steady' from per-game accuracy list."""
    if len(game_accuracies) < _MIN_ROUNDS_FOR_COMEBACK:
        return "steady"
    mid = len(game_accuracies) // 2
    first_avg = sum(game_accuracies[:mid]) / mid
    second_avg = sum(game_accuracies[mid:]) / (len(game_accuracies) - mid)
    diff = second_avg - first_avg
    if diff > _TREND_IMPROVEMENT_THRESHOLD:
        return "improving"
    if diff < -_TREND_IMPROVEMENT_THRESHOLD:
        return "declining"
    return "steady"


def _best_trump_suit(trump_total: dict, trump_correct: dict) -> tuple[str | None, float]:
    """Return (best_suit_name_or_None, accuracy_float) across the four trump suits."""
    best_suit, best_pct = None, 0.0
    for suit in _TRUMP_SUITS:
        t = trump_total.get(suit, 0)
        if t >= _MIN_ROUNDS_FOR_BEST_SUIT:
            pct = trump_correct.get(suit, 0) / t
            if pct > best_pct:
                best_pct, best_suit = pct, suit
    return best_suit, best_pct


def _classify_tempo(first_half_scores: list[float], second_half_scores: list[float]) -> str:
    """Return '1st half', '2nd half', or 'even' based on average score per half."""
    first_avg = sum(first_half_scores) / len(first_half_scores) if first_half_scores else 0.0
    second_avg = sum(second_half_scores) / len(second_half_scores) if second_half_scores else 0.0
    if first_avg - second_avg > _TEMPO_DIFF_THRESHOLD:
        return "1st half"
    if second_avg - first_avg > _TEMPO_DIFF_THRESHOLD:
        return "2nd half"
    return "even"


def _build_fun_facts(acc: "_RoundAccumulator", favorite_bid: int | None) -> list[str]:
    """Assemble the fun-facts list from accumulator data."""
    highest_bid = max(acc.bid_counts.keys()) if acc.bid_counts else 0
    facts = []
    if acc.biggest_round_score >= _BIG_ROUND_SCORE_THRESHOLD:
        facts.append(f"Scored +{acc.biggest_round_score} in a single round")
    if acc.max_zero_streak >= _NOTABLE_ZERO_STREAK:
        facts.append(f"Nailed {acc.max_zero_streak} zero bids in a row")
    if favorite_bid is not None and favorite_bid >= _HIGH_FAVORITE_BID:
        facts.append(f"Loves bidding {favorite_bid}")
    elif favorite_bid == 0:
        facts.append("Favorite bid: zero")
    if highest_bid >= _REMARKABLE_BID:
        facts.append(f"Once bid {highest_bid}")
    return facts


# ── Shared accumulator ────────────────────────────────────────────────────────


@dataclass
class _RoundAccumulator:
    # Shared fields
    wins: int = 0
    games_played: int = 0
    overbids_count: int = 0
    underbids_count: int = 0
    exact_bids_count: int = 0
    zero_bid_attempts: int = 0
    zero_bid_successes: int = 0
    comeback_wins: int = 0
    comeback_opportunities: int = 0
    game_totals: list[float] = field(default_factory=list)
    game_accuracies: list[float] = field(default_factory=list)
    first_half_scores: list[float] = field(default_factory=list)
    second_half_scores: list[float] = field(default_factory=list)

    # aggregate_career-only fields
    weighted_correct: float = 0.0
    weighted_overbids: float = 0.0
    weighted_underbids: float = 0.0
    weighted_total: float = 0.0
    high_card_correct: float = 0.0
    high_card_total: float = 0.0
    low_card_correct: float = 0.0
    low_card_total: float = 0.0

    # compute_display_extras-only fields
    total_rounds: int = 0
    biggest_round_score: int = 0
    zero_bid_streak: int = 0
    max_zero_streak: int = 0
    bid_counts: dict = field(default_factory=dict)
    trump_correct: dict = field(default_factory=dict)
    trump_total: dict = field(default_factory=dict)


def _accumulate_rounds(player_name: str, game_metrics_list: list) -> _RoundAccumulator:
    """Single pass over all games/rounds for a player, collecting every field."""
    acc = _RoundAccumulator()

    for gm in game_metrics_list:
        if player_name not in gm.players:
            continue
        pm = gm.player_metrics.get(player_name)
        if pm is None or pm.bids_total == 0:
            continue

        n = min(len(pm.bid_sequence), len(gm.cards_per_round), len(pm.round_scores))
        if n == 0:
            continue

        halfway = n // 2
        game_correct = 0

        for i in range(n):
            bid, hand = pm.bid_sequence[i]
            score = pm.round_scores[i]
            cards = gm.cards_per_round[i]
            w = _weight(cards)
            made = bid == hand

            # Weighted accuracy (aggregate_career)
            acc.weighted_total += w
            if made:
                acc.weighted_correct += w
                acc.exact_bids_count += 1
                game_correct += 1
            elif bid > hand:
                acc.weighted_overbids += w
                acc.overbids_count += 1
            else:
                acc.weighted_underbids += w
                acc.underbids_count += 1

            # High/low card (aggregate_career)
            if cards >= _HIGH_CARD_THRESHOLD:
                acc.high_card_total += 1.0
                if made:
                    acc.high_card_correct += 1.0
            if cards <= _LOW_CARD_THRESHOLD:
                low_w = _weight(cards)
                acc.low_card_total += low_w
                if made:
                    acc.low_card_correct += low_w

            # Zero bid (shared)
            if bid == 0:
                acc.zero_bid_attempts += 1
                if made:
                    acc.zero_bid_successes += 1
                    acc.zero_bid_streak += 1
                    if acc.zero_bid_streak > acc.max_zero_streak:
                        acc.max_zero_streak = acc.zero_bid_streak
                else:
                    acc.zero_bid_streak = 0

            # Tempo (shared — store as lists; aggregate uses sum/len)
            if halfway >= 1:
                if i < halfway:
                    acc.first_half_scores.append(score)
                else:
                    acc.second_half_scores.append(score)

            # Display-only fields
            acc.total_rounds += 1
            if score > acc.biggest_round_score:
                acc.biggest_round_score = score
            acc.bid_counts[bid] = acc.bid_counts.get(bid, 0) + 1

            if i < len(gm.trump_per_round) and gm.trump_per_round[i]:
                trump = gm.trump_per_round[i].lower()
                acc.trump_total[trump] = acc.trump_total.get(trump, 0) + 1
                if made:
                    acc.trump_correct[trump] = acc.trump_correct.get(trump, 0) + 1

        acc.games_played += 1
        acc.game_totals.append(pm.total_score)
        if pm.bids_total > 0:
            acc.game_accuracies.append(game_correct / pm.bids_total)
        if gm.winner == player_name:
            acc.wins += 1

        # Comeback (shared)
        if gm.round_count >= _MIN_ROUNDS_FOR_COMEBACK:
            halfway_scores = _compute_halfway_scores(gm)
            if halfway_scores:
                leader = max(halfway_scores, key=lambda name: halfway_scores[name])
                if player_name != leader:
                    acc.comeback_opportunities += 1
                    if gm.winner == player_name:
                        acc.comeback_wins += 1

    return acc


# ── Display extras constants ───────────────────────────────────────────────────

_TRUMP_SUITS = ["spades", "diamonds", "clubs", "hearts"]
_TRUMP_SYMBOLS = {"spades": "♠", "diamonds": "♦", "clubs": "♣", "hearts": "♥"}
_MIN_ROUNDS_FOR_BEST_SUIT = 2
_TEMPO_DIFF_THRESHOLD = 3
_BIG_ROUND_SCORE_THRESHOLD = 40
_NOTABLE_ZERO_STREAK = 3
_HIGH_FAVORITE_BID = 4
_REMARKABLE_BID = 6


# ── Core functions ────────────────────────────────────────────────────────────


def aggregate_career(player_name: str, game_metrics_list: list) -> CareerMetrics:
    """Aggregate a player's career stats from a list of GameMetrics.

    Returns CareerMetrics with:
      - feature_vector: 10-d, all values in [0, 1]
      - extras: dict with wins, games_played, bidding_style, consistency, trend, etc.
      - games_played: int
    """
    acc = _accumulate_rounds(player_name, game_metrics_list)
    if acc.games_played == 0:
        return _empty_career()

    stddev_raw = _stddev(acc.game_totals)
    first_avg = _safe_div(sum(acc.first_half_scores), len(acc.first_half_scores))
    second_avg = _safe_div(sum(acc.second_half_scores), len(acc.second_half_scores))

    feature_vector = [
        _safe_div(acc.weighted_correct, acc.weighted_total),  # 0 bid_accuracy
        _safe_div(acc.weighted_overbids, acc.weighted_total),  # 1 overbid_ratio
        _safe_div(acc.weighted_underbids, acc.weighted_total),  # 2 underbid_ratio
        min(stddev_raw / _SCORE_STDDEV_CAP, 1.0),  # 3 score_variance
        _safe_div(acc.zero_bid_successes, acc.zero_bid_attempts),  # 4 zero_bid_success
        _safe_div(acc.high_card_correct, acc.high_card_total),  # 5 high_card_accuracy
        _safe_div(acc.low_card_correct, acc.low_card_total),  # 6 low_card_accuracy
        _normalize_tempo(first_avg),  # 7 tempo_first_half
        _normalize_tempo(second_avg),  # 8 tempo_second_half
        _safe_div(acc.comeback_wins, acc.comeback_opportunities),  # 9 comeback_rate
    ]

    bidding_style, _ = _classify_bidding_style(
        acc.overbids_count, acc.underbids_count, acc.exact_bids_count
    )
    extras = {
        "wins": acc.wins,
        "games_played": acc.games_played,
        "bidding_style": bidding_style,
        "consistency": _classify_consistency(acc.game_totals),
        "trend": _classify_trend(acc.game_accuracies),
    }
    return CareerMetrics(
        feature_vector=feature_vector, extras=extras, games_played=acc.games_played
    )


def compute_display_extras(player_name: str, game_metrics_list: list) -> dict:
    """Compute full display extras for a player from GameMetrics objects."""
    acc = _accumulate_rounds(player_name, game_metrics_list)

    if acc.games_played == 0:
        return {
            "wins": 0,
            "games_played": 0,
            "total_rounds": 0,
            "best_trump": None,
            "best_trump_pct": None,
            "trend": "steady",
            "favorite_bid": None,
            "biggest_round_score": 0,
            "fun_facts": [],
            "bidding_style": "balanced",
            "overbid_pct": 0,
            "zero_bid_rate": 0,
            "clutch_wins": 0,
            "clutch_opportunities": 0,
            "tempo": "even",
            "consistency": "high",
        }

    best_suit, best_pct = _best_trump_suit(acc.trump_total, acc.trump_correct)
    bidding_style, overbid_pct = _classify_bidding_style(
        acc.overbids_count, acc.underbids_count, acc.exact_bids_count
    )
    favorite_bid = max(acc.bid_counts, key=lambda b: acc.bid_counts[b]) if acc.bid_counts else None

    return {
        "wins": acc.wins,
        "games_played": acc.games_played,
        "total_rounds": acc.total_rounds,
        "best_trump": _TRUMP_SYMBOLS.get(best_suit) if best_suit else None,
        "best_trump_pct": round(best_pct * 100) if best_suit else None,
        "trend": _classify_trend(acc.game_accuracies),
        "favorite_bid": favorite_bid,
        "biggest_round_score": acc.biggest_round_score,
        "fun_facts": _build_fun_facts(acc, favorite_bid),
        "bidding_style": bidding_style,
        "overbid_pct": overbid_pct,
        "zero_bid_rate": (
            round(acc.zero_bid_successes / acc.zero_bid_attempts * 100)
            if acc.zero_bid_attempts > 0
            else 0
        ),
        "clutch_wins": acc.comeback_wins,
        "clutch_opportunities": acc.comeback_opportunities,
        "tempo": _classify_tempo(acc.first_half_scores, acc.second_half_scores),
        "consistency": _classify_consistency(acc.game_totals),
    }


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


def compute_accuracy_by_cards_metrics(player_name: str, game_metrics_list: list) -> dict:
    """Compute bid accuracy breakdown by card count from GameMetrics objects."""
    by_cards: dict[int, dict] = {}

    for gm in game_metrics_list:
        if player_name not in gm.players:
            continue

        pm = gm.player_metrics.get(player_name)
        if pm is None:
            continue

        n = min(len(pm.bid_sequence), len(gm.cards_per_round))
        for i in range(n):
            bid, hand = pm.bid_sequence[i]
            cards = gm.cards_per_round[i]
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


# ── Bridge functions (accept game objects, convert to GameMetrics internally) ─


def _games_to_metrics(games: list) -> list:
    """Convert game-like objects (with .players and .rounds) to GameMetrics."""
    result = []
    for g in games:
        gm = compute_game_metrics(g.players, g.rounds)
        # Preserve winner from the game object if set
        if hasattr(g, "winner") and g.winner is not None:
            gm.winner = g.winner
        result.append(gm)
    return result


def compute_feature_vector(player_name: str, games: list) -> list[float]:
    """Bridge: compute 10-d feature vector from game objects.

    Converts games → GameMetrics → aggregate_career → feature_vector.
    """
    return aggregate_career(player_name, _games_to_metrics(games)).feature_vector


def compute_player_extras(player_name: str, games: list) -> dict:
    """Bridge: compute display extras dict from game objects."""
    return compute_display_extras(player_name, _games_to_metrics(games))


def compute_accuracy_by_cards(player_name: str, games: list) -> dict:
    """Compute accuracy-by-cards — accepts game objects or GameMetrics."""
    return compute_accuracy_by_cards_metrics(player_name, _games_to_metrics(games))
