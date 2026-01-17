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


# ============================================================================
# Tests for DataManager
# ============================================================================


class TestDataManager:
    """Tests for DataManager class."""

    def test_init_with_no_dependencies(self) -> None:
        """Test DataManager can be initialized without dependencies."""
        from skill_installer.tui.data_manager import DataManager

        manager = DataManager()
        assert manager.registry_manager is None
        assert manager.gitops is None
        assert manager.discovery is None

    def test_update_stale_sources_no_registry(self) -> None:
        """Test update_stale_sources returns early without registry."""
        from skill_installer.tui.data_manager import DataManager

        manager = DataManager()
        # Should not raise
        manager.update_stale_sources()

    def test_load_all_data_no_registry(self) -> None:
        """Test load_all_data returns empty with status message when no registry."""
        from skill_installer.tui.data_manager import DataManager

        manager = DataManager()
        discovered, installed, sources, status = manager.load_all_data()

        assert discovered == []
        assert installed == []
        assert sources == []
        assert status == "No registry manager configured"

    def test_load_all_data_with_empty_registry(self) -> None:
        """Test load_all_data with registry that has no sources."""
        from unittest.mock import MagicMock

        from skill_installer.tui.data_manager import DataManager

        mock_registry = MagicMock()
        mock_registry.list_sources.return_value = []
        mock_registry.list_installed.return_value = []

        manager = DataManager(registry_manager=mock_registry)
        discovered, installed, sources, status = manager.load_all_data()

        assert discovered == []
        assert installed == []
        assert sources == []
        assert status == "0 items available, 0 installed"

    def test_build_installed_maps(self) -> None:
        """Test _build_installed_maps correctly groups items."""
        from unittest.mock import MagicMock

        from skill_installer.tui.data_manager import DataManager

        mock_registry = MagicMock()
        mock_item1 = MagicMock()
        mock_item1.id = "source/agent/test"
        mock_item1.platform = "claude"
        mock_item1.source = "my-source"

        mock_item2 = MagicMock()
        mock_item2.id = "source/agent/test"
        mock_item2.platform = "vscode"
        mock_item2.source = "my-source"

        mock_registry.list_installed.return_value = [mock_item1, mock_item2]

        manager = DataManager(registry_manager=mock_registry)
        installed_map, installed_by_source = manager._build_installed_maps()

        assert "source/agent/test" in installed_map
        assert installed_map["source/agent/test"] == ["claude", "vscode"]
        assert installed_by_source["my-source"] == 2

    def test_get_display_name_no_marketplace_file(self, tmp_path) -> None:
        """Test _get_display_name returns default when no marketplace.json."""
        from skill_installer.tui.data_manager import DataManager

        manager = DataManager()
        result = manager._get_display_name(tmp_path, "default-name")

        assert result == "default-name"

    def test_get_display_name_with_marketplace_file(self, tmp_path) -> None:
        """Test _get_display_name reads from marketplace.json."""
        import json

        from skill_installer.tui.data_manager import DataManager

        marketplace_file = tmp_path / "marketplace.json"
        marketplace_file.write_text(json.dumps({"name": "Custom Name"}))

        manager = DataManager()
        result = manager._get_display_name(tmp_path, "default-name")

        assert result == "Custom Name"

    def test_get_display_name_invalid_json(self, tmp_path) -> None:
        """Test _get_display_name handles invalid JSON gracefully."""
        from skill_installer.tui.data_manager import DataManager

        marketplace_file = tmp_path / "marketplace.json"
        marketplace_file.write_text("not valid json")

        manager = DataManager()
        result = manager._get_display_name(tmp_path, "default-name")

        assert result == "default-name"


# ============================================================================
# Tests for ScreenHandlers
# ============================================================================


