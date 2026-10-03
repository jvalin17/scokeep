"""Last Game title selection — exclusive assign, coverage, fair fill."""

from __future__ import annotations

import math

# Unique consolation titles when a player has no unused exclusive award left.
# Never reuse another player's displayed title string.
_FILLER_TITLES = (
    ("solid_night", "👍", "The Ally", "Played a solid game from start to finish."),
    ("good_fight", "🥊", "The Contender", "Stayed competitive and kept competing."),
    ("team_player", "🤝", "The Host", "Helped keep the table fun and lively."),
    ("close_call", "😅", "The Spark", "Came close to landing a standout award."),
    ("comeback_kid", "🚀", "The Bounce", "Fought back and stayed in the mix."),
    ("lucky_charm", "🍀", "The Charm", "Caught a few lucky breaks along the way."),
    ("quiet_force", "🤫", "The Shadow", "Did the job quietly and reliably."),
    ("late_bloom", "🌸", "The Bloom", "Finished stronger than they started."),
    ("card_sharp", "🂡", "The Dealer", "Knew their way around the deck."),
    ("night_owl", "🦉", "The Owl", "Stayed sharp through the late rounds."),
    ("crowd_favorite", "👏", "The Favorite", "Made the game more fun for everyone."),
    ("always_there", "📍", "The Regular", "Showed up for every round of the game."),
)




def assign_exclusive(candidates: list[dict]) -> list[dict]:
    """Assign each title to the best player. Drop ties (same score for same key)."""
    by_key: dict[str, list[dict]] = {}
    for cand in candidates:
        by_key.setdefault(cand["key"], []).append(cand)

    exclusive: list[dict] = []
    for _key, cands in by_key.items():
        cands.sort(key=lambda c: -c["score"])
        best_score = cands[0]["score"]
        winners = [c for c in cands if c["score"] == best_score]
        if len(winners) == 1:
            exclusive.append(winners[0])
    return exclusive


def _used_titles(result: list[dict]) -> set[str]:
    return {item.get("title") or item["key"] for item in result}


def _filler_for_player(player: str, used_keys: set, used_titles: set[str]) -> dict | None:
    """Pick a unique fun filler title never shown elsewhere in this game."""
    slug = "".join(ch for ch in player.lower() if ch.isalnum())[:12] or "player"
    for index, (base_key, emoji, title, desc) in enumerate(_FILLER_TITLES):
        if title in used_titles:
            continue
        key = f"fill_{base_key}_{slug}"
        if key in used_keys:
            key = f"fill_{base_key}_{slug}_{index}"
        if key in used_keys:
            continue
        return {
            "key": key,
            "emoji": emoji,
            "title": title,
            "desc": desc,
            "player": player,
            "detail": "Part of the full game",
            "score": 1.0,
        }
    title = f"The {player} Arc"
    if title in used_titles:
        title = f"The {player} Forever"
    return {
        "key": f"fill_arc_{slug}",
        "emoji": "⭐",
        "title": title,
        "desc": "A friendly nod for joining the full game.",
        "player": player,
        "detail": "Part of the full game",
        "score": 0.5,
    }


def phase1_coverage(
    players: list[str], exclusive: list[dict], all_candidates: list[dict], used_keys: set
) -> list[dict]:
    """Give every player at least one title (coverage pass). Titles stay unique."""
    result = []
    for player in players:
        used_titles = _used_titles(result)
        player_excl = sorted(
            [
                c
                for c in exclusive
                if c["player"] == player
                and c["key"] not in used_keys
                and (c.get("title") or c["key"]) not in used_titles
            ],
            key=lambda c: -c["score"],
        )
        if player_excl:
            best = player_excl[0]
            result.append(best)
            used_keys.add(best["key"])
            continue

        fallback = sorted(
            [
                c
                for c in all_candidates
                if c["player"] == player
                and c["key"] not in used_keys
                and (c.get("title") or c["key"]) not in used_titles
            ],
            key=lambda c: -c["score"],
        )
        if fallback:
            best = fallback[0]
            result.append(best)
            used_keys.add(best["key"])
            continue

        filler = _filler_for_player(player, used_keys, used_titles)
        if filler:
            result.append(filler)
            used_keys.add(filler["key"])
    return result


def phase2_fair_fill(
    exclusive: list[dict],
    used_keys: set,
    result: list[dict],
    target: int,
    max_per_player: int,
) -> None:
    """Fill remaining slots preferring players with fewest titles so far."""
    remaining = [c for c in exclusive if c["key"] not in used_keys]

    while len(result) < target and remaining:
        counts: dict[str, int] = {}
        for item in result:
            counts[item["player"]] = counts.get(item["player"], 0) + 1
        used_titles = _used_titles(result)

        eligible = [
            c
            for c in remaining
            if c["key"] not in used_keys
            and (c.get("title") or c["key"]) not in used_titles
            and counts.get(c["player"], 0) < max_per_player
        ]
        if not eligible:
            break

        fewest = min(counts.get(c["player"], 0) for c in eligible)
        pool = [c for c in eligible if counts.get(c["player"], 0) == fewest]
        chosen = max(pool, key=lambda c: c["score"])
        remaining.remove(chosen)
        result.append(chosen)
        used_keys.add(chosen["key"])


def select_titles(
    candidates: list[dict], players: list[str], target: int | None = None
) -> list[dict]:
    if target is None:
        target = max(4, min(2 * len(players), 14))

    max_per_player = max(1, math.ceil(target / max(len(players), 1)))
    exclusive = assign_exclusive(candidates)
    used_keys: set = set()
    result = phase1_coverage(players, exclusive, candidates, used_keys)
    phase2_fair_fill(exclusive, used_keys, result, target, max_per_player)
    return result
