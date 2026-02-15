#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "Stooq - Environment Setup"
echo "========================================"
echo "Project directory: $PROJECT_DIR"
echo ""

# Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi
echo "Found: $(python3 --version)"
echo ""

# Create venv
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi
echo ""

# Upgrade pip
echo "Upgrading pip..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
echo "pip upgraded"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
echo "Dependencies installed"
echo ""

# Install Playwright browsers (if playwright is installed)
if "$VENV_DIR/bin/pip" show playwright &> /dev/null; then
    echo "Installing Playwright browsers..."
    "$VENV_DIR/bin/playwright" install chromium
    echo "Playwright browsers installed"
    echo ""
fi

# Check .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        echo "Creating .env from .env.example..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo ".env file created"
    else
        echo "Creating empty .env file..."
        touch "$PROJECT_DIR/.env"
        echo ".env file created"
    fi
    echo "Please edit .env and configure your settings"
else
    echo ".env file exists"
fi
echo ""

# Grant execution permissions to scripts
chmod +x "$SCRIPT_DIR/setup-env.sh"
[ -f "$SCRIPT_DIR/install-systemd.sh" ] && chmod +x "$SCRIPT_DIR/install-systemd.sh"
[ -f "$SCRIPT_DIR/run.sh" ] && chmod +x "$SCRIPT_DIR/run.sh"
[ -f "$SCRIPT_DIR/deploy.sh" ] && chmod +x "$SCRIPT_DIR/deploy.sh"

echo "Environment setup completed!"