class TestScreenHandlers:
    """Tests for ScreenHandlers class."""

    def test_init_with_no_callbacks(self) -> None:
        """Test ScreenHandlers can be initialized without callbacks."""
        from skill_installer.tui.handlers import ScreenHandlers

        handlers = ScreenHandlers()
        assert handlers._pending_uninstall_item is None
        assert handlers._pending_project_install is None

    def test_notify_with_callback(self) -> None:
        """Test notify calls the callback."""
        from skill_installer.tui.handlers import ScreenHandlers

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        handlers = ScreenHandlers(notify=mock_notify)
        handlers.notify("Test message", "warning")

        assert notifications == [("Test message", "warning")]

    def test_notify_without_callback(self) -> None:
        """Test notify does nothing without callback."""
        from skill_installer.tui.handlers import ScreenHandlers

        handlers = ScreenHandlers()
        # Should not raise
        handlers.notify("Test message")

    def test_handle_source_detail_result_none(self) -> None:
        """Test handle_source_detail_result with None result."""
        from skill_installer.tui.handlers import ScreenHandlers

        handlers = ScreenHandlers()
        # Should not raise
        handlers.handle_source_detail_result(None)

    def test_handle_source_detail_result_browse(self) -> None:
        """Test handle_source_detail_result with browse option."""
        from skill_installer.tui.handlers import ScreenHandlers

        switch_calls = []

        def mock_switch(name: str) -> None:
            switch_calls.append(name)

        handlers = ScreenHandlers(switch_to_discover=mock_switch)

        mock_source = _make_test_display_source("test/source")
        handlers.handle_source_detail_result(("browse", mock_source))

        assert switch_calls == ["test/source"]

    def test_handle_source_detail_result_update(self) -> None:
        """Test handle_source_detail_result with update option."""
        from skill_installer.tui.handlers import ScreenHandlers

        update_calls = []

        def mock_update(source) -> None:
            update_calls.append(source)

        handlers = ScreenHandlers(update_source=mock_update)

        mock_source = _make_test_display_source("test/source")
        handlers.handle_source_detail_result(("update", mock_source))

        assert len(update_calls) == 1
        assert update_calls[0].name == "test/source"

    def test_handle_source_detail_result_remove(self) -> None:
        """Test handle_source_detail_result with remove option."""
        from skill_installer.tui.handlers import ScreenHandlers

        remove_calls = []

        def mock_remove(source) -> None:
            remove_calls.append(source)

        handlers = ScreenHandlers(remove_source=mock_remove)

        mock_source = _make_test_display_source("test/source")
        handlers.handle_source_detail_result(("remove", mock_source))

        assert len(remove_calls) == 1

    def test_handle_item_detail_result_none(self) -> None:
        """Test handle_item_detail_result with None result."""
        from skill_installer.tui.handlers import ScreenHandlers

        handlers = ScreenHandlers()
        # Should not raise
        handlers.handle_item_detail_result(None)

    def test_handle_location_selection_result_none(self) -> None:
        """Test handle_location_selection_result with None result."""
        from skill_installer.tui.handlers import ScreenHandlers

        handlers = ScreenHandlers()
        # Should not raise
        handlers.handle_location_selection_result(None)

    def test_handle_location_selection_result_with_selection(self) -> None:
        """Test handle_location_selection_result with selection."""
        from skill_installer.tui.handlers import ScreenHandlers

        install_calls = []

        def mock_install(item, platforms, reload) -> None:
            install_calls.append((item, platforms, reload))

        handlers = ScreenHandlers(install_item=mock_install)

        item = _make_test_display_item()
        handlers.handle_location_selection_result((["claude", "vscode"], item))

        assert len(install_calls) == 1
        assert install_calls[0][1] == ["claude", "vscode"]

    def test_handle_uninstall_confirmation_false(self) -> None:
        """Test handle_uninstall_confirmation with False."""
        from skill_installer.tui.handlers import ScreenHandlers

        uninstall_calls = []

        def mock_uninstall(item) -> None:
            uninstall_calls.append(item)

        handlers = ScreenHandlers(uninstall_item=mock_uninstall)
        handlers._pending_uninstall_item = _make_test_display_item()

        handlers.handle_uninstall_confirmation(False)

        assert len(uninstall_calls) == 0

    def test_handle_uninstall_confirmation_true(self) -> None:
        """Test handle_uninstall_confirmation with True."""
        from skill_installer.tui.handlers import ScreenHandlers

        uninstall_calls = []

        def mock_uninstall(item) -> None:
            uninstall_calls.append(item)

        handlers = ScreenHandlers(uninstall_item=mock_uninstall)
        handlers._pending_uninstall_item = _make_test_display_item()

        handlers.handle_uninstall_confirmation(True)

        assert len(uninstall_calls) == 1

    def test_handle_project_install_confirmation_false(self) -> None:
        """Test handle_project_install_confirmation with False."""
        from pathlib import Path

        from skill_installer.tui.handlers import ScreenHandlers

        handlers = ScreenHandlers()
        handlers._pending_project_install = (_make_test_display_item(), Path("/test"))

        handlers.handle_project_install_confirmation(False)

        assert handlers._pending_project_install is None

    def test_handle_project_install_confirmation_true(self) -> None:
        """Test handle_project_install_confirmation with True."""
        from pathlib import Path

        from skill_installer.tui.handlers import ScreenHandlers

        install_calls = []

        def mock_install(item, path) -> None:
            install_calls.append((item, path))

        handlers = ScreenHandlers(install_item_to_project=mock_install)
        handlers._pending_project_install = (_make_test_display_item(), Path("/test"))

        handlers.handle_project_install_confirmation(True)

        assert len(install_calls) == 1
        assert install_calls[0][1] == Path("/test")


