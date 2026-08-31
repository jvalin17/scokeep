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
    backfill_meta,
    bayesian_shrink,
    compute_accuracy_by_cards,
    compute_feature_vector,
    compute_player_extras,
    cosine_similarity,
    ema_update,
    generate_insights,
    global_z_normalize,
)


def _make_round(cards_dealt, bids, hands_won, scores, trump_suit="spades"):
    """Create a mock round object for testing."""

    class MockRound:
        def __init__(self, cards_dealt, bids, hands_won, scores, trump_suit):
            self.cards_dealt = cards_dealt
            self.bids = bids
            self.hands_won = hands_won
            self.scores = scores
            self.trump_suit = trump_suit

    return MockRound(cards_dealt, bids, hands_won, scores, trump_suit)


def _make_game(players, rounds_data, winner=None):
    """Create a mock game with rounds. winner is player name.

    rounds_data: list of tuples. Each tuple is either:
      (cards_dealt, bids, hands_won, scores) — trump defaults to "spades"
      (cards_dealt, bids, hands_won, scores, trump_suit)
    """

    class MockGame:
        def __init__(self, players, rounds, winner):
            self.players = players
            self.rounds = rounds
            self.winner = winner

    rounds = []
    for r in rounds_data:
        if len(r) == 5:
            rounds.append(_make_round(*r))
        else:
            rounds.append(_make_round(*r, trump_suit="spades"))
    return MockGame(players, rounds, winner)


# Trump suits cycle: spades → diamonds → clubs → hearts
TRUMP_CYCLE = ["spades", "diamonds", "clubs", "hearts"]


def _make_realistic_game(players, round_results, winner=None):
    """Build a realistic multi-round game with descending card counts.

    round_results: list of dicts per round, each with:
        {player_name: (bid, hands_won, score)}
    Cards dealt descend from len(round_results) + starting card count.
    If winner is None, computed from total scores.
    """
    rounds_data = []
    start_cards = len(round_results)
    for round_idx, result in enumerate(round_results):
        cards = start_cards - round_idx
        if cards < 1:
            cards = round_idx - start_cards + 2  # ascending after 1
        trump = TRUMP_CYCLE[round_idx % 4]
        bids = {}
        hands = {}
        scores = {}
        for player_idx, name in enumerate(players):
            if name in result:
                bid, hand, score = result[name]
                idx_str = str(player_idx)
                bids[idx_str] = bid
                hands[idx_str] = hand
                scores[idx_str] = score
        rounds_data.append((cards, bids, hands, scores, trump))

    if winner is None:
        totals = dict.fromkeys(players, 0)
        for result in round_results:
            for name, (_, _, score) in result.items():
                totals[name] += score
        winner = max(totals, key=lambda n: totals[n])

    return _make_game(players, rounds_data, winner)


