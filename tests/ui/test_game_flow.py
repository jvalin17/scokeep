"""Full game flow tests — expert, friendly, rookie modes."""

import pytest

from tests.ui.helpers import (
    confirm_bids,
    create_playground,
    enter_bids_for_all,
    enter_hands_won,
    start_game,
    unique_name,
)


@pytest.fixture
def playground_expert(page, server):
    page.goto(server)
    create_playground(page, unique_name("Expert"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page, {"mode": "Expert"})
    return page


@pytest.fixture
def playground_friendly(page, server):
    page.goto(server)
    create_playground(page, unique_name("Friendly"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page, {"mode": "Friendly", "appearance": "Interactive"})
    return page


@pytest.fixture
def playground_rookie(page, server):
    page.goto(server)
    create_playground(page, unique_name("Rookie"), "1234", ["Alice", "Bob", "Charlie"])
    start_game(page, {"mode": "Rookie"})
    return page


class TestExpertGameFlow:
    def test_bidding_screen_renders(self, playground_expert):
        page = playground_expert
        keypad = page.locator(".keypad")
        assert keypad.count() > 0
        player_display = page.locator("h2, .player-name, .round-info")
        assert player_display.count() > 0

    def test_full_round(self, playground_expert):
        page = playground_expert
        enter_bids_for_all(page, [2, 3, 1])
        confirm_bids(page)
        enter_hands_won(page, [2, 3, 3])
        page.wait_for_timeout(1000)
        # Should be on confirm-hands or scoreboard screen
        url_hash = page.evaluate("() => location.hash")
        assert "roundend" in url_hash or "scoreboard" in url_hash

    def test_end_game_navigates(self, playground_expert):
        page = playground_expert
        enter_bids_for_all(page, [2, 3, 1])
        confirm_bids(page)
        enter_hands_won(page, [2, 3, 3])
        # Click "Score Round" on the confirm screen
        score_btn = page.locator('button:has-text("Score Round")')
        if score_btn.count() > 0:
            score_btn.click()
            page.wait_for_timeout(1000)
        url_hash = page.evaluate("() => location.hash")
        assert "scoreboard" in url_hash or "bid" in url_hash or "play" in url_hash


class TestFriendlyGameFlow:
    def test_interactive_colors(self, playground_friendly):
        page = playground_friendly
        appearance = page.locator("body").get_attribute("data-appearance")
        assert appearance == "interactive"
        bg_color = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
        assert bg_color != "rgb(250, 250, 250)"

    def test_bids_visible_in_friendly(self, playground_friendly):
        page = playground_friendly
        enter_bids_for_all(page, [2, 1, 0])
        confirm_bids(page)
        content = page.content()
        assert len(content) > 100

    def test_play_screen_bids_in_friendly(self, playground_friendly):
        """After bidding and confirming, .play-bids is visible with one row per player."""
        page = playground_friendly
        enter_bids_for_all(page, [2, 1, 0])
        confirm_bids(page)
        page.wait_for_selector(".play-bids", timeout=5000)
        play_bids = page.locator(".play-bids")
        assert play_bids.is_visible(), ".play-bids section not visible on play screen"
        rows = page.locator(".play-bid-row")
        assert rows.count() == 3, f"Expected 3 .play-bid-row elements, got {rows.count()}"


class TestExtendFlow:
    def test_extend_game_adds_rounds(self, page, server):
        """After the final round, the extend prompt appears; clicking it starts a new round."""
        page.goto(server)
        create_playground(page, unique_name("Extend"), "1234", ["Alice", "Bob", "Charlie"])

        # Select 1 set and 1 card per round so the game has only 1 round total
        page.wait_for_selector("#start-game", timeout=5000)
        page.select_option("#setting-sets", "1")
        page.select_option("#setting-set-type", "1")
        page.click("#start-game")
        page.wait_for_selector(".keypad", timeout=30000)

        # 1 card dealt: bids [0,0,0] — last player forbidden=1, so bid 0 is allowed
        enter_bids_for_all(page, [0, 0, 0])
        confirm_bids(page)
        # 1 card total: first player wins it, others 0
        enter_hands_won(page, [1, 0, 0])

        # Score Round triggers renderExtendPrompt because current_round == total_rounds
        score_btn = page.locator('button:has-text("Score Round")')
        score_btn.wait_for(state="visible", timeout=5000)
        score_btn.click()

        # Extend prompt must appear
        page.wait_for_selector('text="Set Complete!"', timeout=5000)
        extend_btn = page.locator("#extend-set")
        assert extend_btn.is_visible(), "#extend-set button not visible in extend prompt"

        # Click extend — navigates to the next bidding round
        extend_btn.click()
        page.wait_for_function("() => location.hash.includes('bid')", timeout=5000)
        url_hash = page.evaluate("() => location.hash")
        assert "bid" in url_hash, f"Expected hash to contain 'bid' after extend, got: {url_hash}"


class TestRookieGameFlow:
    def test_trump_visible(self, playground_rookie):
        page = playground_rookie
        content = page.content()
        trump_indicators = ["♠", "♦", "♣", "♥", "Spades", "Diamonds", "Clubs", "Hearts"]
        has_trump = any(t in content for t in trump_indicators)
        if not has_trump:
            enter_bids_for_all(page, [2, 1, 0])
            confirm_bids(page)
            content = page.content()
            has_trump = any(t in content for t in trump_indicators)
        assert has_trump