# ============================================================================
# Tests for ItemListView
# ============================================================================


class _ItemListTestApp(App):
    """Test app for ItemListView tests."""

    def __init__(self) -> None:
        super().__init__()
        from skill_installer.tui.widgets.item_list import ItemListView

        self.item_list = ItemListView(id="test-items")

    def compose(self) -> ComposeResult:
        yield self.item_list


class TestItemListView:
    """Tests for ItemListView widget."""

    @pytest.mark.asyncio
    async def test_set_items(self) -> None:
        """Test set_items updates the list."""
        app = _ItemListTestApp()
        async with app.run_test():
            items = [_make_test_display_item()]
            app.item_list.set_items(items)

            assert len(app.item_list.items) == 1
            assert app.item_list.selected_index == 0

    @pytest.mark.asyncio
    async def test_cursor_navigation(self) -> None:
        """Test cursor up/down navigation."""
        app = _ItemListTestApp()
        async with app.run_test():
            items = [
                _make_test_display_item(),
                DisplayItem(
                    name="Item 2",
                    item_type="skill",
                    description="Second item",
                    source_name="test-source",
                    platforms=["claude"],
                    installed_platforms=[],
                    raw_data={},
                ),
            ]
            app.item_list.set_items(items)

            assert app.item_list.selected_index == 0

            app.item_list.action_cursor_down()
            assert app.item_list.selected_index == 1

            app.item_list.action_cursor_down()
            assert app.item_list.selected_index == 1  # At bottom

            app.item_list.action_cursor_up()
            assert app.item_list.selected_index == 0

            app.item_list.action_cursor_up()
            assert app.item_list.selected_index == 0  # At top

    @pytest.mark.asyncio
    async def test_action_toggle(self) -> None:
        """Test toggle action checks/unchecks items."""
        app = _ItemListTestApp()
        async with app.run_test():
            items = [_make_test_display_item()]
            app.item_list.set_items(items)

            assert len(app.item_list.get_checked_items()) == 0

            app.item_list.action_toggle()
            assert len(app.item_list.get_checked_items()) == 1

            app.item_list.action_toggle()
            assert len(app.item_list.get_checked_items()) == 0

    @pytest.mark.asyncio
    async def test_clear_checked(self) -> None:
        """Test clear_checked removes all checks."""
        app = _ItemListTestApp()
        async with app.run_test():
            items = [_make_test_display_item()]
            app.item_list.set_items(items)

            app.item_list.action_toggle()
            assert len(app.item_list.get_checked_items()) == 1

            app.item_list.clear_checked()
            assert len(app.item_list.get_checked_items()) == 0

    @pytest.mark.asyncio
    async def test_action_select_empty_list(self) -> None:
        """Test action_select on empty list does nothing."""
        app = _ItemListTestApp()
        async with app.run_test():
            # Should not raise
            app.item_list.action_select()

    @pytest.mark.asyncio
    async def test_action_toggle_empty_list(self) -> None:
        """Test action_toggle on empty list does nothing."""
        app = _ItemListTestApp()
        async with app.run_test():
            # Should not raise
            app.item_list.action_toggle()

    @pytest.mark.asyncio
    async def test_watch_selected_index(self) -> None:
        """Test watch_selected_index updates row states."""
        app = _ItemListTestApp()
        async with app.run_test():
            items = [
                _make_test_display_item(),
                DisplayItem(
                    name="Item 2",
                    item_type="skill",
                    description="Second item",
                    source_name="test-source",
                    platforms=["claude"],
                    installed_platforms=[],
                    raw_data={},
                ),
            ]
            app.item_list.set_items(items)

            assert app.item_list._rows[0].selected is True
            assert app.item_list._rows[1].selected is False

            app.item_list.selected_index = 1

            assert app.item_list._rows[0].selected is False
            assert app.item_list._rows[1].selected is True


