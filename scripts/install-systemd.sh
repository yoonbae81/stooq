#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICE_NAME="stooq-downloader"

echo "Stooq - Systemd Timer Installation"
echo "=============================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Load environment variables from .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    # Use a safer way to export .env
    set -a
    [ -f "$PROJECT_DIR/.env" ] && . "$PROJECT_DIR/.env"
    set +a
    echo "Environment variables loaded from .env"
fi

# Create systemd directory
echo "Setting up systemd timer..."
mkdir -p "$SYSTEMD_USER_DIR"

# Create service file with environment variables
echo "Creating $SERVICE_NAME.service..."
cat > "$SYSTEMD_USER_DIR/$SERVICE_NAME.service" << EOF
[Unit]
Description=Stooq Data Downloader Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
# EnvironmentFile only works if the file exists and has correct format
$( [ -f "$PROJECT_DIR/.env" ] && echo "EnvironmentFile=$PROJECT_DIR/.env" )

ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/src/main.py

StandardOutput=journal
StandardError=journal
SyslogIdentifier=stooq-downloader

[Install]
WantedBy=default.target
EOF

# Copy timer file
echo "Copying $SERVICE_NAME.timer..."
cp "$SCRIPT_DIR/systemd/$SERVICE_NAME.timer" "$SYSTEMD_USER_DIR/"

echo "Systemd files installed"
echo ""

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl --user daemon-reload

# Enable and start timer
echo "Enabling and starting timer..."
systemctl --user enable "$SERVICE_NAME.timer"
systemctl --user start "$SERVICE_NAME.timer"

echo ""
echo "Timer installation completed!"
echo ""
echo "Useful commands:"
echo "  • Check timer status:   systemctl --user status $SERVICE_NAME.timer"
echo "  • Check service logs:   journalctl --user -u $SERVICE_NAME.service"
echo "  • Follow logs:          journalctl --user -u $SERVICE_NAME.service -f"
