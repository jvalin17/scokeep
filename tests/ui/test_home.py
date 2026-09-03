"""Home screen tests — rendering, create form, join form."""

import pytest

from tests.ui.helpers import VIEWPORTS


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_home_renders(page, server, viewport):
    """Home screen renders at all viewports."""
    page.set_viewport_size(viewport)
    page.goto(server)
    page.wait_for_selector(".logo", timeout=3000)
    assert page.title() != ""


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_create_form_visible(page, server, viewport):
    """Create playground form is visible."""
    page.set_viewport_size(viewport)
    page.goto(server)
    form_inputs = page.locator("input")
    assert form_inputs.count() >= 2


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=lambda v: v["name"])
def test_join_tab_exists(page, server, viewport):
    """Join tab exists on home screen."""
    page.set_viewport_size(viewport)
    page.goto(server)
    join_tab = page.locator('.tab[data-tab="join"], button:has-text("Join")')
    assert join_tab.count() > 0


def test_no_horizontal_overflow(page, server):
    """No horizontal scroll on home screen."""
    page.goto(server)
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow


def test_howto_includes_per_game_titles_explanation(page, server):
    """How To must explain what per-game titles are."""
    from pathlib import Path

    js = Path("app/static/js/screens/home.js").read_text()
    assert "Per-Game Titles" in js or "per-game title" in js or "Post-Game Awards" in js, (
        "How To missing per-game titles explanation"
    )


def test_howto_includes_career_records_explanation(page, server):
    """How To must list career record categories."""
    from pathlib import Path

    js = Path("app/static/js/screens/home.js").read_text()
    assert "Comeback King" in js or "Iron Wall" in js, "How To missing career record examples"