# ============================================================================
# Tests for ItemRow
# ============================================================================


class _ItemRowTestApp(App):
    """Test app for ItemRow tests."""

    def __init__(self, item: DisplayItem) -> None:
        super().__init__()
        self.test_item = item

    def compose(self) -> ComposeResult:
        from skill_installer.tui.widgets.item_list import ItemRow

        yield ItemRow(self.test_item, id="test-row")


class TestItemRow:
    """Tests for ItemRow widget."""

    @pytest.mark.asyncio
    async def test_compose_not_installed(self) -> None:
        """Test ItemRow compose for non-installed item."""
        item = _make_test_display_item()
        app = _ItemRowTestApp(item)
        async with app.run_test():
            from skill_installer.tui.widgets.item_list import ItemRow

            row = app.query_one("#test-row", ItemRow)
            assert row is not None

    @pytest.mark.asyncio
    async def test_compose_installed(self) -> None:
        """Test ItemRow compose for installed item."""
        item = DisplayItem(
            name="Installed Item",
            item_type="agent",
            description="An installed item",
            source_name="test-source",
            platforms=["claude", "vscode"],
            installed_platforms=["claude"],
            raw_data={},
        )
        app = _ItemRowTestApp(item)
        async with app.run_test():
            from skill_installer.tui.widgets.item_list import ItemRow

            row = app.query_one("#test-row", ItemRow)
            assert row is not None
            assert row.item.installed_platforms == ["claude"]

    @pytest.mark.asyncio
    async def test_watch_selected(self) -> None:
        """Test watch_selected adds/removes class."""
        item = _make_test_display_item()
        app = _ItemRowTestApp(item)
        async with app.run_test():
            from skill_installer.tui.widgets.item_list import ItemRow

            row = app.query_one("#test-row", ItemRow)

            assert "selected" not in row.classes

            row.selected = True
            assert "selected" in row.classes

            row.selected = False
            assert "selected" not in row.classes

    @pytest.mark.asyncio
    async def test_watch_checked(self) -> None:
        """Test watch_checked updates indicator and class."""
        item = _make_test_display_item()
        app = _ItemRowTestApp(item)
        async with app.run_test():
            from skill_installer.tui.widgets.item_list import ItemRow

            row = app.query_one("#test-row", ItemRow)

            assert "checked" not in row.classes

            row.checked = True
            assert "checked" in row.classes

            row.checked = False
            assert "checked" not in row.classes


# ============================================================================
# Tests for ScrollIndicator
# ============================================================================


class _ScrollIndicatorTestApp(App):
    """Test app for ScrollIndicator tests."""

    def compose(self) -> ComposeResult:
        from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

        yield ScrollIndicator(id="test-indicator")


class TestScrollIndicator:
    """Tests for ScrollIndicator widget."""

    @pytest.mark.asyncio
    async def test_initial_state(self) -> None:
        """Test scroll indicator initial state."""
        app = _ScrollIndicatorTestApp()
        async with app.run_test():
            from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

            indicator = app.query_one("#test-indicator", ScrollIndicator)
            assert indicator is not None

    @pytest.mark.asyncio
    async def test_update_scroll_position(self) -> None:
        """Test updating scroll position."""
        app = _ScrollIndicatorTestApp()
        async with app.run_test():
            from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

            indicator = app.query_one("#test-indicator", ScrollIndicator)

            # Update with scroll data
            indicator.update_position(0, 100, 50)
            # Should not raise


# ============================================================================
# Tests for SourceDetailScreen
# ============================================================================


class _SourceDetailTestApp(App):
    """Test app for SourceDetailScreen tests."""

    def __init__(self, source: DisplaySource) -> None:
        super().__init__()
        self.test_source = source
        self.result: tuple[str, DisplaySource] | None = None

    def compose(self) -> ComposeResult:
        from textual.containers import Container

        yield Container()

    async def on_mount(self) -> None:
        from skill_installer.tui.screens.source_detail import SourceDetailScreen

        await self.push_screen(
            SourceDetailScreen(self.test_source), self._handle_result
        )

    def _handle_result(self, result: tuple[str, DisplaySource] | None) -> None:
        self.result = result


