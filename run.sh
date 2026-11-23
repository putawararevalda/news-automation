#!/bin/bash
# Runner script for Daily News Automation
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/opt/homebrew/bin/python3"

if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(which python3)"
fi

echo "Running Daily News Update at $(date)..."
"$PYTHON_BIN" "$SCRIPT_DIR/daily_news.py" "$@"
