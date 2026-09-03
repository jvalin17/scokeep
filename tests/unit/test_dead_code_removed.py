"""TDD: Verify dead code has been removed.

These functions were identified as unused in production code and should be deleted.
"""

import inspect


class TestDeadCodeRemoved:
    """Dead functions must not exist in the codebase."""

    def test_no_min_max_normalize(self):
        import app.services.personality_engine as pe

        assert not hasattr(pe, "min_max_normalize"), "min_max_normalize is dead code"

    def test_no_james_stein_shrink(self):
        import app.services.personality_engine as pe

        assert not hasattr(pe, "james_stein_shrink"), "james_stein_shrink is dead code"

    def test_no_build_awards_in_analytics(self):
        import app.services.analytics as a

        assert not hasattr(a, "_build_awards"), "_build_awards is dead code"

    def test_no_accumulate_game_stats(self):
        import app.services.analytics as a

        assert not hasattr(a, "_accumulate_game_stats"), "_accumulate_game_stats is dead code"

    def test_no_tally_bid(self):
        import app.services.analytics as a

        assert not hasattr(a, "_tally_bid"), "_tally_bid is dead code"

    def test_no_best_player(self):
        import app.services.analytics as a

        assert not hasattr(a, "_best_player"), "_best_player is dead code"

    def test_no_best_accuracy(self):
        import app.services.analytics as a

        assert not hasattr(a, "_best_accuracy"), "_best_accuracy is dead code"

    def test_analytics_under_500_lines(self):
        """After dead code removal, analytics.py should be smaller."""
        import app.services.analytics as a

        source = inspect.getsource(a)
        lines = source.count("\n")
        assert lines <= 450, f"analytics.py has {lines} lines, expected ≤450 after cleanup"
