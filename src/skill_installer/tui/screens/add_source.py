"""Add source modal screen."""

from __future__ import annotations

import re

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static


class AddSourceScreen(ModalScreen[str | None]):
    """Modal screen for adding a new marketplace source."""

    DEFAULT_CSS = """
    AddSourceScreen {
        align: center middle;
    }
    AddSourceScreen > Vertical {
        background: $surface;
        border: thick $primary;
        width: 70%;
        height: auto;
        max-height: 60%;
        padding: 1 2;
    }
    AddSourceScreen #add-source-title {
        text-style: bold;
        color: $text;
        padding: 1 2;
    }
    AddSourceScreen #add-source-examples {
        color: $text-muted;
        padding: 0 2 1 2;
    }
    AddSourceScreen #add-source-input {
        margin: 1 2;
    }
    AddSourceScreen #add-source-preview {
        color: $text-muted;
        padding: 0 2;
        height: 2;
    }
    AddSourceScreen #add-source-error {
        color: $error;
        padding: 0 2;
        height: 2;
    }
    AddSourceScreen #add-source-actions {
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    AddSourceScreen Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    # Pattern for owner/repo shorthand
    SHORTHAND_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Add Repository", id="add-source-title")
            yield Static(
                "Examples:\n"
                "  • owner/repo (GitHub)\n"
                "  • git@github.com:owner/repo.git (SSH)\n"
                "  • https://example.com/marketplace.json",
                id="add-source-examples",
            )
            yield Input(
                placeholder="Enter repository URL or owner/repo",
                id="add-source-input",
            )
            yield Static("", id="add-source-preview")
            yield Static("", id="add-source-error")
            with Vertical(id="add-source-actions"):
                yield Button("Add", id="add-source-confirm", variant="primary")
                yield Button("Cancel", id="add-source-cancel")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one("#add-source-input", Input).focus()

    @on(Input.Changed, "#add-source-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Update preview as user types."""
        value = event.value.strip()
        preview = self.query_one("#add-source-preview", Static)
        error = self.query_one("#add-source-error", Static)

        error.update("")

        if not value:
            preview.update("")
            return

        expanded = self._expand_url(value)
        if expanded != value:
            preview.update(f"→ {expanded}")
        else:
            preview.update("")

    def _expand_url(self, value: str) -> str:
        """Expand shorthand to full URL.

        Args:
            value: User input value.

        Returns:
            Expanded URL or original value.
        """
        if self.SHORTHAND_PATTERN.match(value):
            return f"https://github.com/{value}"
        return value

    def _validate_url(self, value: str) -> str | None:
        """Validate the URL.

        Args:
            value: URL to validate.

        Returns:
            Error message if invalid, None if valid.
        """
        if not value:
            return "Please enter a repository URL"

        # Check for common patterns
        if value.startswith("https://"):
            return None
        if value.startswith("http://"):
            return "Insecure URL. Use https://"
        if value.startswith("git@") and ":" in value:
            return None
        if self.SHORTHAND_PATTERN.match(value):
            return None

        return "Invalid URL format. Use owner/repo, SSH, or HTTPS URL."

    @on(Button.Pressed, "#add-source-confirm")
    def on_confirm_pressed(self) -> None:
        """Handle confirm button press."""
        self._submit()

    @on(Button.Pressed, "#add-source-cancel")
    def on_cancel_pressed(self) -> None:
        """Handle cancel button press."""
        self.dismiss(None)

    @on(Input.Submitted, "#add-source-input")
    def on_input_submitted(self) -> None:
        """Handle Enter key in input."""
        self._submit()

    def _submit(self) -> None:
        """Validate and submit the URL."""
        input_widget = self.query_one("#add-source-input", Input)
        value = input_widget.value.strip()
        error_widget = self.query_one("#add-source-error", Static)

        validation_error = self._validate_url(value)
        if validation_error:
            error_widget.update(f"⚠ {validation_error}")
            return

        expanded = self._expand_url(value)
        self.dismiss(expanded)

    def action_cancel(self) -> None:
        """Cancel and close the modal."""
        self.dismiss(None)
