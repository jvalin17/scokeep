"""Unit tests for Scoresheet GameSettings schema + open-ended create helpers."""

import pytest
from pydantic import ValidationError

from app.schemas.game import GameSettings
from app.services.game import (
    SCORESHEET_OPEN_ENDED_ROUNDS,
    GameService,
    is_scoresheet_settings,
)


def test_game_settings_accepts_scoresheet():
    settings = GameSettings(
        game_type="scoresheet",
        winner="lowest",
        show_totals=False,
        allow_negatives=True,
        label="Mini golf",
    )
    dumped = settings.model_dump()
    assert dumped["game_type"] == "scoresheet"
    assert dumped["winner"] == "lowest"
    assert dumped["show_totals"] is False
    assert dumped["allow_negatives"] is True
    assert dumped["label"] == "Mini golf"


def test_game_settings_rejects_unknown_type():
    with pytest.raises(ValidationError):
        GameSettings(game_type="call_break")


def test_is_scoresheet_settings():
    assert is_scoresheet_settings({"game_type": "scoresheet"}) is True
    assert is_scoresheet_settings({"game_type": "kachuful"}) is False
    assert is_scoresheet_settings({}) is False


def test_open_ended_cap_constant():
    assert SCORESHEET_OPEN_ENDED_ROUNDS >= 100


def test_game_type_is_locked_after_scored_round():
    """Once a round has been scored, game_type must not change."""
    assert GameService.game_type_is_locked(completed_rounds=0) is False
    assert GameService.game_type_is_locked(completed_rounds=1) is True


def test_game_settings_label_max_length_80():
    ok = GameSettings(game_type="scoresheet", label="A" * 80)
    assert len(ok.label) == 80
    with pytest.raises(ValidationError):
        GameSettings(game_type="scoresheet", label="A" * 81)