class TestBackfillMeta:
    """Cached insights blobs without meta get backfilled from PERSONALITY_META."""

    def test_adds_meta_when_missing(self):
        blob = {
            "players": {
                "Ravi": {"personality": "sniper", "games_analyzed": 5},
                "Meera": {"personality": "phoenix", "games_analyzed": 4},
            },
        }
        result = backfill_meta(blob)
        assert result["players"]["Ravi"]["meta"]["name"] == "The Sniper"
        assert result["players"]["Ravi"]["meta"]["icon"] == "🎯"
        assert result["players"]["Meera"]["meta"]["name"] == "The Phoenix"

    def test_preserves_existing_meta(self):
        custom_meta = {"name": "Custom", "tagline": "T", "color": "#000", "icon": "X"}
        blob = {
            "players": {
                "Ravi": {"personality": "sniper", "meta": custom_meta},
            },
        }
        result = backfill_meta(blob)
        assert result["players"]["Ravi"]["meta"] == custom_meta

    def test_skips_players_without_personality(self):
        blob = {
            "players": {
                "Ravi": {"personality": None, "unlock_at": 3},
            },
        }
        result = backfill_meta(blob)
        assert "meta" not in result["players"]["Ravi"]

    def test_returns_none_for_none_blob(self):
        assert backfill_meta(None) is None

    def test_handles_empty_players(self):
        blob = {"players": {}}
        result = backfill_meta(blob)
        assert result["players"] == {}


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
            "bid_accuracy",
            "overbid_ratio",
            "underbid_ratio",
            "score_variance",
            "zero_bid_success",
            "high_card_accuracy",
            "low_card_accuracy",
            "tempo_first_half",
            "tempo_second_half",
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
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                    ],
                    winner="Bob",
                )
            )
        vector = compute_feature_vector("Alice", games)
        # dim 0 = bid_accuracy
        assert vector[0] == pytest.approx(1.0)

    def test_zero_accuracy(self):
        """Player never makes a bid → accuracy = 0.0."""
        games = []
        for _ in range(3):
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30}),
                    ],
                    winner="Bob",
                )
            )
        vector = compute_feature_vector("Alice", games)
        assert vector[0] == pytest.approx(0.0)

    def test_overbid_ratio(self):
        """Player always overbids → overbid_ratio = 1.0."""
        games = []
        for _ in range(3):
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 3, "1": 2}, {"0": 1, "1": 2}, {"0": -30, "1": 20}),
                    ],
                    winner="Bob",
                )
            )
        vector = compute_feature_vector("Alice", games)
        # dim 1 = overbid_ratio
        assert vector[1] == pytest.approx(1.0)
        # dim 2 = underbid_ratio should be 0
        assert vector[2] == pytest.approx(0.0)

    def test_underbid_ratio(self):
        """Player always underbids → underbid_ratio = 1.0."""
        games = []
        for _ in range(3):
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 1, "1": 2}, {"0": 3, "1": 2}, {"0": -10, "1": 20}),
                    ],
                    winner="Bob",
                )
            )
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
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 0, "1": 5}, {"0": 0, "1": 5}, {"0": 10, "1": 50}),
                    ],
                    winner="Bob",
                )
            )
        vector = compute_feature_vector("Alice", games)
        assert vector[4] == pytest.approx(1.0)

    def test_failed_zero_bids(self):
        """Player bids 0 but wins hands → zero_bid_success = 0.0."""
        games = []
        for _ in range(3):
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 0, "1": 5}, {"0": 2, "1": 3}, {"0": -10, "1": -50}),
                    ],
                    winner="Alice",
                )
            )
        vector = compute_feature_vector("Alice", games)
        assert vector[4] == pytest.approx(0.0)

    def test_no_zero_bids(self):
        """Player never bids 0 → zero_bid_success = 0.0 (no data)."""
        games = []
        for _ in range(3):
            games.append(
                _make_game(
                    players=["Alice", "Bob"],
                    rounds_data=[
                        (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
                    ],
                    winner="Alice",
                )
            )
        vector = compute_feature_vector("Alice", games)
        assert vector[4] == pytest.approx(0.0)


class TestFeatureVectorTempo:
    """Test tempo dimensions (1st half vs 2nd half)."""

    def test_strong_first_half(self):
        """Player scores well in 1st half, poorly in 2nd → tempo_first > tempo_second."""
        games = [
            _make_game(
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
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 7 = tempo_first_half, dim 8 = tempo_second_half
        assert vector[7] > vector[8]


class TestFeatureVectorHighLowCards:
    """Test high-card and low-card accuracy dimensions."""

    def test_high_card_specialist(self):
        """Perfect accuracy on 6-8 cards, zero on 1-3 → high > low."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (8, {"0": 3, "1": 5}, {"0": 3, "1": 5}, {"0": 30, "1": 50}),
                    (2, {"0": 1, "1": 1}, {"0": 0, "1": 1}, {"0": -10, "1": 11}),
                ],
                winner="Bob",
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 5 = high_card_accuracy, dim 6 = low_card_accuracy
        assert vector[5] == pytest.approx(1.0)
        assert vector[6] == pytest.approx(0.0)


class TestFeatureVectorComeback:
    """Test comeback rate dimension."""

    def test_comeback_win(self):
        """Player behind at halfway but wins → comeback_rate = 1.0."""
        games = [
            _make_game(
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
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        # dim 9 = comeback_rate
        assert vector[9] == pytest.approx(1.0)

    def test_no_comeback_opportunities(self):
        """Player always leads → comeback_rate = 0.0."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
                    (4, {"0": 2, "1": 2}, {"0": 2, "1": 2}, {"0": 20, "1": 20}),
                    (3, {"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}),
                    (2, {"0": 1, "1": 1}, {"0": 1, "1": 1}, {"0": 11, "1": 11}),
                ],
                winner="Alice",
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        assert vector[9] == pytest.approx(0.0)


class TestFeatureVectorScoreVariance:
    """Test score variance dimension."""

    def test_consistent_scores(self):
        """Same total score every game → variance = 0.0."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            )
        ] * 3
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
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[(5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30})],
                winner="Bob",
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        assert len(vector) == 10
        # All values should be finite numbers
        for value in vector:
            assert math.isfinite(value)


class TestGlobalZNormalize:
    """Test global z-score normalization using fixed priors."""

    def test_at_prior_mean_gives_half(self):
        """Value equal to prior mean → normalized to 0.5 (sigmoid of 0)."""
        # dim 0: mean=0.50, so input 0.50 → z=0 → sigmoid(0)=0.5
        vectors = {"Alice": [0.50, 0.35, 0.40, 0.50, 0.60, 0.50, 0.50, 0.50, 0.50, 0.30]}
        result = global_z_normalize(vectors)
        for v in result["Alice"]:
            assert v == pytest.approx(0.5, abs=0.001)

    def test_above_mean_gives_above_half(self):
        """Value above prior mean → normalized > 0.5."""
        # dim 0: mean=0.50, value=0.70 → z>0 → sigmoid>0.5
        vectors = {"Alice": [0.70, 0.35, 0.40, 0.50, 0.60, 0.50, 0.50, 0.50, 0.50, 0.30]}
        result = global_z_normalize(vectors)
        assert result["Alice"][0] > 0.5

    def test_below_mean_gives_below_half(self):
        """Value below prior mean → normalized < 0.5."""
        vectors = {"Alice": [0.30, 0.35, 0.40, 0.50, 0.60, 0.50, 0.50, 0.50, 0.50, 0.30]}
        result = global_z_normalize(vectors)
        assert result["Alice"][0] < 0.5

    def test_empty_input_returns_empty(self):
        """Empty dict returns empty dict."""
        result = global_z_normalize({})
        assert result == {}

    def test_output_in_zero_one_range(self):
        """All output values stay in [0, 1] (sigmoid bounded)."""
        vectors = {
            "Alice": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            "Bob": [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0],
        }
        result = global_z_normalize(vectors)
        for player, vec in result.items():
            for v in vec:
                assert 0.0 <= v <= 1.0, f"{player} has out-of-range value {v}"

    def test_preserves_all_dimensions(self):
        """Output has same players and 10 dimensions each."""
        vectors = {
            "Alice": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "Bob": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
        }
        result = global_z_normalize(vectors)
        assert set(result.keys()) == {"Alice", "Bob"}
        assert len(result["Alice"]) == 10
        assert len(result["Bob"]) == 10

    def test_independent_of_other_players(self):
        """Each player is normalized independently — adding a player doesn't shift others."""
        vectors_one = {"Alice": [0.8, 0.3, 0.5, 0.4, 0.7, 0.6, 0.5, 0.6, 0.4, 0.2]}
        vectors_two = {
            "Alice": [0.8, 0.3, 0.5, 0.4, 0.7, 0.6, 0.5, 0.6, 0.4, 0.2],
            "Bob": [0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9],
        }
        result_one = global_z_normalize(vectors_one)
        result_two = global_z_normalize(vectors_two)
        for i in range(10):
            assert result_one["Alice"][i] == pytest.approx(result_two["Alice"][i])


class TestBayesianShrink:
    """Test Bayesian shrinkage toward fixed prior (0.5)."""

    def test_high_game_count_minimal_shrinkage(self):
        """With many games, player vector stays close to raw value."""
        player_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = bayesian_shrink(player_vector, games_played=50)
        # weight = 50/(50+5) ≈ 0.909 → result[0] = 0.5 + 0.909*(1.0-0.5) ≈ 0.954
        assert result[0] > 0.9

    def test_low_game_count_heavy_shrinkage(self):
        """With few games, player vector shrinks heavily toward 0.5."""
        player_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result_3 = bayesian_shrink(player_vector, games_played=3)
        result_50 = bayesian_shrink(player_vector, games_played=50)
        # With 3 games, should be much closer to 0.5 than with 50
        assert result_3[0] < result_50[0]

    def test_at_3_games_weight_is_37_5_pct(self):
        """At 3 games: weight=3/(3+5)=0.375, so result[0]=0.5+0.375*(v-0.5)."""
        player_vector = [1.0] + [0.5] * 9
        result = bayesian_shrink(player_vector, games_played=3)
        expected = 0.5 + (3 / 8) * (1.0 - 0.5)
        assert result[0] == pytest.approx(expected, abs=0.001)

    def test_at_5_games_fifty_fifty(self):
        """At 5 games: weight=5/(5+5)=0.5, result is halfway to prior."""
        player_vector = [1.0] + [0.5] * 9
        result = bayesian_shrink(player_vector, games_played=5)
        assert result[0] == pytest.approx(0.75, abs=0.001)

    def test_shrinkage_preserves_dimensions(self):
        """Output has exactly 10 dimensions."""
        player_vector = [0.1] * 10
        result = bayesian_shrink(player_vector, games_played=5)
        assert len(result) == 10

    def test_player_at_prior_unchanged(self):
        """If player equals prior (0.5), shrinkage has no effect."""
        vec = [0.5] * 10
        result = bayesian_shrink(vec, games_played=3)
        for v in result:
            assert v == pytest.approx(0.5)

    def test_all_finite_values(self):
        """Result never contains NaN or Inf."""
        player_vector = [0.0] * 10
        result = bayesian_shrink(player_vector, games_played=3)
        for value in result:
            assert math.isfinite(value)

    def test_pipeline_preserves_differences_at_3_games(self):
        """With 3 games, pipeline must NOT collapse different vectors to identical."""
        vectors = {
            "Alice": [0.8, 0.1, 0.1, 0.3, 0.7, 0.9, 0.6, 0.6, 0.5, 0.2],
            "Bob":   [0.3, 0.6, 0.4, 0.7, 0.4, 0.3, 0.8, 0.4, 0.7, 0.5],
            "Carol": [0.5, 0.3, 0.7, 0.5, 0.5, 0.5, 0.5, 0.8, 0.3, 0.1],
            "Dave":  [0.6, 0.4, 0.2, 0.4, 0.6, 0.6, 0.4, 0.5, 0.5, 0.3],
        }
        normalized = global_z_normalize(vectors)
        shrunk = {p: bayesian_shrink(v, 3) for p, v in normalized.items()}

        # All 4 vectors must be different
        values = list(shrunk.values())
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                assert values[i] != values[j], (
                    f"Player {i} and {j} have identical vectors after pipeline"
                )


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
        # alpha=0.4: result[0] = 0.4*1.0 + 0.6*0.0 = 0.4
        assert result[0] == pytest.approx(0.4)
        # result[1] = 0.4*0.0 + 0.6*1.0 = 0.6
        assert result[1] == pytest.approx(0.6)

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
            magnitude = math.sqrt(sum(c**2 for c in centroid))
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
            "Bob": [0.3, 0.9, 0.1, 0.7, 0.1, 0.4, 0.2, 0.5, 0.5, 0.3],
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
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (8, {"0": 3, "1": 5}, {"0": 3, "1": 5}, {"0": 30, "1": 50}),
                    (5, {"0": 2, "1": 3}, {"0": 0, "1": 3}, {"0": -20, "1": 30}),
                    (3, {"0": 1, "1": 2}, {"0": 1, "1": 2}, {"0": 11, "1": 20}),
                ],
                winner="Bob",
            )
        ]
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
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            )
        ]
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


