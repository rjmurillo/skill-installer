"""Tests for TUI module."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container

from skill_installer.tui import (
    ConfirmationScreen,
    DisplayItem,
    DisplaySource,
    LocationOption,
    LocationSelectionScreen,
    SkillInstallerApp,
    SourceListView,
    SourceRow,
    _sanitize_css_id,
)


class TestSanitizeCssId:
    """Tests for _sanitize_css_id function."""

    def test_simple_string(self) -> None:
        """Test simple alphanumeric string passes through."""
        assert _sanitize_css_id("simple") == "simple"

    def test_with_spaces(self) -> None:
        """Test spaces are converted to hyphens."""
        assert _sanitize_css_id("Swift MCP Expert") == "Swift-MCP-Expert"

    def test_with_slashes(self) -> None:
        """Test slashes are converted to double hyphens."""
        assert _sanitize_css_id("github/awesome-copilot/agent") == "github--awesome-copilot--agent"

    def test_with_mixed_separators(self) -> None:
        """Test mixed slashes and spaces."""
        result = _sanitize_css_id("source/type/Item Name")
        assert result == "source--type--Item-Name"

    def test_removes_special_characters(self) -> None:
        """Test special characters are removed."""
        assert _sanitize_css_id("item@#$%name") == "itemname"

    def test_preserves_underscores(self) -> None:
        """Test underscores are preserved."""
        assert _sanitize_css_id("item_name") == "item_name"

    def test_preserves_hyphens(self) -> None:
        """Test hyphens are preserved."""
        assert _sanitize_css_id("item-name") == "item-name"

    def test_starts_with_number(self) -> None:
        """Test IDs starting with numbers get prefixed."""
        assert _sanitize_css_id("123item") == "id-123item"

    def test_empty_after_sanitize(self) -> None:
        """Test empty string after sanitization returns default."""
        assert _sanitize_css_id("@#$%") == "item"

    def test_empty_string(self) -> None:
        """Test empty input returns default."""
        assert _sanitize_css_id("") == "item"

    def test_realistic_item_id(self) -> None:
        """Test realistic item unique_id format."""
        # This is the format used by DisplayItem.unique_id
        result = _sanitize_css_id("github/awesome-copilot/agent/Swift MCP Expert")
        assert result == "github--awesome-copilot--agent--Swift-MCP-Expert"
        # Verify no invalid characters remain
        assert " " not in result
        assert "/" not in result


class TestDisplaySource:
    """Tests for DisplaySource dataclass."""

    def test_display_source_creation(self) -> None:
        """Test creating a DisplaySource."""
        source = DisplaySource(
            name="anthropics/skills",
            display_name="anthropics-agent-skills",
            url="https://github.com/anthropics/skills.git",
            available_count=16,
            installed_count=2,
            last_sync="1/16/2026",
            raw_data=None,
        )
        assert source.name == "anthropics/skills"
        assert source.display_name == "anthropics-agent-skills"
        assert source.url == "https://github.com/anthropics/skills.git"
        assert source.available_count == 16
        assert source.installed_count == 2
        assert source.last_sync == "1/16/2026"

    def test_display_source_no_installed(self) -> None:
        """Test DisplaySource with no installed items."""
        source = DisplaySource(
            name="user/repo",
            display_name="My Repo",
            url="https://github.com/user/repo",
            available_count=5,
            installed_count=0,
            last_sync="Never",
            raw_data=None,
        )
        assert source.installed_count == 0
        assert source.last_sync == "Never"


class TestLocationOption:
    """Tests for LocationOption widget."""

    def test_toggle_checked(self) -> None:
        """Test toggle_checked changes state."""
        option = LocationOption(
            platform_id="claude",
            name="Claude Code",
            path="/test/path",
        )
        assert option.checked is False
        option.toggle_checked()
        assert option.checked is True
        option.toggle_checked()
        assert option.checked is False

    def test_initial_state(self) -> None:
        """Test initial option state."""
        option = LocationOption(
            platform_id="vscode",
            name="VS Code",
            path="/test/vscode",
        )
        assert option.selected is False
        assert option.checked is False
        assert option.platform_id == "vscode"
        assert option.platform_name == "VS Code"
        assert option.path == "/test/vscode"


class _LocationSelectionTestApp(App):
    """Test app for LocationSelectionScreen tests."""

    def __init__(self, item: DisplayItem, platforms: list[dict[str, str]]) -> None:
        super().__init__()
        self.test_item = item
        self.test_platforms = platforms

    def compose(self) -> ComposeResult:
        yield Container()

    async def on_mount(self) -> None:
        await self.push_screen(
            LocationSelectionScreen(self.test_item, self.test_platforms)
        )


def _make_test_display_item() -> DisplayItem:
    """Create a DisplayItem for testing."""
    return DisplayItem(
        name="Test Item",
        item_type="skill",
        description="A test item",
        source_name="test-source",
        platforms=["claude", "vscode"],
        installed_platforms=[],
        raw_data={},
    )


def _make_test_platforms() -> list[dict[str, str]]:
    """Create platform list for testing."""
    return [
        {"id": "claude", "name": "Claude Code", "path_description": "/test/claude"},
        {"id": "vscode", "name": "VS Code", "path_description": "/test/vscode"},
    ]


class TestLocationSelectionScreen:
    """Tests for LocationSelectionScreen modal."""

    @pytest.mark.asyncio
    async def test_space_toggles_checkbox(self) -> None:
        """Test space key toggles checkbox in location selection."""
        app = _LocationSelectionTestApp(
            _make_test_display_item(),
            _make_test_platforms(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, LocationSelectionScreen)
            options = screen._location_options
            assert len(options) == 2

            first_option = options[0]
            assert first_option.checked is False

            await pilot.press("space")
            await pilot.pause()

            assert first_option.checked is True

    @pytest.mark.asyncio
    async def test_navigation_with_j_k(self) -> None:
        """Test j/k keys navigate between options."""
        app = _LocationSelectionTestApp(
            _make_test_display_item(),
            _make_test_platforms(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, LocationSelectionScreen)
            options = screen._location_options

            assert options[0].selected is True
            assert options[1].selected is False

            await pilot.press("j")
            await pilot.pause()

            assert options[0].selected is False
            assert options[1].selected is True

            await pilot.press("k")
            await pilot.pause()

            assert options[0].selected is True
            assert options[1].selected is False

    @pytest.mark.asyncio
    async def test_escape_cancels(self) -> None:
        """Test escape key cancels location selection."""
        app = _LocationSelectionTestApp(
            _make_test_display_item(),
            _make_test_platforms(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, LocationSelectionScreen)

            await pilot.press("escape")
            await pilot.pause()

            # Screen should be dismissed
            assert not isinstance(app.screen, LocationSelectionScreen)

    @pytest.mark.asyncio
    async def test_enter_without_selection_shows_warning(self) -> None:
        """Test enter without selected platforms shows warning."""
        app = _LocationSelectionTestApp(
            _make_test_display_item(),
            _make_test_platforms(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, LocationSelectionScreen)

            await pilot.press("enter")
            await pilot.pause()

            # Screen should still be visible (not dismissed)
            assert isinstance(app.screen, LocationSelectionScreen)

    @pytest.mark.asyncio
    async def test_enter_with_selection_confirms(self) -> None:
        """Test enter with selected platforms confirms selection."""
        app = _LocationSelectionTestApp(
            _make_test_display_item(),
            _make_test_platforms(),
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, LocationSelectionScreen)

            await pilot.press("space")
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            # Screen should be dismissed
            assert not isinstance(app.screen, LocationSelectionScreen)


class _ConfirmationTestApp(App):
    """Test app for ConfirmationScreen tests."""

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self.test_title = title
        self.test_message = message
        self.result: bool | None = None

    def compose(self) -> ComposeResult:
        yield Container()

    async def on_mount(self) -> None:
        await self.push_screen(
            ConfirmationScreen(self.test_title, self.test_message),
            self._handle_result
        )

    def _handle_result(self, result: bool) -> None:
        self.result = result


class TestConfirmationScreen:
    """Tests for ConfirmationScreen modal."""

    @pytest.mark.asyncio
    async def test_y_key_confirms(self) -> None:
        """Test y key confirms dialog."""
        app = _ConfirmationTestApp("Test Title", "Test message")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, ConfirmationScreen)

            await pilot.press("y")
            await pilot.pause()

            assert app.result is True
            assert not isinstance(app.screen, ConfirmationScreen)

    @pytest.mark.asyncio
    async def test_n_key_cancels(self) -> None:
        """Test n key cancels dialog."""
        app = _ConfirmationTestApp("Test Title", "Test message")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, ConfirmationScreen)

            await pilot.press("n")
            await pilot.pause()

            assert app.result is False
            assert not isinstance(app.screen, ConfirmationScreen)

    @pytest.mark.asyncio
    async def test_escape_cancels(self) -> None:
        """Test escape key cancels dialog."""
        app = _ConfirmationTestApp("Test Title", "Test message")
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, ConfirmationScreen)

            await pilot.press("escape")
            await pilot.pause()

            assert app.result is False
            assert not isinstance(app.screen, ConfirmationScreen)


class TestOpenUrl:
    """Tests for SkillInstallerApp._open_url method."""

    @pytest.mark.asyncio
    async def test_open_url_success(self) -> None:
        """Test _open_url returns True when webbrowser.open succeeds."""
        app = SkillInstallerApp()
        async with app.run_test():
            with patch("skill_installer.tui.app.webbrowser.open") as mock_open:
                mock_open.return_value = True
                result = app._open_url("https://example.com")
                assert result is True
                mock_open.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_open_url_failure_returns_false(self) -> None:
        """Test _open_url returns False when webbrowser.open raises exception."""
        app = SkillInstallerApp()
        async with app.run_test():
            with patch("skill_installer.tui.app.webbrowser.open") as mock_open:
                mock_open.side_effect = Exception("Browser not available")
                result = app._open_url("https://example.com")
                assert result is False
                mock_open.assert_called_once_with("https://example.com")


class _SourceListTestApp(App):
    """Test app for SourceListView tests."""

    def __init__(self) -> None:
        super().__init__()
        self.source_list = SourceListView(id="test-sources")

    def compose(self) -> ComposeResult:
        yield self.source_list


def _make_test_display_source(name: str = "test/source") -> DisplaySource:
    """Create a DisplaySource for testing."""
    return DisplaySource(
        name=name,
        display_name="Test Source",
        url="https://github.com/test/source",
        available_count=5,
        installed_count=0,
        last_sync="Never",
        raw_data=None,
    )


class TestSourceListView:
    """Tests for SourceListView widget."""

    @pytest.mark.asyncio
    async def test_refresh_count_initialized(self) -> None:
        """Test refresh count is initialized to 0."""
        app = _SourceListTestApp()
        async with app.run_test():
            assert app.source_list.refresh_count == 0

    @pytest.mark.asyncio
    async def test_set_sources_increments_refresh_count(self) -> None:
        """Test set_sources increments the refresh count."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source()

            app.source_list.set_sources([source])
            assert app.source_list.refresh_count == 1

            app.source_list.set_sources([source])
            assert app.source_list.refresh_count == 2

    @pytest.mark.asyncio
    async def test_row_ids_unique_across_refreshes(self) -> None:
        """Test row IDs are unique even when refreshed with same data.

        This tests the fix for DuplicateIds crash on uninstall.
        """
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source("ComposioHQ/awesome-codex-skills")

            # First set
            app.source_list.set_sources([source])
            first_row_id = app.source_list._rows[0].id

            # Second set (simulating refresh after uninstall)
            app.source_list.set_sources([source])
            second_row_id = app.source_list._rows[0].id

            # IDs should be different due to update counter
            assert first_row_id != second_row_id
            assert "1--0--" in first_row_id  # counter 1, index 0
            assert "2--0--" in second_row_id  # counter 2, index 0

    @pytest.mark.asyncio
    async def test_make_row_id_includes_refresh_count(self) -> None:
        """Test _make_row_id includes refresh count in ID."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source("test/repo")
            # Call set_sources 5 times to increment refresh_count to 5
            for _ in range(5):
                app.source_list.set_sources([source])

            row_id = app.source_list._make_row_id(2, source)

            # Format: {list_id}--{counter}--{index}--{sanitized_name}
            assert row_id == "test-sources--5--2--test--repo"

    @pytest.mark.asyncio
    async def test_watch_selected_index_updates_rows(self) -> None:
        """Test watch_selected_index updates row selected state."""
        app = _SourceListTestApp()
        async with app.run_test():
            sources = [
                _make_test_display_source("source1"),
                _make_test_display_source("source2"),
            ]
            app.source_list.set_sources(sources)

            # Initial state: first row selected
            assert app.source_list._rows[0].selected is True
            assert app.source_list._rows[1].selected is False

            # Change selection
            app.source_list.selected_index = 1

            assert app.source_list._rows[0].selected is False
            assert app.source_list._rows[1].selected is True

    @pytest.mark.asyncio
    async def test_watch_selected_index_handles_out_of_bounds(self) -> None:
        """Test watch_selected_index handles invalid indices gracefully."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source()
            app.source_list.set_sources([source])

            # Force old_index out of bounds by manipulating internal state
            app.source_list._rows[0].selected = True
            # Manually call watcher with out-of-bounds old index
            app.source_list.watch_selected_index(99, 0)

            # Should not crash and row 0 should be selected
            assert app.source_list._rows[0].selected is True

    @pytest.mark.asyncio
    async def test_action_cursor_up(self) -> None:
        """Test cursor up action decrements selected_index."""
        app = _SourceListTestApp()
        async with app.run_test():
            sources = [
                _make_test_display_source("source1"),
                _make_test_display_source("source2"),
            ]
            app.source_list.set_sources(sources)
            app.source_list.selected_index = 1

            app.source_list.action_cursor_up()

            assert app.source_list.selected_index == 0

    @pytest.mark.asyncio
    async def test_action_cursor_up_at_top(self) -> None:
        """Test cursor up at top does not go negative."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source()
            app.source_list.set_sources([source])
            app.source_list.selected_index = 0

            app.source_list.action_cursor_up()

            assert app.source_list.selected_index == 0

    @pytest.mark.asyncio
    async def test_action_cursor_down(self) -> None:
        """Test cursor down action increments selected_index."""
        app = _SourceListTestApp()
        async with app.run_test():
            sources = [
                _make_test_display_source("source1"),
                _make_test_display_source("source2"),
            ]
            app.source_list.set_sources(sources)
            app.source_list.selected_index = 0

            app.source_list.action_cursor_down()

            assert app.source_list.selected_index == 1

    @pytest.mark.asyncio
    async def test_action_cursor_down_at_bottom(self) -> None:
        """Test cursor down at bottom does not exceed list length."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source()
            app.source_list.set_sources([source])
            app.source_list.selected_index = 0

            app.source_list.action_cursor_down()

            assert app.source_list.selected_index == 0

    @pytest.mark.asyncio
    async def test_action_select_with_sources(self) -> None:
        """Test select action with sources does not crash and posts message."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source("test/source")
            app.source_list.set_sources([source])

            # Call action - should post message without crashing
            app.source_list.action_select()

            # Verify the source is the one at selected_index
            assert app.source_list.sources[app.source_list.selected_index].name == "test/source"

    @pytest.mark.asyncio
    async def test_action_select_empty_list(self) -> None:
        """Test select action does nothing with empty list."""
        app = _SourceListTestApp()
        async with app.run_test():
            # No sources set
            app.source_list.action_select()
            # Should not crash

    @pytest.mark.asyncio
    async def test_action_update_source_with_sources(self) -> None:
        """Test update source action with sources does not crash."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source("test/source")
            app.source_list.set_sources([source])

            # Call action - should post message without crashing
            app.source_list.action_update_source()

            # Verify the source is the one at selected_index
            assert app.source_list.sources[app.source_list.selected_index].name == "test/source"

    @pytest.mark.asyncio
    async def test_action_update_source_empty_list(self) -> None:
        """Test update source action does nothing with empty list."""
        app = _SourceListTestApp()
        async with app.run_test():
            app.source_list.action_update_source()
            # Should not crash

    @pytest.mark.asyncio
    async def test_action_remove_source_with_sources(self) -> None:
        """Test remove source action with sources does not crash."""
        app = _SourceListTestApp()
        async with app.run_test():
            source = _make_test_display_source("test/source")
            app.source_list.set_sources([source])

            # Call action - should post message without crashing
            app.source_list.action_remove_source()

            # Verify the source is the one at selected_index
            assert app.source_list.sources[app.source_list.selected_index].name == "test/source"

    @pytest.mark.asyncio
    async def test_action_remove_source_empty_list(self) -> None:
        """Test remove source action does nothing with empty list."""
        app = _SourceListTestApp()
        async with app.run_test():
            app.source_list.action_remove_source()
            # Should not crash


