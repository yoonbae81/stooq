#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Project root is one level up from scripts/
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." &> /dev/null && pwd )"

# Define variables
SERVICE_NAME="stooq-downloader"
SERVICE_TEMPLATE="$SCRIPT_DIR/systemd/${SERVICE_NAME}.service"
TIMER_TEMPLATE="$SCRIPT_DIR/systemd/${SERVICE_NAME}.timer"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
PYTHON_EXECUTABLE="$PROJECT_DIR/.venv/bin/python3"

echo "📍 Project Root: $PROJECT_DIR"
echo "🐍 Python Exec: $PYTHON_EXECUTABLE"

# Check if running on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "⚠️  Warning: This script is intended for Linux systems with systemd."
    echo "   You seem to be running on $(uname). Operations may fail."
    echo "   Continuing anyway as requested..."
fi

# Ensure log directory exists
mkdir -p "$PROJECT_DIR/logs"

# Create systemd user directory
mkdir -p "$SYSTEMD_USER_DIR"

# Install files with path replacement
echo "📦 Installing systemd units to $SYSTEMD_USER_DIR..."

# Replace placeholders in service file and save to systemd directory
sed -e "s|{{WORKING_DIRECTORY}}|$PROJECT_DIR|g" \
    -e "s|{{PYTHON_EXECUTABLE}}|$PYTHON_EXECUTABLE|g" \
    "$SERVICE_TEMPLATE" > "$SYSTEMD_USER_DIR/${SERVICE_NAME}.service"

# Copy timer file
cp "$TIMER_TEMPLATE" "$SYSTEMD_USER_DIR/"

# Reload systemd
echo "🔄 Reloading systemd daemon..."
if systemctl --user daemon-reload; then
    echo "✅ Daemon reloaded."
else
    echo "❌ Failed to reload daemon (is systemd running?)"
    exit 1
fi

# Enable and start timer
echo "⏰ Enabling and starting timer..."
systemctl --user enable --now "${SERVICE_NAME}.timer"

# Show status
echo "📊 Timer status:"
systemctl --user list-timers --all | grep "$SERVICE_NAME" || echo "Timer not found in list."

echo ""
echo "🎉 Installation complete!"
echo "   To allow the timer to run while you are logged out, run:"
echo "   loginctl enable-linger $USER"
echo ""
echo "   View logs with: journalctl --user -u stooq-downloader"
echo "   View timer status: systemctl --user status stooq-downloader.timer"
