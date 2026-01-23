#!/bin/bash
# Run available demos

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate venv if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "Error: Virtual environment not found. Run scripts/setup.sh first."
        exit 1
    fi
fi

# Available demos
declare -A DEMOS=(
    ["pygame"]="demos.pygame.main:Ecosystem simulation with pygame rendering (requires pygame-ce)"
    ["hello_ecs"]="demos.hello_ecs.main:Simple ECS hello world example"
    ["chain_reaction"]="demos.chain_reaction.main:Chain reaction demonstrating observers"
    ["character_sheet"]="demos.character_sheet.main:RPG character sheet with stats and relationships"
    ["inventory_tree"]="demos.inventory_tree.main:Inventory tree with containers and items"
    ["spatial_aoe"]="demos.spatial_aoe.main:Spatial index AOE damage example"
)

# Function to show menu
show_menu() {
    echo "Available Relics Demos:"
    echo ""
    local i=1
    for key in "${!DEMOS[@]}"; do
        IFS=':' read -r module description <<< "${DEMOS[$key]}"
        echo "  $i) $key - $description"
        ((i++))
    done
    echo ""
    echo "  q) Quit"
    echo ""
}

# Function to run a demo
run_demo() {
    local demo_key="$1"
    if [[ -z "${DEMOS[$demo_key]}" ]]; then
        echo "Unknown demo: $demo_key"
        return 1
    fi

    IFS=':' read -r module description <<< "${DEMOS[$demo_key]}"

    # Check pygame for pygame demo
    if [[ "$demo_key" == "pygame" ]]; then
        if ! python -c "import pygame" 2>/dev/null; then
            echo "Error: pygame-ce not installed. Run: pip install -e '.[demo]'"
            return 1
        fi
        echo ""
        echo "Starting $demo_key demo..."
        echo "Controls: WASD=scroll, Space=pause, Escape=quit"
        echo ""
    else
        echo ""
        echo "Starting $demo_key demo..."
        echo ""
    fi

    python -m "$module"
}

# Check if a demo was specified as argument
if [[ -n "$1" ]]; then
    if [[ "$1" == "--list" ]] || [[ "$1" == "-l" ]]; then
        show_menu
        exit 0
    fi
    run_demo "$1"
    exit $?
fi

# Interactive mode
while true; do
    show_menu
    read -p "Select a demo (number or name): " choice

    # Handle quit
    if [[ "$choice" == "q" ]] || [[ "$choice" == "Q" ]]; then
        echo "Goodbye!"
        exit 0
    fi

    # Handle numeric choice
    if [[ "$choice" =~ ^[0-9]+$ ]]; then
        # Get the Nth key
        i=1
        for key in "${!DEMOS[@]}"; do
            if [[ "$i" == "$choice" ]]; then
                run_demo "$key"
                echo ""
                read -p "Press Enter to continue..."
                break
            fi
            ((i++))
        done
    else
        # Handle name choice
        if [[ -n "${DEMOS[$choice]}" ]]; then
            run_demo "$choice"
            echo ""
            read -p "Press Enter to continue..."
        else
            echo "Invalid choice: $choice"
            echo ""
        fi
    fi
done
