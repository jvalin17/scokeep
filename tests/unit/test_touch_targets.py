"""Unit test: touch target selectors must specify min-width/min-height >= 44px."""

import re
from pathlib import Path

CSS_PATH = Path("app/static/css/style.css")
TOUCH_SELECTORS = [".btn-refresh", ".btn-home", ".island-toggle", ".btn-end-game"]


def _extract_rule(css: str, selector: str) -> str:
    """Extract the CSS rule block for a selector."""
    pattern = re.compile(re.escape(selector) + r"\s*\{([^}]+)\}", re.DOTALL)
    match = pattern.search(css)
    return match.group(1) if match else ""


class TestTouchTargets:
    def test_touch_targets_have_min_44px(self):
        """All interactive elements must have min-width and min-height >= 44px."""
        css = CSS_PATH.read_text()
        for selector in TOUCH_SELECTORS:
            rule = _extract_rule(css, selector)
            assert "min-width:" in rule or "width:" in rule, (
                f"{selector} missing min-width (touch target < 44px)"
            )
            assert "min-height:" in rule or "height:" in rule, (
                f"{selector} missing min-height (touch target < 44px)"
            )
