# Stooq Market Data Downloader

A high-performance, fully automated Python tool designed to download market data from [stooq.com](https://stooq.com). It features robust browser automation, a custom CAPTCHA recognition engine, and automated settings configuration.

## 🚀 Key Features

- **Automated CAPTCHA Solving**: Custom-built template matching engine using Jaccard similarity for 100% accuracy on Stooq's red-text CAPTCHAs.
- **Settings Automation**: Automatically configures the 'Setting Files Content' on Stooq to ensure specific tickers (like `AAPL.US`) are included in all data intervals.
- **Session Persistence**: Maintains browser sessions and cookies to minimize CAPTCHA challenges and allow faster subsequent downloads.
- **Comprehensive Data Fetching**: Downloads historical data across Daily, Hourly, and 5-minute intervals.
- **Smart Data Verification**: Post-download validation to ensure file integrity and the presence of expected tickers (e.g., verifying `AAPL.US` exists and `9823.JP` is excluded).
- **Service-Ready**: Includes Systemd timer and service units for scheduled, reliable background execution.

## 🛠 Project Architecture

The project is designed with a modular architecture for easy maintenance and reliability:

- **`src/main.py`**: The central orchestrator that manages the entire workflow.
- **`src/configurator.py`**: Handles browser-based configuration of Stooq data settings.
- **`src/captcha.py`**: The recognition engine that solves authorization challenges.
- **`src/session_manager.py`**: Manages cookie persistence and local directory setup.
- **`src/link_finder.py`**: Identifies the latest available data links via web scraping.
- **`src/downloader.py`**: Executes the actual file downloads and handles cleanup.

## 📋 Requirements

- Python 3.8+
- Playwright (Chromium engine)
- Libraries: `numpy`, `pillow`, `scipy`, `playwright`, `requests`

## ⚙️ Installation & Setup

1. **Auto-Setup**: Run the provided script to create a virtual environment, install dependencies, and setup Playwright:
   ```bash
   chmod +x scripts/setup-env.sh
   ./scripts/setup-env.sh
   ```

2. **Verify Environment**:
   ```bash
   .venv/bin/python scripts/check_env.py
   ```

## 🖥 Usage

### Manual Execution
To run the downloader manually and fetch the latest files:
```bash
.venv/bin/python src/main.py
```

Optional arguments:
- `--force`: Force download even if files already exist in the `data/` directory.

### CAPTCHA Model Management
If the CAPTCHA style changes, you can rebuild the template model:
1. `scripts/captcha/collect_samples.py`: Gathers raw CAPTCHA images.
2. Manually label images in the folder by renaming them to the 4-char code.
3. `scripts/captcha/build_templates.py`: Re-trains the `captcha/model.pkl` file.

## 🕒 Scheduling with Systemd

The project includes pre-configured systemd units for Mac/Linux environments to run the downloader on a schedule.

1. **Install Service**:
   ```bash
   chmod +x scripts/install-systemd.sh
   ./scripts/install-systemd.sh
   ```

This will set up `stooq.timer` to run the task periodically.

## 📂 Project Structure

```text
stooq/
├── src/
│   ├── main.py              # Main orchestrator
│   ├── captcha.py           # CAPTCHA solving logic
│   ├── configurator.py      # Stooq settings automation
│   ├── downloader.py        # File download handling
│   ├── link_finder.py       # Scraper for download links
│   └── session_manager.py   # Cookie/Session management
├── captcha/
│   ├── model.pkl            # Pre-trained template database
│   └── training_data/       # Labeled samples for training
├── scripts/
│   ├── setup-env.sh         # One-click environment setup
│   ├── install-systemd.sh   # Service installation script
│   └── captcha/             # Model building utilities
├── data/                    # Storage for downloaded CSV/TXT files
├── cookies/                 # Persisted browser sessions (gitignored)
└── README.md                # Documentation
```

## ⚖️ Disclaimer

This project is for educational and personal research purposes only. Please ensure your use of market data complies with the Terms of Service of [stooq.com](https://stooq.com).
