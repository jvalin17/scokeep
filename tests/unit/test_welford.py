"""TDD: Tests for Welford auto-calibrating priors in personality_engine.

Written BEFORE implementation. Tests the Welford accumulator for running
mean/variance and adaptive_z_normalize that uses playground-specific stats.
"""

import pytest


class TestWelfordAccumulator:
    """Welford online algorithm for running mean and variance."""

    def test_welford_update_single_vector(self):
        from app.services.personality_engine import welford_update

        state = {"count": 0, "mean": [0.0] * 10, "m2": [0.0] * 10}
        vec = [0.5, 0.3, 0.2, 0.4, 0.6, 0.5, 0.5, 0.5, 0.5, 0.3]
        result = welford_update(state, vec)
        assert result["count"] == 1
        assert result["mean"] == vec

    def test_welford_update_two_vectors(self):
        from app.services.personality_engine import welford_update

        state = {"count": 0, "mean": [0.0] * 10, "m2": [0.0] * 10}
        v1 = [1.0] * 10
        v2 = [0.0] * 10
        state = welford_update(state, v1)
        state = welford_update(state, v2)
        assert state["count"] == 2
        for m in state["mean"]:
            assert m == pytest.approx(0.5)

    def test_welford_variance_after_multiple(self):
        from app.services.personality_engine import welford_update, welford_variance

        state = {"count": 0, "mean": [0.0] * 10, "m2": [0.0] * 10}
        for val in [0.2, 0.4, 0.6, 0.8, 1.0]:
            vec = [val] * 10
            state = welford_update(state, vec)
        variance = welford_variance(state)
        # Mean = 0.6, variance of [0.2, 0.4, 0.6, 0.8, 1.0] = 0.08
        assert len(variance) == 10
        for v in variance:
            assert v == pytest.approx(0.08, abs=0.01)

    def test_welford_variance_single_sample(self):
        from app.services.personality_engine import welford_update, welford_variance

        state = {"count": 0, "mean": [0.0] * 10, "m2": [0.0] * 10}
        state = welford_update(state, [0.5] * 10)
        variance = welford_variance(state)
        # Single sample: variance should be 0
        for v in variance:
            assert v == pytest.approx(0.0)


class TestAdaptiveZNormalize:
    """adaptive_z_normalize uses playground-specific stats when count >= 20."""

    def test_falls_back_to_global_priors_under_threshold(self):
        from app.services.personality_engine import adaptive_z_normalize, global_z_normalize

        vectors = {"Alice": [0.5] * 10}
        calibration = {"count": 5, "mean": [0.9] * 10, "m2": [0.1] * 10}
        result = adaptive_z_normalize(vectors, calibration)
        expected = global_z_normalize(vectors)
        assert result["Alice"] == expected["Alice"]

    def test_uses_playground_stats_above_threshold(self):
        from app.services.personality_engine import adaptive_z_normalize

        vectors = {"Alice": [0.5] * 10}
        # Playground stats: mean=0.5, variance=0.04 → sd=0.2
        calibration = {"count": 25, "mean": [0.5] * 10, "m2": [1.0] * 10}
        result = adaptive_z_normalize(vectors, calibration)
        # At mean with count>=20, should use playground stats, not global
        # Result should be ~0.5 (sigmoid of z=0)
        for v in result["Alice"]:
            assert v == pytest.approx(0.5, abs=0.01)

    def test_uses_global_when_no_calibration(self):
        from app.services.personality_engine import adaptive_z_normalize, global_z_normalize

        vectors = {"Alice": [0.5] * 10}
        result = adaptive_z_normalize(vectors, None)
        expected = global_z_normalize(vectors)
        assert result["Alice"] == expected["Alice"]

    def test_handles_zero_variance_dimension(self):
        from app.services.personality_engine import adaptive_z_normalize

        vectors = {"Alice": [0.5] * 10}
        calibration = {"count": 25, "mean": [0.5] * 10, "m2": [0.0] * 10}
        result = adaptive_z_normalize(vectors, calibration)
        # Zero variance → should fall back to 0.5 for that dimension
        for v in result["Alice"]:
            assert v == pytest.approx(0.5)

    def test_empty_vectors_returns_empty(self):
        from app.services.personality_engine import adaptive_z_normalize

        calibration = {"count": 25, "mean": [0.5] * 10, "m2": [1.0] * 10}
        assert adaptive_z_normalize({}, calibration) == {}
        assert adaptive_z_normalize({}, None) == {}

    def test_welford_variance_zero_samples(self):
        from app.services.personality_engine import welford_variance

        state = {"count": 0, "mean": [0.0] * 10, "m2": [0.0] * 10}
        variance = welford_variance(state)
        for v in variance:
            assert v == pytest.approx(0.0)
