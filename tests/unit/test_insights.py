"""Unit tests for player insights — feature vector computation, normalization, shrinkage."""

import math

import pytest

from app.services.insights import (
    CARD_COUNT_WEIGHTS,
    FEATURE_DIMENSIONS,
    GROWTH_TEMPLATES,
    PERSONALITY_CENTROIDS,
    STRENGTH_TEMPLATES,
    assign_personalities_unique,
    assign_personality,
    compute_accuracy_by_cards,
    compute_feature_vector,
    cosine_similarity,
    ema_update,
    generate_insights,
    james_stein_shrink,
    min_max_normalize,
)


def _make_round(cards_dealt, bids, hands_won, scores):
    """Create a mock round object for testing."""
    class MockRound:
        def __init__(self, cards_dealt, bids, hands_won, scores):
            self.cards_dealt = cards_dealt
            self.bids = bids
            self.hands_won = hands_won
            self.scores = scores
    return MockRound(cards_dealt, bids, hands_won, scores)


def _make_game(players, rounds_data, winner=None):
    """Create a mock game with rounds. winner is player name."""
    class MockGame:
        def __init__(self, players, rounds, winner):
            self.players = players
            self.rounds = rounds
            self.winner = winner
    rounds = [_make_round(*r) for r in rounds_data]
    return MockGame(players, rounds, winner)


class TestCardCountWeights:
    """Verify 1-card=0.2x, 2-card=0.5x, 3+=1.0x weighting."""

    def test_one_card_weight(self):
        assert CARD_COUNT_WEIGHTS[1] == 0.2

    def test_two_card_weight(self):
        assert CARD_COUNT_WEIGHTS[2] == 0.5

    def test_three_plus_card_weight(self):
        for cards in range(3, 9):
            assert CARD_COUNT_WEIGHTS.get(cards, 1.0) == 1.0


class TestFeatureDimensions:
    """Verify all 10 dimensions are defined."""

    def test_ten_dimensions(self):
        assert len(FEATURE_DIMENSIONS) == 10

    def test_dimension_names(self):
        expected = [
            "bid_accuracy", "overbid_ratio", "underbid_ratio",
            "score_variance", "zero_bid_success", "high_card_accuracy",
            "low_card_accuracy", "tempo_first_half", "tempo_second_half",
            "comeback_rate",
        ]
        assert expected == FEATURE_DIMENSIONS


class TestFeatureVectorBasic:
    """Test feature vector computation with simple data."""

    def test_perfect_accuracy_all_rounds(self):
        """Player bids correctly every time → accuracy = 1.0."""
        # 3 games, player 0 always bids 2 on 5 cards and makes it
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            ))
        vector = compute_feature_vector("Alice", games)
        # dim 0 = bid_accuracy
        assert vector[0] == pytest.approx(1.0)

    def test_zero_accuracy(self):
        """Player never makes a bid → accuracy = 0.0."""
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30}),
                ],
                winner="Bob",
            ))
        vector = compute_feature_vector("Alice", games)
        assert vector[0] == pytest.approx(0.0)

    def test_overbid_ratio(self):
        """Player always overbids → overbid_ratio = 1.0."""
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 3, "1": 2}, {"0": 1, "1": 2}, {"0": -30, "1": 20}),
                ],
                winner="Bob",
            ))
        vector = compute_feature_vector("Alice", games)
        # dim 1 = overbid_ratio
        assert vector[1] == pytest.approx(1.0)
        # dim 2 = underbid_ratio should be 0
        assert vector[2] == pytest.approx(0.0)

    def test_underbid_ratio(self):
        """Player always underbids → underbid_ratio = 1.0."""
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 1, "1": 2}, {"0": 3, "1": 2}, {"0": -10, "1": 20}),
                ],
                winner="Bob",
            ))
        vector = compute_feature_vector("Alice", games)
        assert vector[2] == pytest.approx(1.0)
        assert vector[1] == pytest.approx(0.0)


