#!/bin/bash
# Run the ecosystem demo

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate venv if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Error: Virtual environment not found. Run scripts/setup.sh first."
        exit 1
    fi
fi

# Check if pygame-ce is installed
if ! python -c "import pygame" 2>/dev/null; then
    echo "Error: pygame-ce not installed. Run: pip install -e '.[demo]'"
    exit 1
fi

# Run the demo
echo "Starting ecosystem demo..."
echo "Controls: WASD=scroll, Space=pause, Escape=quit"
echo ""
python -m demos.pygame.main
