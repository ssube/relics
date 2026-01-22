#!/bin/bash
# Setup virtual environment and install dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Setting up virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created virtual environment"
else
    echo "Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install package with all dependencies
echo "Installing relics with dev and demo dependencies..."
pip install -e ".[dev,demo]"

echo ""
echo "Setup complete!"
echo "Activate the virtual environment with: source venv/bin/activate"