class TestPlayerExtras:
    """Test compute_player_extras — bidding style, clutch, tempo, etc."""

    def test_bidding_style_aggressive(self):
        """Player who overbids more than underbids → aggressive."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 4, "1": 1}, {"0": 2, "1": 3}, {"0": -40, "1": -10}),
                    (5, {"0": 3, "1": 2}, {"0": 1, "1": 4}, {"0": -30, "1": -20}),
                ],
                winner="Bob",
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        assert extras["bidding_style"] == "aggressive"
        assert extras["overbid_pct"] > 0

    def test_bidding_style_conservative(self):
        """Player who underbids more → conservative."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 1, "1": 4}, {"0": 3, "1": 2}, {"0": -10, "1": -40}),
                    (5, {"0": 0, "1": 5}, {"0": 2, "1": 3}, {"0": -10, "1": -50}),
                ],
                winner="Alice",
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        assert extras["bidding_style"] == "conservative"

    def test_zero_bid_rate(self):
        """Zero bid success rate computed correctly."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 0, "1": 5}, {"0": 0, "1": 5}, {"0": 10, "1": 50}),
                    (5, {"0": 0, "1": 5}, {"0": 2, "1": 3}, {"0": -10, "1": -50}),
                ],
                winner="Bob",
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        assert extras["zero_bid_rate"] == 50  # 1 success out of 2 per game

    def test_clutch_factor(self):
        """Comeback wins tracked correctly."""
        games = [
            _make_game(
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
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        assert extras["clutch_wins"] == 3
        assert extras["clutch_opportunities"] == 3

    def test_tempo(self):
        """Tempo identifies 1st half vs 2nd half player."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    # 1st half: Alice scores high
                    (5, {"0": 3, "1": 2}, {"0": 3, "1": 2}, {"0": 30, "1": 20}),
                    (4, {"0": 2, "1": 2}, {"0": 2, "1": 2}, {"0": 20, "1": 20}),
                    # 2nd half: Alice scores low
                    (3, {"0": 2, "1": 1}, {"0": 0, "1": 1}, {"0": -20, "1": 11}),
                    (2, {"0": 1, "1": 1}, {"0": 0, "1": 1}, {"0": -10, "1": 11}),
                ],
                winner="Bob",
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        assert extras["tempo"] == "1st half"

    def test_consistency_with_same_scores(self):
        """Same score every game → high consistency."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        assert extras["consistency"] == "high"

    def test_extras_has_all_fields(self):
        """Extras dict has all expected keys."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            )
        ] * 3
        extras = compute_player_extras("Alice", games)
        expected_keys = {
            "wins",
            "games_played",
            "total_rounds",
            "best_trump",
            "best_trump_pct",
            "trend",
            "favorite_bid",
            "biggest_round_score",
            "fun_facts",
            "bidding_style",
            "overbid_pct",
            "zero_bid_rate",
            "clutch_wins",
            "clutch_opportunities",
            "tempo",
            "consistency",
        }
        assert expected_keys.issubset(set(extras.keys()))


