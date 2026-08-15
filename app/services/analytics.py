"""Analytics service — player stats, leaderboard, game history, bid accuracy."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import HIGH_ROLLER_MIN_BID
from app.models.game import Game
from app.models.round import Round


class AnalyticsService:

    @staticmethod
    async def get_playground_stats(
        db: AsyncSession, playground_id: int, insights_blob: dict | None = None,
    ) -> dict:
        games, all_rounds = await AnalyticsService._load_data(db, playground_id)
        empty_highlights = {
            "career": {
                "sniper": [], "zero_master": [], "high_roller": [],
                "all_in": [], "jinxed": [], "perfect_set": [],
            },
            "last_game": None,
        }
        if not games:
            return {
                "game_history": [],
                "highlights": empty_highlights,
                "insights": insights_blob,
                "total_games": 0,
            }

        rounds_by_game = AnalyticsService._group_rounds(all_rounds)
        _player_data, game_history = AnalyticsService._calc_player_stats(
            games, rounds_by_game,
        )
        highlights = AnalyticsService._calc_highlights(
            games, rounds_by_game,
        )
        last_game_awards = AnalyticsService._calc_last_game_awards(
            games, rounds_by_game,
        )
        highlights["last_game"] = last_game_awards

        return {
            "game_history": game_history[:20],
            "highlights": highlights,
            "insights": insights_blob,
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
    def _calc_trends(games, rounds_by_game) -> list[dict]:
        """Calculate per-player trends: streaks, overbid/underbid, clutch."""
        all_players: set[str] = set()
        for g in games:
            all_players.update(g.players)

        trend_data: dict[str, dict] = {}
        for name in all_players:
            trend_data[name] = {
                "overbids": 0, "underbids": 0, "total_bid_rounds": 0,
                "current_streak": 0, "longest_streak": 0,
                "clutch_wins": 0, "clutch_opportunities": 0,
            }

        # Process games oldest-first for streak calculation
        sorted_games = sorted(games, key=lambda g: g.started_at or g.id)

        for game in sorted_games:
            players = game.players
            game_rounds = rounds_by_game.get(game.id, [])
            if not game_rounds:
                continue

            # Compute game totals and per-round running totals
            game_totals: dict[str, int] = dict.fromkeys(players, 0)
            halfway = len(game_rounds) // 2
            halfway_totals: dict[str, int] = dict.fromkeys(players, 0)

            for round_idx, r in enumerate(game_rounds):
                for idx_str, score in r.scores.items():
                    idx = int(idx_str)
                    if idx < len(players):
                        game_totals[players[idx]] += score
                        if round_idx < halfway:
                            halfway_totals[players[idx]] += score

                # Count overbids/underbids
                for idx_str in r.bids:
                    idx = int(idx_str)
                    if idx < len(players):
                        bid = r.bids.get(idx_str)
                        hand = r.hands_won.get(idx_str)
                        if bid is not None and hand is not None:
                            name = players[idx]
                            trend_data[name]["total_bid_rounds"] += 1
                            if bid > hand:
                                trend_data[name]["overbids"] += 1
                            elif bid < hand:
                                trend_data[name]["underbids"] += 1

            winner = max(game_totals, key=lambda n: game_totals[n])

            # Streaks
            for name in players:
                if name == winner:
                    trend_data[name]["current_streak"] += 1
                    if trend_data[name]["current_streak"] > trend_data[name]["longest_streak"]:
                        trend_data[name]["longest_streak"] = trend_data[name]["current_streak"]
                else:
                    trend_data[name]["current_streak"] = 0

            # Clutch: was behind at halfway but won
            if len(game_rounds) >= 2:
                halfway_leader = max(halfway_totals, key=lambda n: halfway_totals[n])
                for name in players:
                    if name != halfway_leader:
                        trend_data[name]["clutch_opportunities"] += 1
                        if name == winner:
                            trend_data[name]["clutch_wins"] += 1

        return [
            {"name": name, **data}
            for name, data in trend_data.items()
        ]

    @staticmethod
    def _calc_highlights(games, rounds_by_game) -> dict:
        """Calculate player highlights: career records + recent form."""
        all_players: set[str] = set()
        for g in games:
            all_players.update(g.players)

        # Career counters per player
        career: dict[str, dict] = {}
        for name in all_players:
            career[name] = {
                "sniper": 0, "zero_master": 0, "high_roller": 0,
                "all_in": 0, "current_miss_streak": 0, "longest_miss_streak": 0,
                "perfect_sets": 0,
            }

        sorted_games = sorted(games, key=lambda g: g.started_at or g.id)

        for game in sorted_games:
            players = game.players
            game_rounds = rounds_by_game.get(game.id, [])
            if not game_rounds:
                continue

            rounds_per_set = game.settings.get("rounds_per_set", 8)

            # Track per-set accuracy for perfect set detection
            set_bids: dict[str, list[bool]] = {name: [] for name in players}

            for round_idx, r in enumerate(game_rounds):
                for idx_str in r.bids:
                    idx = int(idx_str)
                    if idx >= len(players):
                        continue
                    name = players[idx]
                    bid = r.bids.get(idx_str)
                    hand = r.hands_won.get(idx_str)
                    if bid is None or hand is None:
                        continue

                    made = bid == hand

                    # Career: sniper (bid 1 made)
                    if bid == 1 and made:
                        career[name]["sniper"] += 1

                    # Career: zero master (bid 0 made)
                    if bid == 0 and made:
                        career[name]["zero_master"] += 1

                    # Career: high roller (bid 3+ made)
                    if bid >= HIGH_ROLLER_MIN_BID and made:
                        career[name]["high_roller"] += 1

                    # Career: all-in (bid = cards dealt and made)
                    if bid == r.cards_dealt and made:
                        career[name]["all_in"] += 1

                    # Career: jinxed (miss streak)
                    if not made:
                        career[name]["current_miss_streak"] += 1
                        current = career[name]["current_miss_streak"]
                        if current > career[name]["longest_miss_streak"]:
                            career[name]["longest_miss_streak"] = current
                    else:
                        career[name]["current_miss_streak"] = 0

                    # Perfect set tracking
                    set_bids[name].append(made)

                # Check for perfect set at set boundaries
                if (round_idx + 1) % rounds_per_set == 0:
                    for name in players:
                        results = set_bids.get(name, [])
                        if len(results) >= rounds_per_set and all(results[-rounds_per_set:]):
                            career[name]["perfect_sets"] += 1
                    set_bids = {name: [] for name in players}

        # Build career tables (sorted by count descending)
        def career_table(key, count_key="count"):
            table = []
            for name, data in career.items():
                value = data[key]
                if count_key == "longest":
                    table.append({"name": name, "longest": value})
                else:
                    table.append({"name": name, "count": value})
            sort_key = "longest" if count_key == "longest" else "count"
            table.sort(key=lambda x: -x[sort_key])
            return table

        return {
            "career": {
                "sniper": career_table("sniper"),
                "zero_master": career_table("zero_master"),
                "high_roller": career_table("high_roller"),
                "all_in": career_table("all_in"),
                "jinxed": career_table(
                    "longest_miss_streak", "longest",
                ),
                "perfect_set": career_table("perfect_sets"),
            },
        }

    @staticmethod
    def _calc_last_game_awards(games, rounds_by_game) -> dict | None:
        """Awards for the most recent finished game."""
        sorted_games = sorted(
            games, key=lambda g: g.started_at or g.id,
        )
        if not sorted_games:
            return None

        game = sorted_games[-1]
        players = game.players
        game_rounds = rounds_by_game.get(game.id, [])
        if not game_rounds:
            return None

        totals = dict.fromkeys(players, 0)
        bids_made = dict.fromkeys(players, 0)
        bids_total = dict.fromkeys(players, 0)
        zero_bids_made = dict.fromkeys(players, 0)
        overbids = dict.fromkeys(players, 0)
        underbids = dict.fromkeys(players, 0)
        best_bid = {}  # name → highest bid that was made
        miss_streak = dict.fromkeys(players, 0)
        longest_miss = dict.fromkeys(players, 0)

        for r in game_rounds:
            for idx_str in r.bids:
                idx = int(idx_str)
                if idx >= len(players):
                    continue
                name = players[idx]
                bid = r.bids.get(idx_str)
                hand = r.hands_won.get(idx_str)
                score = r.scores.get(idx_str, 0)
                if bid is None or hand is None:
                    continue

                totals[name] += score
                bids_total[name] += 1
                made = bid == hand

                if made:
                    bids_made[name] += 1
                    miss_streak[name] = 0
                    if bid == 0:
                        zero_bids_made[name] += 1
                    if name not in best_bid or bid > best_bid[name]:
                        best_bid[name] = bid
                else:
                    miss_streak[name] += 1
                    if miss_streak[name] > longest_miss[name]:
                        longest_miss[name] = miss_streak[name]

                if bid > hand:
                    overbids[name] += 1
                elif bid < hand:
                    underbids[name] += 1

        def best_player(data, key="value"):
            if not data:
                return None
            name = max(data, key=lambda n: data[n])
            return {"name": name, key: data[name]} if data[name] > 0 else None

        # MVP: highest total score
        mvp_name = max(totals, key=lambda n: totals[n])
        mvp = {"name": mvp_name, "score": totals[mvp_name]}

        # Sharpshooter: best accuracy
        accuracies = {}
        for name in players:
            if bids_total[name] > 0:
                accuracies[name] = round(
                    bids_made[name] / bids_total[name] * 100,
                )
        sharpshooter = None
        if accuracies:
            best = max(accuracies, key=lambda n: accuracies[n])
            sharpshooter = {
                "name": best, "accuracy": accuracies[best],
            }

        # Brick Wall: most successful 0-bids
        brick_wall = best_player(zero_bids_made, "count")

        # Bold Move: highest bid that was made
        bold_move = None
        if best_bid:
            boldest = max(best_bid, key=lambda n: best_bid[n])
            if best_bid[boldest] > 0:
                bold_move = {
                    "name": boldest, "bid": best_bid[boldest],
                }

        # Cursed: longest miss streak
        cursed = best_player(longest_miss, "streak")

        # Sandbagger: most underbids
        sandbagger = best_player(underbids, "count")

        # Gambler: most overbids
        gambler = best_player(overbids, "count")

        return {
            "mvp": mvp,
            "sharpshooter": sharpshooter,
            "brick_wall": brick_wall,
            "bold_move": bold_move,
            "cursed": cursed,
            "sandbagger": sandbagger,
            "gambler": gambler,
        }

    @staticmethod
    async def clear_stats(db: AsyncSession, playground_id: int) -> int:
        """Delete all finished games and their rounds. Returns count deleted."""
        games_result = await db.execute(
            select(Game.id).where(
                Game.playground_id == playground_id,
                Game.status == "finished",
            )
        )
        game_ids = [row[0] for row in games_result.all()]
        if not game_ids:
            return 0

        await db.execute(
            delete(Round).where(Round.game_id.in_(game_ids))
        )
        await db.execute(
            delete(Game).where(Game.id.in_(game_ids))
        )
        await db.commit()
        return len(game_ids)
