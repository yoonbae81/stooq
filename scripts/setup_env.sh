#!/bin/bash
# Stooq Project Environment Setup Script

# 1. Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Stooq project environment setup...${NC}"

# Move to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 2. Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo -e "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✅ Virtual environment created${NC}"
    else
        echo -e "${RED}  ❌ Failed to create virtual environment${NC}"
        exit 1
    fi
else
    echo -e "📦 .venv already exists."
fi

# 3. Install Pip Packages
echo -e "\n📥 Installing dependencies (pip install)..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Dependencies installed${NC}"
else
    echo -e "${RED}  ❌ Failed to install dependencies${NC}"
    exit 1
fi

# 4. Install Playwright Browsers
echo -e "\n🌐 Installing Playwright browsers (Chromium)..."
.venv/bin/playwright install chromium

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✅ Playwright setup complete${NC}"
else
    echo -e "${RED}  ❌ Playwright setup failed${NC}"
    exit 1
fi

# 5. Grant Execution Permissions
echo -e "\n🔐 Granting execution permissions..."
chmod +x scripts/check_env.py
chmod +x scripts/captcha/collect_samples.py
chmod +x scripts/captcha/build_templates.py
chmod +x src/download.py
chmod +x tests/test_captcha.py

echo -e "${GREEN}  ✅ Permissions granted${NC}"

# 6. Final Health Check
echo -e "\n🔍 Running environment health check..."
.venv/bin/python3 scripts/check_env.py

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✨ All environment setup steps completed successfully!${NC}"
    echo -e "You can now start the downloader with:"
    echo -e "   ${GREEN}.venv/bin/python src/download.py${NC}"
else
    echo -e "\n${RED}⚠️  Setup finished with some environment warnings.${NC}"
fi
