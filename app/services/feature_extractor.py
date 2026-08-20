"""Feature extraction from game data — vectors, accuracy, player extras.

Extracts numerical features from round-level game data for personality
assignment and player insight cards.
"""

import math

# Card-count weights: 1-card rounds ~80% luck, 2-card ~50%, 3+ = skill
CARD_COUNT_WEIGHTS = {1: 0.2, 2: 0.5}

# High-card rounds: 6+ cards dealt (more skill, less luck)
HIGH_CARD_THRESHOLD = 6
# Low-card rounds: 3 or fewer cards dealt (more luck)
LOW_CARD_THRESHOLD = 3

# Minimum rounds for meaningful comeback detection
MIN_ROUNDS_FOR_COMEBACK = 4

# Trend detection: accuracy improvement threshold between game halves
TREND_IMPROVEMENT_THRESHOLD = 0.1

# Tempo detection: avg score difference threshold between game halves
TEMPO_DIFFERENCE_THRESHOLD = 3

# Consistency buckets: stddev of per-game total scores
# Kachuful totals range ~50-300, so stddev needs higher thresholds
CONSISTENCY_HIGH_THRESHOLD = 60    # below = reliable
CONSISTENCY_MEDIUM_THRESHOLD = 120  # below = mixed, above = unpredictable

# Bidding style: minimum gap between overbids and underbids (as % of total)
STYLE_MARGIN_PCT = 10

# Minimum rounds on a trump suit before it counts as "best suit"
MIN_ROUNDS_FOR_BEST_SUIT = 2

# Fun fact thresholds
BIG_ROUND_SCORE_THRESHOLD = 40
NOTABLE_ZERO_STREAK = 3
HIGH_FAVORITE_BID = 4
REMARKABLE_BID = 6

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

TRUMP_SUITS = ["spades", "diamonds", "clubs", "hearts"]
TRUMP_SYMBOLS = {"spades": "♠", "diamonds": "♦", "clubs": "♣", "hearts": "♥"}


def _weight_for_cards(cards_dealt: int) -> float:
    """Return the weight for a round based on cards dealt."""
    return CARD_COUNT_WEIGHTS.get(cards_dealt, 1.0)


def _safe_divide(numerator: float, denominator: float) -> float:
    """Divide safely, returning 0.0 if denominator is zero."""
    return numerator / denominator if denominator > 0 else 0.0


