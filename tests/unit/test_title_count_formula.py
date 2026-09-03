"""TDD: Title count formula → clamp(2*N, 4, 14).

The old formula was max(10, len(players) + 2). The new formula is
clamp(2 * num_players, 4, 14) — 2 titles per player, min 4, max 14.
"""


class TestTitleCountFormula:
    """select_titles default target uses clamp(2*N, 4, 14)."""

    def _make_candidates(self, n_players):
        """Generate enough candidates for testing."""
        players = [f"P{i}" for i in range(n_players)]
        candidates = []
        for i, p in enumerate(players):
            for j in range(5):
                candidates.append(
                    {
                        "key": f"title_{i}_{j}",
                        "emoji": "🏆",
                        "title": f"Title {i}-{j}",
                        "desc": "test",
                        "player": p,
                        "detail": "test",
                        "score": float(100 - i * 10 - j),
                    }
                )
        return candidates, players

    def test_2_players_gets_4_titles(self):
        """2 players → clamp(4, 4, 14) = 4."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(2)
        result = select_titles(candidates, players)
        assert len(result) == 4

    def test_3_players_gets_6_titles(self):
        """3 players → clamp(6, 4, 14) = 6."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(3)
        result = select_titles(candidates, players)
        assert len(result) == 6

    def test_4_players_gets_8_titles(self):
        """4 players → clamp(8, 4, 14) = 8."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(4)
        result = select_titles(candidates, players)
        assert len(result) == 8

    def test_5_players_gets_10_titles(self):
        """5 players → clamp(10, 4, 14) = 10."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(5)
        result = select_titles(candidates, players)
        assert len(result) == 10

    def test_7_players_gets_14_titles(self):
        """7 players → clamp(14, 4, 14) = 14."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(7)
        result = select_titles(candidates, players)
        assert len(result) == 14

    def test_8_players_capped_at_14(self):
        """8 players → clamp(16, 4, 14) = 14."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(8)
        result = select_titles(candidates, players)
        assert len(result) == 14

    def test_explicit_target_overrides(self):
        """Explicit target parameter overrides, but coverage guarantee still applies."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(2)
        result = select_titles(candidates, players, target=3)
        assert len(result) == 3

    def test_fewer_candidates_than_target(self):
        """When candidates < target, return all candidates without error."""
        from app.services.game_titles import select_titles

        candidates = [
            {
                "key": "only_one",
                "emoji": "🏆",
                "title": "Only",
                "desc": "test",
                "player": "P0",
                "detail": "t",
                "score": 100.0,
            },
        ]
        result = select_titles(candidates, ["P0", "P1", "P2", "P3"], target=8)
        assert len(result) == 1  # only 1 candidate available

    def test_1_player_gets_4_titles(self):
        """1 player → clamp(2, 4, 14) = 4."""
        from app.services.game_titles import select_titles

        candidates, players = self._make_candidates(1)
        result = select_titles(candidates, players)
        assert len(result) == 4