class TestFeatureVectorWeighting:
    """Test that 1-card and 2-card rounds are down-weighted."""

    def test_one_card_round_weighted_down(self):
        """Accuracy on 1-card round contributes 0.2x weight."""
        # Game 1: 1-card round, Alice correct
        # Game 2: 5-card round, Alice incorrect
        # Game 3: 5-card round, Alice incorrect
        # Without weighting: 1/3 = 33% accuracy
        # With weighting: 0.2 / (0.2 + 1.0 + 1.0) = 0.2/2.2 ≈ 9.1%
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(1, {"0": 0, "1": 1}, {"0": 0, "1": 1}, {"0": 10, "1": 11})],
                winner="Bob",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30})],
                winner="Bob",
            ),
        ]
        vector = compute_feature_vector("Alice", games)
        expected_accuracy = 0.2 / (0.2 + 1.0 + 1.0)
        assert vector[0] == pytest.approx(expected_accuracy, abs=0.01)

    def test_two_card_round_weighted(self):
        """Accuracy on 2-card round contributes 0.5x weight."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(2, {"0": 1, "1": 1}, {"0": 1, "1": 1}, {"0": 11, "1": 11})],
                winner="Alice",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30})],
                winner="Bob",
            ),
        ]
        vector = compute_feature_vector("Alice", games)
        expected_accuracy = 0.5 / (0.5 + 1.0 + 1.0)
        assert vector[0] == pytest.approx(expected_accuracy, abs=0.01)


class TestFeatureVectorZeroBid:
    """Test zero-bid success rate (dimension 4)."""

    def test_perfect_zero_bids(self):
        """Player always bids 0 and wins 0 → zero_bid_success = 1.0."""
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 0, "1": 5}, {"0": 0, "1": 5}, {"0": 10, "1": 50}),
                ],
                winner="Bob",
            ))
        vector = compute_feature_vector("Alice", games)
        assert vector[4] == pytest.approx(1.0)

    def test_failed_zero_bids(self):
        """Player bids 0 but wins hands → zero_bid_success = 0.0."""
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 0, "1": 5}, {"0": 2, "1": 3}, {"0": -10, "1": -50}),
                ],
                winner="Alice",
            ))
        vector = compute_feature_vector("Alice", games)
        assert vector[4] == pytest.approx(0.0)

    def test_no_zero_bids(self):
        """Player never bids 0 → zero_bid_success = 0.0 (no data)."""
        games = []
        for _ in range(3):
            games.append(_make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
                ],
                winner="Alice",
            ))
        vector = compute_feature_vector("Alice", games)
        assert vector[4] == pytest.approx(0.0)


class TestFeatureVectorTempo:
    """Test tempo dimensions (1st half vs 2nd half)."""

    def test_strong_first_half(self):
        """Player scores well in 1st half, poorly in 2nd → tempo_first > tempo_second."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                # 1st half (rounds 1-2): Alice scores high
                (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
                (4, {"0": 2, "1": 2}, {"0": 2, "1": 2}, {"0": 20, "1": 20}),
                # 2nd half (rounds 3-4): Alice scores low
                (3, {"0": 2, "1": 1}, {"0": 0, "1": 1}, {"0": -20, "1": 11}),
                (2, {"0": 1, "1": 1}, {"0": 0, "1": 1}, {"0": -10, "1": 11}),
            ],
            winner="Bob",
        )] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 7 = tempo_first_half, dim 8 = tempo_second_half
        assert vector[7] > vector[8]


