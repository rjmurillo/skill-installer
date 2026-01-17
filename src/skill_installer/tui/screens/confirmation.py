"""Confirmation modal screen."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmationScreen(ModalScreen[bool]):
    """Modal screen for confirming destructive actions."""

    DEFAULT_CSS = """
    ConfirmationScreen {
        align: center middle;
    }
    ConfirmationScreen > Vertical {
        background: $surface;
        border: thick $primary;
        width: 60%;
        height: auto;
        max-height: 50%;
        padding: 1 2;
    }
    ConfirmationScreen #confirm-title {
        text-style: bold;
        color: $text;
        padding: 1 2;
    }
    ConfirmationScreen #confirm-message {
        color: $text-muted;
        padding: 1 2;
    }
    ConfirmationScreen #confirm-actions {
        height: auto;
        padding: 1 2;
        align: center middle;
    }
    ConfirmationScreen Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.message_text = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.title_text, id="confirm-title")
            yield Static(self.message_text, id="confirm-message")
            with Horizontal(id="confirm-actions"):
                yield Button("Yes (y)", id="confirm-yes", variant="error")
                yield Button("No (n)", id="confirm-no", variant="primary")

    @on(Button.Pressed, "#confirm-yes")
    def on_confirm_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def on_confirm_no(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
