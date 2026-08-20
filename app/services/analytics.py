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
            game_rounds = rounds_by_game.get(game.id, [])
            if game_rounds:
                history.append(_game_to_history(game, game_rounds))
        return history

    @staticmethod
    def _calc_highlights(games, rounds_by_game) -> dict:
        """Career records: one pass, rule-driven."""
        all_players = {name for g in games for name in g.players}
        career = _init_career(all_players)
        for game in sorted(games, key=lambda g: g.started_at or g.id):
            _process_game_for_career(game, rounds_by_game, career)
        return {"career": _career_tables(career)}

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


def _iter_round_bids(players, game_rounds):
    """Yield (name, bid, hand, score, rnd) for each valid player bid."""
    for rnd in game_rounds:
        for idx_str in rnd.bids:
            idx = int(idx_str)
            if idx >= len(players):
                continue
            bid = rnd.bids.get(idx_str)
            hand = rnd.hands_won.get(idx_str)
            if bid is None or hand is None:
                continue
            score = rnd.scores.get(idx_str, 0)
            yield players[idx], bid, hand, score, rnd


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
        for name, bid, hand, _score, cur_rnd in _iter_round_bids(players, [rnd]):
            made = bid == hand
            _apply_career_rules(career[name], bid, hand, made, cur_rnd.cards_dealt)
            set_results[name].append(made)

        _check_perfect_sets(
            round_idx, rounds_per_set, players, set_results, career,
        )
        if rounds_per_set > 0 and (round_idx + 1) % rounds_per_set == 0:
            set_results = {n: [] for n in players}


def _apply_career_rules(player_career, bid, hand, made, cards_dealt):
    """Apply career rules and miss streak to one player bid."""
    for rule_name, check in CAREER_RULES.items():
        if check(bid, hand, cards_dealt):
            player_career[rule_name] += 1
    if not made:
        player_career["current_miss_streak"] += 1
        current = player_career["current_miss_streak"]
        if current > player_career["longest_miss_streak"]:
            player_career["longest_miss_streak"] = current
    else:
        player_career["current_miss_streak"] = 0


def _game_to_history(game, game_rounds):
    """Convert one game + rounds into a history entry dict."""
    players = game.players
    game_totals = dict.fromkeys(players, 0)
    for rnd in game_rounds:
        for idx_str, score in rnd.scores.items():
            idx = int(idx_str)
            if idx < len(players):
                game_totals[players[idx]] += score
    winner = max(game_totals, key=lambda n: game_totals[n]) if game_totals else None
    return {
        "game_id": game.id,
        "date": game.started_at.isoformat() if game.started_at else None,
        "players": players,
        "scores": game_totals,
        "winner": winner,
        "rounds_played": len(game_rounds),
        "mode": game.settings.get("mode", "expert"),
    }


def _init_career(all_players):
    """Initialize career counters for all players."""
    return {
        name: dict.fromkeys(CAREER_RULES, 0)
        | {"current_miss_streak": 0, "longest_miss_streak": 0, "perfect_sets": 0}
        for name in all_players
    }


def _career_tables(career):
    """Build sorted career tables from counters."""
    return {
        "sniper": _career_table(career, "sniper"),
        "zero_master": _career_table(career, "zero_master"),
        "high_roller": _career_table(career, "high_roller"),
        "all_in": _career_table(career, "all_in"),
        "jinxed": _career_table(career, "longest_miss_streak", "longest"),
        "perfect_set": _career_table(career, "perfect_sets"),
    }