class TestFeatureVectorHighLowCards:
    """Test high-card and low-card accuracy dimensions."""

    def test_high_card_specialist(self):
        """Perfect accuracy on 6-8 cards, zero on 1-3 → high > low."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (8, {"0": 3, "1": 5}, {"0": 3, "1": 5}, {"0": 30, "1": 50}),
                (2, {"0": 1, "1": 1}, {"0": 0, "1": 1}, {"0": -10, "1": 11}),
            ],
            winner="Bob",
        )] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 5 = high_card_accuracy, dim 6 = low_card_accuracy
        assert vector[5] == pytest.approx(1.0)
        assert vector[6] == pytest.approx(0.0)


class TestFeatureVectorComeback:
    """Test comeback rate dimension."""

    def test_comeback_win(self):
        """Player behind at halfway but wins → comeback_rate = 1.0."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                # 1st half: Alice behind
                (5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30}),
                (4, {"0": 2, "1": 2}, {"0": 0, "1": 2}, {"0": -20, "1": 20}),
                # 2nd half: Alice catches up
                (3, {"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": -10}),
                (2, {"0": 2, "1": 0}, {"0": 2, "1": 0}, {"0": 20, "1": -10}),
            ],
            winner="Alice",
        )] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 9 = comeback_rate
        assert vector[9] == pytest.approx(1.0)

    def test_no_comeback_opportunities(self):
        """Player always leads → comeback_rate = 0.0."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
                (4, {"0": 2, "1": 2}, {"0": 2, "1": 2}, {"0": 20, "1": 20}),
                (3, {"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}),
                (2, {"0": 1, "1": 1}, {"0": 1, "1": 1}, {"0": 11, "1": 11}),
            ],
            winner="Alice",
        )] * 3
        vector = compute_feature_vector("Alice", games)
        assert vector[9] == pytest.approx(0.0)


class TestFeatureVectorScoreVariance:
    """Test score variance dimension."""

    def test_consistent_scores(self):
        """Same total score every game → variance = 0.0."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
            ],
            winner="Bob",
        )] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 3 = score_variance (stddev), same score each game → 0
        assert vector[3] == pytest.approx(0.0)

    def test_variable_scores(self):
        """Different scores each game → variance > 0."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 50, "1": 30})],
                winner="Alice",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 10, "1": 30})],
                winner="Bob",
            ),
        ]
        vector = compute_feature_vector("Alice", games)
        # Scores: 50, -20, 10 → stddev > 0
        assert vector[3] > 0


class TestFeatureVectorEdgeCases:
    """Edge cases for feature vector computation."""

    def test_player_not_in_game(self):
        """Player not in some games — only counts games they played."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                players=["Charlie", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
                winner="Bob",
            ),
        ]
        vector = compute_feature_vector("Alice", games)
        # Alice only in 2 games, should still compute
        assert vector[0] == pytest.approx(1.0)  # perfect accuracy

    def test_returns_ten_dimensions(self):
        """Vector always has exactly 10 dimensions."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
            winner="Bob",
        )] * 3
        vector = compute_feature_vector("Alice", games)
        assert len(vector) == 10
        # All values should be finite numbers
        for value in vector:
            assert math.isfinite(value)


class TestMinMaxNormalize:
    """Test min-max normalization across players."""

    def test_two_players_opposite_extremes(self):
        """One player max, one min → normalized to 1.0 and 0.0."""
        vectors = {
            "Alice": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "Bob":   [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }
        result = min_max_normalize(vectors)
        assert result["Alice"][0] == pytest.approx(1.0)
        assert result["Bob"][0] == pytest.approx(0.0)
        assert result["Alice"][1] == pytest.approx(0.0)
        assert result["Bob"][1] == pytest.approx(1.0)

    def test_single_player_gets_centered(self):
        """Single player → all dimensions = 0.5."""
        vectors = {"Alice": [0.8, 0.3, 0.5, 10.0, 0.9, 0.7, 0.2, 5.0, -3.0, 0.5]}
        result = min_max_normalize(vectors)
        for dim_value in result["Alice"]:
            assert dim_value == pytest.approx(0.5)

    def test_three_players_middle_value(self):
        """Middle player gets proportional value."""
        vectors = {
            "Alice": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "Bob":   [0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "Charlie": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }
        result = min_max_normalize(vectors)
        assert result["Alice"][0] == pytest.approx(0.0)
        assert result["Bob"][0] == pytest.approx(0.5)
        assert result["Charlie"][0] == pytest.approx(1.0)

    def test_same_value_all_players_gets_centered(self):
        """All players have same value for a dimension → 0.5."""
        vectors = {
            "Alice": [0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "Bob":   [0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }
        result = min_max_normalize(vectors)
        assert result["Alice"][0] == pytest.approx(0.5)
        assert result["Bob"][0] == pytest.approx(0.5)

    def test_preserves_all_dimensions(self):
        """Output has same players and 10 dimensions each."""
        vectors = {
            "Alice": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "Bob":   [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
        }
        result = min_max_normalize(vectors)
        assert set(result.keys()) == {"Alice", "Bob"}
        assert len(result["Alice"]) == 10
        assert len(result["Bob"]) == 10


class TestJamesSteinShrinkage:
    """Test James-Stein shrinkage toward population mean."""

    def test_high_game_count_minimal_shrinkage(self):
        """With many games, player vector stays close to raw value."""
        player_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        population_mean = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        result = james_stein_shrink(player_vector, population_mean, games_played=50)
        # With 50 games, should be very close to raw vector
        assert result[0] > 0.9

    def test_low_game_count_heavy_shrinkage(self):
        """With few games, player vector shrinks heavily toward population mean."""
        player_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        population_mean = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        result_3 = james_stein_shrink(player_vector, population_mean, games_played=3)
        result_50 = james_stein_shrink(player_vector, population_mean, games_played=50)
        # With 3 games, should be much closer to mean than with 50
        assert result_3[0] < result_50[0]

    def test_shrinkage_preserves_dimensions(self):
        """Output has exactly 10 dimensions."""
        player_vector = [0.1] * 10
        population_mean = [0.5] * 10
        result = james_stein_shrink(player_vector, population_mean, games_played=5)
        assert len(result) == 10

    def test_player_at_mean_stays_at_mean(self):
        """If player equals population mean, shrinkage has no effect."""
        mean = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        result = james_stein_shrink(mean[:], mean, games_played=3)
        for i in range(10):
            assert result[i] == pytest.approx(0.5)

    def test_all_finite_values(self):
        """Result never contains NaN or Inf."""
        player_vector = [0.0] * 10
        population_mean = [0.0] * 10
        result = james_stein_shrink(player_vector, population_mean, games_played=3)
        for value in result:
            assert math.isfinite(value)


class TestEmaUpdate:
    """Test exponential moving average for vector smoothing."""

    def test_first_computation_uses_raw(self):
        """No stored vector → returns new vector unchanged."""
        new_vector = [0.8, 0.2, 0.5, 0.3, 0.9, 0.1, 0.7, 0.4, 0.6, 0.5]
        result = ema_update(new_vector, stored_vector=None)
        for i in range(10):
            assert result[i] == pytest.approx(new_vector[i])

    def test_blends_with_stored(self):
        """With stored vector, result is between new and stored."""
        new_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        stored = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = ema_update(new_vector, stored)
        # alpha=0.3: result[0] = 0.3*1.0 + 0.7*0.0 = 0.3
        assert result[0] == pytest.approx(0.3)
        # result[1] = 0.3*0.0 + 0.7*1.0 = 0.7
        assert result[1] == pytest.approx(0.7)

    def test_preserves_dimensions(self):
        """Output has 10 dimensions."""
        result = ema_update([0.5] * 10, [0.5] * 10)
        assert len(result) == 10


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self):
        """Same vector → similarity = 1.0."""
        vec = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Perpendicular vectors → similarity = 0.0."""
        vec_a = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self):
        """Zero vector → similarity = 0.0 (no crash)."""
        vec_a = [0.0] * 10
        vec_b = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)


