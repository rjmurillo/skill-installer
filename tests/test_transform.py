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

    def test_claude_to_vscode(self, transformer: TransformEngine) -> None:
        """Test transforming Claude format to VS Code format."""
        claude_content = """---
name: analyst
description: Research specialist
model: sonnet
---

# Analyst Agent

Use Task(subagent_type="implementer", prompt="Write code") for implementation.
"""
        result = transformer.claude_to_vscode(claude_content)

        # Should add tools
        assert "tools:" in result
        # Should transform model name
        assert "claude-sonnet-4-5" in result
        # Should transform syntax
        assert '#runSubagent("implementer"' in result
        assert "Task(subagent_type=" not in result

    def test_vscode_to_claude(self, transformer: TransformEngine) -> None:
        """Test transforming VS Code format to Claude format."""
        vscode_content = """---
name: analyst
description: Research specialist
model: claude-sonnet-4-5
tools:
  - read
  - edit
---

# Analyst Agent

Use #runSubagent("implementer", "Write code") for implementation.
"""
        result = transformer.vscode_to_claude(vscode_content)

        # Should remove tools
        assert "tools:" not in result
        # Should transform model name
        assert "sonnet" in result
        assert "claude-sonnet-4-5" not in result
        # Should transform syntax
        assert 'Task(subagent_type="implementer"' in result
        assert "#runSubagent" not in result

    def test_transform_same_platform(self, transformer: TransformEngine) -> None:
        """Test that same platform returns unchanged content."""
        content = "# Test content"
        result = transformer.transform(content, "claude", "claude")
        assert result == content

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

    def test_transform_frontmatter_to_vscode(self, transformer: TransformEngine) -> None:
        """Test transforming frontmatter for VS Code."""
        frontmatter = {"name": "test", "model": "sonnet"}
        result = transformer._transform_frontmatter_to_vscode(frontmatter)
        assert "tools" in result
        assert result["model"] == "claude-sonnet-4-5"

    def test_transform_frontmatter_to_claude(self, transformer: TransformEngine) -> None:
        """Test transforming frontmatter for Claude."""
        frontmatter = {
            "name": "test",
            "model": "claude-sonnet-4-5",
            "tools": ["read", "edit"],
        }
        result = transformer._transform_frontmatter_to_claude(frontmatter)
        assert "tools" not in result
        assert result["model"] == "sonnet"

    def test_transform_syntax_to_vscode(self, transformer: TransformEngine) -> None:
        """Test transforming Claude syntax to VS Code syntax."""
        body = 'Use Task(subagent_type="analyst", prompt="Research this") to investigate.'
        result = transformer._transform_syntax_to_vscode(body)
        assert '#runSubagent("analyst", "Research this")' in result

    def test_transform_syntax_to_vscode_no_prompt(self, transformer: TransformEngine) -> None:
        """Test transforming Claude syntax without prompt."""
        body = 'Use Task(subagent_type="analyst") to investigate.'
        result = transformer._transform_syntax_to_vscode(body)
        assert '#runSubagent("analyst")' in result

    def test_transform_syntax_to_claude(self, transformer: TransformEngine) -> None:
        """Test transforming VS Code syntax to Claude syntax."""
        body = 'Use #runSubagent("analyst", "Research this") to investigate.'
        result = transformer._transform_syntax_to_claude(body)
        assert 'Task(subagent_type="analyst", prompt="Research this")' in result

    def test_transform_syntax_to_claude_no_prompt(self, transformer: TransformEngine) -> None:
        """Test transforming VS Code syntax without prompt."""
        body = 'Use #runSubagent("analyst") to investigate.'
        result = transformer._transform_syntax_to_claude(body)
        assert 'Task(subagent_type="analyst")' in result

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

    def test_copilot_to_claude(self, transformer: TransformEngine) -> None:
        """Test Copilot to Claude transformation (same as VS Code)."""
        content = """---
name: test
tools:
  - read
---

Use #runSubagent("analyst") to research.
"""
        result = transformer.copilot_to_claude(content)
        assert 'Task(subagent_type="analyst")' in result

    def test_claude_to_copilot(self, transformer: TransformEngine) -> None:
        """Test Claude to Copilot transformation (same as VS Code)."""
        content = """---
name: test
---

Use Task(subagent_type="analyst") to research.
"""
        result = transformer.claude_to_copilot(content)
        assert '#runSubagent("analyst")' in result


class TestTransformStrategies:
    """Tests for individual transformation strategies."""

    def test_claude_to_vscode_strategy_frontmatter(self) -> None:
        """Test ClaudeToVSCodeStrategy frontmatter transformation."""
        from skill_installer.transform import ClaudeToVSCodeStrategy

        strategy = ClaudeToVSCodeStrategy()
        frontmatter = {"name": "test", "model": "sonnet"}
        result = strategy.transform_frontmatter(frontmatter)

        assert result["tools"] == ["read", "edit", "shell", "search"]
        assert result["model"] == "claude-sonnet-4-5"

    def test_claude_to_vscode_strategy_syntax(self) -> None:
        """Test ClaudeToVSCodeStrategy syntax transformation."""
        from skill_installer.transform import ClaudeToVSCodeStrategy

        strategy = ClaudeToVSCodeStrategy()
        body = 'Use Task(subagent_type="analyst") to investigate.'
        result = strategy.transform_syntax(body)

        assert '#runSubagent("analyst")' in result

    def test_vscode_to_claude_strategy_frontmatter(self) -> None:
        """Test VSCodeToClaudeStrategy frontmatter transformation."""
        from skill_installer.transform import VSCodeToClaudeStrategy

        strategy = VSCodeToClaudeStrategy()
        frontmatter = {"model": "claude-sonnet-4-5", "tools": ["read"]}
        result = strategy.transform_frontmatter(frontmatter)

        assert "tools" not in result
        assert result["model"] == "sonnet"
        assert result["name"] == "agent"

    def test_vscode_to_claude_strategy_syntax(self) -> None:
        """Test VSCodeToClaudeStrategy syntax transformation."""
        from skill_installer.transform import VSCodeToClaudeStrategy

        strategy = VSCodeToClaudeStrategy()
        body = 'Use #runSubagent("analyst") to investigate.'
        result = strategy.transform_syntax(body)

        assert 'Task(subagent_type="analyst")' in result

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
