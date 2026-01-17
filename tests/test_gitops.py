"""Tests for gitops module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_installer.gitops import CACHE_DIR, GitOps, GitOpsError


@pytest.fixture
def temp_gitops(tmp_path: Path) -> GitOps:
    """Create a GitOps instance with temporary cache."""
    return GitOps(cache_dir=tmp_path / "cache")


class TestGitOps:
    """Tests for GitOps class."""

    def test_default_cache_dir(self) -> None:
        """Test default cache directory."""
        gitops = GitOps()
        assert gitops.cache_dir == CACHE_DIR

    def test_custom_cache_dir(self, tmp_path: Path) -> None:
        """Test custom cache directory."""
        cache_dir = tmp_path / "custom"
        gitops = GitOps(cache_dir=cache_dir)
        assert gitops.cache_dir == cache_dir

    def test_ensure_cache_dir(self, temp_gitops: GitOps) -> None:
        """Test cache directory creation."""
        temp_gitops.ensure_cache_dir()
        assert temp_gitops.cache_dir.exists()

    def test_get_repo_path(self, temp_gitops: GitOps) -> None:
        """Test getting repository path."""
        path = temp_gitops.get_repo_path("my-source")
        assert path == temp_gitops.cache_dir / "my-source"

    def test_is_cached_false(self, temp_gitops: GitOps) -> None:
        """Test is_cached returns False when not cached."""
        assert temp_gitops.is_cached("nonexistent") is False

    def test_is_cached_true(self, temp_gitops: GitOps) -> None:
        """Test is_cached returns True when cached."""
        repo_path = temp_gitops.get_repo_path("test")
        repo_path.mkdir(parents=True)
        assert temp_gitops.is_cached("test") is True

    def test_get_file_hash(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test getting file hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = temp_gitops.get_file_hash(test_file)
        assert len(hash1) == 64  # SHA256 hex digest

        # Same content = same hash
        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("test content")
        hash2 = temp_gitops.get_file_hash(test_file2)
        assert hash1 == hash2

    def test_get_file_hash_different_content(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test different content produces different hash."""
        test_file1 = tmp_path / "test1.txt"
        test_file1.write_text("content 1")

        test_file2 = tmp_path / "test2.txt"
        test_file2.write_text("content 2")

        assert temp_gitops.get_file_hash(test_file1) != temp_gitops.get_file_hash(test_file2)

    def test_get_tree_hash_file(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test getting hash for a single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        file_hash = temp_gitops.get_file_hash(test_file)
        tree_hash = temp_gitops.get_tree_hash(test_file)
        assert file_hash == tree_hash

    def test_get_tree_hash_directory(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test getting hash for a directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content 1")
        (test_dir / "file2.txt").write_text("content 2")

        hash1 = temp_gitops.get_tree_hash(test_dir)
        assert len(hash1) == 64

        # Modify a file
        (test_dir / "file1.txt").write_text("modified")
        hash2 = temp_gitops.get_tree_hash(test_dir)
        assert hash1 != hash2

    def test_remove_cached_exists(self, temp_gitops: GitOps) -> None:
        """Test removing cached repository that exists."""
        repo_path = temp_gitops.get_repo_path("test")
        repo_path.mkdir(parents=True)
        (repo_path / "file.txt").write_text("test")

        assert temp_gitops.remove_cached("test") is True
        assert not repo_path.exists()

    def test_remove_cached_not_exists(self, temp_gitops: GitOps) -> None:
        """Test removing cached repository that doesn't exist."""
        assert temp_gitops.remove_cached("nonexistent") is False

    @patch("skill_installer.gitops.Repo")
    def test_clone_or_fetch_new_repo(self, mock_repo: MagicMock, temp_gitops: GitOps) -> None:
        """Test cloning a new repository."""
        temp_gitops.ensure_cache_dir()
        mock_repo.clone_from.return_value = MagicMock()

        result = temp_gitops.clone_or_fetch("https://github.com/test/repo", "test", "main")

        mock_repo.clone_from.assert_called_once()
        assert result == temp_gitops.get_repo_path("test")

    @patch("skill_installer.gitops.Repo")
    def test_clone_or_fetch_existing_repo(self, mock_repo: MagicMock, temp_gitops: GitOps) -> None:
        """Test fetching an existing repository."""
        repo_path = temp_gitops.get_repo_path("test")
        repo_path.mkdir(parents=True)

        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance

        result = temp_gitops.clone_or_fetch("https://github.com/test/repo", "test", "main")

        mock_repo.assert_called_once_with(repo_path)
        mock_repo_instance.remotes.origin.fetch.assert_called_once()
        assert result == repo_path

    @patch("skill_installer.gitops.Repo")
    def test_clone_or_fetch_git_error(self, mock_repo: MagicMock, temp_gitops: GitOps) -> None:
        """Test handling git errors."""
        from git.exc import GitCommandError

        temp_gitops.ensure_cache_dir()
        mock_repo.clone_from.side_effect = GitCommandError("clone", "error")

        with pytest.raises(GitOpsError, match="Git operation failed"):
            temp_gitops.clone_or_fetch("https://github.com/test/repo", "test", "main")

    @patch("skill_installer.gitops.Repo")
    def test_clone_fallback_main_to_master(
        self, mock_repo: MagicMock, temp_gitops: GitOps
    ) -> None:
        """Test fallback from main to master when main fails."""
        from git.exc import GitCommandError

        temp_gitops.ensure_cache_dir()

        def clone_side_effect(url: str, path: Path, branch: str, depth: int) -> MagicMock:
            if branch == "main":
                raise GitCommandError("clone", "branch not found")
            return MagicMock()

        mock_repo.clone_from.side_effect = clone_side_effect

        result = temp_gitops.clone_or_fetch("https://github.com/test/repo", "test", "main")

        assert result == temp_gitops.get_repo_path("test")
        assert mock_repo.clone_from.call_count == 2

    @patch("skill_installer.gitops.Repo")
    def test_clone_explicit_ref_no_fallback(
        self, mock_repo: MagicMock, temp_gitops: GitOps
    ) -> None:
        """Test that explicit non-default refs don't trigger fallback."""
        from git.exc import GitCommandError

        temp_gitops.ensure_cache_dir()
        mock_repo.clone_from.side_effect = GitCommandError("clone", "branch not found")

        with pytest.raises(GitOpsError):
            temp_gitops.clone_or_fetch("https://github.com/test/repo", "test", "feature-branch")

        # Should only try the explicit ref, not fall back
        assert mock_repo.clone_from.call_count == 1

    def test_extract_github_owner_repo_https(self, temp_gitops: GitOps) -> None:
        """Test extracting owner/repo from HTTPS URL."""
        result = temp_gitops._extract_github_owner_repo(
            "https://github.com/owner/repo.git"
        )
        assert result == ("owner", "repo")

    def test_extract_github_owner_repo_ssh(self, temp_gitops: GitOps) -> None:
        """Test extracting owner/repo from SSH URL."""
        result = temp_gitops._extract_github_owner_repo("git@github.com:owner/repo.git")
        assert result == ("owner", "repo")

    def test_extract_github_owner_repo_no_git_suffix(self, temp_gitops: GitOps) -> None:
        """Test extracting owner/repo from URL without .git suffix."""
        result = temp_gitops._extract_github_owner_repo("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_extract_github_owner_repo_non_github(self, temp_gitops: GitOps) -> None:
        """Test non-GitHub URL returns None."""
        result = temp_gitops._extract_github_owner_repo("https://gitlab.com/owner/repo")
        assert result is None

    def test_get_branches_to_try_main(self, temp_gitops: GitOps) -> None:
        """Test branches to try when ref is main."""
        result = temp_gitops._get_branches_to_try("main")
        assert result == ["main", "master"]

    def test_get_branches_to_try_master(self, temp_gitops: GitOps) -> None:
        """Test branches to try when ref is master."""
        result = temp_gitops._get_branches_to_try("master")
        assert result == ["main", "master"]

    def test_get_branches_to_try_custom(self, temp_gitops: GitOps) -> None:
        """Test branches to try with custom ref."""
        result = temp_gitops._get_branches_to_try("feature-branch")
        assert result == ["feature-branch"]

    def test_get_license_not_cached(self, temp_gitops: GitOps) -> None:
        """Test getting license from non-existent repo."""
        license_text = temp_gitops.get_license("nonexistent")
        assert license_text is None

    def test_get_license_mit(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test extracting MIT license."""
        repo_path = temp_gitops.cache_dir / "test-repo"
        repo_path.mkdir(parents=True)

        license_file = repo_path / "LICENSE"
        license_file.write_text("MIT License\n\nCopyright (c) 2024 Test")

        license_text = temp_gitops.get_license("test-repo")
        assert license_text == "MIT License"

    def test_get_license_apache(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test extracting Apache license."""
        repo_path = temp_gitops.cache_dir / "test-repo"
        repo_path.mkdir(parents=True)

        license_file = repo_path / "LICENSE.md"
        license_file.write_text("Apache License 2.0\n\nSome more text")

        license_text = temp_gitops.get_license("test-repo")
        assert license_text == "Apache License 2.0"

    def test_get_license_long_first_line(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test extracting license with very long first line containing MIT."""
        repo_path = temp_gitops.cache_dir / "test-repo"
        repo_path.mkdir(parents=True)

        license_file = repo_path / "LICENSE.txt"
        long_line = "This is a very long license text that contains the word MIT but is longer than 100 characters and should be truncated"
        license_file.write_text(long_line)

        license_text = temp_gitops.get_license("test-repo")
        assert license_text == "MIT"

    def test_get_license_no_file(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test when no license file exists."""
        repo_path = temp_gitops.cache_dir / "test-repo"
        repo_path.mkdir(parents=True)

        license_text = temp_gitops.get_license("test-repo")
        assert license_text is None

    def test_get_license_empty_file(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test when license file is empty."""
        repo_path = temp_gitops.cache_dir / "test-repo"
        repo_path.mkdir(parents=True)

        license_file = repo_path / "LICENSE"
        license_file.write_text("")

        license_text = temp_gitops.get_license("test-repo")
        assert license_text is None

    def test_get_license_various_patterns(self, temp_gitops: GitOps, tmp_path: Path) -> None:
        """Test various license file patterns."""
        repo_path = temp_gitops.cache_dir / "test-repo"
        repo_path.mkdir(parents=True)

        # Test LICENCE (British spelling)
        license_file = repo_path / "LICENCE"
        license_file.write_text("BSD 3-Clause License")

        license_text = temp_gitops.get_license("test-repo")
        assert license_text == "BSD 3-Clause License"


class TestGitOpsError:
    """Tests for GitOpsError exception."""

    def test_gitops_error(self) -> None:
        """Test GitOpsError exception."""
        error = GitOpsError("Test error message")
        assert str(error) == "Test error message"
