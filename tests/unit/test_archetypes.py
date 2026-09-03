"""TDD: Tests for 9 archetypes + per-persona weight vectors.

Written BEFORE implementation.
Architecture: merge Phoenix+Comeback Kid, remove Wildcard,
rename Architect→Reader, Minimalist→Surgeon, add Tilter.
Per-persona weights: each archetype emphasizes different feature dimensions.
"""


import pytest

EXPECTED_ARCHETYPES = {
    "sniper",
    "gambler",
    "phoenix",   # merged Phoenix + Comeback Kid
    "rock",
    "sprinter",
    "ghost",
    "reader",    # renamed from architect
    "surgeon",   # renamed from minimalist
    "tilter",    # new — streak player
}

REMOVED_ARCHETYPES = {"wildcard", "comeback_kid", "architect", "minimalist"}


class TestArchetypeCount:
    def test_exactly_9_centroids(self):
        from app.services.personality_engine import PERSONALITY_CENTROIDS

        assert len(PERSONALITY_CENTROIDS) == 9

    def test_exactly_9_meta(self):
        from app.services.personality_engine import PERSONALITY_META

        assert len(PERSONALITY_META) == 9

    def test_centroid_keys_match_expected(self):
        from app.services.personality_engine import PERSONALITY_CENTROIDS

        assert set(PERSONALITY_CENTROIDS.keys()) == EXPECTED_ARCHETYPES

    def test_meta_keys_match_expected(self):
        from app.services.personality_engine import PERSONALITY_META

        assert set(PERSONALITY_META.keys()) == EXPECTED_ARCHETYPES

    def test_removed_archetypes_absent(self):
        from app.services.personality_engine import PERSONALITY_CENTROIDS

        for key in REMOVED_ARCHETYPES:
            assert key not in PERSONALITY_CENTROIDS, f"{key} should be removed"


class TestPerPersonaWeights:
    def test_weight_vectors_exist(self):
        from app.services.personality_engine import PERSONALITY_WEIGHTS

        assert isinstance(PERSONALITY_WEIGHTS, dict)
        assert set(PERSONALITY_WEIGHTS.keys()) == EXPECTED_ARCHETYPES

    def test_weight_vectors_are_10d(self):
        from app.services.personality_engine import PERSONALITY_WEIGHTS

        for name, weights in PERSONALITY_WEIGHTS.items():
            assert len(weights) == 10, f"{name} weight vector has {len(weights)} dims"

    def test_weight_values_positive(self):
        from app.services.personality_engine import PERSONALITY_WEIGHTS

        for name, weights in PERSONALITY_WEIGHTS.items():
            for i, w in enumerate(weights):
                assert w > 0, f"{name} dim {i} weight is {w}, must be positive"

    def test_sniper_emphasizes_accuracy(self):
        """Sniper should weight accuracy (dim 0) higher than overbid (dim 1)."""
        from app.services.personality_engine import PERSONALITY_WEIGHTS

        w = PERSONALITY_WEIGHTS["sniper"]
        assert w[0] > w[1], "Sniper should emphasize accuracy over overbids"

    def test_gambler_emphasizes_overbids(self):
        """Gambler should weight overbids (dim 1) and variance (dim 3) high."""
        from app.services.personality_engine import PERSONALITY_WEIGHTS

        w = PERSONALITY_WEIGHTS["gambler"]
        assert w[1] > w[0], "Gambler should emphasize overbids over accuracy"

    def test_tilter_emphasizes_variance(self):
        """Tilter should weight score_variance (dim 3) highest."""
        from app.services.personality_engine import PERSONALITY_WEIGHTS

        w = PERSONALITY_WEIGHTS["tilter"]
        assert w[3] >= max(w[0], w[1], w[2]), "Tilter should emphasize variance"


