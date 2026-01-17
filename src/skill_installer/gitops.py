"""Git operations for source management."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

if TYPE_CHECKING:
    pass

# Default cache location for cloned repos
CACHE_DIR = Path.home() / ".skill-installer" / "cache"


class GitOpsError(Exception):
    """Error during git operations."""

    pass


class GitOps:
    """Manages git operations for source repositories."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize git operations manager.

        Args:
            cache_dir: Directory for cloned repos. Defaults to ~/.skill-installer/cache.
        """
        self.cache_dir = cache_dir or CACHE_DIR

    def ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, source_name: str) -> Path:
        """Get the local path for a source repository.

        Args:
            source_name: Name of the source.

        Returns:
            Path to the local clone.
        """
        return self.cache_dir / source_name

    def clone_or_fetch(self, url: str, name: str, ref: str = "main") -> Path:
        """Clone a repository or fetch updates if already cloned.

        Args:
            url: Git repository URL.
            name: Name for the local clone.
            ref: Branch/tag to checkout. Defaults to "main".

        Returns:
            Path to the local clone.

        Raises:
            GitOpsError: If clone or fetch fails.
        """
        self.ensure_cache_dir()
        repo_path = self.get_repo_path(name)

        try:
            if repo_path.exists():
                return self._fetch_and_checkout(repo_path, ref)
            return self._clone(url, repo_path, ref)
        except (GitCommandError, InvalidGitRepositoryError) as e:
            raise GitOpsError(f"Git operation failed: {e}") from e

    def _clone(self, url: str, path: Path, ref: str) -> Path:
        """Clone a repository.

        Args:
            url: Git repository URL.
            path: Local path for the clone.
            ref: Branch/tag to checkout.

        Returns:
            Path to the clone.
        """
        repo = Repo.clone_from(url, path, branch=ref, depth=1)
        repo.git.checkout(ref)
        return path

    def _fetch_and_checkout(self, path: Path, ref: str) -> Path:
        """Fetch updates and checkout ref.

        Args:
            path: Path to local repository.
            ref: Branch/tag to checkout.

        Returns:
            Path to the repository.
        """
        repo = Repo(path)
        repo.remotes.origin.fetch(depth=1)
        repo.git.checkout(ref)
        repo.git.pull("origin", ref)
        return path

    def get_file_hash(self, path: Path) -> str:
        """Get SHA256 hash of a file's content.

        Args:
            path: Path to the file.

        Returns:
            Hex digest of the SHA256 hash.
        """
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def get_tree_hash(self, path: Path) -> str:
        """Get combined hash of all files in a directory.

        Args:
            path: Path to the directory.

        Returns:
            Hex digest of the combined SHA256 hash.
        """
        if path.is_file():
            return self.get_file_hash(path)

        hasher = hashlib.sha256()
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                hasher.update(file_path.read_bytes())
        return hasher.hexdigest()

    def remove_cached(self, name: str) -> bool:
        """Remove a cached repository.

        Args:
            name: Name of the source.

        Returns:
            True if removed, False if not found.
        """
        repo_path = self.get_repo_path(name)
        if repo_path.exists():
            import shutil

            shutil.rmtree(repo_path)
            return True
        return False

    def is_cached(self, name: str) -> bool:
        """Check if a repository is cached.

        Args:
            name: Name of the source.

        Returns:
            True if cached, False otherwise.
        """
        return self.get_repo_path(name).exists()
