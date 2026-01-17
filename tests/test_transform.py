"""Tests for transform module."""

from __future__ import annotations

import pytest

from skill_installer.transform import TransformEngine


@pytest.fixture
def transformer() -> TransformEngine:
    """Create a TransformEngine instance."""
    return TransformEngine()


class TestTransformEngine:
    """Tests for TransformEngine class."""

    def test_claude_to_vscode_blocked(self, transformer: TransformEngine) -> None:
        """Test that Claude to VSCode transform is blocked."""
        with pytest.raises(NotImplementedError, match="not supported"):
            transformer.claude_to_vscode("content")

    def test_vscode_to_claude_blocked(self, transformer: TransformEngine) -> None:
        """Test that VSCode to Claude transform is blocked."""
        with pytest.raises(NotImplementedError, match="not supported"):
            transformer.vscode_to_claude("content")

    def test_copilot_to_claude_blocked(self, transformer: TransformEngine) -> None:
        """Test that Copilot to Claude transform is blocked."""
        with pytest.raises(NotImplementedError, match="not supported"):
            transformer.copilot_to_claude("content")

    def test_claude_to_copilot_blocked(self, transformer: TransformEngine) -> None:
        """Test that Claude to Copilot transform is blocked."""
        with pytest.raises(NotImplementedError, match="not supported"):
            transformer.claude_to_copilot("content")

    def test_transform_same_platform(self, transformer: TransformEngine) -> None:
        """Test that same platform returns unchanged content."""
        content = "# Test content"
        result = transformer.transform(content, "claude", "claude")
        assert result == content

    def test_transform_cross_platform_blocked(self, transformer: TransformEngine) -> None:
        """Test that cross-platform transforms raise error."""
        with pytest.raises(ValueError, match="Cannot transform"):
            transformer.transform("content", "claude", "vscode")
        with pytest.raises(ValueError, match="Cannot transform"):
            transformer.transform("content", "vscode", "claude")

    def test_transform_unknown_platforms(self, transformer: TransformEngine) -> None:
        """Test that unknown platforms raise error."""
        with pytest.raises(ValueError, match="Cannot transform"):
            transformer.transform("content", "unknown", "claude")

    def test_model_mapping(self, transformer: TransformEngine) -> None:
        """Test model name mapping."""
        assert transformer.MODEL_MAP["sonnet"] == "claude-sonnet-4-5"
        assert transformer.MODEL_MAP["claude-sonnet-4-5"] == "sonnet"
        assert transformer.MODEL_MAP["haiku"] == "claude-haiku-3-5"
        assert transformer.MODEL_MAP["opus"] == "claude-opus-4-5"

    def test_split_frontmatter(self, transformer: TransformEngine) -> None:
        """Test splitting frontmatter from body."""
        content = """---
name: test
---

# Body content
"""
        frontmatter, body = transformer._split_frontmatter(content)
        assert frontmatter["name"] == "test"
        assert "# Body content" in body

    def test_split_frontmatter_no_frontmatter(self, transformer: TransformEngine) -> None:
        """Test splitting content without frontmatter."""
        content = "# Just body content"
        frontmatter, body = transformer._split_frontmatter(content)
        assert frontmatter == {}
        assert body == content

    def test_create_frontmatter_string(self, transformer: TransformEngine) -> None:
        """Test creating frontmatter string."""
        frontmatter = {"name": "test", "description": "Test agent"}
        result = transformer._create_frontmatter_string(frontmatter)
        assert result.startswith("---\n")
        assert result.endswith("---\n\n")
        assert "name: test" in result

    def test_create_frontmatter_string_empty(self, transformer: TransformEngine) -> None:
        """Test creating frontmatter string from empty dict."""
        result = transformer._create_frontmatter_string({})
        assert result == ""

    def test_transform_frontmatter_to_vscode_blocked(
        self, transformer: TransformEngine
    ) -> None:
        """Test that frontmatter transform to VSCode is blocked."""
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            transformer._transform_frontmatter_to_vscode({"name": "test"})

    def test_transform_frontmatter_to_claude_blocked(
        self, transformer: TransformEngine
    ) -> None:
        """Test that frontmatter transform to Claude is blocked."""
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            transformer._transform_frontmatter_to_claude({"name": "test"})

    def test_transform_syntax_to_vscode_blocked(
        self, transformer: TransformEngine
    ) -> None:
        """Test that syntax transform to VSCode is blocked."""
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            transformer._transform_syntax_to_vscode("body")

    def test_transform_syntax_to_claude_blocked(
        self, transformer: TransformEngine
    ) -> None:
        """Test that syntax transform to Claude is blocked."""
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            transformer._transform_syntax_to_claude("body")

    def test_detect_platform_claude(self, transformer: TransformEngine) -> None:
        """Test detecting Claude format."""
        content = """---
name: test
---

Use Task(subagent_type="analyst") to research.
"""
        assert transformer.detect_platform(content) == "claude"

    def test_detect_platform_vscode(self, transformer: TransformEngine) -> None:
        """Test detecting VS Code format."""
        content = """---
name: test
tools:
  - read
---

Use #runSubagent("analyst") to research.
"""
        assert transformer.detect_platform(content) == "vscode"

    def test_detect_platform_unknown(self, transformer: TransformEngine) -> None:
        """Test detecting unknown format."""
        content = "# Just content"
        assert transformer.detect_platform(content) is None