class TestWeightedSimilarity:
    def test_weighted_cosine_similarity_exists(self):
        from app.services.personality_engine import weighted_cosine_similarity

        assert callable(weighted_cosine_similarity)

    def test_weighted_cosine_similarity_basic(self):
        from app.services.personality_engine import weighted_cosine_similarity

        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        w = [1.0, 1.0, 1.0]
        assert weighted_cosine_similarity(a, b, w) == pytest.approx(1.0)

    def test_weights_change_result(self):
        """Different weights should produce different similarity scores."""
        from app.services.personality_engine import weighted_cosine_similarity

        a = [0.8, 0.2, 0.5, 0.3, 0.6, 0.5, 0.5, 0.5, 0.5, 0.3]
        b = [0.3, 0.8, 0.5, 0.3, 0.6, 0.5, 0.5, 0.5, 0.5, 0.3]
        uniform = [1.0] * 10
        accuracy_heavy = [2.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        sim_uniform = weighted_cosine_similarity(a, b, uniform)
        sim_heavy = weighted_cosine_similarity(a, b, accuracy_heavy)
        assert sim_uniform != pytest.approx(sim_heavy, abs=0.01)

    def test_assign_uses_weighted_similarity(self):
        """assign_personality should use per-persona weights, not plain cosine."""
        from app.services.personality_engine import assign_personality

        # This just verifies it runs without error with 9 archetypes
        vector = [0.7, 0.1, 0.1, 0.2, 0.6, 0.8, 0.8, 0.6, 0.6, 0.2]
        result = assign_personality(vector)
        assert result["personality"] in EXPECTED_ARCHETYPES
        assert result["confidence"] > 0


class TestNewArchetypeMeta:
    def test_reader_meta(self):
        from app.services.personality_engine import PERSONALITY_META

        assert "reader" in PERSONALITY_META
        assert PERSONALITY_META["reader"]["name"] == "The Reader"

    def test_surgeon_meta(self):
        from app.services.personality_engine import PERSONALITY_META

        assert "surgeon" in PERSONALITY_META
        assert PERSONALITY_META["surgeon"]["name"] == "The Surgeon"

    def test_tilter_meta(self):
        from app.services.personality_engine import PERSONALITY_META

        assert "tilter" in PERSONALITY_META
        assert PERSONALITY_META["tilter"]["name"] == "The Tilter"

    def test_phoenix_meta_updated(self):
        """Phoenix absorbed Comeback Kid — tagline should reflect resilience."""
        from app.services.personality_engine import PERSONALITY_META

        assert "phoenix" in PERSONALITY_META
        assert "comeback_kid" not in PERSONALITY_META

    def test_all_meta_have_required_fields(self):
        from app.services.personality_engine import PERSONALITY_META

        for name, meta in PERSONALITY_META.items():
            assert "name" in meta, f"{name} missing 'name'"
            assert "tagline" in meta, f"{name} missing 'tagline'"
            assert "color" in meta, f"{name} missing 'color'"
            assert "icon" in meta, f"{name} missing 'icon'"


class TestCentroidDifferentiation:
    def test_no_two_centroids_too_similar(self):
        """No pair of centroids should have cosine similarity > 0.95."""
        from app.services.personality_engine import (
            PERSONALITY_CENTROIDS,
            cosine_similarity,
        )

        names = list(PERSONALITY_CENTROIDS.keys())
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                sim = cosine_similarity(
                    PERSONALITY_CENTROIDS[a], PERSONALITY_CENTROIDS[b]
                )
                assert sim < 0.95, f"{a} and {b} too similar: {sim:.3f}"

    def test_phoenix_differs_from_sprinter(self):
        """Phoenix and Sprinter had 7/10 identical dims before — must be fixed."""
        from app.services.personality_engine import (
            PERSONALITY_CENTROIDS,
            cosine_similarity,
        )

        sim = cosine_similarity(
            PERSONALITY_CENTROIDS["phoenix"], PERSONALITY_CENTROIDS["sprinter"]
        )
        assert sim < 0.90, f"Phoenix/Sprinter still too similar: {sim:.3f}"