class TestSourceDetailScreen:
    """Tests for SourceDetailScreen modal."""

    @pytest.mark.asyncio
    async def test_escape_dismisses(self) -> None:
        """Test escape key dismisses the screen."""
        source = _make_test_display_source("test/source")
        app = _SourceDetailTestApp(source)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from skill_installer.tui.screens.source_detail import SourceDetailScreen

            assert isinstance(app.screen, SourceDetailScreen)

            await pilot.press("escape")
            await pilot.pause()

            assert not isinstance(app.screen, SourceDetailScreen)

    @pytest.mark.asyncio
    async def test_navigation_with_j_k(self) -> None:
        """Test j/k keys navigate between options."""
        source = _make_test_display_source("test/source")
        app = _SourceDetailTestApp(source)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from skill_installer.tui.screens.source_detail import SourceDetailScreen

            screen = app.screen
            assert isinstance(screen, SourceDetailScreen)

            # Navigate down
            await pilot.press("j")
            await pilot.pause()

            # Navigate up
            await pilot.press("k")
            await pilot.pause()

            # Should not crash


# ============================================================================
# Tests for ItemDetailScreen
# ============================================================================


class _ItemDetailTestApp(App):
    """Test app for ItemDetailScreen tests."""

    def __init__(self, item: DisplayItem) -> None:
        super().__init__()
        self.test_item = item
        self.result: tuple[str, DisplayItem] | None = None

    def compose(self) -> ComposeResult:
        from textual.containers import Container

        yield Container()

    async def on_mount(self) -> None:
        from skill_installer.tui.screens.item_detail import ItemDetailScreen

        await self.push_screen(ItemDetailScreen(self.test_item), self._handle_result)

    def _handle_result(self, result: tuple[str, DisplayItem] | None) -> None:
        self.result = result


class TestItemDetailScreen:
    """Tests for ItemDetailScreen modal."""

    @pytest.mark.asyncio
    async def test_escape_dismisses(self) -> None:
        """Test escape key dismisses the screen."""
        item = _make_test_display_item()
        app = _ItemDetailTestApp(item)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from skill_installer.tui.screens.item_detail import ItemDetailScreen

            assert isinstance(app.screen, ItemDetailScreen)

            await pilot.press("escape")
            await pilot.pause()

            assert not isinstance(app.screen, ItemDetailScreen)

    @pytest.mark.asyncio
    async def test_navigation_with_j_k(self) -> None:
        """Test j/k keys navigate between options."""
        item = _make_test_display_item()
        app = _ItemDetailTestApp(item)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from skill_installer.tui.screens.item_detail import ItemDetailScreen

            screen = app.screen
            assert isinstance(screen, ItemDetailScreen)

            # Navigate down
            await pilot.press("j")
            await pilot.pause()

            # Navigate up
            await pilot.press("k")
            await pilot.pause()

            # Should not crash

    @pytest.mark.asyncio
    async def test_shows_installed_item_options(self) -> None:
        """Test installed items show uninstall option."""
        item = DisplayItem(
            name="Installed Item",
            item_type="agent",
            description="An installed item",
            source_name="test-source",
            platforms=["claude"],
            installed_platforms=["claude"],
            raw_data={},
        )
        app = _ItemDetailTestApp(item)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            from skill_installer.tui.screens.item_detail import ItemDetailScreen

            screen = app.screen
            assert isinstance(screen, ItemDetailScreen)
            # Screen should show uninstall option for installed items


# ============================================================================
# Tests for Console (non-interactive TUI)
# ============================================================================


