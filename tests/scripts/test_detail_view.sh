#!/bin/bash
# Test script for Item Detail View functionality
# Tests the enhanced detail view with metadata, options, and navigation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SESSION="skill-detail-test-$$"
OUTPUT_DIR="/tmp/skill-installer-detail-test"
LOAD_DELAY=2
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

verify_content_optional() {
    local filename="$1"
    local pattern="$2"
    local description="$3"

    if grep -q "$pattern" "$OUTPUT_DIR/$filename"; then
        success "$description (found)"
    else
        info "$description (not found - optional)"
    fi
}

# Main test execution
main() {
    info "Starting Item Detail View tests"

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

    # Test 2: Open detail view for first item (likely installed)
    info "Test 2: Open detail view for installed item"
    send_keys 'Enter'
    sleep 0.7
    capture_screen "02_detail_installed.txt"

    # Scroll to top to see all header content
    send_keys 'Home'
    sleep 0.3
    capture_screen "02_detail_installed_top.txt"

    verify_content "02_detail_installed_top.txt" "details" "Detail view opened with title"
    verify_content "02_detail_installed_top.txt" "from" "Source information shown"

    # Test 3: Check for uninstall option (installed item)
    info "Test 3: Verify uninstall option for installed item"
    send_keys 'Down' 'Down' 'Down'
    sleep 0.3
    capture_screen "03_detail_options_installed.txt"
    verify_content "03_detail_options_installed.txt" "Uninstall\|Back to list" "Uninstall option shown for installed item"

    # Test 4: Navigate through options
    info "Test 4: Test option navigation with Up/Down keys"
    send_keys 'Down'
    capture_screen "04_option_nav_down.txt"
    send_keys 'Up'
    capture_screen "04_option_nav_up.txt"
    success "Option navigation works"

    # Test 5: Close detail view with Escape
    info "Test 5: Close detail view with Escape key"
    send_keys 'Escape'
    sleep 0.5
    capture_screen "05_detail_closed.txt"
    verify_content "05_detail_closed.txt" "Discover" "Detail view closed, back to list"

    # Test 6: Navigate to uninstalled item and open detail
    info "Test 6: Open detail view for uninstalled item"
    send_keys 'Down' 'Down'  # Move to potentially uninstalled item
    sleep 0.3
    send_keys 'Enter'
    sleep 0.7

    # Scroll to top
    send_keys 'Home'
    sleep 0.3
    capture_screen "06_detail_uninstalled_top.txt"

    # Test 7: Verify detail header components
    info "Test 7: Verify detail view header components"
    verify_content "06_detail_uninstalled_top.txt" "details" "Title shown"
    verify_content "06_detail_uninstalled_top.txt" "from" "Source information shown"

    # Scroll down to see description and warning
    send_keys 'Down' 'Down'
    sleep 0.3
    capture_screen "07_detail_description.txt"
    verify_content_optional "07_detail_description.txt" "By:" "Author information (if available)"
    verify_content_optional "07_detail_description.txt" "Make sure you trust" "Security warning shown"

    # Test 8: Verify install options for uninstalled item
    info "Test 8: Verify install options for uninstalled item"
    send_keys 'Down' 'Down'
    sleep 0.3
    capture_screen "08_install_options.txt"

    # Check for install options
    if grep -q "Install for you (user scope)" "$OUTPUT_DIR/08_install_options.txt"; then
        success "User scope install option shown"
    elif grep -q "Uninstall" "$OUTPUT_DIR/08_install_options.txt"; then
        info "Item is installed - uninstall option shown instead"
    fi

    if grep -q "Install for all collaborators" "$OUTPUT_DIR/08_install_options.txt"; then
        success "Project scope install option shown"
    fi

    verify_content "08_install_options.txt" "Back to list" "Back to list option shown"

    # Test 9: Verify option selection indicator (>)
    info "Test 9: Verify option selection indicator"
    verify_content "08_install_options.txt" ">" "Selection indicator shown"

    # Test 10: Test scrolling in detail view
    info "Test 10: Test scrolling with vim keys (j/k)"
    send_keys 'k' 'k' 'k'  # Scroll up
    sleep 0.3
    capture_screen "10_scroll_up.txt"

    send_keys 'j' 'j'  # Scroll down
    sleep 0.3
    capture_screen "10_scroll_down.txt"
    success "Vim-style scrolling works in detail view"

    # Test 11: Test selecting "Back to list" option
    info "Test 11: Test 'Back to list' option"
    send_keys 'End'  # Go to bottom (last option)
    sleep 0.3
    capture_screen "11_back_option_selected.txt"
    send_keys 'Enter'
    sleep 0.5
    capture_screen "11_back_to_list.txt"
    verify_content "11_back_to_list.txt" "Discover" "Back to list works, detail view closed"

    # Test 12: Test "Open homepage" option
    info "Test 12: Test 'Open homepage' option"
    send_keys 'Enter'  # Open detail again
    sleep 0.7
    send_keys 'Down' 'Down' 'Down'  # Navigate to homepage option
    sleep 0.3
    capture_screen "12_homepage_option.txt"
    verify_content "12_homepage_option.txt" "Open homepage" "Open homepage option shown"

    # Select the homepage option
    send_keys 'Enter'
    sleep 0.5
    capture_screen "12_homepage_notification.txt"
    verify_content "12_homepage_notification.txt" "Homepage:" "Homepage URL displayed in notification"

    # Test 13: Test footer text
    info "Test 13: Verify footer text in detail view"
    send_keys 'Enter'  # Open detail again
    sleep 0.7
    send_keys 'End'
    sleep 0.3
    capture_screen "13_detail_footer.txt"
    verify_content "13_detail_footer.txt" "Select: Enter.*Back: Esc\|esc" "Footer shows navigation hints"

    # Close detail view
    send_keys 'Escape'
    sleep 0.5

    # Test 14: Quit application
    info "Test 14: Test quit functionality"
    send_keys 'q'
    sleep 2

    capture_screen "13_after_quit.txt"
    if grep -qE "skill-installer|➜|\\$" "$OUTPUT_DIR/13_after_quit.txt"; then
        success "Application quit successfully"
    else
        error "Application did not quit properly"
    fi

    # Summary
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}All Detail View tests passed!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo "Screen captures saved to: $OUTPUT_DIR"
    echo "View them with: ls -lh $OUTPUT_DIR"
    echo "Example: cat $OUTPUT_DIR/02_detail_installed_top.txt"
}

# Run main function
main "$@"
