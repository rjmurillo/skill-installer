"""Base platform implementation with shared behavior.

This module extracts commonalities identified via CVA (Commonality/Variability
Analysis). All platforms share the same validation algorithm structure; they
vary only in which frontmatter fields are required.

Pattern: Template Method - base class defines algorithm skeleton, subclasses
provide specific steps.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from skill_installer.validation import parse_frontmatter


class BasePlatform(ABC):
    """Base class for platform implementations.

    Extracts common validation structure. Subclasses override
    `get_required_fields()` to specify platform-specific requirements.
    """

    name: str
    agent_extension: str
    supports_skills: bool

    @property
    @abstractmethod
    def base_dir(self) -> Path:
        """Get the base directory for this platform."""
        ...

    @abstractmethod
    def ensure_dirs(self) -> None:
        """Create platform directories if they don't exist."""
        ...

    @abstractmethod
    def get_install_path(self, item_type: str, name: str) -> Path:
        """Get the installation path for an item."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this platform is available on the current system."""
        ...

    @abstractmethod
    def get_project_install_path(
        self, project_root: Path, item_type: str, name: str
    ) -> Path:
        """Get the project-local installation path for an item."""
        ...

    def get_required_fields(self) -> list[str]:
        """Get the required frontmatter fields for this platform.

        Override in subclasses to specify platform-specific requirements.
        Per GitHub/VSCode specs, frontmatter fields are optional for agents.
        https://docs.github.com/en/copilot/reference/custom-agents-configuration
        
        Returns:
            List of field names that must be present in frontmatter.
        """
        return []

    def get_field_error_message(self, field: str) -> str:
        """Get error message for a missing field.

        Override in subclasses for platform-specific messages.

        Args:
            field: The missing field name (with colon).

        Returns:
            Human-readable error message.
        """
        field_name = field.rstrip(":")
        return f"Frontmatter must include '{field_name}' field"

    def validate_agent(self, content: str) -> list[str]:
        """Validate agent/skill content for this platform's format.

        Template Method: calls parse_frontmatter (common), then checks
        required fields (varies by platform).

        Args:
            content: File content to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        result = parse_frontmatter(content)
        if not result.success:
            return result.errors

        errors = []
        for field in self.get_required_fields():
            if field not in result.data:
                errors.append(self.get_field_error_message(field))

        return errors