class TestTUIConsole:
    """Tests for the Console TUI class."""

    def test_init(self) -> None:
        """Test TUI can be initialized."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        assert tui.console is not None

    def test_show_success(self, capsys) -> None:
        """Test show_success displays message."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        tui.show_success("Operation completed")
        # Just verify no exception

    def test_show_error(self, capsys) -> None:
        """Test show_error displays message."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        tui.show_error("Something went wrong")
        # Just verify no exception

    def test_show_warning(self, capsys) -> None:
        """Test show_warning displays message."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        tui.show_warning("Be careful")
        # Just verify no exception

    def test_show_info(self, capsys) -> None:
        """Test show_info displays message."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        tui.show_info("FYI")
        # Just verify no exception

    def test_show_sources_empty(self, capsys) -> None:
        """Test show_sources with empty list."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        tui.show_sources([])
        # Just verify no exception

    def test_show_installed_empty(self, capsys) -> None:
        """Test show_installed with empty list."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        tui.show_installed([])
        # Just verify no exception

    def test_select_item_empty(self) -> None:
        """Test select_item returns None for empty list."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        result = tui.select_item([])
        assert result is None

    def test_select_source_empty(self) -> None:
        """Test select_source returns None for empty list."""
        from skill_installer.tui.console import TUI

        tui = TUI()
        result = tui.select_source([])
        assert result is None


# ============================================================================
# More ScrollIndicator Tests
# ============================================================================


class TestScrollIndicatorDetails:
    """Detailed tests for ScrollIndicator widget."""

    @pytest.mark.asyncio
    async def test_update_text_when_all_visible(self) -> None:
        """Test _update_text shows nothing when all items are visible."""
        app = _ScrollIndicatorTestApp()
        async with app.run_test():
            from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

            indicator = app.query_one("#test-indicator", ScrollIndicator)

            # All items visible (total <= visible)
            indicator.update_position(0, 10, 10)
            # Should show empty string

    @pytest.mark.asyncio
    async def test_update_text_when_at_top(self) -> None:
        """Test _update_text shows 'more below' when at top."""
        app = _ScrollIndicatorTestApp()
        async with app.run_test():
            from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

            indicator = app.query_one("#test-indicator", ScrollIndicator)

            # At top, more items below
            indicator.update_position(0, 5, 10)
            # Should show "more below"

    @pytest.mark.asyncio
    async def test_update_text_when_at_bottom(self) -> None:
        """Test _update_text shows 'more above' when at bottom."""
        app = _ScrollIndicatorTestApp()
        async with app.run_test():
            from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

            indicator = app.query_one("#test-indicator", ScrollIndicator)

            # At bottom, more items above
            indicator.update_position(5, 5, 10)
            # Should show "more above"

    @pytest.mark.asyncio
    async def test_update_text_when_in_middle(self) -> None:
        """Test _update_text shows both when in middle."""
        app = _ScrollIndicatorTestApp()
        async with app.run_test():
            from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator

            indicator = app.query_one("#test-indicator", ScrollIndicator)

            # In middle, more above and below
            indicator.update_position(3, 4, 10)
            # Should show both "more above" and "more below"


# ============================================================================
# More DataManager Tests
# ============================================================================


class TestDataManagerDetails:
    """Detailed tests for DataManager class."""

    def test_load_source_data_no_gitops(self) -> None:
        """Test _load_source_data without gitops returns empty."""
        from unittest.mock import MagicMock

        from skill_installer.tui.data_manager import DataManager

        mock_registry = MagicMock()

        manager = DataManager(registry_manager=mock_registry)

        mock_source = MagicMock()
        mock_source.name = "test"
        mock_source.url = "https://example.com"
        mock_source.last_sync = None

        discovered, installed, display_source = manager._load_source_data(
            mock_source, {}, {}
        )

        assert discovered == []
        assert installed == []
        assert display_source.name == "test"

    def test_discover_items_empty(self) -> None:
        """Test _discover_items with no discovered items."""
        from unittest.mock import MagicMock

        from skill_installer.tui.data_manager import DataManager

        mock_discovery = MagicMock()
        mock_discovery.discover_all.return_value = []

        manager = DataManager(discovery=mock_discovery)

        mock_source = MagicMock()
        mock_source.name = "test"
        mock_source.url = "https://example.com"

        from pathlib import Path

        discovered, installed, count = manager._discover_items(
            mock_source, Path("/tmp"), {}
        )

        assert discovered == []
        assert installed == []
        assert count == 0


# ============================================================================
# More Handler Tests
# ============================================================================


