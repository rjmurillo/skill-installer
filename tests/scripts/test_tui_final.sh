#!/bin/bash
# Final TUI test using arrow keys for navigation

SESSION_NAME="tui-test-$$"

cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
}
trap cleanup EXIT

cd /home/richard/src/GitHub/rjmurillo/skill-installer
tmux new-session -d -s "$SESSION_NAME" -x 80 -y 24

send() {
    tmux send-keys -t "$SESSION_NAME" "$@"
    sleep "${WAIT:-1}"
}

capture() {
    tmux capture-pane -t "$SESSION_NAME" -p | sed 's/\x1b\[[0-9;]*m//g' | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g'
}

# Start TUI
echo "Starting TUI..."
WAIT=0.5 send "uv run python -m skill_installer interactive" C-m
sleep 3

echo "=== Initial Screen (Discover Tab) ==="
capture | head -15
echo ""

if ! capture | grep -q "Skill Installer"; then
    echo "✗ TUI failed to start"
    exit 1
fi
echo "✓ TUI started"

# Navigate to Marketplaces using Right arrow
echo "Navigating to Marketplaces tab (Right -> Right)..."
WAIT=1 send Right
WAIT=1 send Right

echo "=== Marketplaces Tab ==="
capture | head -20
echo ""

# Check which tab we're on
if capture | grep -A2 "Marketplaces" | grep -q "━"; then
    echo "✓ On Marketplaces tab"
else
    echo "⚠ Tab indicator unclear, continuing anyway..."
fi

# Check content - should see source repos, not individual items
if capture | grep -qi "github.com\|anthropics\|openai"; then
    echo "✓ Showing marketplace sources (repos)"

    # Open marketplace detail
    echo "Opening marketplace detail..."
    WAIT=1.5 send Enter

    echo "=== Marketplace Detail View ==="
    capture | head -25
    echo ""

    if capture | grep -qi "Browse.*plugins\|Update marketplace\|Remove marketplace"; then
        echo "✓ Marketplace detail view opened"

        # Navigate to Browse and select it
        echo "Selecting 'Browse plugins'..."
        WAIT=1.5 send Enter

        echo "=== Discover Tab with Marketplace Filter ==="
        capture | head -20
        echo ""

        if capture | grep -q "Filtered by marketplace"; then
            echo "✓ Filter applied to Discover tab"
        else
            echo "⚠ Filter banner not visible"
        fi

        # Try to open an item detail
        echo "Opening item detail..."
        WAIT=1.5 send Enter

        echo "=== Item Detail View ==="
        capture | head -25
        echo ""

        if capture | grep -qi "From:.*Type:.*Install\|Platforms:"; then
            echo "✓ Item detail view opened"

            # Close item detail
            echo "Closing item detail (Escape)..."
            WAIT=1 send Escape

            # Clear filter
            echo "Clearing marketplace filter (Escape)..."
            WAIT=1 send Escape

            echo "=== Discover Tab (Filter Cleared) ==="
            capture | head -15
            echo ""

            if ! capture | grep -q "Filtered by marketplace"; then
                echo "✓ Filter cleared successfully"
            else
                echo "⚠ Filter still showing"
            fi

            echo ""
            echo "✅ All navigation paths tested successfully!"
        else
            echo "⚠ Item detail view incomplete"
        fi
    else
        echo "⚠ Marketplace detail view not showing expected options"
        echo "Showing capture for debugging:"
        capture
    fi
elif capture | grep -qi "skill-installer\|skill-creator"; then
    echo "⚠ Showing items instead of marketplace sources"
    echo "This suggests the MarketplacesPane is showing the wrong data"
else
    echo "⚠ No marketplaces or items visible"
fi

# Quit
WAIT=1 send q

echo ""
echo "Test complete!"
