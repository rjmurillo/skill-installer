"""Git operations for source management."""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
import ssl
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default branches to try when cloning
DEFAULT_BRANCHES = ["main", "master"]

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

        Note:
            Prefer using factory methods `create()` or `create_default()` for construction.
        """
        self.cache_dir = cache_dir or CACHE_DIR

    @classmethod
    def create(cls, cache_dir: Path) -> GitOps:
        """Create a git operations manager with a custom cache directory.

        Args:
            cache_dir: Directory for cloned repositories.

        Returns:
            Configured GitOps instance.
        """
        return cls(cache_dir=cache_dir)

    @classmethod
    def create_default(cls) -> GitOps:
        """Create a git operations manager with the default cache directory.

        Uses ~/.skill-installer/cache as the cache location.

        Returns:
            GitOps configured with default paths.
        """
        return cls()

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
        """Clone a repository with branch fallback.

        Tries the specified ref first. If ref is "main" and fails, tries "master".
        If both fail, queries GitHub API for the default branch.

        Args:
            url: Git repository URL.
            path: Local path for the clone.
            ref: Branch/tag to checkout.

        Returns:
            Path to the clone.

        Raises:
            GitCommandError: If all branch attempts fail.
        """
        branches_to_try = self._get_branches_to_try(ref)
        last_error: GitCommandError | None = None

        for branch in branches_to_try:
            try:
                return self._try_clone(url, path, branch)
            except GitCommandError as e:
                last_error = e
                logger.debug("Clone failed with branch '%s': %s", branch, e)
                self._cleanup_failed_clone(path)

        # All standard branches failed, try GitHub API
        api_branch = self._query_github_default_branch(url)
        if api_branch and api_branch not in branches_to_try:
            try:
                return self._try_clone(url, path, api_branch)
            except GitCommandError as e:
                last_error = e
                logger.debug("Clone failed with API branch '%s': %s", api_branch, e)
                self._cleanup_failed_clone(path)

        if last_error:
            raise last_error
        raise GitCommandError("clone", "No valid branch found")

    def _get_branches_to_try(self, ref: str) -> list[str]:
        """Get ordered list of branches to try for cloning.

        Args:
            ref: The requested branch reference.

        Returns:
            List of branches to try in order.
        """
        if ref in DEFAULT_BRANCHES:
            return DEFAULT_BRANCHES.copy()
        return [ref]

    def _try_clone(self, url: str, path: Path, ref: str) -> Path:
        """Attempt to clone with a specific branch.

        Args:
            url: Git repository URL.
            path: Local path for the clone.
            ref: Branch to checkout.

        Returns:
            Path to the clone.
        """
        repo = Repo.clone_from(url, path, branch=ref, depth=1)
        repo.git.checkout(ref)
        logger.debug("Successfully cloned with branch '%s'", ref)
        return path

    def _cleanup_failed_clone(self, path: Path) -> None:
        """Remove partial clone directory after failed attempt.

        Args:
            path: Path to clean up.
        """
        if path.exists():
            shutil.rmtree(path)

    def _query_github_default_branch(self, url: str) -> str | None:
        """Query GitHub API for repository default branch.

        Args:
            url: Git repository URL.

        Returns:
            Default branch name if found, None otherwise.
        """
        owner_repo = self._extract_github_owner_repo(url)
        if not owner_repo:
            return None

        owner, repo = owner_repo
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            request = urllib.request.Request(
                api_url,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            with urllib.request.urlopen(
                request, timeout=10, context=ssl.create_default_context()
            ) as response:
                import json

                data = json.loads(response.read().decode("utf-8"))
                default_branch = data.get("default_branch")
                if default_branch:
                    logger.debug("GitHub API returned default branch: %s", default_branch)
                return default_branch
        except Exception as e:
            logger.debug("GitHub API query failed: %s", e)
            return None

    def _extract_github_owner_repo(self, url: str) -> tuple[str, str] | None:
        """Extract owner and repo from a GitHub URL.

        Args:
            url: Git repository URL.

        Returns:
            Tuple of (owner, repo) if GitHub URL, None otherwise.
        """
        patterns = [
            r"github\.com[/:]([^/]+)/([^/.]+?)(?:\.git)?$",
            r"github\.com[/:]([^/]+)/([^/.]+?)/?$",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        return None

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

    def get_license(self, name: str) -> str | None:
        """Extract license information from a cached repository.

        Looks for common LICENSE file patterns (LICENSE, LICENSE.md, LICENSE.txt, etc.)
        and returns the first line or SPDX identifier if found.

        Args:
            name: Name of the source.

        Returns:
            License string if found, None otherwise.
        """
        repo_path = self.get_repo_path(name)
        if not repo_path.exists():
            return None

        license_patterns = [
            "LICENSE",
            "LICENSE.md",
            "LICENSE.txt",
            "LICENCE",
            "LICENCE.md",
            "LICENCE.txt",
            "COPYING",
            "COPYING.md",
            "COPYING.txt",
        ]

        for pattern in license_patterns:
            license_file = repo_path / pattern
            if license_file.exists() and license_file.is_file():
                try:
                    content = license_file.read_text(encoding="utf-8", errors="ignore")
                    lines = [line.strip() for line in content.split("\n") if line.strip()]
                    if lines:
                        first_line = lines[0]
                        if len(first_line) > 100:
                            if "MIT" in first_line.upper():
                                return "MIT"
                            if "APACHE" in first_line.upper():
                                return "Apache-2.0"
                            if "GPL" in first_line.upper():
                                return "GPL"
                            if "BSD" in first_line.upper():
                                return "BSD"
                            return first_line[:100] + "..."
                        return first_line
                except Exception:
                    continue

        return None
