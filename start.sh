#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# Activate virtualenv if present
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

echo "Starting Job Hunter AI on http://localhost:5050"
python3 app.py
