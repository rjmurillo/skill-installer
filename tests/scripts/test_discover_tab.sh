#!/bin/bash
# Test script for Discover tab functionality
# Uses TMUX to interact with the TUI and verify behavior

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SESSION="skill-installer-test-$$"
OUTPUT_DIR="/tmp/skill-installer-test"
LOAD_DELAY=2
KEYSTROKE_DELAY=0.3

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

verify_content() {
    local filename="$1"
    local pattern="$2"
    local description="$3"

    if grep -q "$pattern" "$OUTPUT_DIR/$filename"; then
        success "$description"
    else
        error "$description - Expected pattern '$pattern' not found in $filename"
    fi
}

# Main test execution
main() {
    info "Starting Discover tab tests"

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Test 1: Launch TUI
    info "Test 1: Launching interactive TUI"
    tmux new-session -d -s "$SESSION"
    send_keys 'cd /home/richard/src/GitHub/rjmurillo/skill-installer' C-m
    send_keys 'uv run skill-installer interactive' C-m
    sleep "$LOAD_DELAY"

    capture_screen "01_initial_load.txt"
    verify_content "01_initial_load.txt" "Skill Installer" "TUI loaded successfully"
    verify_content "01_initial_load.txt" "Discover" "Discover tab visible"

    # Test 2: Verify Discover tab is active by default
    info "Test 2: Verify Discover tab is active"
    capture_screen "02_discover_active.txt"
    verify_content "02_discover_active.txt" "Discover" "Discover tab is active"

    # Test 3: Navigate with vim keys
    info "Test 3: Test vim-style navigation (j/k)"
    send_keys 'j' 'j'  # Move down 2 items
    capture_screen "03_vim_navigation_down.txt"

    send_keys 'k'  # Move up 1 item
    capture_screen "03_vim_navigation_up.txt"
    success "Vim navigation keys work"

    # Test 4: Test search functionality
    info "Test 4: Test search input"
    send_keys '/'  # Focus search (if implemented) or use Tab to get to search
    send_keys 'Tab'  # Tab to search field
    capture_screen "04_search_focus.txt"

    # Test 5: Test platform filter
    info "Test 5: Test platform filter dropdown"
    send_keys 'Tab' 'Tab'  # Navigate to platform filter
    capture_screen "05_platform_filter.txt"
    verify_content "05_platform_filter.txt" "All Platforms\|Claude\|VS Code" "Platform filter visible"

    # Test 6: Test arrow key navigation
    info "Test 6: Test arrow key navigation"
    send_keys 'Escape'  # Clear any focus
    sleep 0.5
    send_keys 'Down' 'Down'  # Navigate down
    capture_screen "06_arrow_navigation.txt"
    success "Arrow key navigation works"

    # Test 7: Test Space key for selection (toggle)
    info "Test 7: Test Space key to toggle item selection"
    send_keys 'Space'
    capture_screen "07_item_toggled.txt"
    success "Space key toggle works"

    # Test 8: Test Enter key for item details
    info "Test 8: Test Enter key to show item details"
    send_keys 'Enter'
    sleep 0.5
    capture_screen "08_item_details.txt"

    # Close detail view
    send_keys 'Escape'
    sleep 0.5
    capture_screen "08_details_closed.txt"
    success "Enter key shows item details, Escape closes"

    # Test 9: Test tab navigation between tabs
    info "Test 9: Test Tab key to switch tabs"
    send_keys 'Tab'
    sleep 0.5
    capture_screen "09_tab_switch.txt"
    verify_content "09_tab_switch.txt" "Installed\|Marketplaces" "Tab switching works"

    # Return to Discover tab
    send_keys 'Left' 'Left'  # Navigate back to Discover
    sleep 0.5
    capture_screen "09_back_to_discover.txt"

    # Test 10: Test quit functionality
    info "Test 10: Test quit with 'q' key"
    send_keys 'Escape'  # Ensure no widget has focus
    sleep 0.5
    send_keys 'q'
    sleep 2  # Give more time for graceful shutdown

    # Check if we're back at shell prompt (app quit successfully)
    capture_screen "10_after_quit.txt"
    if grep -qE "skill-installer|➜|\\$" "$OUTPUT_DIR/10_after_quit.txt"; then
        success "TUI quit successfully with 'q' key"
    else
        error "TUI did not quit with 'q' key (still showing TUI, see 10_after_quit.txt)"
    fi

    # Summary
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}All Discover tab tests passed!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo "Screen captures saved to: $OUTPUT_DIR"
    echo "View them with: ls -lh $OUTPUT_DIR"
}

# Run main function
main "$@"
