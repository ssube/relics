# Spatial Index Addon

Efficient spatial indexing for the Relics ECS framework, supporting 2D (QuadTree) and 3D (Octree) spatial queries.

## Features

- **2D Spatial Indexing** with QuadTree data structure
- **3D Spatial Indexing** with Octree data structure
- **Lazy and Materialized** index implementations
- **Automatic Updates** via observer integration
- **Multiple Query Types**: circle, rectangle, sphere, box, nearest neighbor
- **Custom Position Components** via position extractors
- **QueryBuilder Integration** with `with_index()`

## Quick Start

```python
from relics import World
from relics.addons.spatial import (
    Position2D,
    QuadTreeBounds,
    create_spatial_index_2d,
)

# Create world and register prefab
world = World()
world.register_prefab("enemy", {Position2D: Position2D(x=0, y=0)})

# Create spatial index
index = create_spatial_index_2d(
    world,
    bounds=QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500),
)

# Spawn entities
for i in range(100):
    world.spawn("enemy", {Position2D: Position2D(x=i * 10, y=i * 10)})

# Query nearby entities
for entity in index.query_circle(center_x=250, center_y=250, radius=100):
    print(f"Nearby: {entity.id}")

# Find k-nearest neighbors
nearest = index.query_nearest(x=500, y=500, count=5)
for entity, distance in nearest:
    print(f"{entity.id} at distance {distance:.2f}")
```

## Components

### Position2D

2D position component with change tracking.

```python
from relics.addons.spatial import Position2D

# Use in prefab
world.register_prefab("player", {
    Position2D: Position2D(x=100, y=200)
})

# Modify position (automatically tracked)
entity = world.spawn("player")
pos = entity.get_component(Position2D)
pos.x = 150  # Triggers index update
pos.y = 250
world.tick(0)  # Process updates
```

### Position3D

3D position component with change tracking.

```python
from relics.addons.spatial import Position3D

world.register_prefab("ship", {
    Position3D: Position3D(x=0, y=0, z=100)
})
```

### Bounds2D / AABB

Bounding box components for area-based queries.

```python
from relics.addons.spatial import Bounds2D, AABB

# 2D bounding box
bounds = Bounds2D(center_x=50, center_y=50, half_width=25, half_height=15)
print(bounds.min_x, bounds.max_x)  # 25, 75

# 3D axis-aligned bounding box
aabb = AABB(center_x=0, center_y=0, center_z=0,
            half_width=10, half_height=10, half_depth=10)
```

## Index Types

### Lazy Index

Performs brute-force O(n) queries on each access. Best for:
- Small entity counts (<100)
- Infrequent queries
- Rapidly changing entity sets

```python
from relics.addons.spatial import LazySpatialIndex2D

index = LazySpatialIndex2D(world, Position2D)
# No bounds required - works with any position
```

### Materialized Index

Maintains a QuadTree/Octree for O(log n) queries. Best for:
- Large entity counts (1000+)
- Frequent queries
- Relatively stable entity positions

```python
from relics.addons.spatial import MaterializedSpatialIndex2D, QuadTreeBounds

bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
index = MaterializedSpatialIndex2D(world, Position2D, bounds)
```

## Factory Functions

### create_spatial_index_2d

Creates a 2D spatial index with optional auto-observer registration.

```python
index = create_spatial_index_2d(
    world,
    component_type=Position2D,           # Default
    position_extractor=None,             # Custom (x, y) extractor
    materialized=True,                   # Use QuadTree
    auto_register_observer=True,         # Auto-update on changes
    bounds=QuadTreeBounds(...),          # Required for materialized
    max_entities_per_node=8,             # QuadTree tuning
    max_depth=8,                         # QuadTree tuning
)
```

### create_spatial_index_3d

Creates a 3D spatial index.

```python
from relics.addons.spatial import create_spatial_index_3d, OctreeBounds

index = create_spatial_index_3d(
    world,
    bounds=OctreeBounds(
        center_x=500, center_y=500, center_z=500,
        half_width=500, half_height=500, half_depth=500
    ),
)
```

## Query Methods

### 2D Queries

```python
# Circle query - entities within radius
for entity in index.query_circle(center_x=100, center_y=100, radius=50):
    ...

# Rectangle query - entities within bounds
for entity in index.query_rectangle(min_x=0, min_y=0, max_x=200, max_y=200):
    ...

# Custom region query
from relics.addons.spatial import Circle, Rectangle
circle = Circle(center_x=100, center_y=100, radius=50)
for entity in index.query_region(circle):
    ...

# Nearest neighbor query
results = index.query_nearest(x=100, y=100, count=10)
for entity, distance in results:
    print(f"{entity.id}: {distance:.2f}")

# Get entity IDs only (for set operations)
ids = set(index.query_circle_ids(100, 100, 50))
```

### 3D Queries

```python
# Sphere query
for entity in index.query_sphere(center_x=100, center_y=100, center_z=100, radius=50):
    ...

# Box query
for entity in index.query_box(
    min_x=0, min_y=0, min_z=0,
    max_x=200, max_y=200, max_z=200
):
    ...

# Custom region query
from relics.addons.spatial import Sphere, Box
sphere = Sphere(center_x=100, center_y=100, center_z=100, radius=50)
for entity in index.query_region(sphere):
    ...
```

## Custom Position Components

Use any component as a position source with a custom extractor.