def _check_perfect_sets(round_idx, rounds_per_set, players, set_results, career):
    """Check for perfect sets at set boundaries."""
    if rounds_per_set <= 0 or (round_idx + 1) % rounds_per_set != 0:
        return
    for name in players:
        results = set_results.get(name, [])
        if len(results) >= rounds_per_set and all(results[-rounds_per_set:]):
            career[name]["perfect_sets"] += 1


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
    s = {
        "totals": dict.fromkeys(players, 0),
        "bids_made": dict.fromkeys(players, 0),
        "bids_total": dict.fromkeys(players, 0),
        "zero_bids_made": dict.fromkeys(players, 0),
        "overbids": dict.fromkeys(players, 0),
        "underbids": dict.fromkeys(players, 0),
        "best_bid": {},
        "longest_miss": dict.fromkeys(players, 0),
        "best_round": {},
        "worst_round": {},
        "hit_streak": dict.fromkeys(players, 0),
        "longest_hit": dict.fromkeys(players, 0),
    }
    miss_streak = dict.fromkeys(players, 0)
    hit_streak = dict.fromkeys(players, 0)

    for name, bid, hand, score, _rnd in _iter_round_bids(players, game_rounds):
        s["totals"][name] += score
        s["bids_total"][name] += 1
        made = bid == hand
        _tally_bid(s, miss_streak, hit_streak, name, bid, hand, made, score)

    return s


def _tally_bid(s, miss_streak, hit_streak, name, bid, hand, made, score):
    """Update stat counters for a single bid result."""
    if made:
        s["bids_made"][name] += 1
        miss_streak[name] = 0
        hit_streak[name] += 1
        if hit_streak[name] > s["longest_hit"][name]:
            s["longest_hit"][name] = hit_streak[name]
        if bid == 0:
            s["zero_bids_made"][name] += 1
        if name not in s["best_bid"] or bid > s["best_bid"][name]:
            s["best_bid"][name] = bid
    else:
        miss_streak[name] += 1
        hit_streak[name] = 0
        if miss_streak[name] > s["longest_miss"][name]:
            s["longest_miss"][name] = miss_streak[name]
    if bid > hand:
        s["overbids"][name] += 1
    elif bid < hand:
        s["underbids"][name] += 1
    # Track best/worst single round scores
    if name not in s["best_round"] or score > s["best_round"][name]:
        s["best_round"][name] = score
    if name not in s["worst_round"] or score < s["worst_round"][name]:
        s["worst_round"][name] = score


def _best_player(data, key="value"):
    """Find player with highest value. Returns None if all zero."""
    if not data:
        return None
    name = max(data, key=lambda n: data[n])
    return {"name": name, key: data[name]} if data[name] > 0 else None


def _build_awards(stats):
    """Transform accumulated stats into award dicts."""
    totals = stats["totals"]
    mvp_name = max(totals, key=lambda n: totals[n])
    worst_name = min(totals, key=lambda n: totals[n])
    return {
        "mvp": {"name": mvp_name, "score": totals[mvp_name]},
        "sharpshooter": _best_accuracy(stats),
        "brick_wall": _best_player(stats["zero_bids_made"], "count"),
        "bold_move": _best_player(stats["best_bid"], "bid"),
        "cursed": _best_player(stats["longest_miss"], "streak"),
        "sandbagger": _best_player(stats["underbids"], "count"),
        "gambler": _best_player(stats["overbids"], "count"),
        "on_fire": _best_player(stats["longest_hit"], "streak"),
        "best_round": _best_player(stats["best_round"], "score"),
        "worst_round": _worst_player(stats["worst_round"], "score"),
        "wooden_spoon": {"name": worst_name, "score": totals[worst_name]},
    }


def _worst_player(data, key="value"):
    """Find player with lowest (most negative) value."""
    if not data:
        return None
    name = min(data, key=lambda n: data[n])
    return {"name": name, key: data[name]} if data[name] < 0 else None


def _best_accuracy(stats):
    """Find player with best bid accuracy."""
    accuracies = {
        name: round(stats["bids_made"][name] / stats["bids_total"][name] * 100)
        for name in stats["totals"] if stats["bids_total"][name] > 0
    }
    if not accuracies:
        return None
    best = max(accuracies, key=lambda n: accuracies[n])
    return {"name": best, "accuracy": accuracies[best]}
