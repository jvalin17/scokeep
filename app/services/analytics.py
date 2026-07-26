"""Analytics service — player stats, leaderboard, game history, bid accuracy."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.round import Round


class AnalyticsService:

    @staticmethod
    async def get_playground_stats(db: AsyncSession, playground_id: int) -> dict:
        games, all_rounds = await AnalyticsService._load_data(db, playground_id)
        if not games:
            return {
                "leaderboard": [],
                "game_history": [],
                "head_to_head": [],
                "total_games": 0,
            }

        rounds_by_game = AnalyticsService._group_rounds(all_rounds)
        player_data, game_history = AnalyticsService._calc_player_stats(
            games, rounds_by_game,
        )
        leaderboard = AnalyticsService._calc_leaderboard(player_data)
        head_to_head = AnalyticsService._calc_head_to_head(
            games, rounds_by_game,
        )

        return {
            "leaderboard": leaderboard,
            "game_history": game_history[:20],
            "head_to_head": head_to_head,
            "total_games": len(games),
        }

    @staticmethod
    async def _load_data(db: AsyncSession, playground_id: int):
        """Load all finished games and their scored rounds."""
        games_result = await db.execute(
            select(Game)
            .where(Game.playground_id == playground_id, Game.status == "finished")
            .order_by(Game.started_at.desc())
        )
        games = list(games_result.scalars().all())
        if not games:
            return [], []

        game_ids = [g.id for g in games]
        rounds_result = await db.execute(
            select(Round)
            .where(Round.game_id.in_(game_ids), Round.status == "scored")
            .order_by(Round.game_id, Round.round_num)
        )
        return games, list(rounds_result.scalars().all())

    @staticmethod
    def _group_rounds(all_rounds: list) -> dict[int, list]:
        """Group rounds by game_id."""
        by_game: dict[int, list] = {}
        for r in all_rounds:
            by_game.setdefault(r.game_id, []).append(r)
        return by_game

    @staticmethod
    def _calc_player_stats(games, rounds_by_game):
        """Calculate per-player aggregates and game history."""
        all_players: set[str] = set()
        for g in games:
            all_players.update(g.players)

        player_data: dict[str, dict] = {}
        for name in all_players:
            player_data[name] = {
                "games_played": 0, "wins": 0, "total_score": 0,
                "total_rounds": 0, "bids_made": 0, "bids_total": 0,
                "best_game_score": None, "worst_game_score": None,
            }

        game_history = []
        for game in games:
            players = game.players
            game_rounds = rounds_by_game.get(game.id, [])
            if not game_rounds:
                continue

            game_totals: dict[str, int] = dict.fromkeys(players, 0)
            for r in game_rounds:
                for idx_str, score in r.scores.items():
                    idx = int(idx_str)
                    if idx < len(players):
                        name = players[idx]
                        game_totals[name] += score
                        pd = player_data[name]
                        pd["total_rounds"] += 1
                        pd["total_score"] += score

                        bid = r.bids.get(idx_str)
                        hand = r.hands_won.get(idx_str)
                        if bid is not None and hand is not None:
                            pd["bids_total"] += 1
                            if bid == hand:
                                pd["bids_made"] += 1

            winner = max(
                game_totals, key=lambda n: game_totals[n],
            ) if game_totals else None

            for name in players:
                pd = player_data[name]
                pd["games_played"] += 1
                gs = game_totals.get(name, 0)
                if pd["best_game_score"] is None or gs > pd["best_game_score"]:
                    pd["best_game_score"] = gs
                if pd["worst_game_score"] is None or gs < pd["worst_game_score"]:
                    pd["worst_game_score"] = gs
                if name == winner:
                    pd["wins"] += 1

            game_history.append({
                "game_id": game.id,
                "date": game.started_at.isoformat() if game.started_at else None,
                "players": players,
                "scores": game_totals,
                "winner": winner,
                "rounds_played": len(game_rounds),
                "mode": game.settings.get("mode", "expert"),
            })

        return player_data, game_history

    @staticmethod
    def _calc_leaderboard(player_data: dict) -> list[dict]:
        """Build sorted leaderboard from player aggregates."""
        leaderboard = []
        for name, pd in player_data.items():
            if pd["games_played"] == 0:
                continue
            avg = pd["total_score"] / pd["total_rounds"] if pd["total_rounds"] else 0
            acc = pd["bids_made"] / pd["bids_total"] if pd["bids_total"] else 0
            leaderboard.append({
                "name": name,
                "wins": pd["wins"],
                "games_played": pd["games_played"],
                "win_rate": round(pd["wins"] / pd["games_played"] * 100),
                "total_score": pd["total_score"],
                "avg_score_per_round": round(avg, 1),
                "bid_accuracy": round(acc * 100),
                "best_game": pd["best_game_score"],
                "worst_game": pd["worst_game_score"],
            })
        leaderboard.sort(key=lambda x: (-x["wins"], -x["total_score"]))
        return leaderboard

    @staticmethod
    def _calc_head_to_head(games, rounds_by_game) -> list[dict]:
        """Calculate head-to-head records between player pairs."""
        h2h: dict[tuple, dict] = {}
        for game in games:
            players = game.players
            game_rounds = rounds_by_game.get(game.id, [])
            if not game_rounds:
                continue

            game_totals: dict[str, int] = {}
            for r in game_rounds:
                for idx_str, score in r.scores.items():
                    idx = int(idx_str)
                    if idx < len(players):
                        game_totals.setdefault(players[idx], 0)
                        game_totals[players[idx]] += score

            for i, p1 in enumerate(players):
                for p2 in players[i + 1:]:
                    key = tuple(sorted([p1, p2]))
                    if key not in h2h:
                        h2h[key] = {key[0]: 0, key[1]: 0, "games": 0}
                    h2h[key]["games"] += 1
                    s1 = game_totals.get(p1, 0)
                    s2 = game_totals.get(p2, 0)
                    if s1 > s2:
                        h2h[key][p1] += 1
                    elif s2 > s1:
                        h2h[key][p2] += 1

        return [{"players": list(k), "record": v} for k, v in h2h.items()]
