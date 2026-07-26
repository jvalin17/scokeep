"""Unit tests for HTML sanitization utility.

Tests that player names with HTML/script tags are properly escaped
to prevent XSS attacks.
"""

from app.utils.sanitize import sanitize_player_name, sanitize_player_names


class TestSanitizePlayerName:

    def test_plain_name_unchanged(self):
        assert sanitize_player_name("Alice") == "Alice"

    def test_name_with_spaces_unchanged(self):
        assert sanitize_player_name("Bob Smith") == "Bob Smith"

    def test_script_tag_escaped(self):
        result = sanitize_player_name('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_img_onerror_escaped(self):
        result = sanitize_player_name('<img onerror=alert(1) src=x>')
        assert "<img" not in result
        assert "&lt;img" in result

    def test_angle_brackets_escaped(self):
        result = sanitize_player_name("Alice <Bob> Charlie")
        assert "<" not in result
        assert ">" not in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_quotes_escaped(self):
        result = sanitize_player_name('Alice "Bob" Charlie')
        assert "&quot;" in result

    def test_ampersand_escaped(self):
        result = sanitize_player_name("Alice & Bob")
        assert "&amp;" in result

    def test_unicode_name_preserved(self):
        assert sanitize_player_name("अमित") == "अमित"

    def test_emoji_name_preserved(self):
        assert sanitize_player_name("Alice 🎴") == "Alice 🎴"

    def test_empty_string(self):
        assert sanitize_player_name("") == ""


class TestSanitizePlayerNames:

    def test_list_of_clean_names(self):
        result = sanitize_player_names(["Alice", "Bob", "Charlie"])
        assert result == ["Alice", "Bob", "Charlie"]

    def test_list_with_xss_name(self):
        result = sanitize_player_names(["<script>x</script>", "Bob"])
        assert "<script>" not in result[0]
        assert result[1] == "Bob"

    def test_empty_list(self):
        assert sanitize_player_names([]) == []

    def test_single_name(self):
        result = sanitize_player_names(["Alice"])
        assert result == ["Alice"]