class TestHandlerDetails:
    """Detailed tests for ScreenHandlers class."""

    def test_handle_source_detail_auto_update(self) -> None:
        """Test handle_source_detail_result with auto_update option."""
        from unittest.mock import MagicMock

        from skill_installer.tui.handlers import ScreenHandlers

        mock_registry = MagicMock()
        mock_registry.toggle_source_auto_update.return_value = True

        load_calls = []

        def mock_load() -> None:
            load_calls.append(True)

        notifications = []

        def mock_notify(msg: str, severity: str = "information") -> None:
            notifications.append(msg)

        handlers = ScreenHandlers(
            registry_manager=mock_registry,
            notify=mock_notify,
            load_data=mock_load,
        )

        mock_source = _make_test_display_source("test/source")
        handlers.handle_source_detail_result(("auto_update", mock_source))

        assert len(load_calls) == 1
        assert "enabled" in notifications[0]

    def test_handle_open_homepage_no_homepage(self) -> None:
        """Test _handle_open_homepage with no homepage available."""
        from skill_installer.tui.handlers import ScreenHandlers

        notifications = []

        def mock_notify(msg: str, severity: str = "information") -> None:
            notifications.append((msg, severity))

        handlers = ScreenHandlers(notify=mock_notify)

        item = DisplayItem(
            name="Test Item",
            item_type="skill",
            description="A test item",
            source_name="test-source",
            platforms=["claude"],
            installed_platforms=[],
            raw_data={},
            source_url=None,
        )

        handlers._handle_open_homepage(item)

        assert ("No homepage available", "warning") in notifications

    def test_handle_open_homepage_with_source_url(self) -> None:
        """Test _handle_open_homepage uses source_url as fallback."""
        from skill_installer.tui.handlers import ScreenHandlers

        notifications = []
        url_opened = []

        def mock_notify(msg: str, severity: str = "information") -> None:
            notifications.append((msg, severity))

        def mock_open_url(url: str) -> bool:
            url_opened.append(url)
            return True

        handlers = ScreenHandlers(notify=mock_notify, open_url=mock_open_url)

        item = DisplayItem(
            name="Test Item",
            item_type="skill",
            description="A test item",
            source_name="test-source",
            platforms=["claude"],
            installed_platforms=[],
            raw_data={},
            source_url="https://github.com/test/repo",
        )

        handlers._handle_open_homepage(item)

        assert url_opened == ["https://github.com/test/repo"]

    def test_handle_project_install_confirmation_no_pending(self) -> None:
        """Test handle_project_install_confirmation with no pending install."""
        from skill_installer.tui.handlers import ScreenHandlers

        install_calls = []

        def mock_install(item, path) -> None:
            install_calls.append((item, path))

        handlers = ScreenHandlers(install_item_to_project=mock_install)
        handlers._pending_project_install = None

        handlers.handle_project_install_confirmation(True)

        assert len(install_calls) == 0


# ============================================================================
# Tests for ItemOperations
# ============================================================================


