"""Analytics service — game history, career highlights, last game awards."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import HIGH_ROLLER_MIN_BID
from app.models.game import Game
from app.models.round import Round

# Career record rules: name → condition(bid, hand, cards_dealt)
CAREER_RULES = {
    "sniper": lambda bid, hand, cards: bid == 1 and bid == hand,
    "zero_master": lambda bid, hand, cards: bid == 0 and bid == hand,
    "high_roller": lambda bid, hand, cards: (
        bid >= HIGH_ROLLER_MIN_BID and bid == hand
    ),
    "all_in": lambda bid, hand, cards: bid == cards and bid == hand,
}


class AnalyticsService:

    @staticmethod
    async def get_playground_stats(
        db: AsyncSession, playground_id: int,
        insights_blob: dict | None = None,
    ) -> dict:
        empty_highlights = {
            "career": {
                "sniper": [], "zero_master": [], "high_roller": [],
                "all_in": [], "jinxed": [], "perfect_set": [],
            },
            "last_game": None,
        }

        games, all_rounds = await AnalyticsService._load_data(
            db, playground_id,
        )
        if not games:
            return {
                "game_history": [],
                "highlights": (insights_blob or {}).get(
                    "highlights", empty_highlights,
                ),
                "insights": insights_blob,
                "total_games": 0,
            }

        rounds_by_game = AnalyticsService._group_rounds(all_rounds)
        game_history = AnalyticsService._calc_game_history(
            games, rounds_by_game,
        )
        highlights = _resolve_highlights(
            insights_blob, games, rounds_by_game,
        )

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
            .where(
                Game.playground_id == playground_id,
                Game.status == "finished",
            )
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
        for rnd in all_rounds:
            by_game.setdefault(rnd.game_id, []).append(rnd)
        return by_game

    @staticmethod
    def _calc_game_history(games, rounds_by_game) -> list[dict]:
        """Build game history for the Games tab."""
        history = []
        for game in games:
            players = game.players
            game_rounds = rounds_by_game.get(game.id, [])
            if not game_rounds:
                continue

            game_totals = dict.fromkeys(players, 0)
            for rnd in game_rounds:
                for idx_str, score in rnd.scores.items():
                    idx = int(idx_str)
                    if idx < len(players):
                        game_totals[players[idx]] += score

            winner = (
                max(game_totals, key=lambda n: game_totals[n])
                if game_totals else None
            )

            history.append({
                "game_id": game.id,
                "date": (
                    game.started_at.isoformat()
                    if game.started_at else None
                ),
                "players": players,
                "scores": game_totals,
                "winner": winner,
                "rounds_played": len(game_rounds),
                "mode": game.settings.get("mode", "expert"),
            })
        return history

    @staticmethod
    def _calc_highlights(games, rounds_by_game) -> dict:
        """Career records: one pass, rule-driven."""
        all_players = {name for g in games for name in g.players}
        career = {
            name: dict.fromkeys(CAREER_RULES, 0)
            | {
                "current_miss_streak": 0,
                "longest_miss_streak": 0,
                "perfect_sets": 0,
            }
            for name in all_players
        }

        sorted_games = sorted(
            games, key=lambda g: g.started_at or g.id,
        )

        for game in sorted_games:
            _process_game_for_career(
                game, rounds_by_game, career,
            )

        return {
            "career": {
                "sniper": _career_table(career, "sniper"),
                "zero_master": _career_table(career, "zero_master"),
                "high_roller": _career_table(career, "high_roller"),
                "all_in": _career_table(career, "all_in"),
                "jinxed": _career_table(
                    career, "longest_miss_streak", "longest",
                ),
                "perfect_set": _career_table(career, "perfect_sets"),
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
        game_rounds = rounds_by_game.get(game.id, [])
        if not game_rounds:
            return None

        stats = _accumulate_game_stats(game.players, game_rounds)
        return _build_awards(stats)

    @staticmethod
    async def clear_stats(db: AsyncSession, playground_id: int) -> int:
        """Delete all finished games and their rounds."""
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


# ── Helper functions (module-level, testable independently) ──


def _resolve_highlights(insights_blob, games, rounds_by_game):
    """Return cached highlights if fresh, otherwise recompute."""
    cached = (insights_blob or {}).get("highlights")
    cached_total = (insights_blob or {}).get("total_games", 0)
    if cached and cached_total == len(games):
        return cached

    highlights = AnalyticsService._calc_highlights(
        games, rounds_by_game,
    )
    last_game = AnalyticsService._calc_last_game_awards(
        games, rounds_by_game,
    )
    highlights["last_game"] = last_game
    return highlights


def _process_game_for_career(game, rounds_by_game, career):
    """Process one game's rounds for career record counting."""
    players = game.players
    game_rounds = rounds_by_game.get(game.id, [])
    if not game_rounds:
        return

    rounds_per_set = game.settings.get("rounds_per_set", 8)
    set_results: dict[str, list[bool]] = {n: [] for n in players}

    for round_idx, rnd in enumerate(game_rounds):
        for idx_str in rnd.bids:
            idx = int(idx_str)
            if idx >= len(players):
                continue
            name = players[idx]
            bid = rnd.bids.get(idx_str)
            hand = rnd.hands_won.get(idx_str)
            if bid is None or hand is None:
                continue

            made = bid == hand

            # Apply all career rules
            for rule_name, check in CAREER_RULES.items():
                if check(bid, hand, rnd.cards_dealt):
                    career[name][rule_name] += 1

            # Miss streak
            if not made:
                career[name]["current_miss_streak"] += 1
                current = career[name]["current_miss_streak"]
                if current > career[name]["longest_miss_streak"]:
                    career[name]["longest_miss_streak"] = current
            else:
                career[name]["current_miss_streak"] = 0

            set_results[name].append(made)

        # Perfect set at set boundaries
        if rounds_per_set > 0 and (round_idx + 1) % rounds_per_set == 0:
            for name in players:
                results = set_results.get(name, [])
                if (
                    len(results) >= rounds_per_set
                    and all(results[-rounds_per_set:])
                ):
                    career[name]["perfect_sets"] += 1
            set_results = {n: [] for n in players}


