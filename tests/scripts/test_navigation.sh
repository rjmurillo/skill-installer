#!/bin/bash
# Quick test of tab navigation

SESSION_NAME="nav-test-$$"

cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
}
trap cleanup EXIT

cd /home/richard/src/GitHub/rjmurillo/skill-installer
tmux new-session -d -s "$SESSION_NAME" -x 80 -y 24

tmux send-keys -t "$SESSION_NAME" "uv run python -m skill_installer interactive" C-m
sleep 3

echo "=== Tab 1: Initial (Discover) ==="
tmux capture-pane -t "$SESSION_NAME" -p | sed 's/\x1b\[[0-9;]*m//g' | head -6

sleep 1
tmux send-keys -t "$SESSION_NAME" Right
sleep 1

echo ""
echo "=== Tab 2: After Right (should be Installed) ==="
tmux capture-pane -t "$SESSION_NAME" -p | sed 's/\x1b\[[0-9;]*m//g' | head -6

sleep 1
tmux send-keys -t "$SESSION_NAME" Right
sleep 1

echo ""
echo "=== Tab 3: After Right x2 (should be Marketplaces) ==="
tmux capture-pane -t "$SESSION_NAME" -p | sed 's/\x1b\[[0-9;]*m//g' | head -12

tmux send-keys -t "$SESSION_NAME" q
sleep 1

echo ""
echo "Navigation test complete!"