class TestEdgeCasesReviewerFindings:
    """Tests for edge cases identified by reviewer."""

    def test_more_than_10_players_allows_duplicates(self):
        """With >10 players, some must share personalities."""
        vectors = {f"Player{i}": [0.5 + i * 0.01] * 10 for i in range(12)}
        results = assign_personalities_unique(vectors)
        assert len(results) == 12
        # All should have assignments
        for result in results.values():
            assert result["personality"] in PERSONALITY_CENTROIDS

    def test_feature_vector_with_partial_bids(self):
        """Rounds with missing bid/hand data are skipped gracefully."""
        games = [
            _make_game(
                players=["Alice", "Bob"],
                rounds_data=[
                    # Normal round
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                    # Round where Alice has no bid (missing key)
                    (5, {"1": 3}, {"1": 3}, {"1": 30}),
                    # Normal round
                    (5, {"0": 1, "1": 4}, {"0": 1, "1": 4}, {"0": 11, "1": 40}),
                ],
                winner="Bob",
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        assert len(vector) == 10
        # Should compute from 2 valid rounds per game (6 total), not 3
        assert vector[0] == pytest.approx(1.0)  # 2/2 correct per game

    def test_player_with_zero_games(self):
        """Player not in any game returns zero vector."""
        games = [
            _make_game(
                players=["Bob", "Charlie"],
                rounds_data=[
                    (5, {"0": 2, "1": 3}, {"0": 2, "1": 3}, {"0": 20, "1": 30}),
                ],
                winner="Bob",
            )
        ] * 3
        vector = compute_feature_vector("Alice", games)
        assert all(v == 0.0 for v in vector)

    def test_personality_not_assigned_at_2_games(self):
        """Player with exactly 2 games should NOT get personality."""
        from app.services.insights import MIN_GAMES_FOR_PERSONALITY

        assert MIN_GAMES_FOR_PERSONALITY == 3
        # 2 < 3, so no personality

    def test_tied_scores_winner_is_none(self):
        """When scores are tied, winner is None — no arbitrary pick."""
        from app.services.insights import _GameWithRounds

        class FakeGame:
            def __init__(self):
                self.players = ["Alice", "Bob"]

        class FakeRound:
            def __init__(self):
                self.scores = {"0": 20, "1": 20}

        game = _GameWithRounds(FakeGame(), [FakeRound()])
        assert game.winner is None  # Ties produce no winner


class TestComebackThresholdConsistency:
    """Both feature vector and extras must use same comeback threshold."""

    def test_two_round_game_no_comeback_in_feature_vector(self):
        """2-round game: too few rounds for meaningful comeback in feature vector."""
        game = _make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (5, {"0": 0, "1": 5}, {"0": 0, "1": 5}, {"0": -10, "1": 50}),
                (4, {"0": 4, "1": 0}, {"0": 4, "1": 0}, {"0": 40, "1": -10}),
            ],
            winner="Alice",
        )
        vector = compute_feature_vector("Alice", [game] * 3)
        # 2 rounds: too short, comeback should NOT be counted
        assert vector[9] == pytest.approx(0.0)

    def test_two_round_game_no_comeback_in_extras(self):
        """2-round game: extras should also NOT count comeback."""
        game = _make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                (5, {"0": 0, "1": 5}, {"0": 0, "1": 5}, {"0": -10, "1": 50}),
                (4, {"0": 4, "1": 0}, {"0": 4, "1": 0}, {"0": 40, "1": -10}),
            ],
            winner="Alice",
        )
        extras = compute_player_extras("Alice", [game] * 3)
        assert extras["clutch_wins"] == 0
        assert extras["clutch_opportunities"] == 0

    def test_four_round_game_counts_comeback_in_both(self):
        """4-round game: comeback counted in both feature vector and extras."""
        game = _make_game(
            players=["Alice", "Bob"],
            rounds_data=[
                # 1st half: Alice behind
                (5, {"0": 1, "1": 4}, {"0": 0, "1": 4}, {"0": -10, "1": 40}),
                (4, {"0": 1, "1": 3}, {"0": 0, "1": 3}, {"0": -10, "1": 30}),
                # 2nd half: Alice catches up
                (3, {"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": -10}),
                (2, {"0": 2, "1": 0}, {"0": 2, "1": 0}, {"0": 20, "1": -10}),
            ],
            winner="Alice",
        )
        vector = compute_feature_vector("Alice", [game] * 3)
        assert vector[9] > 0  # comeback_rate > 0

        extras = compute_player_extras("Alice", [game] * 3)
        assert extras["clutch_wins"] > 0
        assert extras["clutch_opportunities"] > 0


