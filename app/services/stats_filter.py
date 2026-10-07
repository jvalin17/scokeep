"""Stats filtering by settings.game_type (Judgement vs Scoresheet)."""


def game_type_of(game) -> str:
    """Return settings.game_type, defaulting missing/legacy rows to kachuful."""
    settings = getattr(game, "settings", None) or {}
    return settings.get("game_type") or "kachuful"


def filter_games_by_type(games: list, game_type: str | None) -> list:
    """Keep finished games matching game_type; all/None returns the full list."""
    if not game_type or game_type == "all":
        return list(games)
    return [game for game in games if game_type_of(game) == game_type]
