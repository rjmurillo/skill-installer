"""Tests for the validation module."""

from skill_installer.validation import FrontmatterResult, parse_frontmatter


class TestFrontmatterResult:
    """Tests for FrontmatterResult class."""

    def test_success_when_no_errors(self) -> None:
        """Result is successful when errors list is empty."""
        result = FrontmatterResult(data="name: test")
        assert result.success is True
        assert result.data == "name: test"
        assert result.errors == []

    def test_failure_when_errors_present(self) -> None:
        """Result is failure when errors list has items."""
        result = FrontmatterResult(errors=["missing frontmatter"])
        assert result.success is False
        assert result.data == ""
        assert result.errors == ["missing frontmatter"]

    def test_default_values(self) -> None:
        """Default values are empty string and empty list."""
        result = FrontmatterResult()
        assert result.data == ""
        assert result.errors == []
        assert result.success is True


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_valid_frontmatter(self) -> None:
        """Parses valid frontmatter correctly."""
        content = "---\nname: test\ndescription: A test\n---\nBody content"
        result = parse_frontmatter(content)
        assert result.success is True
        assert "name: test" in result.data
        assert "description: A test" in result.data
        assert result.errors == []

    def test_missing_opening_delimiter(self) -> None:
        """Returns error when content does not start with ---."""
        content = "name: test\n---\nBody content"
        result = parse_frontmatter(content)
        assert result.success is False
        assert result.errors == ["Content must have YAML frontmatter"]

    def test_missing_closing_delimiter(self) -> None:
        """Returns error when closing --- is missing."""
        content = "---\nname: test\nBody content"
        result = parse_frontmatter(content)
        assert result.success is False
        assert result.errors == ["Invalid frontmatter: missing closing ---"]

    def test_empty_frontmatter(self) -> None:
        """Parses empty frontmatter block."""
        content = "---\n---\nBody content"
        result = parse_frontmatter(content)
        assert result.success is True
        assert result.data == ""

    def test_frontmatter_with_whitespace(self) -> None:
        """Strips whitespace from frontmatter."""
        content = "---\n  name: test  \n---\nBody"
        result = parse_frontmatter(content)
        assert result.success is True
        assert result.data == "name: test"

    def test_empty_content(self) -> None:
        """Returns error for empty content."""
        result = parse_frontmatter("")
        assert result.success is False
        assert result.errors == ["Content must have YAML frontmatter"]

    def test_only_opening_delimiter(self) -> None:
        """Returns error when only opening delimiter exists."""
        content = "---"
        result = parse_frontmatter(content)
        assert result.success is False
        assert result.errors == ["Invalid frontmatter: missing closing ---"]

    def test_multiline_frontmatter(self) -> None:
        """Parses multiline frontmatter correctly."""
        content = """---
name: complex-agent
description: |
  A multi-line
  description here
tools:
  - tool1
  - tool2
---
Body content here"""
        result = parse_frontmatter(content)
        assert result.success is True
        assert "name: complex-agent" in result.data
        assert "tools:" in result.data
