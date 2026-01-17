"""Cross-platform transformation engine.

This module implements content transformation between platform formats using
the Strategy pattern. Each platform pair has a dedicated strategy that
encapsulates frontmatter and syntax transformations.

Pattern: Strategy - encapsulates varying transformation algorithms, allowing
new platform pairs to be added without modifying the engine.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from skill_installer.protocols import TransformStrategy


class BaseTransformStrategy(ABC):
    """Base class for transformation strategies.

    Provides common transformation logic. Subclasses override methods
    to specify platform-specific transformations.
    """

    source_platform: str
    target_platform: str

    # Model name mappings
    MODEL_MAP_TO_FULL = {
        "haiku": "claude-haiku-3-5",
        "sonnet": "claude-sonnet-4-5",
        "opus": "claude-opus-4-5",
    }

    MODEL_MAP_TO_SHORT = {
        "claude-haiku-3-5": "haiku",
        "claude-sonnet-4-5": "sonnet",
        "claude-opus-4-5": "opus",
        "claude-3-5-haiku": "haiku",
        "claude-3-5-sonnet": "sonnet",
    }

    DEFAULT_VSCODE_TOOLS = ["read", "edit", "shell", "search"]

    @abstractmethod
    def transform_frontmatter(self, frontmatter: dict) -> dict:
        """Transform frontmatter fields for the target platform."""
        ...

    @abstractmethod
    def transform_syntax(self, body: str) -> str:
        """Transform body syntax for the target platform."""
        ...

    def _map_model_to_full(self, model: str) -> str:
        """Map short model name to full name."""
        return self.MODEL_MAP_TO_FULL.get(model, model)

    def _map_model_to_short(self, model: str) -> str:
        """Map full model name to short name."""
        return self.MODEL_MAP_TO_SHORT.get(model, model)


class ClaudeToVSCodeStrategy(BaseTransformStrategy):
    """Transform Claude format to VS Code format."""

    source_platform = "claude"
    target_platform = "vscode"

    def transform_frontmatter(self, frontmatter: dict) -> dict:
        """Transform frontmatter for VS Code."""
        result = dict(frontmatter)

        # Add tools if not present
        if "tools" not in result:
            result["tools"] = self.DEFAULT_VSCODE_TOOLS

        # Transform model name to full
        if "model" in result:
            result["model"] = self._map_model_to_full(result["model"])

        return result

    def transform_syntax(self, body: str) -> str:
        """Transform Claude syntax to VS Code syntax."""
        pattern = r'Task\s*\(\s*subagent_type\s*=\s*["\'](\w+)["\']\s*(?:,\s*prompt\s*=\s*["\']([^"\']+)["\'])?\s*\)'

        def replacer(match: re.Match) -> str:
            agent_type = match.group(1)
            prompt = match.group(2)
            if prompt:
                return f'#runSubagent("{agent_type}", "{prompt}")'
            return f'#runSubagent("{agent_type}")'

        return re.sub(pattern, replacer, body)


class VSCodeToClaudeStrategy(BaseTransformStrategy):
    """Transform VS Code format to Claude format."""

    source_platform = "vscode"
    target_platform = "claude"

    def transform_frontmatter(self, frontmatter: dict) -> dict:
        """Transform frontmatter for Claude."""
        result = dict(frontmatter)

        # Remove tools (not used by Claude)
        result.pop("tools", None)

        # Ensure name is present
        if "name" not in result:
            result["name"] = "agent"

        # Transform model name to short
        if "model" in result:
            result["model"] = self._map_model_to_short(result["model"])

        return result

    def transform_syntax(self, body: str) -> str:
        """Transform VS Code syntax to Claude syntax."""
        pattern = r'#runSubagent\s*\(\s*["\'](\w+)["\']\s*(?:,\s*["\']([^"\']+)["\'])?\s*\)'

        def replacer(match: re.Match) -> str:
            agent_type = match.group(1)
            prompt = match.group(2)
            if prompt:
                return f'Task(subagent_type="{agent_type}", prompt="{prompt}")'
            return f'Task(subagent_type="{agent_type}")'

        return re.sub(pattern, replacer, body)


class IdentityStrategy(BaseTransformStrategy):
    """No-op strategy for same-format transformations."""

    def __init__(self, platform: str) -> None:
        """Initialize with platform name."""
        self.source_platform = platform
        self.target_platform = platform

    def transform_frontmatter(self, frontmatter: dict) -> dict:
        """Return frontmatter unchanged."""
        return dict(frontmatter)

    def transform_syntax(self, body: str) -> str:
        """Return body unchanged."""
        return body


class TransformEngine:
    """Transforms content between platform formats.

    Uses Strategy pattern to encapsulate platform-specific transformations.
    Strategies are registered in a lookup table, allowing new platform pairs
    to be added without modifying the transform() method.
    """

    # Model name mappings (kept for backward compatibility and detect_platform)
    MODEL_MAP = {
        # Claude aliases to full names (for VS Code/Copilot)
        "haiku": "claude-haiku-3-5",
        "sonnet": "claude-sonnet-4-5",
        "opus": "claude-opus-4-5",
        # Full names to Claude aliases
        "claude-haiku-3-5": "haiku",
        "claude-sonnet-4-5": "sonnet",
        "claude-opus-4-5": "opus",
        "claude-3-5-haiku": "haiku",
        "claude-3-5-sonnet": "sonnet",
    }

    # Default tools for VS Code/Copilot
    DEFAULT_VSCODE_TOOLS = ["read", "edit", "shell", "search"]

    def __init__(self) -> None:
        """Initialize transform engine with registered strategies."""
        # Strategy registry: (source, target) -> strategy instance
        self._strategies: dict[tuple[str, str], BaseTransformStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register built-in transformation strategies."""
        # Claude to VS Code family
        claude_to_vscode = ClaudeToVSCodeStrategy()
        self._strategies[("claude", "vscode")] = claude_to_vscode
        self._strategies[("claude", "vscode-insiders")] = claude_to_vscode
        self._strategies[("claude", "copilot")] = claude_to_vscode

        # VS Code family to Claude
        vscode_to_claude = VSCodeToClaudeStrategy()
        self._strategies[("vscode", "claude")] = vscode_to_claude
        self._strategies[("vscode-insiders", "claude")] = vscode_to_claude
        self._strategies[("copilot", "claude")] = vscode_to_claude

        # Identity transformations (same format family)
        vscode_identity = IdentityStrategy("vscode")
        self._strategies[("vscode", "copilot")] = vscode_identity
        self._strategies[("vscode", "vscode-insiders")] = vscode_identity
        self._strategies[("vscode-insiders", "vscode")] = vscode_identity
        self._strategies[("vscode-insiders", "copilot")] = vscode_identity
        self._strategies[("copilot", "vscode")] = vscode_identity
        self._strategies[("copilot", "vscode-insiders")] = vscode_identity

    def register_strategy(self, strategy: BaseTransformStrategy) -> None:
        """Register a custom transformation strategy.

        Args:
            strategy: Strategy to register. Must have source_platform and
                target_platform attributes set.
        """
        key = (strategy.source_platform.lower(), strategy.target_platform.lower())
        self._strategies[key] = strategy

    def get_strategy(
        self, source_platform: str, target_platform: str
    ) -> BaseTransformStrategy | None:
        """Get the strategy for a platform pair.

        Args:
            source_platform: Source platform name.
            target_platform: Target platform name.

        Returns:
            Strategy instance or None if not found.
        """
        key = (source_platform.lower(), target_platform.lower())
        return self._strategies.get(key)

    def _apply_strategy(self, content: str, strategy: BaseTransformStrategy) -> str:
        """Apply a transformation strategy to content.

        Args:
            content: Source content.
            strategy: Strategy to apply.

        Returns:
            Transformed content.
        """
        frontmatter, body = self._split_frontmatter(content)
        if not frontmatter:
            # No frontmatter: for VS Code target, add default frontmatter
            if strategy.target_platform in ("vscode", "vscode-insiders", "copilot"):
                transformed = strategy.transform_frontmatter({})
                return self._create_frontmatter_string(transformed) + body
            return content

        # Transform frontmatter and body
        transformed_fm = strategy.transform_frontmatter(frontmatter)
        transformed_body = strategy.transform_syntax(body)

        return self._create_frontmatter_string(transformed_fm) + transformed_body

    def claude_to_vscode(self, content: str) -> str:
        """Convert Claude agent format to VS Code format.

        Args:
            content: Claude agent content.

        Returns:
            VS Code formatted content.
        """
        strategy = self._strategies[("claude", "vscode")]
        return self._apply_strategy(content, strategy)

    def vscode_to_claude(self, content: str) -> str:
        """Convert VS Code agent format to Claude format.

        Args:
            content: VS Code agent content.

        Returns:
            Claude formatted content.
        """
        strategy = self._strategies[("vscode", "claude")]
        return self._apply_strategy(content, strategy)

    def copilot_to_claude(self, content: str) -> str:
        """Convert Copilot CLI format to Claude format.

        Args:
            content: Copilot agent content.

        Returns:
            Claude formatted content.
        """
        strategy = self._strategies[("copilot", "claude")]
        return self._apply_strategy(content, strategy)

    def claude_to_copilot(self, content: str) -> str:
        """Convert Claude format to Copilot CLI format.

        Args:
            content: Claude agent content.

        Returns:
            Copilot formatted content.
        """
        strategy = self._strategies[("claude", "copilot")]
        return self._apply_strategy(content, strategy)

    def transform(self, content: str, source_platform: str, target_platform: str) -> str:
        """Transform content between platforms.

        Args:
            content: Source content.
            source_platform: Source platform name.
            target_platform: Target platform name.

        Returns:
            Transformed content.

        Raises:
            ValueError: If transformation not supported.
        """
        if source_platform == target_platform:
            return content

        # Normalize platform names
        source = source_platform.lower()
        target = target_platform.lower()

        strategy = self.get_strategy(source, target)
        if strategy is None:
            raise ValueError(f"Cannot transform from {source_platform} to {target_platform}")

        return self._apply_strategy(content, strategy)

    def _split_frontmatter(self, content: str) -> tuple[dict, str]:
        """Split content into frontmatter and body.

        Args:
            content: Full file content.

        Returns:
            Tuple of (frontmatter dict, body string).
        """
        if not content.startswith("---"):
            return {}, content

        try:
            end_idx = content.index("---", 3)
            frontmatter_str = content[3:end_idx].strip()
            body = content[end_idx + 3:].lstrip("\n")
            return yaml.safe_load(frontmatter_str) or {}, body
        except (ValueError, yaml.YAMLError):
            return {}, content

    def _create_frontmatter_string(self, frontmatter: dict) -> str:
        """Create frontmatter string from dict.

        Args:
            frontmatter: Frontmatter dictionary.

        Returns:
            YAML frontmatter string with delimiters.
        """
        if not frontmatter:
            return ""
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_str}---\n\n"

    def _create_vscode_frontmatter(self, frontmatter: dict) -> str:
        """Create VS Code frontmatter with defaults.

        Args:
            frontmatter: Base frontmatter.

        Returns:
            VS Code formatted frontmatter string.
        """
        if "tools" not in frontmatter:
            frontmatter["tools"] = self.DEFAULT_VSCODE_TOOLS
        return self._create_frontmatter_string(frontmatter)

    def _transform_frontmatter_to_vscode(self, frontmatter: dict) -> dict:
        """Transform frontmatter for VS Code.

        Delegates to ClaudeToVSCodeStrategy for consistency.

        Args:
            frontmatter: Claude frontmatter.

        Returns:
            VS Code frontmatter.
        """
        strategy = self._strategies[("claude", "vscode")]
        return strategy.transform_frontmatter(frontmatter)

    def _transform_frontmatter_to_claude(self, frontmatter: dict) -> dict:
        """Transform frontmatter for Claude.

        Delegates to VSCodeToClaudeStrategy for consistency.

        Args:
            frontmatter: VS Code/Copilot frontmatter.

        Returns:
            Claude frontmatter.
        """
        strategy = self._strategies[("vscode", "claude")]
        return strategy.transform_frontmatter(frontmatter)

    def _transform_syntax_to_vscode(self, body: str) -> str:
        """Transform body syntax for VS Code.

        Delegates to ClaudeToVSCodeStrategy for consistency.

        Args:
            body: Claude agent body.

        Returns:
            VS Code formatted body.
        """
        strategy = self._strategies[("claude", "vscode")]
        return strategy.transform_syntax(body)

    def _transform_syntax_to_claude(self, body: str) -> str:
        """Transform body syntax for Claude.

        Delegates to VSCodeToClaudeStrategy for consistency.

        Args:
            body: VS Code/Copilot agent body.

        Returns:
            Claude formatted body.
        """
        strategy = self._strategies[("vscode", "claude")]
        return strategy.transform_syntax(body)

    def detect_platform(self, content: str) -> str | None:
        """Detect the platform format of content.

        Args:
            content: Agent content.

        Returns:
            Platform name or None if unknown.
        """
        frontmatter, body = self._split_frontmatter(content)

        # Check for VS Code/Copilot indicators
        if "tools:" in str(frontmatter) or frontmatter.get("tools"):
            return "vscode"

        # Check for Claude indicators
        if "Task(subagent_type=" in body:
            return "claude"

        # Check for VS Code/Copilot syntax
        if "#runSubagent" in body:
            return "vscode"

        # Default to Claude if has name but no tools
        if frontmatter.get("name") and not frontmatter.get("tools"):
            return "claude"

        return None
