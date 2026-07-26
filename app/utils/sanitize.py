"""Input sanitization utilities.

Fixes BUG-002: XSS via player names injected into innerHTML.
Sanitize at the input boundary — before storing in DB.
"""

import html


def sanitize_player_name(name: str) -> str:
    """Escape HTML entities in player names to prevent XSS."""
    return html.escape(name, quote=True)


def sanitize_player_names(names: list[str]) -> list[str]:
    """Escape HTML entities in a list of player names."""
    return [sanitize_player_name(n) for n in names]
