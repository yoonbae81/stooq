#!/bin/bash
set -e

# Define variables
SERVICE_NAME="stooq-downloader"
SERVICE_FILE="scripts/systemd/${SERVICE_NAME}.service"
TIMER_FILE="scripts/systemd/${SERVICE_NAME}.timer"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

# Check if running on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "⚠️  Warning: This script is intended for Linux systems with systemd."
    echo "   You seem to be running on $(uname). Operations may fail."
    echo "   Continuing anyway as requested..."
fi

# Ensure log directory exists
mkdir -p logs

# Create systemd user directory
mkdir -p "$SYSTEMD_USER_DIR"

# Install files
echo "📦 Installing systemd units to $SYSTEMD_USER_DIR..."
cp "$SERVICE_FILE" "$SYSTEMD_USER_DIR/"
cp "$TIMER_FILE" "$SYSTEMD_USER_DIR/"

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
echo "   Logs will be written to: $HOME/GitHub/stooq/logs/"