class TestRealisticMultiRoundGames:
    """Tests using 8-round games with varied bids, like real Kachuful play."""

    def _build_standard_game(self):
        """8-round descending game (8→1 cards). 3 players, varied results.

        Simulates: Ravi (aggressive), Meera (conservative), Kabir (balanced).
        """
        return _make_realistic_game(
            players=["Ravi", "Meera", "Kabir"],
            round_results=[
                # Round 1: 8 cards, spades
                {"Ravi": (5, 3, -50), "Meera": (1, 1, 11), "Kabir": (2, 4, -20)},
                # Round 2: 7 cards, diamonds
                {"Ravi": (4, 4, 40), "Meera": (0, 0, 10), "Kabir": (3, 3, 30)},
                # Round 3: 6 cards, clubs
                {"Ravi": (3, 2, -30), "Meera": (1, 1, 11), "Kabir": (2, 3, -20)},
                # Round 4: 5 cards, hearts
                {"Ravi": (3, 3, 30), "Meera": (0, 0, 10), "Kabir": (2, 2, 20)},
                # Round 5: 4 cards, spades
                {"Ravi": (2, 1, -20), "Meera": (1, 1, 11), "Kabir": (1, 2, -11)},
                # Round 6: 3 cards, diamonds
                {"Ravi": (2, 2, 20), "Meera": (0, 0, 10), "Kabir": (1, 1, 11)},
                # Round 7: 2 cards, clubs
                {"Ravi": (1, 1, 11), "Meera": (0, 1, -10), "Kabir": (1, 0, -11)},
                # Round 8: 1 card, hearts
                {"Ravi": (1, 0, -11), "Meera": (0, 0, 10), "Kabir": (0, 1, -10)},
            ],
        )

    def _build_three_games(self):
        """3 varied games to trigger personality assignment."""
        game1 = self._build_standard_game()
        # Game 2: Meera wins more, Ravi overbids heavily
        game2 = _make_realistic_game(
            players=["Ravi", "Meera", "Kabir"],
            round_results=[
                {"Ravi": (6, 2, -60), "Meera": (2, 2, 20), "Kabir": (0, 4, -10)},
                {"Ravi": (5, 5, 50), "Meera": (0, 0, 10), "Kabir": (2, 2, 20)},
                {"Ravi": (4, 1, -40), "Meera": (1, 1, 11), "Kabir": (1, 4, -11)},
                {"Ravi": (3, 3, 30), "Meera": (0, 0, 10), "Kabir": (3, 3, 30)},
                {"Ravi": (2, 0, -20), "Meera": (1, 1, 11), "Kabir": (1, 3, -11)},
                {"Ravi": (2, 2, 20), "Meera": (1, 0, -11), "Kabir": (0, 1, -10)},
            ],
        )
        # Game 3: Kabir dominates
        game3 = _make_realistic_game(
            players=["Ravi", "Meera", "Kabir"],
            round_results=[
                {"Ravi": (2, 2, 20), "Meera": (1, 1, 11), "Kabir": (5, 5, 50)},
                {"Ravi": (3, 1, -30), "Meera": (0, 0, 10), "Kabir": (4, 6, -40)},
                {"Ravi": (1, 1, 11), "Meera": (2, 2, 20), "Kabir": (3, 3, 30)},
                {"Ravi": (2, 3, -20), "Meera": (0, 0, 10), "Kabir": (3, 2, -30)},
                {"Ravi": (0, 0, 10), "Meera": (1, 1, 11), "Kabir": (3, 3, 30)},
            ],
        )
        return [game1, game2, game3]

    def test_feature_vector_with_8_round_game(self):
        """Feature vector computed correctly from realistic 8-round games."""
        games = self._build_three_games()
        vector = compute_feature_vector("Ravi", games)
        assert len(vector) == 10
        # Ravi makes some bids, misses others → accuracy between 0 and 1
        assert 0.2 < vector[0] < 0.8
        # Ravi overbids often → overbid ratio > underbid
        assert vector[1] > vector[2]
        # Different games have different total scores → variance > 0
        assert vector[3] > 0

    def test_conservative_player_detected(self):
        """Meera bids 0 often → zero_bid_success high, underbid low."""
        games = self._build_three_games()
        vector = compute_feature_vector("Meera", games)
        # Meera bids 0 frequently and makes it → high zero_bid_success (dim 4)
        assert vector[4] > 0.5
        # Meera rarely overbids
        assert vector[1] < 0.3

    def test_aggressive_player_detected(self):
        """Ravi overbids → high overbid ratio."""
        games = self._build_three_games()
        vector = compute_feature_vector("Ravi", games)
        # Ravi frequently overbids
        assert vector[1] > 0.3

    def test_accuracy_by_cards_with_8_rounds(self):
        """Accuracy breakdown across all card counts."""
        game = self._build_standard_game()
        result = compute_accuracy_by_cards("Ravi", [game])
        # Should have entries for card counts 1-8
        assert len(result) == 8
        for cards_str in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            assert cards_str in result
            assert result[cards_str]["rounds"] == 1

    def test_extras_bidding_style_from_realistic_data(self):
        """Extras detect aggressive bidder from multi-round games."""
        games = self._build_three_games()
        extras = compute_player_extras("Ravi", games)
        assert extras["bidding_style"] == "aggressive"
        assert extras["games_played"] == 3
        assert extras["total_rounds"] > 15  # 8+6+5 = 19 rounds

    def test_extras_zero_bid_specialist(self):
        """Meera's zero-bid rate computed from realistic data."""
        games = self._build_three_games()
        extras = compute_player_extras("Meera", games)
        # Meera bids 0 often and succeeds most of the time
        assert extras["zero_bid_rate"] > 50
        # Equal overbids and underbids → balanced (she bids 0 mostly)
        assert extras["bidding_style"] in ("balanced", "conservative")

    def test_extras_trump_suit_tracked(self):
        """Best trump suit computed from realistic games with suit rotation."""
        games = self._build_three_games()
        extras = compute_player_extras("Meera", games)
        # Should have a best trump (multiple rounds per suit)
        if extras["best_trump"]:
            assert extras["best_trump"] in ("♠", "♦", "♣", "♥")
            assert extras["best_trump_pct"] > 0

    def test_unique_personalities_from_realistic_data(self):
        """3 different playstyles → 3 unique personalities."""
        games = self._build_three_games()
        vectors = {name: compute_feature_vector(name, games) for name in ["Ravi", "Meera", "Kabir"]}

        normalized = global_z_normalize(vectors)
        results = assign_personalities_unique(normalized)
        personalities = [r["personality"] for r in results.values()]
        assert len(set(personalities)) == 3

    def test_insights_different_for_each_playstyle(self):
        """Different players get different insight text."""
        games = self._build_three_games()
        vectors = {name: compute_feature_vector(name, games) for name in ["Ravi", "Meera", "Kabir"]}

        normalized = global_z_normalize(vectors)
        results = assign_personalities_unique(normalized)

        insight_sets = set()
        for name in ["Ravi", "Meera", "Kabir"]:
            insights = generate_insights(
                normalized[name],
                results[name]["personality"],
            )
            assert len(insights) == 2
            insight_sets.add(tuple(insights))
        # At least 2 different insight combos (3 would be ideal)
        assert len(insight_sets) >= 2

    def test_full_pipeline_realistic_data(self):
        """End-to-end: 3 realistic games → feature vector → normalize →
        shrink → assign → insights → extras. All outputs valid."""
        games = self._build_three_games()
        players = ["Ravi", "Meera", "Kabir"]

        # Feature vectors
        vectors = {name: compute_feature_vector(name, games) for name in players}
        for name, vec in vectors.items():
            assert len(vec) == 10
            for v in vec:
                assert math.isfinite(v), f"{name} has non-finite value"

        # Normalize
        normalized = global_z_normalize(vectors)
        for vec in normalized.values():
            for v in vec:
                assert 0.0 <= v <= 1.0

        # Shrink
        for name in players:
            shrunk = bayesian_shrink(normalized[name], 3)
            assert len(shrunk) == 10

        # Assign unique
        assignments = assign_personalities_unique(normalized)
        assert len(assignments) == 3
        personalities = [a["personality"] for a in assignments.values()]
        assert len(set(personalities)) == 3

        # Accuracy by cards
        for name in players:
            accuracy = compute_accuracy_by_cards(name, games)
            assert len(accuracy) > 0
            for card_data in accuracy.values():
                assert 0 <= card_data["pct"] <= 100
                assert card_data["rounds"] > 0

        # Extras
        for name in players:
            extras = compute_player_extras(name, games)
            assert extras["games_played"] == 3
            assert extras["total_rounds"] > 0
            assert extras["bidding_style"] in (
                "aggressive",
                "conservative",
                "balanced",
            )
            assert extras["consistency"] in ("high", "medium", "low")
            assert extras["tempo"] in ("1st half", "2nd half", "even")

    def test_trend_requires_four_games(self):
        """Trend stays 'steady' with only 3 games, needs 4+ for signal."""
        games = self._build_three_games()
        extras = compute_player_extras("Ravi", games)
        assert extras["trend"] == "steady"  # Only 3 games, not enough


