"""Insights should react strongly to the latest finished game."""

from app.services.insights import RECENT_GAME_WEIGHT, _blend_recent_career_vector
from app.services.personality_engine import EMA_ALPHA, PERSONALITY_META


def test_ema_alpha_is_highly_reactive():
    assert EMA_ALPHA >= 0.75


def test_recent_game_outweighs_career_history():
    assert RECENT_GAME_WEIGHT >= 0.55


def test_blend_pulls_toward_latest_game():
    career = [0.0] * 10
    latest = [1.0] * 10
    blended = _blend_recent_career_vector(career, latest)
    assert blended[0] == RECENT_GAME_WEIGHT
    assert blended[0] > 0.5


def test_insight_characters_use_bollywood_names():
    expected = {
        "sniper": "Dhurandhar",
        "gambler": "Don",
        "phoenix": "Sultan",
        "rock": "Bahubali",
        "sprinter": "Veeru",
        "ghost": "Mr. India",
        "reader": "Rancho",
        "surgeon": "Bajirao",
        "tilter": "Gabbar",
    }
    for key, name in expected.items():
        assert PERSONALITY_META[key]["name"] == name
        assert PERSONALITY_META[key]["tagline"]
