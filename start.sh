#!/bin/bash
PYTHON=$(which python3.11 2>/dev/null || which python3 2>/dev/null)

if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3.11 not found."
    exit 1
fi

echo "[INFO] Using: $($PYTHON --version)"

if [ ! -d ".venv" ]; then
    echo "[SETUP] Creating venv..."
    $PYTHON -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt -q

# Find Cyrillic TTF font
if [ ! -f "FreeSans.ttf" ]; then
    find /usr/share/fonts -name "FreeSans.ttf" 2>/dev/null | head -1 | xargs -I{} cp {} ./ 2>/dev/null || \
    find /usr/share/fonts -name "DejaVuSans.ttf" 2>/dev/null | head -1 | xargs -I{} cp {} ./FreeSans.ttf 2>/dev/null || \
    echo "[WARN] No TTF font found. PDF will use Helvetica (no Cyrillic)."
fi

echo "[SERVER] Starting at http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