def _career_table(career, key, count_key="count"):
    """Build sorted table from career counters."""
    sort_key = "longest" if count_key == "longest" else "count"
    table = [
        {"name": name, sort_key: data[key]}
        for name, data in career.items()
    ]
    table.sort(key=lambda x: -x[sort_key])
    return table


def _accumulate_game_stats(players, game_rounds):
    """Collect per-player stats from one game's rounds."""
    totals = dict.fromkeys(players, 0)
    bids_made = dict.fromkeys(players, 0)
    bids_total = dict.fromkeys(players, 0)
    zero_bids_made = dict.fromkeys(players, 0)
    overbids = dict.fromkeys(players, 0)
    underbids = dict.fromkeys(players, 0)
    best_bid: dict[str, int] = {}
    miss_streak = dict.fromkeys(players, 0)
    longest_miss = dict.fromkeys(players, 0)

    for rnd in game_rounds:
        for idx_str in rnd.bids:
            idx = int(idx_str)
            if idx >= len(players):
                continue
            name = players[idx]
            bid = rnd.bids.get(idx_str)
            hand = rnd.hands_won.get(idx_str)
            score = rnd.scores.get(idx_str, 0)
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

    return {
        "totals": totals,
        "bids_made": bids_made,
        "bids_total": bids_total,
        "zero_bids_made": zero_bids_made,
        "overbids": overbids,
        "underbids": underbids,
        "best_bid": best_bid,
        "longest_miss": longest_miss,
    }


def _best_player(data, key="value"):
    """Find player with highest value. Returns None if all zero."""
    if not data:
        return None
    name = max(data, key=lambda n: data[n])
    return {"name": name, key: data[name]} if data[name] > 0 else None


def _build_awards(stats):
    """Transform accumulated stats into award dicts."""
    totals = stats["totals"]
    bids_made = stats["bids_made"]
    bids_total = stats["bids_total"]

    mvp_name = max(totals, key=lambda n: totals[n])

    accuracies = {
        name: round(bids_made[name] / bids_total[name] * 100)
        for name in totals if bids_total[name] > 0
    }
    sharpshooter = None
    if accuracies:
        best = max(accuracies, key=lambda n: accuracies[n])
        sharpshooter = {"name": best, "accuracy": accuracies[best]}

    bold_move = None
    if stats["best_bid"]:
        boldest = max(
            stats["best_bid"], key=lambda n: stats["best_bid"][n],
        )
        if stats["best_bid"][boldest] > 0:
            bold_move = {
                "name": boldest,
                "bid": stats["best_bid"][boldest],
            }

    return {
        "mvp": {"name": mvp_name, "score": totals[mvp_name]},
        "sharpshooter": sharpshooter,
        "brick_wall": _best_player(stats["zero_bids_made"], "count"),
        "bold_move": bold_move,
        "cursed": _best_player(stats["longest_miss"], "streak"),
        "sandbagger": _best_player(stats["underbids"], "count"),
        "gambler": _best_player(stats["overbids"], "count"),
    }
