# Spatial AoE - Tactical Combat

Tactical combat with efficient spatial queries for AoE attacks and targeting.

## Features Demonstrated

- **create_spatial_index_2d()** - Factory function with auto-observer registration
- **query_circle()** - Area of effect attacks
- **query_rectangle()** - Zone detection
- **query_nearest()** - Targeting nearest enemy
- **distance_2d()** - Distance calculation utility
- **Position2D** - Built-in monitored position component
- **QuadTreeBounds** - Spatial bounds configuration

## Running

```bash
cd /path/to/relics
source .venv/bin/activate
python demos/spatial_aoe/main.py
```

## Key Concepts

### Creating a Spatial Index

Use the factory function for easy setup:

```python
from relics.addons.spatial import (
    Position2D,
    QuadTreeBounds,
    create_spatial_index_2d,
)

# QuadTreeBounds uses center + half-extents
# This creates a 0-100 x 0-100 region (center at 50,50, extends 50 in each direction)
spatial_index = create_spatial_index_2d(
    world,
    bounds=QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50),
    materialized=True,           # Use QuadTree (faster queries)
    auto_register_observer=True, # Auto-update on position changes
)
```

### Circle Query (AoE)

Find all entities within a radius:

```python
for entity in spatial_index.query_circle(target_x, target_y, radius):
    # Apply damage to entities in blast radius
    health = entity.get_component(Health)
    pos = entity.get_component(Position2D)

    # Calculate distance for damage falloff
    dist = distance_2d(target_x, target_y, pos.x, pos.y)
    damage_multiplier = 1.0 - (dist / radius)
    health.current -= int(base_damage * damage_multiplier)
```

### Rectangle Query (Zone Detection)

Find entities in a rectangular area:

```python
for entity in spatial_index.query_rectangle(min_x, min_y, max_x, max_y):
    unit = entity.get_component(Unit)
    print(f"{unit.name} is in the zone")
```

### Nearest Query (Targeting)

Find the closest entities to a point:

```python
# Returns list of (entity, distance) tuples
nearest = spatial_index.query_nearest(my_x, my_y, count=3)

for entity, distance in nearest:
    unit = entity.get_component(Unit)
    print(f"{unit.name} at distance {distance}")
```

### Using Position2D

The spatial addon provides a pre-built monitored position component:

```python
from relics.addons.spatial import Position2D

# Position2D is already @monitored, so changes trigger index updates
world.register_prefab("unit", {
    Position2D: Position2D(x=0.0, y=0.0),
    # ... other components
})
```

### Distance Calculation

Use the utility function for distance:

```python
from relics.addons.spatial import distance_2d

dist = distance_2d(x1, y1, x2, y2)
```

## How It Works

1. **Index Creation**: A QuadTree-based spatial index is created for the battlefield
2. **Observer Registration**: The factory auto-registers an observer to update the index when positions change
3. **Unit Spawning**: Units are spawned and automatically added to the spatial index
4. **Spatial Queries**: Combat actions use spatial queries:
   - **Zone Detection**: `query_rectangle()` finds units in areas
   - **Targeting**: `query_nearest()` finds closest enemies
   - **AoE**: `query_circle()` finds targets in blast radius

## Performance

The materialized spatial index uses a QuadTree:
- Insert/Update/Remove: O(log n)
- Range queries: O(log n + k) where k is result count
- Nearest queries: O(n) in current implementation

For large numbers of entities, the QuadTree significantly outperforms brute-force O(n) queries.

## Demo Scenario

1. Two teams (Red vs Blue) spawn on opposite sides
2. Zone detection shows units in different battlefield areas
3. Each team leader finds their nearest enemies
4. Red mage casts fireball at Blue team cluster
5. Blue mage retaliates (if still alive)
6. Final survivor count determines winner

## Learning Progression

This is the final demo in the series:

1. [hello_ecs](../hello_ecs/) - Basic ECS concepts
2. [chain_reaction](../chain_reaction/) - Observers and events
3. [inventory_tree](../inventory_tree/) - Relationships and hierarchy
4. **spatial_aoe** (this demo) - Spatial indexing
