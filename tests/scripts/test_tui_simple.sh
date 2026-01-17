#!/bin/bash
# Simplified TUI test using tmux

set -e

SESSION_NAME="tui-test-$$"

# Cleanup on exit
cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
}
trap cleanup EXIT

echo "Creating tmux session..."
cd /home/richard/src/GitHub/rjmurillo/skill-installer
tmux new-session -d -s "$SESSION_NAME" -x 80 -y 24

# Helper to send keys
send() {
    tmux send-keys -t "$SESSION_NAME" "$@"
    sleep "${WAIT:-1}"
}

# Helper to capture screen (strip ANSI codes for readability)
capture() {
    tmux capture-pane -t "$SESSION_NAME" -p | sed 's/\x1b\[[0-9;]*m//g' | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g'
}

# Start TUI
echo "Starting TUI..."
WAIT=0.5 send "uv run python -m skill_installer interactive" C-m
sleep 3

echo ""
echo "=== Initial Screen ==="
capture
echo ""

# Check if started
if capture | grep -q "Skill Installer"; then
    echo "✓ TUI started"
else
    echo "✗ TUI failed to start"
    exit 1
fi

# Navigate to Marketplaces
echo "Navigating to Marketplaces tab..."
WAIT=1 send Tab
WAIT=1 send Tab

echo ""
echo "=== Marketplaces Tab ==="
capture
echo ""

if capture | grep -q "Marketplaces"; then
    echo "✓ On Marketplaces tab"

    # Check if there's a marketplace
    if capture | grep -qi "anthropic\|openai\|skills\|github"; then
        echo "✓ Marketplaces visible"

        # Open marketplace detail
        echo "Opening marketplace detail..."
        WAIT=1.5 send Enter

        echo ""
        echo "=== Marketplace Detail ==="
        capture
        echo ""

        if capture | grep -q "Browse\|Update\|Remove"; then
            echo "✓ Marketplace detail opened"

            # Select Browse
            echo "Selecting Browse..."
            WAIT=1.5 send Enter

            echo ""
            echo "=== Discover Tab with Filter ==="
            capture
            echo ""

            if capture | grep -q "Filtered by marketplace"; then
                echo "✓ Filter applied"
            else
                echo "⚠ Filter banner not found"
            fi

            # Open item detail
            echo "Opening item detail..."
            WAIT=1.5 send Enter

            echo ""
            echo "=== Item Detail ==="
            capture
            echo ""

            if capture | grep -q "From:\|Type:\|Install"; then
                echo "✓ Item detail opened"

                # Close with Escape
                echo "Closing item detail..."
                WAIT=1 send Escape

                echo ""
                echo "=== After Item Detail Close ==="
                capture
                echo ""

                # Clear filter
                echo "Clearing filter..."
                WAIT=1 send Escape

                echo ""
                echo "=== After Filter Clear ==="
                capture
                echo ""

                if ! capture | grep -q "Filtered by marketplace"; then
                    echo "✓ Filter cleared"
                else
                    echo "⚠ Filter still visible"
                fi
            else
                echo "⚠ Item detail didn't show properly"
            fi
        else
            echo "⚠ Marketplace detail didn't show"
        fi
    else
        echo "⚠ No marketplaces found"
        echo "Add a marketplace first: uv run python -m skill_installer source add https://github.com/anthropics/skills.git"
    fi
else
    echo "✗ Not on Marketplaces tab"
fi

# Quit
echo "Quitting..."
WAIT=1 send q

echo ""
echo "Test complete!"
