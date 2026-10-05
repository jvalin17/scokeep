"""Last Game awards use Judgement character names."""

from app.services.title_registry import DECLARATIVE_TITLES


def _title(key: str) -> str:
    return next(d["title"] for d in DECLARATIVE_TITLES if d["key"] == key)


def test_newer_award_names_are_judgement_characters():
    assert _title("glass_cannon") == "The Tilter"
    assert _title("overachiever") == "The Surplus"
    assert _title("sniper_bid") == "The Ace"
    assert _title("wild_card") == "The Wildcard"
    assert _title("steamroller") == "The Engine"
    assert _title("marathon") == "The Clean Sheet"
    assert _title("anchor") == "The Quiet"
    assert _title("penny_pincher") == "The Thrifty"
    assert _title("wrecking_ball") == "The Scrap"
    assert _title("iron_nerve") == "The Rock"
    assert _title("perfectionist") == "The Surgeon"


def test_core_and_worst_case_use_judgement_characters():
    assert _title("champion") == "The Champion"
    assert _title("sharpshooter") == "The Sniper"
    assert _title("gambler") == "The Gambler"
    assert _title("cellar_dweller") == "The Underdog"
    assert _title("cursed") == "The Storm"
    assert _title("rock_bottom") == "The Dive"
    assert _title("humble_pie") == "The Nil"
