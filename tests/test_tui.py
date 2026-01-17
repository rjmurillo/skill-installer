"""Tests for TUI module."""

from __future__ import annotations

import pytest

from skill_installer.tui import _sanitize_css_id


class TestSanitizeCssId:
    """Tests for _sanitize_css_id function."""

    def test_simple_string(self) -> None:
        """Test simple alphanumeric string passes through."""
        assert _sanitize_css_id("simple") == "simple"

    def test_with_spaces(self) -> None:
        """Test spaces are converted to hyphens."""
        assert _sanitize_css_id("Swift MCP Expert") == "Swift-MCP-Expert"

    def test_with_slashes(self) -> None:
        """Test slashes are converted to double hyphens."""
        assert _sanitize_css_id("github/awesome-copilot/agent") == "github--awesome-copilot--agent"

    def test_with_mixed_separators(self) -> None:
        """Test mixed slashes and spaces."""
        result = _sanitize_css_id("source/type/Item Name")
        assert result == "source--type--Item-Name"

    def test_removes_special_characters(self) -> None:
        """Test special characters are removed."""
        assert _sanitize_css_id("item@#$%name") == "itemname"

    def test_preserves_underscores(self) -> None:
        """Test underscores are preserved."""
        assert _sanitize_css_id("item_name") == "item_name"

    def test_preserves_hyphens(self) -> None:
        """Test hyphens are preserved."""
        assert _sanitize_css_id("item-name") == "item-name"

    def test_starts_with_number(self) -> None:
        """Test IDs starting with numbers get prefixed."""
        assert _sanitize_css_id("123item") == "id-123item"

    def test_empty_after_sanitize(self) -> None:
        """Test empty string after sanitization returns default."""
        assert _sanitize_css_id("@#$%") == "item"

    def test_empty_string(self) -> None:
        """Test empty input returns default."""
        assert _sanitize_css_id("") == "item"

    def test_realistic_item_id(self) -> None:
        """Test realistic item unique_id format."""
        # This is the format used by DisplayItem.unique_id
        result = _sanitize_css_id("github/awesome-copilot/agent/Swift MCP Expert")
        assert result == "github--awesome-copilot--agent--Swift-MCP-Expert"
        # Verify no invalid characters remain
        assert " " not in result
        assert "/" not in result
