"""Backend GamePack registry — dispatch by settings.game_type (mirrors FE packs)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.schemas.sync import SyncRoundRequest
from app.services.packs.registry import (
    AWARDS_GATE_JUDGEMENT_ML,
    AWARDS_GATE_SCORESHEET_LIGHT,
    ROUND_META_NOT_APPLICABLE,
    get_pack,
    get_pack_for_settings,
    list_packs,
    resolve_game_type,
)


def test_get_pack_defaults_unknown_to_judgement():
    assert get_pack(None).id == "kachuful"
    assert get_pack("nope").id == "kachuful"
    assert get_pack("scoresheet").id == "scoresheet"


def test_list_packs_includes_both():
    ids = sorted(pack.id for pack in list_packs())
    assert ids == ["kachuful", "scoresheet"]


def test_resolve_game_type():
    assert resolve_game_type({"game_type": "scoresheet"}) == "scoresheet"
    assert resolve_game_type({}) == "kachuful"
    assert resolve_game_type(None) == "kachuful"


def test_scoresheet_pack_create_defaults_and_start_phase():
    pack = get_pack("scoresheet")
    merged = pack.merge_settings({"label": "Declare", "winner": "lowest"})
    assert merged["game_type"] == "scoresheet"
    assert merged["winner"] == "lowest"
    assert merged["label"] == "Declare"
    assert pack.start_phase == "entry"
    assert pack.initial_total_rounds(merged) >= 100
    assert pack.supports_extend is False
    assert pack.awards_gate == AWARDS_GATE_SCORESHEET_LIGHT


def test_judgement_pack_create_defaults():
    pack = get_pack("kachuful")
    merged = pack.merge_settings({"mode": "rookie", "num_sets": 2})
    assert merged["game_type"] == "kachuful"
    assert merged["mode"] == "rookie"
    assert pack.start_phase == "bidding"
    assert pack.initial_total_rounds(merged) == 16
    assert pack.supports_extend is True
    assert pack.awards_gate == AWARDS_GATE_JUDGEMENT_ML


def test_scoresheet_sync_rejects_negatives_when_disabled():
    pack = get_pack("scoresheet")
    game_settings = pack.merge_settings({"allow_negatives": False})

    class FakeGame:
        players = ["Maria", "Diego"]
        settings = game_settings

    body = SyncRoundRequest(
        round_num=1,
        cards_dealt=0,
        trump_suit=ROUND_META_NOT_APPLICABLE,
        scores={"0": -1, "1": 2},
        status="complete",
    )
    with pytest.raises(HTTPException) as exc_info:
        pack.validate_sync_round(FakeGame(), body)
    assert exc_info.value.status_code == 409


def test_scoresheet_sync_accepts_valid_scores():
    pack = get_pack("scoresheet")
    game_settings = pack.merge_settings({"allow_negatives": True})

    class FakeGame:
        players = ["Maria", "Diego"]
        settings = game_settings

    body = SyncRoundRequest(
        round_num=1,
        cards_dealt=0,
        trump_suit=ROUND_META_NOT_APPLICABLE,
        scores={"0": -12, "1": 40},
        status="complete",
    )
    pack.validate_sync_round(FakeGame(), body)  # no raise


def test_scoresheet_sync_rejects_oversized_score():
    pack = get_pack("scoresheet")
    game_settings = pack.merge_settings({})

    class FakeGame:
        players = ["Maria", "Diego"]
        settings = game_settings

    body = SyncRoundRequest(
        round_num=1,
        cards_dealt=0,
        trump_suit=ROUND_META_NOT_APPLICABLE,
        scores={"0": 10000, "1": 1},
        status="complete",
    )
    with pytest.raises(HTTPException) as exc_info:
        pack.validate_sync_round(FakeGame(), body)
    assert exc_info.value.status_code == 409


def test_get_pack_for_settings_resolves_type():
    assert get_pack_for_settings({"game_type": "scoresheet"}).id == "scoresheet"
    assert get_pack_for_settings({}).id == "kachuful"


def test_pack__merge_settings_defaults():
    assert get_pack("kachuful").merge_settings({})["game_type"] == "kachuful"
    assert get_pack("scoresheet").merge_settings({})["game_type"] == "scoresheet"


def test_pack__initial_total_rounds():
    j = get_pack("kachuful").merge_settings({"num_sets": 1, "rounds_per_set": 8})
    assert get_pack("kachuful").initial_total_rounds(j) == 8
    s = get_pack("scoresheet").merge_settings({})
    assert get_pack("scoresheet").initial_total_rounds(s) >= 100


def test_pack__next_phase_on_advance():
    game = type("G", (), {"settings": {}})()
    assert get_pack("kachuful").next_phase_on_advance(game) == "bidding"
    assert get_pack("scoresheet").next_phase_on_advance(game) == "entry"


def test_pack__grow_total_rounds_if_needed():
    class GrowGame:
        current_round = 499
        total_rounds = 500

    g = GrowGame()
    get_pack("kachuful").grow_total_rounds_if_needed(g)
    assert g.total_rounds == 500
    get_pack("scoresheet").grow_total_rounds_if_needed(g)
    assert g.total_rounds > 500


def test_pack__validate_sync_round_accepts_scoresheet():
    pack = get_pack("scoresheet")

    class FakeGame:
        players = ["A", "B"]
        settings = pack.merge_settings({})

    body = SyncRoundRequest(
        round_num=1,
        cards_dealt=0,
        trump_suit=ROUND_META_NOT_APPLICABLE,
        scores={"0": 1, "1": 2},
        status="complete",
    )
    pack.validate_sync_round(FakeGame(), body)
