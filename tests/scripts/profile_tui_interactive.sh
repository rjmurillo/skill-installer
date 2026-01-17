#!/bin/bash
# Profile TUI startup time by launching the app and measuring time to first render.
#
# Usage:
#     ./tests/scripts/profile_tui_interactive.sh
#
# This script:
# 1. Starts the TUI in a tmux session
# 2. Polls until the UI renders
# 3. Measures and reports the startup time
# 4. Cleans up

set -e

SESSION="tui-profile-$$"
LOG_FILE="/tmp/tui_profile_${$}.log"
POLL_INTERVAL=0.5
MAX_WAIT=60

cleanup() {
    tmux kill-session -t "$SESSION" 2>/dev/null || true
    rm -f "$LOG_FILE"
}
trap cleanup EXIT

echo "TUI Interactive Startup Profiler"
echo "================================="
echo ""

# Start timing
START_TIME=$(date +%s.%N)

# Start TUI in tmux
tmux new-session -d -s "$SESSION" -x 120 -y 40
tmux send-keys -t "$SESSION" 'uv run skill-installer interactive' C-m

echo "Waiting for TUI to render..."

# Poll for UI to appear
ELAPSED=0
while [ "$(echo "$ELAPSED < $MAX_WAIT" | bc)" -eq 1 ]; do
    sleep $POLL_INTERVAL
    
    # Capture screen
    tmux capture-pane -t "$SESSION" -p > "$LOG_FILE" 2>/dev/null || true
    
    # Check for TUI loaded indicator
    if grep -q "Skill Installer" "$LOG_FILE" 2>/dev/null; then
        END_TIME=$(date +%s.%N)
        STARTUP_TIME=$(echo "$END_TIME - $START_TIME" | bc)
        
        echo ""
        echo "TUI rendered successfully!"
        echo ""
        echo "================================="
        echo "STARTUP TIME: ${STARTUP_TIME}s"
        echo "================================="
        echo ""
        
        # Show what loaded
        if grep -q "items available" "$LOG_FILE" 2>/dev/null; then
            STATUS=$(grep "items available" "$LOG_FILE" | head -1)
            echo "Status: $STATUS"
        fi
        
        # Quit the app
        tmux send-keys -t "$SESSION" 'q'
        sleep 0.5
        exit 0
    fi
    
    ELAPSED=$(echo "$ELAPSED + $POLL_INTERVAL" | bc)
    printf "."
done

echo ""
echo "ERROR: TUI did not render within ${MAX_WAIT}s"
echo ""
echo "Last captured screen:"
cat "$LOG_FILE"
exit 1
