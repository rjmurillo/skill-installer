#!/bin/bash
# Debug tab navigation

SESSION_NAME="tui-debug-$$"

cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
}
trap cleanup EXIT

cd /home/richard/src/GitHub/rjmurillo/skill-installer
tmux new-session -d -s "$SESSION_NAME" -x 80 -y 24

send() {
    tmux send-keys -t "$SESSION_NAME" "$@"
    sleep 1
}

capture() {
    tmux capture-pane -t "$SESSION_NAME" -p | sed 's/\x1b\[[0-9;]*m//g'
}

# Start TUI
send "uv run python -m skill_installer interactive" C-m
sleep 3

echo "=== Tab 1: Discover (initial) ==="
capture | head -10
echo ""

echo "Pressing Tab once..."
send Tab
sleep 1

echo "=== Tab 2: Installed ==="
capture | head -10
echo ""

echo "Pressing Tab again..."
send Tab
sleep 1

echo "=== Tab 3: Marketplaces ==="
capture | head -15
echo ""

send q
