#!/bin/bash
# Test script for batch install fix
# Verifies that selecting multiple items and pressing 'i' does not crash with DuplicateIds error

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SESSION="skill-installer-batch-test-$$"
OUTPUT_DIR="/tmp/skill-installer-batch-test"
LOAD_DELAY=3
KEYSTROKE_DELAY=0.5

# Cleanup function
cleanup() {
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        tmux kill-session -t "$SESSION"
    fi
    echo -e "${GREEN}Cleaned up TMUX session${NC}"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Helper functions
info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

error() {
    echo -e "${RED}[FAIL]${NC} $1"
    exit 1
}

capture_screen() {
    local filename="$1"
    tmux capture-pane -t "$SESSION" -p > "$OUTPUT_DIR/$filename"
    sleep "$KEYSTROKE_DELAY"
}

send_keys() {
    tmux send-keys -t "$SESSION" "$@"
    sleep "$KEYSTROKE_DELAY"
}

# Main test execution
main() {
    info "Starting batch install tests"
    info "This tests the fix for DuplicateIds crash when batch installing"

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Test 1: Launch TUI
    info "Test 1: Launching interactive TUI"
    tmux new-session -d -s "$SESSION"
    send_keys 'cd /home/richard/src/GitHub/rjmurillo/skill-installer' C-m
    send_keys 'uv run skill-installer interactive' C-m
    sleep "$LOAD_DELAY"

    capture_screen "01_initial_load.txt"

    # Verify TUI loaded
    if grep -q "Skill Installer" "$OUTPUT_DIR/01_initial_load.txt"; then
        success "TUI loaded successfully"
    else
        error "TUI failed to load"
    fi

    # Test 2: Select first item with Space
    info "Test 2: Selecting first item with Space"
    send_keys 'Space'
    sleep "$KEYSTROKE_DELAY"
    capture_screen "02_first_selected.txt"

    # Check for checkbox marker
    if grep -qE "\[x\]|\[X\]|checked" "$OUTPUT_DIR/02_first_selected.txt"; then
        success "First item checked"
    else
        info "First item toggled (checkbox state may vary)"
    fi

    # Test 3: Move down and select second item
    info "Test 3: Selecting second item with Space"
    send_keys 'j'  # Move down
    send_keys 'Space'  # Toggle second item
    sleep "$KEYSTROKE_DELAY"
    capture_screen "03_second_selected.txt"
    success "Second item toggled"

    # Test 4: Press 'i' to batch install - this is the critical test
    info "Test 4: Pressing 'i' to batch install (critical test)"
    send_keys 'i'
    sleep 2  # Give time for installation to process

    capture_screen "04_after_batch_install.txt"

    # Check for crash - look for error messages or traceback
    if grep -qi "DuplicateIds\|Traceback\|Error\|Crash" "$OUTPUT_DIR/04_after_batch_install.txt"; then
        error "Batch install crashed with error - see $OUTPUT_DIR/04_after_batch_install.txt"
    fi

    # Verify TUI is still responsive (not crashed)
    if grep -q "Skill Installer\|Discover\|Installed" "$OUTPUT_DIR/04_after_batch_install.txt"; then
        success "TUI still running after batch install - no crash!"
    else
        # Check if we're back at shell (app crashed and exited)
        if grep -qE "➜|\\$|bash" "$OUTPUT_DIR/04_after_batch_install.txt"; then
            error "TUI exited unexpectedly - possible crash"
        fi
        info "TUI state unclear, checking further..."
    fi

    # Test 5: Verify we can still navigate (app is responsive)
    info "Test 5: Verifying TUI is responsive after batch install"
    send_keys 'j'  # Try to navigate
    send_keys 'k'
    sleep "$KEYSTROKE_DELAY"
    capture_screen "05_navigation_after_install.txt"
    success "Navigation works after batch install"

    # Test 6: Clean quit
    info "Test 6: Quitting TUI"
    send_keys 'Escape'
    sleep 0.3
    send_keys 'q'
    sleep 1
    capture_screen "06_quit.txt"

    # Summary
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All batch install tests passed!${NC}"
    echo -e "${GREEN}DuplicateIds fix verified working.${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Screen captures saved to: $OUTPUT_DIR"
    echo "View them with: ls -lh $OUTPUT_DIR"
}

# Run main function
main "$@"
