"""Unit tests for stats game_type filtering helpers."""

from types import SimpleNamespace

from app.services.stats_filter import filter_games_by_type, game_type_of


def _game(game_type=None, settings=None):
    if settings is not None:
        return SimpleNamespace(settings=settings)
    if game_type is None:
        return SimpleNamespace(settings={})
    return SimpleNamespace(settings={"game_type": game_type})


def test_game_type_of_defaults_missing_to_kachuful():
    assert game_type_of(_game()) == "kachuful"
    assert game_type_of(_game(settings=None)) == "kachuful"
    assert game_type_of(_game("scoresheet")) == "scoresheet"


def test_filter_games_by_type_all_and_specific():
    games = [
        _game("kachuful"),
        _game("scoresheet"),
        _game(),  # missing → kachuful
    ]
    assert len(filter_games_by_type(games, "all")) == 3
    assert len(filter_games_by_type(games, None)) == 3
    judgement = filter_games_by_type(games, "kachuful")
    assert len(judgement) == 2
    assert all(game_type_of(g) == "kachuful" for g in judgement)
    sheet = filter_games_by_type(games, "scoresheet")
    assert len(sheet) == 1
    assert game_type_of(sheet[0]) == "scoresheet"
