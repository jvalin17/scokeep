"""GamePack registry — resolve Rule Pack by settings.game_type.

Public API mirrors FE packs/registry.js getPack / listPacks.
"""

from __future__ import annotations

from app.services.packs import (
    AWARDS_GATE_JUDGEMENT_ML,
    AWARDS_GATE_NONE,
    AWARDS_GATE_SCORESHEET_LIGHT,
    OPEN_ENDED_ROUND_CAP_STEP,
    ROUND_META_NOT_APPLICABLE,
    SCORESHEET_MAX_ABS_SCORE,
    GamePack,
)
from app.services.packs.judgement import judgement_pack
from app.services.packs.scoresheet import scoresheet_pack

PACKS: dict[str, GamePack] = {
    judgement_pack.id: judgement_pack,
    scoresheet_pack.id: scoresheet_pack,
}

DEFAULT_GAME_TYPE = judgement_pack.id


def resolve_game_type(settings: dict | None) -> str:
    """Return game_type from settings, defaulting to Judgement."""
    if not settings:
        return DEFAULT_GAME_TYPE
    return settings.get("game_type") or DEFAULT_GAME_TYPE


def get_pack(game_type: str | None) -> GamePack:
    """Resolve pack; unknown types fall back to Judgement (safe default)."""
    key = game_type or DEFAULT_GAME_TYPE
    return PACKS.get(key, judgement_pack)


def get_pack_for_settings(settings: dict | None) -> GamePack:
    return get_pack(resolve_game_type(settings))


def list_packs() -> list[GamePack]:
    return list(PACKS.values())


def is_scoresheet_settings(settings: dict | None) -> bool:
    """Compatibility helper — prefer get_pack_for_settings in new code."""
    return resolve_game_type(settings) == scoresheet_pack.id


__all__ = [
    "AWARDS_GATE_JUDGEMENT_ML",
    "AWARDS_GATE_NONE",
    "AWARDS_GATE_SCORESHEET_LIGHT",
    "DEFAULT_GAME_TYPE",
    "OPEN_ENDED_ROUND_CAP_STEP",
    "PACKS",
    "ROUND_META_NOT_APPLICABLE",
    "SCORESHEET_MAX_ABS_SCORE",
    "GamePack",
    "get_pack",
    "get_pack_for_settings",
    "is_scoresheet_settings",
    "list_packs",
    "resolve_game_type",
]
