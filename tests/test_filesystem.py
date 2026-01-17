"""Tests for filesystem abstraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_installer.filesystem import RealFileSystem


class TestRealFileSystem:
    """Tests for RealFileSystem implementation."""

    def test_read_text(self, tmp_path: Path) -> None:
        """Test reading text content from a file."""
        fs = RealFileSystem()
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        content = fs.read_text(test_file)

        assert content == "Hello, World!"

    def test_read_text_not_found(self, tmp_path: Path) -> None:
        """Test reading a non-existent file raises FileNotFoundError."""
        fs = RealFileSystem()
        test_file = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError):
            fs.read_text(test_file)

    def test_write_text(self, tmp_path: Path) -> None:
        """Test writing text content to a file."""
        fs = RealFileSystem()
        test_file = tmp_path / "output.txt"

        fs.write_text(test_file, "Test content")

        assert test_file.read_text() == "Test content"

    def test_exists_true(self, tmp_path: Path) -> None:
        """Test exists returns True for existing path."""
        fs = RealFileSystem()
        test_file = tmp_path / "exists.txt"
        test_file.touch()

        assert fs.exists(test_file) is True

    def test_exists_false(self, tmp_path: Path) -> None:
        """Test exists returns False for non-existent path."""
        fs = RealFileSystem()
        test_file = tmp_path / "missing.txt"

        assert fs.exists(test_file) is False

    def test_is_dir_true(self, tmp_path: Path) -> None:
        """Test is_dir returns True for directory."""
        fs = RealFileSystem()
        test_dir = tmp_path / "subdir"
        test_dir.mkdir()

        assert fs.is_dir(test_dir) is True

    def test_is_dir_false_for_file(self, tmp_path: Path) -> None:
        """Test is_dir returns False for file."""
        fs = RealFileSystem()
        test_file = tmp_path / "file.txt"
        test_file.touch()

        assert fs.is_dir(test_file) is False

    def test_is_dir_false_for_missing(self, tmp_path: Path) -> None:
        """Test is_dir returns False for non-existent path."""
        fs = RealFileSystem()
        test_path = tmp_path / "missing"

        assert fs.is_dir(test_path) is False

    def test_mkdir_simple(self, tmp_path: Path) -> None:
        """Test creating a simple directory."""
        fs = RealFileSystem()
        new_dir = tmp_path / "newdir"

        fs.mkdir(new_dir)

        assert new_dir.is_dir()

    def test_mkdir_parents(self, tmp_path: Path) -> None:
        """Test creating nested directories with parents=True."""
        fs = RealFileSystem()
        nested_dir = tmp_path / "a" / "b" / "c"

        fs.mkdir(nested_dir, parents=True)

        assert nested_dir.is_dir()

    def test_mkdir_exist_ok(self, tmp_path: Path) -> None:
        """Test mkdir with exist_ok=True doesn't raise for existing dir."""
        fs = RealFileSystem()
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # Should not raise
        fs.mkdir(existing_dir, exist_ok=True)

        assert existing_dir.is_dir()

    def test_mkdir_raises_without_exist_ok(self, tmp_path: Path) -> None:
        """Test mkdir raises FileExistsError without exist_ok."""
        fs = RealFileSystem()
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        with pytest.raises(FileExistsError):
            fs.mkdir(existing_dir, exist_ok=False)

    def test_unlink(self, tmp_path: Path) -> None:
        """Test removing a file."""
        fs = RealFileSystem()
        test_file = tmp_path / "to_delete.txt"
        test_file.touch()

        fs.unlink(test_file)

        assert not test_file.exists()

    def test_unlink_missing_raises(self, tmp_path: Path) -> None:
        """Test unlinking non-existent file raises FileNotFoundError."""
        fs = RealFileSystem()
        missing_file = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError):
            fs.unlink(missing_file)

    def test_rmtree(self, tmp_path: Path) -> None:
        """Test removing a directory tree."""
        fs = RealFileSystem()
        tree_dir = tmp_path / "tree"
        tree_dir.mkdir()
        (tree_dir / "file1.txt").touch()
        (tree_dir / "subdir").mkdir()
        (tree_dir / "subdir" / "file2.txt").touch()

        fs.rmtree(tree_dir)

        assert not tree_dir.exists()

    def test_copytree(self, tmp_path: Path) -> None:
        """Test copying a directory tree."""
        fs = RealFileSystem()
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        (src_dir / "file1.txt").write_text("content1")
        (src_dir / "subdir").mkdir()
        (src_dir / "subdir" / "file2.txt").write_text("content2")

        dst_dir = tmp_path / "destination"

        fs.copytree(src_dir, dst_dir)

        assert dst_dir.is_dir()
        assert (dst_dir / "file1.txt").read_text() == "content1"
        assert (dst_dir / "subdir" / "file2.txt").read_text() == "content2"
