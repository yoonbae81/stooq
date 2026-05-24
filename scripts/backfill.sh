#!/bin/bash
# Backfill script for missing Stooq data files
# This script identifies missing dates and attempts to download them

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
DATA_DIR="$PROJECT_DIR/data"

# Default to last 30 days
DAYS=${1:-30}

echo "Stooq Data Backfill"
echo "========================================"
echo "Checking for missing data in the last $DAYS days..."
echo "Data directory: $DATA_DIR"
echo ""

# Generate list of dates to check (YYYY-MM-DD format)
DATES=()
for i in $(seq 0 $((DAYS - 1))); do
    DATE=$(date -d "$i days ago" +%Y-%m-%d)
    DATES+=("$DATE")
done

# Check which dates are missing
MISSING_DATES=()
for DATE in "${DATES[@]}"; do
    # Convert to YYYYMMDD format
    YYYYMMDD=$(date -d "$DATE" +%Y%m%d)

    # Check if all three files exist
    D_FILE="$DATA_DIR/${YYYYMMDD}_d.txt"
    H_FILE="$DATA_DIR/${YYYYMMDD}_h.txt"
    FIVE_FILE="$DATA_DIR/${YYYYMMDD}_5.txt"

    if [[ ! -f "$D_FILE" ]] || [[ ! -f "$H_FILE" ]] || [[ ! -f "$FIVE_FILE" ]]; then
        MISSING_DATES+=("$DATE")
        MISSING=""
        [[ ! -f "$D_FILE" ]] && MISSING="${MISSING} _d"
        [[ ! -f "$H_FILE" ]] && MISSING="${MISSING} _h"
        [[ ! -f "$FIVE_FILE" ]] && MISSING="${MISSING} _5"
        echo "Missing $DATE: ${MISSING}"
    fi
done

echo ""
if [[ ${#MISSING_DATES[@]} -eq 0 ]]; then
    echo "No missing data found in the last $DAYS days."
    exit 0
fi

echo "Found ${#MISSING_DATES[@]} missing date(s)."
echo "Starting backfill..."
echo ""

# Download missing dates
FAILED_DATES=()
for DATE in "${MISSING_DATES[@]}"; do
    echo "Attempting to download: $DATE"

    # Run main.py with the specific date
    if "$VENV_PYTHON" "$PROJECT_DIR/src/main.py" --date "$DATE"; then
        echo "  ✓ Successfully downloaded $DATE"
    else
        echo "  ✗ Failed to download $DATE"
        FAILED_DATES+=("$DATE")
    fi
    echo ""
done

# Summary
echo "========================================"
echo "Backfill Summary"
echo "========================================"
echo "Total missing dates: ${#MISSING_DATES[@]}"
echo "Successfully downloaded: $((${#MISSING_DATES[@]} - ${#FAILED_DATES[@]}))"
echo "Failed: ${#FAILED_DATES[@]}"

if [[ ${#FAILED_DATES[@]} -gt 0 ]]; then
    echo ""
    echo "Failed dates:"
    for DATE in "${FAILED_DATES[@]}"; do
        echo "  - $DATE"
    done
    exit 1
fi

echo ""
echo "Backfill completed successfully!"
exit 0
