"""Unique displayed titles — no two players share the same award name."""

from app.services.title_selection import select_titles


def _cand(key, player, score, title):
    return {
        "key": key,
        "emoji": "T",
        "title": title,
        "desc": "Test",
        "player": player,
        "detail": "test",
        "score": float(score),
    }


def test_coverage_does_not_clone_champion_title_text():
    candidates = [
        _cand("t1", "Alice", 100, "Champion"),
        _cand("t1", "Bob", 50, "Champion"),
        _cand("t2", "Alice", 90, "Sharpshooter"),
    ]
    result = select_titles(candidates, ["Alice", "Bob"], target=4)
    titles = [t["title"] for t in result]
    assert len(titles) == len(set(titles)), titles
    assert {t["player"] for t in result} == {"Alice", "Bob"}
    assert not any(str(t["key"]).startswith("arc_") for t in result)
