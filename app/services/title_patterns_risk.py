"""Risk-based Last Game title patterns — Ice in the Veins, Tightrope, From the Hole.

Registers into COMPLEX_PATTERNS. Safe exacts (low ambition) do not qualify.
"""

from __future__ import annotations

from app.services.risk_factor import (
    CLUTCH_MIN_CARDS,
    RISKY_MAKE_THRESHOLD,
    SAFE_AMBITION,
    compute_game_risk,
)
from app.services.title_patterns import COMPLEX_PATTERNS
from app.services.title_registry import GameContext, _candidate


def _risk_pattern(fn):
    COMPLEX_PATTERNS.append(fn)
    return fn


def _has_qualifying_clutch_round(player_agg: dict) -> bool:
    """At least one paid_risk >= threshold on a fat-hand round with real ambition."""
    for round_info in player_agg["rounds"]:
        if (
            round_info["cards"] >= CLUTCH_MIN_CARDS
            and round_info["paid_risk"] >= RISKY_MAKE_THRESHOLD
            and round_info["ambition"] >= SAFE_AMBITION
        ):
            return True
    return False


@_risk_pattern
def _clutch_risk(ctx: GameContext) -> list[dict]:
    """Ice in the Veins — highest total paid risk with a qualifying pressure make."""
    aggregates = compute_game_risk(ctx)
    out = []
    for player in ctx.players:
        agg = aggregates[player]
        if not _has_qualifying_clutch_round(agg):
            continue
        if agg["total_paid_risk"] <= 0:
            continue
        count = sum(
            1
            for round_info in agg["rounds"]
            if (
                round_info["cards"] >= CLUTCH_MIN_CARDS
                and round_info["paid_risk"] >= RISKY_MAKE_THRESHOLD
                and round_info["ambition"] >= SAFE_AMBITION
            )
        )
        detail = f"risk {agg['total_paid_risk']:.1f} across {count} pressure makes"
        out.append(
            _candidate(
                "clutch",
                "❄️",
                "Ice in the Veins",
                "Highest paid risk when the board was thick",
                player,
                detail,
                agg["total_paid_risk"] * 40,
            )
        )
    return out


@_risk_pattern
def _high_wire(ctx: GameContext) -> list[dict]:
    """Tightrope — single highest paid_risk round (ambition must not be safe)."""
    aggregates = compute_game_risk(ctx)
    out = []
    for player in ctx.players:
        agg = aggregates[player]
        best = 0.0
        best_detail = ""
        for round_info in agg["rounds"]:
            if round_info["ambition"] < SAFE_AMBITION:
                continue
            if round_info["paid_risk"] > best:
                best = round_info["paid_risk"]
                best_detail = (
                    f"risk {best:.2f} on bid {round_info['bid']}/{round_info['cards']}"
                )
        if best < RISKY_MAKE_THRESHOLD:
            continue
        out.append(
            _candidate(
                "high_wire",
                "🌉",
                "Tightrope",
                "One swing: biggest single paid-risk make",
                player,
                best_detail,
                best * 50,
            )
        )
    return out


@_risk_pattern
def _pressure_cooker(ctx: GameContext) -> list[dict]:
    """From the Hole — most risky makes while already trailing."""
    aggregates = compute_game_risk(ctx)
    out = []
    for player in ctx.players:
        agg = aggregates[player]
        count = 0
        for round_info in agg["rounds"]:
            if (
                round_info["paid_risk"] >= RISKY_MAKE_THRESHOLD
                and round_info["pressure"] >= 0.5
                and round_info["ambition"] >= SAFE_AMBITION
            ):
                count += 1
        if count < 1:
            continue
        out.append(
            _candidate(
                "pressure_cooker",
                "🕳️",
                "From the Hole",
                "Most risky makes while already trailing",
                player,
                f"{count} trailing pressure makes",
                count * 25,
            )
        )
    return out