class TestTransformStrategies:
    """Tests for individual transformation strategies."""

    def test_claude_to_vscode_strategy_blocked(self) -> None:
        """Test ClaudeToVSCodeStrategy is blocked."""
        from skill_installer.transform import ClaudeToVSCodeStrategy

        strategy = ClaudeToVSCodeStrategy()
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            strategy.transform_frontmatter({"name": "test"})
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            strategy.transform_syntax("body")

    def test_vscode_to_claude_strategy_blocked(self) -> None:
        """Test VSCodeToClaudeStrategy is blocked."""
        from skill_installer.transform import VSCodeToClaudeStrategy

        strategy = VSCodeToClaudeStrategy()
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            strategy.transform_frontmatter({"name": "test"})
        with pytest.raises(NotImplementedError, match="disabled|not supported"):
            strategy.transform_syntax("body")

    def test_identity_strategy_no_change(self) -> None:
        """Test IdentityStrategy returns content unchanged."""
        from skill_installer.transform import IdentityStrategy

        strategy = IdentityStrategy("vscode")
        frontmatter = {"name": "test", "tools": ["read"]}
        body = "Some content"

        assert strategy.transform_frontmatter(frontmatter) == frontmatter
        assert strategy.transform_syntax(body) == body
        assert strategy.source_platform == "vscode"
        assert strategy.target_platform == "vscode"

    def test_register_custom_strategy(self, transformer: TransformEngine) -> None:
        """Test registering a custom transformation strategy."""
        from skill_installer.transform import BaseTransformStrategy

        class CustomStrategy(BaseTransformStrategy):
            source_platform = "custom"
            target_platform = "claude"

            def transform_frontmatter(self, frontmatter: dict) -> dict:
                result = dict(frontmatter)
                result["custom_field"] = "added"
                return result

            def transform_syntax(self, body: str) -> str:
                return body.replace("CUSTOM", "Claude")

        transformer.register_strategy(CustomStrategy())

        # Verify strategy was registered
        strategy = transformer.get_strategy("custom", "claude")
        assert strategy is not None
        assert isinstance(strategy, CustomStrategy)

    def test_get_strategy_returns_none_for_unknown(
        self, transformer: TransformEngine
    ) -> None:
        """Test get_strategy returns None for unknown platform pair."""
        result = transformer.get_strategy("unknown", "unknown")
        assert result is None
