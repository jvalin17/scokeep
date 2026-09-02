"""Analytics service — game history, career highlights, last game awards."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import HIGH_ROLLER_MIN_BID
from app.models.game import Game
from app.models.round import Round
from app.services.round_utils import _iter_round_bids

# Career record rules: name → condition(bid, hand, cards_dealt)
CAREER_RULES = {
    "sniper": lambda bid, hand, cards: bid == 1 and bid == hand,
    "zero_master": lambda bid, hand, cards: bid == 0 and bid == hand,
    "high_roller": lambda bid, hand, cards: bid >= HIGH_ROLLER_MIN_BID and bid == hand,
    "all_in": lambda bid, hand, cards: bid == cards and bid == hand,
}


class AnalyticsService:
    @staticmethod
    async def get_playground_stats(
        db: AsyncSession,
        playground_id: int,
        insights_blob: dict | None = None,
    ) -> dict:
        empty_highlights = {
            "career": {
                "sniper": [], "zero_master": [], "high_roller": [],
                "all_in": [], "jinxed": [], "perfect_set": [],
                "hot_hand": [], "biggest_bid": [], "set_champion": [],
                "set_disaster": [], "comeback_king": [], "sweep": [],
                "iron_wall": [], "heartbreaker": [], "triple_crown": [],
            },
            "last_game": None,
        }

        games, all_rounds = await AnalyticsService._load_data(
            db,
            playground_id,
        )
        if not games:
            return {
                "game_history": [],
                "highlights": (insights_blob or {}).get(
                    "highlights",
                    empty_highlights,
                ),
                "insights": insights_blob,
                "total_games": 0,
            }

        rounds_by_game = AnalyticsService._group_rounds(all_rounds)
        game_history = AnalyticsService._calc_game_history(
            games,
            rounds_by_game,
        )
        highlights = _resolve_highlights(
            insights_blob,
            games,
            rounds_by_game,
        )

        return {
            "game_history": game_history[:20],
            "highlights": highlights,
            "insights": insights_blob,
            "total_games": len(game_history),
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
            games,
            key=lambda g: g.started_at or g.id,
        )
        if not sorted_games:
            return None

        game = sorted_games[-1]
        game_rounds = rounds_by_game.get(game.id, [])
        if not game_rounds:
            return None

        from app.services.game_titles import evaluate_titles

        titles = evaluate_titles(game.players, game_rounds)
        return {"titles": titles}

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

        await db.execute(delete(Round).where(Round.game_id.in_(game_ids)))
        await db.execute(delete(Game).where(Game.id.in_(game_ids)))
        await db.commit()
        return len(game_ids)


# ── Helper functions (module-level, testable independently) ──




def _resolve_highlights(insights_blob, games, rounds_by_game):
    """Return cached highlights if fresh, otherwise recompute."""
    # Filter to games with scored rounds — matches insights blob total_games
    games_with_rounds = [g for g in games if g.id in rounds_by_game]
    cached = (insights_blob or {}).get("highlights")
    cached_total = (insights_blob or {}).get("total_games", 0)
    if cached and cached_total == len(games_with_rounds):
        return cached

    highlights = AnalyticsService._calc_highlights(
        games_with_rounds,
        rounds_by_game,
    )
    last_game = AnalyticsService._calc_last_game_awards(
        games_with_rounds,
        rounds_by_game,
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

    # New accumulators
    game_totals = dict.fromkeys(players, 0)
    game_bids_made = dict.fromkeys(players, 0)
    game_bids_total = dict.fromkeys(players, 0)
    cumulative = {n: [] for n in players}
    running = dict.fromkeys(players, 0)
    set_scores = dict.fromkeys(players, 0)

    for round_idx, rnd in enumerate(game_rounds):
        for name, bid, hand, score, cur_rnd in _iter_round_bids(players, [rnd]):
            made = bid == hand
            _apply_career_rules(career[name], bid, hand, made, cur_rnd.cards_dealt)
            set_results[name].append(made)
            # Accumulate per-game stats
            game_totals[name] += score
            game_bids_total[name] += 1
            if bid == hand:
                game_bids_made[name] += 1
            running[name] += score
            cumulative[name].append(running[name])
            set_scores[name] += score

        _check_perfect_sets(
            round_idx,
            rounds_per_set,
            players,
            set_results,
            career,
        )
        if rounds_per_set > 0 and (round_idx + 1) % rounds_per_set == 0:
            _check_set_scores(players, set_scores, career)
            set_scores = dict.fromkeys(players, 0)
            set_results = {n: [] for n in players}

    # POST-GAME: process final partial set
    _check_set_scores(players, set_scores, career)
    _post_game_career_sweeps(
        players, game_totals, game_bids_made, game_bids_total, cumulative, career
    )



def _post_game_career_sweeps(players, game_totals, game_bids_made, game_bids_total,
                             cumulative, career):
    """Compute post-game sweep/comeback/triple_crown and update career."""
    # Sweep — sole winner gets games_won
    if game_totals:
        top_score = max(game_totals.values())
        winners = [n for n, s in game_totals.items() if s == top_score]
        if len(winners) == 1:
            career[winners[0]]["games_won"] += 1

    # Comeback king
    for name in players:
        cum = cumulative.get(name, [])
        if cum:
            final = cum[-1]
            min_cum = min(cum)
            recovery = final - min_cum
            if recovery > career[name]["biggest_comeback"]:
                career[name]["biggest_comeback"] = recovery

    # Triple crown — sole leader in both score and accuracy
    accuracies = {}
    for name in players:
        total = game_bids_total.get(name, 0)
        if total > 0:
            accuracies[name] = game_bids_made[name] / total
    if accuracies and game_totals:
        best_acc = max(accuracies.values())
        acc_leaders = [n for n, a in accuracies.items() if a == best_acc]
        best_score = max(game_totals.values())
        score_leaders = [n for n, s in game_totals.items() if s == best_score]
        if len(acc_leaders) == 1 and len(score_leaders) == 1 and acc_leaders[0] == score_leaders[0]:
            career[acc_leaders[0]]["triple_crowns"] += 1

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

    # New career tracking fields
    player_career["total_rounds_played"] += 1
    if abs(bid - hand) == 1:
        player_career["off_by_one_total"] += 1
    if made:
        player_career["current_positive_streak"] += 1
        if player_career["current_positive_streak"] > player_career["longest_positive_streak"]:
            player_career["longest_positive_streak"] = player_career["current_positive_streak"]
        if bid > player_career["biggest_bid_made"]:
            player_career["biggest_bid_made"] = bid
        if bid == 0:
            player_career["current_zero_streak"] += 1
            if player_career["current_zero_streak"] > player_career["longest_zero_streak"]:
                player_career["longest_zero_streak"] = player_career["current_zero_streak"]
        else:
            player_career["current_zero_streak"] = 0
    else:
        player_career["current_positive_streak"] = 0
        player_career["current_zero_streak"] = 0


def _game_to_history(game, game_rounds):
    """Convert one game + rounds into a history entry dict."""
    players = game.players
    game_totals = dict.fromkeys(players, 0)
    for rnd in game_rounds:
        for idx_str, score in rnd.scores.items():
            idx = int(idx_str)
            if idx < len(players):
                game_totals[players[idx]] += score
    if game_totals:
        top_score = max(game_totals.values())
        leaders = [n for n, s in game_totals.items() if s == top_score]
        winner = leaders[0] if len(leaders) == 1 else None
    else:
        winner = None
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
        | {
            "current_miss_streak": 0,
            "longest_miss_streak": 0,
            "perfect_sets": 0,
            "longest_positive_streak": 0,
            "current_positive_streak": 0,
            "biggest_bid_made": 0,
            "best_set_score": 0,
            "worst_set_score": 0,
            "biggest_comeback": 0,
            "games_won": 0,
            "longest_zero_streak": 0,
            "current_zero_streak": 0,
            "off_by_one_total": 0,
            "triple_crowns": 0,
            "total_rounds_played": 0,
        }
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
        "hot_hand": _career_table(career, "longest_positive_streak", "longest"),
        "biggest_bid": _career_table(career, "biggest_bid_made", "highest"),
        "set_champion": _career_table(career, "best_set_score", "highest"),
        "set_disaster": _career_table(career, "worst_set_score", "worst"),
        "comeback_king": _career_table(career, "biggest_comeback", "highest"),
        "sweep": _career_table(career, "games_won"),
        "iron_wall": _career_table(career, "longest_zero_streak", "longest"),
        "heartbreaker": _career_table(career, "off_by_one_total"),
        "triple_crown": _career_table(career, "triple_crowns"),
    }


def _check_perfect_sets(round_idx, rounds_per_set, players, set_results, career):
    """Check for perfect sets at set boundaries."""
    if rounds_per_set <= 0 or (round_idx + 1) % rounds_per_set != 0:
        return
    for name in players:
        results = set_results.get(name, [])
        if len(results) >= rounds_per_set and all(results[-rounds_per_set:]):
            career[name]["perfect_sets"] += 1


def _check_set_scores(players, set_scores, career):
    """Update best/worst set score for each player."""
    for name in players:
        score = set_scores.get(name, 0)
        if score > career[name]["best_set_score"]:
            career[name]["best_set_score"] = score
        if score < 0 and score < career[name]["worst_set_score"]:
            career[name]["worst_set_score"] = score


def _career_table(career, key, count_key="count"):
    """Build sorted table from career counters."""
    if count_key == "longest":
        sort_key = "longest"
        table = [{"name": name, sort_key: data[key]} for name, data in career.items()]
        table.sort(key=lambda x: -x[sort_key])
    elif count_key == "highest":
        sort_key = "highest"
        table = [
            {"name": name, sort_key: data[key]}
            for name, data in career.items() if data[key] > 0
        ]
        table.sort(key=lambda x: -x[sort_key])
    elif count_key == "worst":
        sort_key = "worst"
        table = [
            {"name": name, sort_key: data[key]}
            for name, data in career.items() if data[key] < 0
        ]
        table.sort(key=lambda x: x[sort_key])
    else:
        sort_key = "count"
        table = [{"name": name, sort_key: data[key]} for name, data in career.items()]
        table.sort(key=lambda x: -x[sort_key])
    return table


# Legacy award functions — kept for BUG-024 regression tests.
# Production uses game_titles.evaluate_titles.
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
    }
    miss_streak = dict.fromkeys(players, 0)

    for name, bid, hand, score, _rnd in _iter_round_bids(players, game_rounds):
        s["totals"][name] += score
        s["bids_total"][name] += 1
        made = bid == hand
        _tally_bid(s, miss_streak, name, bid, hand, made, score)

    return s


def _tally_bid(s, miss_streak, name, bid, hand, made, score):
    """Update stat counters for a single bid result."""
    if made:
        s["bids_made"][name] += 1
        miss_streak[name] = 0
        if bid == 0:
            s["zero_bids_made"][name] += 1
        if name not in s["best_bid"] or bid > s["best_bid"][name]:
            s["best_bid"][name] = bid
    else:
        miss_streak[name] += 1
        if miss_streak[name] > s["longest_miss"][name]:
            s["longest_miss"][name] = miss_streak[name]
    if bid > hand:
        s["overbids"][name] += 1
    elif bid < hand:
        s["underbids"][name] += 1


def _best_player(data, key="value"):
    """Find player with highest value. Returns None if all zero."""
    if not data:
        return None
    name = max(data, key=lambda n: data[n])
    return {"name": name, key: data[name]} if data[name] > 0 else None


def _build_awards(stats):
    """Transform accumulated stats into award dicts."""
    totals = stats["totals"]
    if not totals:
        return None
    mvp_name = max(totals, key=lambda n: totals[n])
    return {
        "mvp": {"name": mvp_name, "score": totals[mvp_name]},
        "sharpshooter": _best_accuracy(stats),
        "brick_wall": _best_player(stats["zero_bids_made"], "count"),
        "bold_move": _best_player(stats["best_bid"], "bid"),
        "cursed": _best_player(stats["longest_miss"], "streak"),
        "sandbagger": _best_player(stats["underbids"], "count"),
        "gambler": _best_player(stats["overbids"], "count"),
    }


def _best_accuracy(stats):
    """Find player with best bid accuracy."""
    accuracies = {
        name: round(stats["bids_made"][name] / stats["bids_total"][name] * 100)
        for name in stats["totals"]
        if stats["bids_total"][name] > 0
    }
    if not accuracies:
        return None
    best = max(accuracies, key=lambda n: accuracies[n])
    return {"name": best, "accuracy": accuracies[best]}
