"""Validation utilities for skill-installer.

This module provides shared validation functions to eliminate duplication
across platform implementations.
"""

from __future__ import annotations


class FrontmatterResult:
    """Result of parsing frontmatter from content."""

    __slots__ = ("data", "errors", "success")

    def __init__(self, data: str = "", errors: list[str] | None = None) -> None:
        """Initialize frontmatter result.

        Args:
            data: The parsed frontmatter content (raw YAML string).
            errors: List of parsing errors encountered.
        """
        self.data = data
        self.errors = errors or []
        self.success = len(self.errors) == 0


def parse_frontmatter(content: str) -> FrontmatterResult:
    """Parse YAML frontmatter from markdown content.

    Extracts the frontmatter block between the opening and closing '---'
    delimiters. Returns a result object containing the parsed data or
    any errors encountered.

    Args:
        content: The full markdown content with optional frontmatter.

    Returns:
        FrontmatterResult with data (raw YAML string) and any errors.

    Example:
        >>> result = parse_frontmatter("---\\nname: test\\n---\\nBody")
        >>> result.success
        True
        >>> result.data
        'name: test'
    """
    if not content.startswith("---"):
        return FrontmatterResult(errors=["Content must have YAML frontmatter"])

    try:
        end_idx = content.index("---", 3)
        frontmatter = content[3:end_idx].strip()
        return FrontmatterResult(data=frontmatter)
    except ValueError:
        return FrontmatterResult(errors=["Invalid frontmatter: missing closing ---"])
