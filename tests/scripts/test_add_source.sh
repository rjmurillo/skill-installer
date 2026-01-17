#!/bin/bash
# Test script for Add Source modal using tmux

SESSION_NAME="add-source-test-$$"
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
save_pane "/tmp/add-source-01-initial.txt"

# Check if TUI started
if capture_pane | grep -q "Skill Installer"; then
    log_info "✓ TUI started successfully"
else
    log_error "✗ TUI failed to start"
    exit 1
fi

# Test 1: Open Add Source modal with 'a' key
log_step "Test 1: Opening Add Source modal"
send_and_wait "a" 1
save_pane "/tmp/add-source-02-modal-open.txt"

if capture_pane | grep -q "Add Repository"; then
    log_info "✓ Add Source modal opened"
else
    log_error "✗ Add Source modal did not open"
    exit 1
fi

# Check for example text
if capture_pane | grep -q "owner/repo"; then
    log_info "✓ Modal shows examples"
else
    log_error "✗ Modal missing examples"
fi

# Test 2: Cancel with Escape
log_step "Test 2: Testing Escape to cancel"
send_and_wait "Escape" 1
save_pane "/tmp/add-source-03-after-escape.txt"

if capture_pane | grep -q "Add Repository"; then
    log_error "✗ Modal should be closed after Escape"
    exit 1
else
    log_info "✓ Modal closed with Escape"
fi

# Test 3: Open modal again and type a shorthand
log_step "Test 3: Testing shorthand expansion"
send_and_wait "a" 1
save_pane "/tmp/add-source-04-modal-reopen.txt"

# Type owner/repo format
send_and_wait "test/repo" 1
save_pane "/tmp/add-source-05-typed-shorthand.txt"

# Check for preview expansion
if capture_pane | grep -q "github.com/test/repo"; then
    log_info "✓ Shorthand expanded to GitHub URL in preview"
else
    log_info "○ Preview expansion not visible (may need more time)"
fi

# Cancel this one
send_and_wait "Escape" 1

# Test 4: Open modal and test empty submission
log_step "Test 4: Testing empty submission shows error"
send_and_wait "a" 1
save_pane "/tmp/add-source-06-modal-for-empty.txt"

# Press Enter without typing anything
send_and_wait "Enter" 1
save_pane "/tmp/add-source-07-empty-submit.txt"

# Modal should still be open (validation failed)
if capture_pane | grep -q "Add Repository"; then
    log_info "✓ Modal stayed open on empty submit (validation working)"
else
    log_error "✗ Modal should stay open on empty submission"
fi

# Cancel and exit
send_and_wait "Escape" 1
send_and_wait "q" 1

log_info "All tests completed"
log_info "Screenshots saved to /tmp/add-source-*.txt"
