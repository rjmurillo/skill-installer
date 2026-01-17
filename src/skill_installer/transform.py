"""Cross-platform transformation engine."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    pass


class TransformEngine:
    """Transforms content between platform formats."""

    # Model name mappings
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
        """Initialize transform engine."""
        pass

    def claude_to_vscode(self, content: str) -> str:
        """Convert Claude agent format to VS Code format.

        Args:
            content: Claude agent content.

        Returns:
            VS Code formatted content.
        """
        frontmatter, body = self._split_frontmatter(content)
        if not frontmatter:
            # No frontmatter, wrap in VS Code format
            return self._create_vscode_frontmatter({}) + body

        # Transform frontmatter
        transformed = self._transform_frontmatter_to_vscode(frontmatter)

        # Transform body syntax
        body = self._transform_syntax_to_vscode(body)

        return self._create_frontmatter_string(transformed) + body

    def vscode_to_claude(self, content: str) -> str:
        """Convert VS Code agent format to Claude format.

        Args:
            content: VS Code agent content.

        Returns:
            Claude formatted content.
        """
        frontmatter, body = self._split_frontmatter(content)
        if not frontmatter:
            return content

        # Transform frontmatter
        transformed = self._transform_frontmatter_to_claude(frontmatter)

        # Transform body syntax
        body = self._transform_syntax_to_claude(body)

        return self._create_frontmatter_string(transformed) + body

    def copilot_to_claude(self, content: str) -> str:
        """Convert Copilot CLI format to Claude format.

        Args:
            content: Copilot agent content.

        Returns:
            Claude formatted content.
        """
        # Copilot and VS Code use similar formats
        return self.vscode_to_claude(content)

    def claude_to_copilot(self, content: str) -> str:
        """Convert Claude format to Copilot CLI format.

        Args:
            content: Claude agent content.

        Returns:
            Copilot formatted content.
        """
        # Similar to VS Code, but with required name field
        return self.claude_to_vscode(content)

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

        if source == "claude":
            if target in ("vscode", "vscode-insiders"):
                return self.claude_to_vscode(content)
            if target == "copilot":
                return self.claude_to_copilot(content)
        elif source in ("vscode", "vscode-insiders"):
            if target == "claude":
                return self.vscode_to_claude(content)
            if target == "copilot":
                return content  # Same format
        elif source == "copilot":
            if target == "claude":
                return self.copilot_to_claude(content)
            if target in ("vscode", "vscode-insiders"):
                return content  # Same format

        raise ValueError(f"Cannot transform from {source_platform} to {target_platform}")

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

        Args:
            frontmatter: Claude frontmatter.

        Returns:
            VS Code frontmatter.
        """
        result = dict(frontmatter)

        # Add tools if not present
        if "tools" not in result:
            result["tools"] = self.DEFAULT_VSCODE_TOOLS

        # Transform model name
        if "model" in result:
            model = result["model"]
            if model in self.MODEL_MAP:
                result["model"] = self.MODEL_MAP[model]

        return result

    def _transform_frontmatter_to_claude(self, frontmatter: dict) -> dict:
        """Transform frontmatter for Claude.

        Args:
            frontmatter: VS Code/Copilot frontmatter.

        Returns:
            Claude frontmatter.
        """
        result = dict(frontmatter)

        # Remove tools (not used by Claude)
        result.pop("tools", None)

        # Ensure name is present
        if "name" not in result:
            result["name"] = "agent"

        # Transform model name
        if "model" in result:
            model = result["model"]
            if model in self.MODEL_MAP:
                result["model"] = self.MODEL_MAP[model]

        return result

    def _transform_syntax_to_vscode(self, body: str) -> str:
        """Transform body syntax for VS Code.

        Args:
            body: Claude agent body.

        Returns:
            VS Code formatted body.
        """
        # Convert Task(subagent_type="X") to #runSubagent("X")
        pattern = r'Task\s*\(\s*subagent_type\s*=\s*["\'](\w+)["\']\s*(?:,\s*prompt\s*=\s*["\']([^"\']+)["\'])?\s*\)'

        def replacer(match: re.Match) -> str:
            agent_type = match.group(1)
            prompt = match.group(2)
            if prompt:
                return f'#runSubagent("{agent_type}", "{prompt}")'
            return f'#runSubagent("{agent_type}")'

        return re.sub(pattern, replacer, body)

    def _transform_syntax_to_claude(self, body: str) -> str:
        """Transform body syntax for Claude.

        Args:
            body: VS Code/Copilot agent body.

        Returns:
            Claude formatted body.
        """
        # Convert #runSubagent("X") to Task(subagent_type="X")
        pattern = r'#runSubagent\s*\(\s*["\'](\w+)["\']\s*(?:,\s*["\']([^"\']+)["\'])?\s*\)'

        def replacer(match: re.Match) -> str:
            agent_type = match.group(1)
            prompt = match.group(2)
            if prompt:
                return f'Task(subagent_type="{agent_type}", prompt="{prompt}")'
            return f'Task(subagent_type="{agent_type}")'

        return re.sub(pattern, replacer, body)

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
