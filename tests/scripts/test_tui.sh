#!/bin/bash
# Test script for TUI using tmux

SESSION_NAME="tui-test-$$"
WINDOW_NAME="tui"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${YELLOW}[STEP]${NC} $1"
}

# Create a new tmux session in the project directory
log_info "Creating tmux session: $SESSION_NAME"
cd /home/richard/src/GitHub/rjmurillo/skill-installer
tmux new-session -d -s "$SESSION_NAME" -n "$WINDOW_NAME" -c "$(pwd)"

# Set up the pane size
tmux set-option -t "$SESSION_NAME" -g default-terminal "screen-256color"

# Function to send keys and wait
send_and_wait() {
    local keys="$1"
    local wait_time="${2:-1}"
    if [ -n "$keys" ]; then
        tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" "$keys"
    fi
    sleep "$wait_time"
}

# Function to send keys with Enter
send_command() {
    local cmd="$1"
    local wait_time="${2:-1}"
    tmux send-keys -t "$SESSION_NAME:$WINDOW_NAME" "$cmd" C-m
    sleep "$wait_time"
}

# Function to capture pane
capture_pane() {
    tmux capture-pane -t "$SESSION_NAME:$WINDOW_NAME" -p
}

# Function to save pane to file
save_pane() {
    local filename="$1"
    capture_pane > "$filename"
    log_info "Saved screen to $filename"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up tmux session"
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    log_info "Test complete"
}

trap cleanup EXIT

# Start the TUI
log_step "Starting TUI application"
send_command "uv run python -m skill_installer interactive" 3
save_pane "/tmp/tui-01-initial.txt"

# Check if TUI started
if capture_pane | grep -q "Skill Installer"; then
    log_info "✓ TUI started successfully"
else
    log_error "✗ TUI failed to start"
    exit 1
fi

# Navigate to Marketplaces tab
log_step "Navigating to Marketplaces tab"
send_and_wait "Tab" 1
send_and_wait "Tab" 1
save_pane "/tmp/tui-02-marketplaces.txt"

if capture_pane | grep -q "Marketplaces"; then
    log_info "✓ Navigated to Marketplaces tab"
else
    log_error "✗ Failed to navigate to Marketplaces"
fi

# Check if there are any marketplaces
if capture_pane | grep -q "anthropic\|openai\|skills"; then
    log_info "✓ Marketplaces are visible"

    # Press Enter to open marketplace detail
    log_step "Opening marketplace detail view"
    send_and_wait "Enter" 1.5
    save_pane "/tmp/tui-03-marketplace-detail.txt"

    # Check for detail view elements
    DETAIL=$(capture_pane)
    if echo "$DETAIL" | grep -q "Browse\|Update\|Remove"; then
        log_info "✓ Marketplace detail view opened"

        # Check for proper formatting
        if echo "$DETAIL" | grep -q "available"; then
            log_info "✓ Available count shown"
        fi

        if echo "$DETAIL" | grep -q "http"; then
            log_info "✓ URL displayed"
        fi

        # Navigate to Browse option
        log_step "Selecting Browse option"
        send_and_wait "Enter" 1.5
        save_pane "/tmp/tui-04-browse-discover.txt"

        # Check if we're back in Discover tab with filter
        DISCOVER=$(capture_pane)
        if echo "$DISCOVER" | grep -q "Discover"; then
            log_info "✓ Switched to Discover tab"

            if echo "$DISCOVER" | grep -q "Filtered by marketplace"; then
                log_info "✓ Filter banner displayed"
            else
                log_error "✗ Filter banner not found"
            fi

            # Check if items are shown
            if echo "$DISCOVER" | grep -q "skill-installer\|skill-creator"; then
                log_info "✓ Items displayed in filtered view"
            else
                log_error "✗ No items visible"
            fi

            # Test item detail view
            log_step "Opening item detail view"
            send_and_wait "Enter" 1.5
            save_pane "/tmp/tui-05-item-detail.txt"

            ITEM_DETAIL=$(capture_pane)
            if echo "$ITEM_DETAIL" | grep -q "From:\|Type:\|Install"; then
                log_info "✓ Item detail view opened"

                # Close item detail with Escape
                log_step "Closing item detail with Escape"
                send_and_wait "Escape" 1
                save_pane "/tmp/tui-06-after-item-close.txt"

                if capture_pane | grep -q "Discover"; then
                    log_info "✓ Item detail closed successfully"
                else
                    log_error "✗ Failed to close item detail"
                fi
            else
                log_error "✗ Item detail view not showing correctly"
            fi

            # Test clearing filter with Escape
            log_step "Clearing filter with Escape"
            send_and_wait "Escape" 1
            save_pane "/tmp/tui-07-filter-cleared.txt"

            if ! capture_pane | grep -q "Filtered by marketplace"; then
                log_info "✓ Filter cleared successfully"
            else
                log_error "✗ Filter still active"
            fi

        else
            log_error "✗ Did not switch to Discover tab"
        fi

    else
        log_error "✗ Marketplace detail view not showing"
    fi
else
    log_info "No marketplaces configured - adding one for testing"

    # Exit to add a marketplace
    send_and_wait "q" 1
    send_command "uv run python -m skill_installer source add https://github.com/anthropics/skills.git" 3

    # Restart TUI
    send_command "uv run python -m skill_installer interactive" 2
    save_pane "/tmp/tui-marketplace-added.txt"
fi

# Test Space toggle functionality in Discover tab
log_step "Testing Space toggle in Discover tab"
send_and_wait "Tab" 1  # Go back to Discover if not there
send_and_wait "Space" 0.5
save_pane "/tmp/tui-08-toggle-item.txt"

if capture_pane | grep -q "selected for installation"; then
    log_info "✓ Space toggle working (status bar updated)"
else
    log_info "- Space toggle status (check manually)"
fi

# Final state capture
log_step "Capturing final state"
save_pane "/tmp/tui-09-final.txt"

# Quit the TUI
log_step "Quitting TUI"
send_and_wait "q" 1

log_info "All test captures saved to /tmp/tui-*.txt"
log_info "Review the files to verify UI state"

# Display summary
echo ""
echo "=== Test Summary ==="
ls -lh /tmp/tui-*.txt
echo ""
echo "View captures with: cat /tmp/tui-*.txt"