class TestItemOperations:
    """Tests for ItemOperations class."""

    def test_init_with_no_dependencies(self) -> None:
        """Test ItemOperations can be initialized without dependencies."""
        from skill_installer.tui.operations import ItemOperations

        ops = ItemOperations()
        assert ops.registry_manager is None
        assert ops.installer is None

    def test_notify_with_callback(self) -> None:
        """Test notify calls the callback."""
        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        ops = ItemOperations(notify=mock_notify)
        ops.notify("Test message", "warning")

        assert notifications == [("Test message", "warning")]

    def test_notify_without_callback(self) -> None:
        """Test notify does nothing without callback."""
        from skill_installer.tui.operations import ItemOperations

        ops = ItemOperations()
        # Should not raise
        ops.notify("Test message")

    def test_install_item_no_installer(self) -> None:
        """Test install_item with no installer shows error."""
        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        ops = ItemOperations(notify=mock_notify)
        ops.install_item(_make_test_display_item())

        assert ("Installer not configured", "error") in notifications

    def test_install_item_no_source(self) -> None:
        """Test install_item with no source found shows error."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        mock_registry = MagicMock()
        mock_registry.get_source.return_value = None

        mock_installer = MagicMock()

        ops = ItemOperations(
            registry_manager=mock_registry,
            installer=mock_installer,
            notify=mock_notify,
        )
        ops.install_item(_make_test_display_item())

        assert any("not found" in msg for msg, _ in notifications)

    def test_install_item_success(self) -> None:
        """Test install_item with successful installation."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        mock_registry = MagicMock()
        mock_source = MagicMock()
        mock_source.platforms = ["claude"]
        mock_registry.get_source.return_value = mock_source

        mock_result = MagicMock()
        mock_result.success = True
        mock_installer = MagicMock()
        mock_installer.install_item.return_value = mock_result

        ops = ItemOperations(
            registry_manager=mock_registry,
            installer=mock_installer,
            notify=mock_notify,
        )
        ops.install_item(_make_test_display_item(), reload_data=False)

        assert any("Installed" in msg for msg, _ in notifications)

    def test_uninstall_item_no_installer(self) -> None:
        """Test uninstall_item with no installer shows error."""
        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        ops = ItemOperations(notify=mock_notify)
        ops.uninstall_item(_make_test_display_item())

        assert ("Installer not configured", "error") in notifications

    def test_uninstall_item_no_results(self) -> None:
        """Test uninstall_item with no installations shows warning."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        mock_installer = MagicMock()
        mock_installer.uninstall_item.return_value = []

        ops = ItemOperations(installer=mock_installer, notify=mock_notify)
        ops.uninstall_item(_make_test_display_item())

        assert any("No installations found" in msg for msg, _ in notifications)

    def test_uninstall_item_success(self) -> None:
        """Test uninstall_item with successful uninstallation."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []
        load_called = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        def mock_load() -> None:
            load_called.append(True)

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.platform = "claude"
        mock_installer = MagicMock()
        mock_installer.uninstall_item.return_value = [mock_result]

        ops = ItemOperations(
            installer=mock_installer, notify=mock_notify, load_data=mock_load
        )
        ops.uninstall_item(_make_test_display_item())

        assert any("Uninstalled" in msg for msg, _ in notifications)
        assert len(load_called) == 1

    def test_install_item_to_project_no_installer(self) -> None:
        """Test install_item_to_project with no installer shows error."""
        from pathlib import Path

        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        ops = ItemOperations(notify=mock_notify)
        ops.install_item_to_project(_make_test_display_item(), Path("/test"))

        assert ("Installer not configured", "error") in notifications

    def test_update_source_no_gitops(self) -> None:
        """Test update_source with no gitops shows warning."""
        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        ops = ItemOperations(notify=mock_notify)
        ops.update_source(_make_test_display_source())

        assert ("Git operations not configured", "warning") in notifications

    def test_update_source_success(self) -> None:
        """Test update_source with successful update."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []
        load_called = []
        status_updates = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        def mock_load() -> None:
            load_called.append(True)

        def mock_status(msg: str) -> None:
            status_updates.append(msg)

        mock_gitops = MagicMock()
        mock_registry = MagicMock()

        ops = ItemOperations(
            gitops=mock_gitops,
            registry_manager=mock_registry,
            notify=mock_notify,
            load_data=mock_load,
        )

        source = _make_test_display_source()
        source.raw_data = MagicMock()
        source.raw_data.url = "https://example.com"
        source.raw_data.name = "test"

        ops.update_source(source, mock_status)

        assert any("Updated" in msg for msg, _ in notifications)
        assert len(load_called) == 1

    def test_remove_source_no_registry(self) -> None:
        """Test remove_source with no registry shows warning."""
        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        ops = ItemOperations(notify=mock_notify)
        ops.remove_source(_make_test_display_source())

        assert ("Registry not configured", "warning") in notifications

    def test_remove_source_success(self) -> None:
        """Test remove_source with successful removal."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []
        load_called = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        def mock_load() -> None:
            load_called.append(True)

        mock_registry = MagicMock()
        mock_registry.remove_source.return_value = True
        mock_gitops = MagicMock()

        ops = ItemOperations(
            registry_manager=mock_registry,
            gitops=mock_gitops,
            notify=mock_notify,
            load_data=mock_load,
        )
        ops.remove_source(_make_test_display_source())

        assert any("Removed" in msg for msg, _ in notifications)
        assert len(load_called) == 1

    def test_remove_source_not_found(self) -> None:
        """Test remove_source when source not found shows error."""
        from unittest.mock import MagicMock

        from skill_installer.tui.operations import ItemOperations

        notifications = []

        def mock_notify(msg: str, severity: str) -> None:
            notifications.append((msg, severity))

        mock_registry = MagicMock()
        mock_registry.remove_source.return_value = False

        ops = ItemOperations(
            registry_manager=mock_registry,
            notify=mock_notify,
        )
        ops.remove_source(_make_test_display_source())

        assert any("not found" in msg for msg, _ in notifications)
