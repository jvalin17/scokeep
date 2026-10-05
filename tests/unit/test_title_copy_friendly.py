"""Award titles use Judgement-style characters; ℹ descriptions stay clear."""

from __future__ import annotations

import re

from app.services.game_titles import TITLE_REGISTRY, build_context
from app.services.title_registry import DECLARATIVE_TITLES
from app.services.title_selection import _FILLER_TITLES
from tests.guards.fixtures import PLAYERS_4, full_game_4p

_FORBIDDEN_TITLE_FRAGMENTS = (
    "cellar dweller",
    "cursed",
    "rock bottom",
    "humble pie",
    "blew the lead",
    "scatterbrain",
    "sandbagger",
    "fat-hand",
    "ice cold",
    "from the hole",
    "biggest losses",
    "no tricks",
    "heartbreaker",
    "brick wall",
    "ice in the veins",
    "from the cellar",
)

_TITLE_RE = re.compile(r"^The [A-Z][A-Za-z0-9' -]+$")


def _all_keyed_titles() -> list[tuple[str, str, str]]:
    """Return (source, title, desc) for every award display string."""
    rows: list[tuple[str, str, str]] = []
    for defn in DECLARATIVE_TITLES:
        rows.append((defn["key"], defn["title"], defn["desc"]))
    for base_key, _emoji, title, desc in _FILLER_TITLES:
        rows.append((base_key, title, desc))
    ctx = build_context(PLAYERS_4, full_game_4p())
    seen_keys: set[str] = set()
    for pattern_fn in TITLE_REGISTRY:
        for candidate in pattern_fn(ctx):
            key = candidate["key"]
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append((key, candidate["title"], candidate["desc"]))
    return rows


def test_award_titles_use_judgement_character_form():
    for _key, title, _desc in _all_keyed_titles():
        assert _TITLE_RE.match(title), f"expected Judgement character title, got {title!r}"


def test_award_titles_are_unique():
    # Static definitions must not collide (patterns evaluated once per key).
    static_titles = [defn["title"] for defn in DECLARATIVE_TITLES] + [
        title for _key, _emoji, title, _desc in _FILLER_TITLES
    ]
    assert len(static_titles) == len(set(static_titles)), sorted(
        title for title in set(static_titles) if static_titles.count(title) > 1
    )


def test_award_titles_avoid_harsh_wording():
    for _key, title, _desc in _all_keyed_titles():
        lowered = title.lower()
        for fragment in _FORBIDDEN_TITLE_FRAGMENTS:
            assert fragment not in lowered, f"harsh title wording: {title!r}"


def test_award_descriptions_are_proper_info_sentences():
    for _key, title, desc in _all_keyed_titles():
        assert desc.endswith("."), f"{title!r} desc should end with period: {desc!r}"
        assert len(desc) >= 28, f"{title!r} desc too short for ℹ tip: {desc!r}"
        assert re.search(r"[A-Za-z]", desc), f"{title!r} desc empty of words"


def test_filler_detail_is_friendly():
    from app.services.title_selection import _filler_for_player

    filler = _filler_for_player("Alice", set(), set())
    assert filler is not None
    assert filler["detail"] != "table presence"
    assert _TITLE_RE.match(filler["title"])
    assert filler["desc"].endswith(".")
    assert len(filler["desc"]) >= 28
