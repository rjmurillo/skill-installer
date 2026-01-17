"""Filesystem abstraction for testability.

This module provides a filesystem abstraction that enables testing
without real I/O operations. The RealFileSystem implementation
wraps standard library operations.
"""

from __future__ import annotations

import shutil
from pathlib import Path


class RealFileSystem:
    """Production filesystem implementation.

    Wraps standard library Path and shutil operations.
    Satisfies the FileSystem protocol structurally.
    """

    def read_text(self, path: Path) -> str:
        """Read text content from a file."""
        return path.read_text()

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to a file."""
        path.write_text(content)

    def exists(self, path: Path) -> bool:
        """Check if a path exists."""
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory."""
        return path.is_dir()

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory."""
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def unlink(self, path: Path) -> None:
        """Remove a file."""
        path.unlink()

    def rmtree(self, path: Path) -> None:
        """Remove a directory tree."""
        shutil.rmtree(path)

    def copytree(self, src: Path, dst: Path) -> None:
        """Copy a directory tree."""
        shutil.copytree(src, dst)