def _stddev(values: list[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _compute_halfway_scores(game) -> dict[str, int]:
    """Compute cumulative scores at the halfway point of a game."""
    rounds_list = game.rounds
    halfway = len(rounds_list) // 2
    scores: dict[str, int] = dict.fromkeys(game.players, 0)
    for rnd_idx, rnd in enumerate(rounds_list):
        if rnd_idx >= halfway:
            break
        for idx_str, score_val in rnd.scores.items():
            idx = int(idx_str)
            if idx < len(game.players):
                scores[game.players[idx]] += score_val
    return scores


def _get_player_round_data(rnd, player_idx_str: str):
    """Extract bid, hand, score for a player from a round. Returns None if missing."""
    bid = rnd.bids.get(player_idx_str)
    hand = rnd.hands_won.get(player_idx_str)
    if bid is None or hand is None:
        return None
    score = rnd.scores.get(player_idx_str, 0)
    return bid, hand, score


def compute_feature_vector(player_name: str, games: list) -> list[float]:
    """Compute a 10-dimension feature vector for a player across all games."""
    accum = _FeatureAccumulator()

    for game in games:
        if player_name not in game.players:
            continue
        player_idx_str = str(game.players.index(player_name))
        accum.process_game(game, player_name, player_idx_str)

    return accum.to_vector()


class _FeatureAccumulator:
    """Accumulates round-level data and produces a 10-d feature vector."""

    def __init__(self):
        self.weighted_correct = 0.0
        self.weighted_overbids = 0.0
        self.weighted_underbids = 0.0
        self.weighted_total = 0.0
        self.zero_bid_attempts = 0
        self.zero_bid_successes = 0
        self.high_card_correct = 0.0
        self.high_card_total = 0.0
        self.low_card_correct = 0.0
        self.low_card_total = 0.0
        self.first_half_score_sum = 0.0
        self.first_half_round_count = 0
        self.second_half_score_sum = 0.0
        self.second_half_round_count = 0
        self.comeback_opportunities = 0
        self.comeback_wins = 0
        self.game_scores: list[float] = []

    def process_game(self, game, player_name: str, player_idx_str: str):
        """Process all rounds in a single game."""
        halfway = len(game.rounds) // 2
        game_total_score = 0.0

        for round_idx, rnd in enumerate(game.rounds):
            data = _get_player_round_data(rnd, player_idx_str)
            if data is None:
                continue
            bid, hand, score = data
            self._process_round(bid, hand, score, rnd.cards_dealt, round_idx, halfway)
            game_total_score += score

        self.game_scores.append(game_total_score)
        self._check_comeback(game, player_name, halfway)

    def _process_round(self, bid, hand, score, cards_dealt, round_idx, halfway):
        weight = _weight_for_cards(cards_dealt)
        made = bid == hand

        self._track_accuracy(weight, made, bid, hand)
        self._track_card_range(cards_dealt, made)
        self._track_tempo(score, round_idx, halfway)

        if bid == 0:
            self.zero_bid_attempts += 1
            if hand == 0:
                self.zero_bid_successes += 1

    def _track_accuracy(self, weight, made, bid, hand):
        self.weighted_total += weight
        if made:
            self.weighted_correct += weight
        elif bid > hand:
            self.weighted_overbids += weight
        else:
            self.weighted_underbids += weight

    def _track_card_range(self, cards_dealt, made):
        if cards_dealt >= HIGH_CARD_THRESHOLD:
            self.high_card_total += 1.0
            if made:
                self.high_card_correct += 1.0
        if cards_dealt <= LOW_CARD_THRESHOLD:
            low_weight = _weight_for_cards(cards_dealt)
            self.low_card_total += low_weight
            if made:
                self.low_card_correct += low_weight

    def _track_tempo(self, score, round_idx, halfway):
        if round_idx < halfway:
            self.first_half_score_sum += score
            self.first_half_round_count += 1
        else:
            self.second_half_score_sum += score
            self.second_half_round_count += 1

    def _check_comeback(self, game, player_name: str, halfway: int):
        if len(game.rounds) < MIN_ROUNDS_FOR_COMEBACK:
            return
        halfway_scores = _compute_halfway_scores(game)
        halfway_leader = max(halfway_scores, key=lambda n: halfway_scores[n])
        if player_name != halfway_leader:
            self.comeback_opportunities += 1
            if game.winner == player_name:
                self.comeback_wins += 1

    def to_vector(self) -> list[float]:
        return [
            _safe_divide(self.weighted_correct, self.weighted_total),
            _safe_divide(self.weighted_overbids, self.weighted_total),
            _safe_divide(self.weighted_underbids, self.weighted_total),
            _stddev(self.game_scores),
            _safe_divide(self.zero_bid_successes, self.zero_bid_attempts),
            _safe_divide(self.high_card_correct, self.high_card_total),
            _safe_divide(self.low_card_correct, self.low_card_total),
            _safe_divide(self.first_half_score_sum, self.first_half_round_count),
            _safe_divide(self.second_half_score_sum, self.second_half_round_count),
            _safe_divide(self.comeback_wins, self.comeback_opportunities),
        ]


def compute_accuracy_by_cards(player_name: str, games: list) -> dict:
    """Compute bid accuracy breakdown by cards dealt (unweighted, for display)."""
    by_cards: dict[int, dict] = {}

    for game in games:
        if player_name not in game.players:
            continue
        player_idx_str = str(game.players.index(player_name))

        for rnd in game.rounds:
            data = _get_player_round_data(rnd, player_idx_str)
            if data is None:
                continue
            bid, hand, _score = data
            cards = rnd.cards_dealt
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


def compute_player_extras(player_name: str, games: list) -> dict:
    """Compute additional stats for the player card."""
    accum = _ExtrasAccumulator()

    for game in games:
        if player_name not in game.players:
            continue
        accum.process_game(game, player_name)

    return accum.to_dict()


class _ExtrasAccumulator:
    """Accumulates data for player extras (bidding style, clutch, tempo, etc.)."""

    def __init__(self):
        self.wins = 0
        self.games_played = 0
        self.total_rounds = 0
        self.biggest_round_score = 0
        self.bid_counts: dict[int, int] = {}
        self.trump_correct: dict[str, int] = {}
        self.trump_total: dict[str, int] = {}
        self.zero_bid_attempts = 0
        self.zero_bid_successes = 0
        self.zero_bid_streak = 0
        self.max_zero_streak = 0
        self.overbids = 0
        self.underbids = 0
        self.exact_bids = 0
        self.first_half_scores: list[float] = []
        self.second_half_scores: list[float] = []
        self.game_totals: list[int] = []
        self.comeback_wins = 0
        self.comeback_opportunities = 0
        self.game_accuracies: list[float] = []

    def process_game(self, game, player_name: str):
        player_idx_str = str(game.players.index(player_name))
        self.games_played += 1
        if game.winner == player_name:
            self.wins += 1

        game_correct = 0
        game_total = 0
        halfway = len(game.rounds) // 2

        for round_idx, rnd in enumerate(game.rounds):
            data = _get_player_round_data(rnd, player_idx_str)
            if data is None:
                continue
            bid, hand, score = data
            self._process_round(bid, hand, score, rnd, round_idx, halfway)
            game_total += 1
            if bid == hand:
                game_correct += 1

        game_score = sum(
            rnd.scores.get(player_idx_str, 0)
            for rnd in game.rounds
            if rnd.bids.get(player_idx_str) is not None
        )
        self.game_totals.append(game_score)
        self._check_comeback(game, player_name)

        if game_total > 0:
            self.game_accuracies.append(game_correct / game_total)

    def _process_round(self, bid, hand, score, rnd, round_idx, halfway):
        self.total_rounds += 1
        made = bid == hand

        if score > self.biggest_round_score:
            self.biggest_round_score = score

        self.bid_counts[bid] = self.bid_counts.get(bid, 0) + 1
        self._track_bid_direction(bid, hand)
        self._track_trump(rnd, made)
        self._track_zero_bids(bid, hand)
        self._track_tempo(score, round_idx, halfway)

    def _track_bid_direction(self, bid, hand):
        if bid > hand:
            self.overbids += 1
        elif bid < hand:
            self.underbids += 1
        else:
            self.exact_bids += 1

    def _track_trump(self, rnd, made):
        trump = rnd.trump_suit if hasattr(rnd, "trump_suit") else None
        if not trump:
            return
        trump_lower = trump.lower()
        self.trump_total[trump_lower] = self.trump_total.get(trump_lower, 0) + 1
        if made:
            self.trump_correct[trump_lower] = self.trump_correct.get(trump_lower, 0) + 1

    def _track_zero_bids(self, bid, hand):
        if bid != 0:
            return
        self.zero_bid_attempts += 1
        if hand == 0:
            self.zero_bid_successes += 1
            self.zero_bid_streak += 1
            if self.zero_bid_streak > self.max_zero_streak:
                self.max_zero_streak = self.zero_bid_streak
        else:
            self.zero_bid_streak = 0

    def _track_tempo(self, score, round_idx, halfway):
        if round_idx < halfway:
            self.first_half_scores.append(score)
        else:
            self.second_half_scores.append(score)

    def _check_comeback(self, game, player_name: str):
        if len(game.rounds) < 4:
            return
        halfway_scores = _compute_halfway_scores(game)
        halfway_leader = max(halfway_scores, key=lambda n: halfway_scores[n])
        if player_name != halfway_leader:
            self.comeback_opportunities += 1
            if game.winner == player_name:
                self.comeback_wins += 1

    def _best_trump(self) -> tuple[str | None, int]:
        best_suit = None
        best_pct = 0
        for suit in TRUMP_SUITS:
            total = self.trump_total.get(suit, 0)
            if total >= MIN_ROUNDS_FOR_BEST_SUIT:
                pct = self.trump_correct.get(suit, 0) / total
                if pct > best_pct:
                    best_pct = pct
                    best_suit = suit
        return best_suit, round(best_pct * 100) if best_suit else 0

    def _trend(self) -> str:
        if len(self.game_accuracies) < MIN_ROUNDS_FOR_COMEBACK:
            return "steady"
        mid = len(self.game_accuracies) // 2
        first_avg = sum(self.game_accuracies[:mid]) / mid
        second_avg = sum(self.game_accuracies[mid:]) / (len(self.game_accuracies) - mid)
        diff = second_avg - first_avg
        if diff > TREND_IMPROVEMENT_THRESHOLD:
            return "improving"
        if diff < -TREND_IMPROVEMENT_THRESHOLD:
            return "declining"
        return "steady"

    def _bidding_style(self) -> tuple[str, int]:
        total_bids = self.overbids + self.underbids + self.exact_bids
        if total_bids == 0:
            return "balanced", 0
        overbid_pct = round(self.overbids / total_bids * 100)
        underbid_pct = round(self.underbids / total_bids * 100)
        gap = abs(overbid_pct - underbid_pct)
        if gap < STYLE_MARGIN_PCT:
            return "balanced", overbid_pct
        if self.overbids > self.underbids:
            return "aggressive", overbid_pct
        return "conservative", underbid_pct

    def _tempo(self) -> str:
        first_avg = (
            sum(self.first_half_scores) / len(self.first_half_scores)
            if self.first_half_scores else 0
        )
        second_avg = (
            sum(self.second_half_scores) / len(self.second_half_scores)
            if self.second_half_scores else 0
        )
        if first_avg - second_avg > TEMPO_DIFFERENCE_THRESHOLD:
            return "1st half"
        if second_avg - first_avg > TEMPO_DIFFERENCE_THRESHOLD:
            return "2nd half"
        return "even"

    def _consistency(self) -> str:
        stddev = _stddev([float(s) for s in self.game_totals])
        if stddev < CONSISTENCY_HIGH_THRESHOLD:
            return "high"
        if stddev < CONSISTENCY_MEDIUM_THRESHOLD:
            return "medium"
        return "low"

    def _fun_facts(self, favorite_bid) -> list[str]:
        facts = []
        if self.biggest_round_score >= BIG_ROUND_SCORE_THRESHOLD:
            facts.append(f"Scored +{self.biggest_round_score} in a single round")
        if self.max_zero_streak >= NOTABLE_ZERO_STREAK:
            facts.append(f"Nailed {self.max_zero_streak} zero bids in a row")
        if favorite_bid is not None and favorite_bid >= HIGH_FAVORITE_BID:
            facts.append(f"Loves bidding {favorite_bid}")
        elif favorite_bid == 0:
            facts.append("Favorite bid: zero")
        highest_bid = max(self.bid_counts.keys()) if self.bid_counts else 0
        if highest_bid >= REMARKABLE_BID:
            facts.append(f"Once bid {highest_bid}")
        return facts

    def to_dict(self) -> dict:
        best_suit, best_suit_pct = self._best_trump()
        style, overbid_pct = self._bidding_style()
        favorite_bid = (
            max(self.bid_counts, key=lambda b: self.bid_counts[b])
            if self.bid_counts else None
        )

        return {
            "wins": self.wins,
            "games_played": self.games_played,
            "total_rounds": self.total_rounds,
            "best_trump": TRUMP_SYMBOLS.get(best_suit) if best_suit else None,
            "best_trump_pct": best_suit_pct if best_suit else None,
            "trend": self._trend(),
            "favorite_bid": favorite_bid,
            "biggest_round_score": self.biggest_round_score,
            "fun_facts": self._fun_facts(favorite_bid),
            "bidding_style": style,
            "overbid_pct": overbid_pct,
            "zero_bid_rate": (
                round(self.zero_bid_successes / self.zero_bid_attempts * 100)
                if self.zero_bid_attempts > 0 else 0
            ),
            "clutch_wins": self.comeback_wins,
            "clutch_opportunities": self.comeback_opportunities,
            "tempo": self._tempo(),
            "consistency": self._consistency(),
        }
