"""CSS styles for the Skill Installer TUI."""

APP_CSS = """
Screen {
    background: $surface;
}

#app-title {
    dock: top;
    height: 3;
    padding: 1 2;
    background: $primary-background;
    text-style: bold;
    color: $text;
}

TabbedContent {
    height: 1fr;
}

TabPane {
    padding: 1;
}

Footer {
    background: $primary-background;
}

#status-bar {
    dock: bottom;
    height: 1;
    padding: 0 2;
    background: $primary-background;
    color: $text-muted;
}
"""
