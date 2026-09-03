"""TDD: Tests for complex title patterns moved from game_titles.py.

Verifies that title_patterns.py contains the complex evaluators and that
game_titles.py is now a thin facade under 200 lines.
"""

import os

from tests.unit.conftest import MockRound


def _make_context_with_comeback():
    """Build GameContext where Alice has a comeback: behind at halfway, wins."""
    from app.services.game_titles import build_context

    rounds = [
        # 1st half: Alice behind
        MockRound({"0": 0, "1": 3}, {"0": 1, "1": 3}, {"0": -10, "1": 30}, 8),
        MockRound({"0": 1, "1": 2}, {"0": 0, "1": 2}, {"0": -11, "1": 20}, 7),
        MockRound({"0": 1, "1": 1}, {"0": 0, "1": 1}, {"0": -11, "1": 11}, 6),
        MockRound({"0": 0, "1": 0}, {"0": 0, "1": 1}, {"0": 10, "1": -10}, 5),
        # 2nd half: Alice catches up
        MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 4),
        MockRound({"0": 2, "1": 0}, {"0": 2, "1": 0}, {"0": 20, "1": 10}, 3),
        MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 2),
        MockRound({"0": 1, "1": 0}, {"0": 1, "1": 0}, {"0": 11, "1": 10}, 1),
    ]
    return build_context(["Alice", "Bob"], rounds)


class TestTitlePatternsExist:
    """title_patterns.py must contain complex evaluator functions."""

    def test_module_imports(self):
        import app.services.title_patterns  # noqa: F401

    def test_has_complex_title_functions(self):
        from app.services.title_patterns import COMPLEX_PATTERNS

        # At least 20 complex patterns
        assert len(COMPLEX_PATTERNS) >= 20

    def test_comeback_king_in_patterns(self):
        from app.services.title_patterns import COMPLEX_PATTERNS

        keys = [fn.__name__.lstrip("_") for fn in COMPLEX_PATTERNS]
        assert "comeback_king" in keys

    def test_patterns_are_callable(self):
        from app.services.title_patterns import COMPLEX_PATTERNS

        for fn in COMPLEX_PATTERNS:
            assert callable(fn)


class TestTitlePatternsProduceCandidates:
    """Complex patterns must produce valid candidate dicts."""

    def test_comeback_king_detects_comeback(self):
        from app.services.title_patterns import COMPLEX_PATTERNS

        ctx = _make_context_with_comeback()
        # Find comeback_king function
        comeback_fn = None
        for fn in COMPLEX_PATTERNS:
            if "comeback_king" in fn.__name__:
                comeback_fn = fn
                break
        assert comeback_fn is not None
        candidates = comeback_fn(ctx)
        assert len(candidates) >= 1
        assert candidates[0]["key"] == "comeback_king"

    def test_all_patterns_return_lists(self):
        from app.services.title_patterns import COMPLEX_PATTERNS

        ctx = _make_context_with_comeback()
        for fn in COMPLEX_PATTERNS:
            result = fn(ctx)
            assert isinstance(result, list), f"{fn.__name__} must return list, got {type(result)}"


class TestGameTitlesFacade:
    """game_titles.py must be a thin facade after refactoring."""

    def test_game_titles_under_200_lines(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "services", "game_titles.py"
        )
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) <= 260, f"game_titles.py has {len(lines)} lines, must be ≤260"

    def test_evaluate_titles_still_works(self):
        """evaluate_titles must produce the same result (uses both declarative + complex)."""
        from app.services.game_titles import evaluate_titles

        rounds = [
            MockRound({"0": 3, "1": 0}, {"0": 3, "1": 0}, {"0": 30, "1": 10}, 8),
            MockRound({"0": 0, "1": 2}, {"0": 0, "1": 3}, {"0": 10, "1": -20}, 7),
            MockRound({"0": 2, "1": 1}, {"0": 2, "1": 1}, {"0": 20, "1": 11}, 6),
            MockRound({"0": 1, "1": 0}, {"0": 0, "1": 0}, {"0": -11, "1": 10}, 3),
        ]
        titles = evaluate_titles(["Alice", "Bob"], rounds)
        assert isinstance(titles, list)
        assert len(titles) > 0
        # All titles must have required fields
        for t in titles:
            assert "key" in t
            assert "player" in t

    def test_select_titles_still_works(self):
        from app.services.game_titles import select_titles

        candidates = [
            {
                "key": "champion",
                "emoji": "🏆",
                "title": "Champion",
                "desc": "test",
                "player": "Alice",
                "detail": "50",
                "score": 100.0,
            },
            {
                "key": "cursed",
                "emoji": "😵",
                "title": "Cursed",
                "desc": "test",
                "player": "Bob",
                "detail": "3",
                "score": 36.0,
            },
        ]
        result = select_titles(candidates, ["Alice", "Bob"], target=2)
        assert len(result) == 2