```python
from pydantic.dataclasses import dataclass
from relics import Component
from relics.monitored import monitored

@monitored  # Required for change tracking
@dataclass
class Transform(Component):
    pos_x: float
    pos_y: float
    rotation: float
    scale: float

index = create_spatial_index_2d(
    world,
    component_type=Transform,
    position_extractor=lambda t: (t.pos_x, t.pos_y),
    bounds=QuadTreeBounds(500, 500, 500, 500),
)
```

## QueryBuilder Integration

Combine spatial queries with component queries.

```python
from relics.addons.spatial import Position2D, create_spatial_index_2d

# Create index
index = create_spatial_index_2d(world, bounds=QuadTreeBounds(500, 500, 500, 500))

# Get nearby entity IDs
nearby_ids = set(index.query_circle_ids(player_x, player_y, attack_range))

# Filter to only enemies using set intersection
nearby_enemies = [
    e for e in world.query().with_all([Enemy]).execute_entities()
    if e.id in nearby_ids
]

# Or use with_index() for automatic filtering
all_indexed = list(
    world.query()
    .with_all([Enemy])
    .with_index(index)
    .execute_entities()
)
```

## Dual Index Pattern

Apply both 2D and 3D indexes to the same world for different views.

```python
# 3D world with Position3D entities
world.register_prefab("ship", {Position3D: Position3D(x=0, y=0, z=0)})

# Full 3D spatial index
index_3d = create_spatial_index_3d(
    world,
    bounds=OctreeBounds(500, 500, 250, 500, 500, 250),
)

# Top-down 2D view (ignores Z coordinate)
index_2d = create_spatial_index_2d(
    world,
    component_type=Position3D,
    position_extractor=lambda c: (c.x, c.y),  # Ignore Z
    bounds=QuadTreeBounds(500, 500, 500, 500),
)

# Ships at same X,Y but different Z
ship1 = world.spawn("ship", {Position3D: Position3D(x=100, y=100, z=50)})
ship2 = world.spawn("ship", {Position3D: Position3D(x=100, y=100, z=200)})

# 2D query finds both (same X,Y)
list(index_2d.query_circle(100, 100, 10))  # [ship1, ship2]

# 3D query can distinguish by height
list(index_3d.query_sphere(100, 100, 50, 30))   # [ship1]
list(index_3d.query_sphere(100, 100, 200, 30))  # [ship2]
```

## Manual Index Updates

When `auto_register_observer=False`, manage updates manually.

```python
index = create_spatial_index_2d(
    world,
    bounds=QuadTreeBounds(500, 500, 500, 500),
    auto_register_observer=False,
)

# Add entity manually
entity = world.spawn("enemy", {Position2D: Position2D(x=100, y=100)})
index.add_entity(entity.id)

# Update after position change
pos = entity.get_component(Position2D)
pos.x = 200
index.update(entity.id)

# Remove entity
index.remove_entity(entity.id)

# Force full rebuild
index.invalidate()
```

## Performance Characteristics

| Operation | Lazy Index | Materialized Index |
|-----------|------------|-------------------|
| Query | O(n) | O(log n + k) |
| Insert | O(1) | O(log n) |
| Update | O(1) | O(log n) |
| Remove | O(1) | O(log n) |
| Memory | O(1) | O(n) |

Where n = total entities, k = entities in result.

### Benchmarks (10k entities)

- Materialized circle query: <5ms
- Materialized sphere query: <10ms
- Nearest neighbor (k=10): <30ms
- Bulk insert: ~200ms

### Tuning Parameters

```python
index = MaterializedSpatialIndex2D(
    world,
    Position2D,
    bounds,
    max_entities_per_node=16,  # Higher = shallower tree, faster insert
    max_depth=10,              # Higher = deeper tree, better query locality
)
```

## API Reference

### Query Regions

| Class | Constructor | Description |
|-------|-------------|-------------|
| `Circle` | `(center_x, center_y, radius)` | 2D circular region |
| `Rectangle` | `(min_x, min_y, max_x, max_y)` | 2D rectangular region |
| `Sphere` | `(center_x, center_y, center_z, radius)` | 3D spherical region |
| `Box` | `(min_x, min_y, min_z, max_x, max_y, max_z)` | 3D box region |

### Index Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `count()` | `int` | Total entities in index |
| `get_entity_ids()` | `Set[EntityId]` | All indexed entity IDs |
| `query_circle(...)` | `Iterator[Entity]` | Entities in circle |
| `query_circle_ids(...)` | `Iterator[EntityId]` | Entity IDs in circle |
| `query_rectangle(...)` | `Iterator[Entity]` | Entities in rectangle |
| `query_rectangle_ids(...)` | `Iterator[EntityId]` | Entity IDs in rectangle |
| `query_region(region)` | `Iterator[Entity]` | Entities in custom region |
| `query_region_ids(region)` | `Iterator[EntityId]` | Entity IDs in custom region |
| `query_nearest(x, y, count)` | `List[(Entity, float)]` | K-nearest neighbors |
| `add_entity(id)` | `None` | Add entity to index |
| `remove_entity(id)` | `None` | Remove entity from index |
| `update(id)` | `None` | Update entity position |
| `invalidate()` | `None` | Force full rebuild |

### 3D-Specific Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `query_sphere(...)` | `Iterator[Entity]` | Entities in sphere |
| `query_sphere_ids(...)` | `Iterator[EntityId]` | Entity IDs in sphere |
| `query_box(...)` | `Iterator[Entity]` | Entities in box |
| `query_box_ids(...)` | `Iterator[EntityId]` | Entity IDs in box |
| `query_nearest(x, y, z, count)` | `List[(Entity, float)]` | K-nearest in 3D |
