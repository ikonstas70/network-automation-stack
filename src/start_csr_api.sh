#!/bin/bash
# Start the CSR1000v Flask API Gateway

VENV_DIR="$HOME/csr_env"
SCRIPT="$(dirname "$0")/csr_api_secure.py"
FLASK_PORT=8080

if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "[!] Virtual environment not found at $VENV_DIR"
    echo "[!] Create it with: python3 -m venv ~/csr_env && pip install flask"
    exit 1
fi

echo "[*] Starting Flask API on port $FLASK_PORT..."
python3 "$SCRIPT" --host 0.0.0.0 --port $FLASK_PORT