class TestPersonalityCentroids:
    """Test centroid definitions."""

    def test_ten_personalities_defined(self):
        """All 10 personalities have centroids."""
        assert len(PERSONALITY_CENTROIDS) == 10

    def test_centroids_are_ten_dimensional(self):
        """Each centroid has 10 dimensions."""
        for name, centroid in PERSONALITY_CENTROIDS.items():
            assert len(centroid) == 10, f"{name} centroid has {len(centroid)} dims"

    def test_centroids_are_unit_length(self):
        """Each centroid is normalized to unit length."""
        for name, centroid in PERSONALITY_CENTROIDS.items():
            magnitude = math.sqrt(sum(c ** 2 for c in centroid))
            assert magnitude == pytest.approx(1.0, abs=0.01), (
                f"{name} centroid magnitude = {magnitude}"
            )


class TestAssignPersonality:
    """Test personality assignment from feature vector."""

    def test_sniper_assignment(self):
        """High accuracy vector → assigned as sniper."""
        # Vector with very high accuracy (dim 0), moderate everything else
        vector = [1.0, 0.0, 0.0, 0.3, 0.5, 0.8, 0.8, 0.5, 0.5, 0.3]
        result = assign_personality(vector)
        assert result["personality"] == "sniper"

    def test_ghost_assignment(self):
        """High zero-bid success → assigned as ghost."""
        vector = [0.5, 0.0, 0.3, 0.3, 1.0, 0.4, 0.5, 0.5, 0.5, 0.3]
        result = assign_personality(vector)
        assert result["personality"] == "ghost"

    def test_wildcard_assignment(self):
        """High variance → assigned as wildcard."""
        vector = [0.4, 0.5, 0.5, 1.0, 0.3, 0.4, 0.4, 0.5, 0.5, 0.4]
        result = assign_personality(vector)
        assert result["personality"] == "wildcard"

    def test_result_has_confidence(self):
        """Result includes confidence score and gap."""
        vector = [1.0, 0.0, 0.0, 0.3, 0.5, 0.8, 0.8, 0.5, 0.5, 0.3]
        result = assign_personality(vector)
        assert "confidence" in result
        assert "confidence_gap" in result
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["confidence_gap"] >= 0.0

    def test_all_zeros_still_assigns(self):
        """Zero vector still gets a personality (no crash)."""
        vector = [0.0] * 10
        result = assign_personality(vector)
        assert result["personality"] in PERSONALITY_CENTROIDS

    def test_excluded_personalities_skipped(self):
        """Excluded personalities are not assigned."""
        vector = [1.0, 0.0, 0.0, 0.3, 0.5, 0.8, 0.8, 0.5, 0.5, 0.3]
        result_free = assign_personality(vector)
        assert result_free["personality"] == "sniper"
        result_excluded = assign_personality(vector, excluded={"sniper"})
        assert result_excluded["personality"] != "sniper"


