"""Last Game title selection — exclusive assign, coverage, fair fill."""

from __future__ import annotations

import math


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


def phase1_coverage(
    players: list[str], exclusive: list[dict], all_candidates: list[dict], used_keys: set
) -> list[dict]:
    """Give every player at least one title (coverage pass)."""
    result = []
    for player in players:
        player_excl = sorted(
            [c for c in exclusive if c["player"] == player and c["key"] not in used_keys],
            key=lambda c: -c["score"],
        )
        if player_excl:
            best = player_excl[0]
            result.append(best)
            used_keys.add(best["key"])
            continue

        fallback = sorted(
            [c for c in all_candidates if c["player"] == player],
            key=lambda c: -c["score"],
        )
        if not fallback:
            continue
        best = fallback[0]
        if best["key"] in used_keys:
            slug = "".join(ch for ch in player.lower() if ch.isalnum())[:12] or "player"
            best = {**best, "key": f"arc_{slug}"}
        result.append(best)
        used_keys.add(best["key"])
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

        eligible = [
            c
            for c in remaining
            if c["key"] not in used_keys and counts.get(c["player"], 0) < max_per_player
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
