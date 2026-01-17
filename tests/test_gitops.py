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


class TestGitOpsError:
    """Tests for GitOpsError exception."""

    def test_gitops_error(self) -> None:
        """Test GitOpsError exception."""
        error = GitOpsError("Test error message")
        assert str(error) == "Test error message"