class TestEmptyGameWins:
    """Games with 0 scored rounds must not produce phantom wins."""

    def test_empty_game_excluded_from_wrapped_games(self):
        """_GameWithRounds should not be created for games with no rounds."""
        from app.services.insights import _GameWithRounds

        class FakeGame:
            def __init__(self, players):
                self.players = players
                self.id = 1

        # Empty rounds → _determine_winner picks first player as "winner" with 0
        game = _GameWithRounds(FakeGame(["Alice", "Bob"]), [])
        # This phantom winner is the bug — winner should be None for empty games
        assert game.winner is None

    def test_total_wins_matches_games_played(self):
        """Sum of all player wins must equal number of games with rounds."""
        games = [
            _make_game(
                ["Alice", "Bob"],
                [(8, {"0": 2, "1": 3}, {"0": 2, "1": 6}, {"0": 20, "1": 30})],
                winner="Bob",
            ),
            _make_game(
                ["Alice", "Bob"],
                [(8, {"0": 3, "1": 1}, {"0": 3, "1": 5}, {"0": 30, "1": -11})],
                winner="Alice",
            ),
        ]
        alice_extras = compute_player_extras("Alice", games)
        bob_extras = compute_player_extras("Bob", games)
        total_wins = alice_extras["wins"] + bob_extras["wins"]
        assert total_wins == 2  # 2 games, 2 wins total
