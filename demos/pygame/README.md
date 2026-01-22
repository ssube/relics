# Relics ECS - Ecosystem Demo

A standalone Pygame demo showcasing the Relics ECS framework with an ecosystem simulation.

## Overview

This demo features a simple ecosystem where rabbits seek flowers and flee from foxes. It demonstrates core ECS concepts including:

- **Components**: Position, Velocity, AI state, markers
- **Systems**: AI behavior, movement, collision detection, rendering
- **Prefabs**: Entity templates for quick spawning
- **Queries**: Finding entities by component composition

## Installation

Install pygame-ce as an optional dependency:

```bash
pip install -e ".[demo]"
```

This installs [pygame-ce](https://pyga.me/) (the community edition fork of pygame).

## Running the Demo

```bash
python -m demo.main
```

Or directly:

```bash
python demo/main.py
```

## Controls

| Key | Action |
|-----|--------|
| W | Scroll camera up |
| A | Scroll camera left |
| S | Scroll camera down |
| D | Scroll camera right |
| Shift | Hold for 2x camera speed |
| Space | Pause/Resume simulation |
| Escape | Quit demo |

## World

- **Viewport**: 800x600 pixels
- **World Size**: 2000x2000 pixels (scrollable)
- **Target FPS**: 60

## Entities

| Entity | Count | Size | Color | Behavior |
|--------|-------|------|-------|----------|
| Rabbit | 10-15 | 16x16 | White | Seek flowers, flee foxes |
| Fox | 5-10 | 32x32 | Red | Chase rabbits until out of range |
| Tree | 20-30 | 32x32 | Brown | Static obstacle |
| Stone | 10-15 | 16x16 | Grey | Static obstacle |
| Flower | 10-20 | 16x16 | Purple | Consumable, respawns when eaten |

## AI Behavior

### Rabbits
1. **Flee**: If a fox is within 150 pixels, move away from it
2. **Seek**: If no threat, move toward the nearest flower
3. **Idle**: If no flowers exist, gradually slow down

### Foxes
1. **Chase**: If a rabbit is within 200 pixels, pursue it
2. **Lose Target**: If the chased rabbit moves beyond 200 pixels, stop chasing
3. **Idle**: If no rabbits nearby, gradually slow down

## Interactions

- **Fox catches Rabbit**: Rabbit respawns at a safe location (300+ pixels from all foxes)
- **Rabbit reaches Flower**: Flower is consumed and respawns at a random location

## File Structure

```
demo/
├── __init__.py      # Package marker
├── main.py          # Entry point: Pygame init, game loop
├── config.py        # Constants (sizes, counts, colors, speeds)
├── components.py    # ECS components (Position, Velocity, AI states)
├── systems.py       # ECS systems (AI, Movement, Collision, Render)
├── prefabs.py       # Prefab registration and spawning
├── camera.py        # Scrolling viewport camera
└── README.md        # This file
```

## Architecture

The demo follows clean ECS principles:

1. **Components** are pure data containers with no logic
2. **Systems** process entities that match specific component queries
3. **Prefabs** define entity templates for consistent spawning
4. **The World** manages all entities, components, and systems

### System Execution Order

1. `RabbitAISystem` - Calculates rabbit velocities based on threats/goals
2. `FoxAISystem` - Calculates fox velocities based on chase targets
3. `CameraSystem` - Converts camera input to velocity
4. `MovementSystem` - Applies velocities to positions
5. `BoundsSystem` - Clamps positions to world bounds
6. `CollisionSystem` - Handles fox-rabbit and rabbit-flower interactions

The `InputSystem` and `RenderSystem` are special non-ECS systems that interface directly with Pygame.