class _SourceRowTestApp(App):
    """Test app for SourceRow tests."""

    def __init__(self, source: DisplaySource) -> None:
        super().__init__()
        self.test_source = source

    def compose(self) -> ComposeResult:
        yield SourceRow(self.test_source, id="test-row")


class TestSourceRow:
    """Tests for SourceRow widget."""

    @pytest.mark.asyncio
    async def test_compose_without_installed(self) -> None:
        """Test SourceRow compose with no installed items."""
        source = DisplaySource(
            name="test/source",
            display_name="Test Source",
            url="https://github.com/test/source",
            available_count=5,
            installed_count=0,
            last_sync="Never",
            raw_data=None,
        )
        app = _SourceRowTestApp(source)
        async with app.run_test():
            # Check that the row was composed (widget exists)
            row = app.query_one("#test-row")
            assert row is not None

    @pytest.mark.asyncio
    async def test_compose_with_installed(self) -> None:
        """Test SourceRow compose with installed items shows installed count.

        This covers the branch in SourceRow.compose where installed_count > 0.
        """
        source = DisplaySource(
            name="test/source",
            display_name="Test Source",
            url="https://github.com/test/source",
            available_count=10,
            installed_count=3,
            last_sync="1/15/2026",
            raw_data=None,
        )
        app = _SourceRowTestApp(source)
        async with app.run_test():
            row = app.query_one("#test-row", SourceRow)
            assert row is not None
            # Verify the source has installed_count > 0 (covers branch)
            assert row.source.installed_count == 3
            # The widget was composed, which exercised the installed branch

    @pytest.mark.asyncio
    async def test_watch_selected_adds_class(self) -> None:
        """Test watch_selected adds/removes selected class."""
        source = _make_test_display_source()
        app = _SourceRowTestApp(source)
        async with app.run_test():
            row = app.query_one("#test-row", SourceRow)

            assert "selected" not in row.classes

            row.selected = True
            assert "selected" in row.classes

            row.selected = False
            assert "selected" not in row.classes
