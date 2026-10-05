"""GamePack protocol — Rule Pack contract for backend game types.

Mirrors FE packs/registry.js: packs own settings defaults, start phase,
advance behavior, sync validation, and awards gate.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.models.game import Game
from app.schemas.sync import SyncRoundRequest

AwardsGate = Literal["judgement_ml", "scoresheet_light", "none"]

# Stored in Round.trump_suit when the pack does not use trump (Scoresheet).
ROUND_META_NOT_APPLICABLE = "n/a"

# Open-ended Scoresheet round capacity step (grow instead of auto-ending).
OPEN_ENDED_ROUND_CAP_STEP = 500

# Scoresheet dialer digit cap (±9999).
SCORESHEET_MAX_ABS_SCORE = 9999

AWARDS_GATE_JUDGEMENT_ML: AwardsGate = "judgement_ml"
AWARDS_GATE_SCORESHEET_LIGHT: AwardsGate = "scoresheet_light"
AWARDS_GATE_NONE: AwardsGate = "none"


@dataclass(frozen=True)
class GamePack:
    """Immutable Rule Pack for one game_type."""

    id: str
    display_name: str
    start_phase: str
    settings_defaults: dict[str, Any]
    awards_gate: AwardsGate
    supports_extend: bool
    allowed_phases: frozenset[str]
    merge_settings: Callable[[dict], dict]
    initial_total_rounds: Callable[[dict], int]
    next_phase_on_advance: Callable[[Game], str]
    grow_total_rounds_if_needed: Callable[[Game], None]
    validate_sync_round: Callable[[Game, SyncRoundRequest], None]
    should_compute_judgement_insights: bool