class TestUniqueAssignment:
    """Test draft-style unique personality assignment."""

    def test_all_players_get_unique_personalities(self):
        """No two players share a personality when <= 10 players."""
        vectors = {
            "Alice": [0.9, 0.1, 0.1, 0.2, 0.5, 0.8, 0.3, 0.5, 0.5, 0.3],
            "Bob":   [0.3, 0.9, 0.1, 0.7, 0.1, 0.4, 0.2, 0.5, 0.5, 0.3],
            "Charlie": [0.5, 0.1, 0.1, 0.1, 0.9, 0.4, 0.5, 0.5, 0.5, 0.3],
        }
        results = assign_personalities_unique(vectors)
        personalities = [r["personality"] for r in results.values()]
        assert len(set(personalities)) == 3  # all unique

    def test_similar_players_still_get_different(self):
        """Even very similar players get different personalities."""
        base = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        vectors = {
            "Alice": base[:],
            "Bob": base[:],
            "Charlie": base[:],
        }
        results = assign_personalities_unique(vectors)
        personalities = [r["personality"] for r in results.values()]
        assert len(set(personalities)) == 3

    def test_all_players_assigned(self):
        """Every player gets an assignment."""
        vectors = {f"Player{i}": [0.5] * 10 for i in range(5)}
        results = assign_personalities_unique(vectors)
        assert len(results) == 5
        for result in results.values():
            assert "personality" in result
            assert "confidence" in result

    def test_empty_input(self):
        """Empty vectors dict returns empty results."""
        assert assign_personalities_unique({}) == {}


class TestGenerateInsights:
    """Test insight generation — 1 strength + 1 growth tip."""

    def test_returns_two_insights(self):
        """Always produces exactly 2 insights."""
        vector = [0.9, 0.1, 0.1, 0.2, 0.5, 0.8, 0.3, 0.5, 0.5, 0.3]
        insights = generate_insights(vector, "sniper")
        assert len(insights) == 2

    def test_strength_and_growth_different_categories(self):
        """Strength and growth tip reference different dimensions."""
        vector = [0.9, 0.1, 0.1, 0.2, 0.5, 0.8, 0.3, 0.5, 0.5, 0.3]
        insights = generate_insights(vector, "sniper")
        # Both should be non-empty strings
        assert isinstance(insights[0], str) and len(insights[0]) > 0
        assert isinstance(insights[1], str) and len(insights[1]) > 0
        # Should not be identical
        assert insights[0] != insights[1]

    def test_all_personalities_produce_insights(self):
        """Every personality type can generate insights."""
        base_vector = [0.5] * 10
        for personality in PERSONALITY_CENTROIDS:
            insights = generate_insights(base_vector, personality)
            assert len(insights) == 2, f"{personality} produced {len(insights)} insights"

    def test_templates_exist_for_all_dimensions(self):
        """Strength and growth templates cover all 10 dimensions."""
        assert len(STRENGTH_TEMPLATES) == 10
        assert len(GROWTH_TEMPLATES) == 10


class TestAccuracyByCards:
    """Test per-card-count accuracy computation."""

    def test_basic_accuracy(self):
        """Correct breakdown for different card counts."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (8, {"0": 3, "1": 5}, {"0": 3, "1": 5}, {"0": 30, "1": 50}),
                (5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30}),
                (3, {"0": 1, "1": 2}, {"0": 1, "1": 2}, {"0": 11, "1": 20}),
            ],
            winner="Bob",
        )]
        result = compute_accuracy_by_cards("Alice", games)
        assert result["8"]["pct"] == 100
        assert result["8"]["rounds"] == 1
        assert result["5"]["pct"] == 0
        assert result["5"]["rounds"] == 1
        assert result["3"]["pct"] == 100
        assert result["3"]["rounds"] == 1

    def test_multiple_games_aggregate(self):
        """Accuracy aggregates across multiple games."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            ),
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30}),
                ],
                winner="Bob",
            ),
        ]
        result = compute_accuracy_by_cards("Alice", games)
        assert result["5"]["pct"] == 50  # 1 out of 2
        assert result["5"]["rounds"] == 2

    def test_no_rounds_for_card_count(self):
        """Card counts with no data are not in result."""
        games = [_make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
            ],
            winner="Bob",
        )]
        result = compute_accuracy_by_cards("Alice", games)
        assert "5" in result
        assert "8" not in result

    def test_player_not_in_game_skipped(self):
        """Games where player didn't participate are skipped."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                players=["Charlie", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
                winner="Bob",
            ),
        ]
        result = compute_accuracy_by_cards("Alice", games)
        assert result["5"]["rounds"] == 1
