# Performance Tuning Guide

This guide covers performance optimization for the spatial indexing addon.

## Choosing an Index Type

### When to Use Lazy Index

Use `LazySpatialIndex2D/3D` when:
- Entity count is small (<100 entities)
- Queries are infrequent (once per second or less)
- Entity positions change very frequently
- No fixed world bounds are known
- Memory is constrained

```python
# Good for small, dynamic scenarios
index = LazySpatialIndex2D(world, Position2D)
```

### When to Use Materialized Index

Use `MaterializedSpatialIndex2D/3D` when:
- Entity count is large (>100 entities)
- Queries are frequent (every frame)
- Entity positions are relatively stable
- World bounds are known
- Query performance is critical

```python
# Good for large, stable scenarios
index = create_spatial_index_2d(
    world,
    bounds=QuadTreeBounds(500, 500, 500, 500),
)
```

## QuadTree/Octree Tuning

### max_entities_per_node

Controls when a node subdivides.

| Value | Effect |
|-------|--------|
| Lower (4-8) | Deeper tree, better query locality, more memory |
| Higher (16-32) | Shallower tree, faster inserts, linear scan per node |

```python
# For query-heavy workloads (more subdivisions)
index = MaterializedSpatialIndex2D(
    world, Position2D, bounds,
    max_entities_per_node=4,
)

# For insert-heavy workloads (fewer subdivisions)
index = MaterializedSpatialIndex2D(
    world, Position2D, bounds,
    max_entities_per_node=32,
)
```

### max_depth

Controls maximum tree depth.

| Value | Effect |
|-------|--------|
| Lower (4-6) | Faster inserts, may have more entities per leaf |
| Higher (8-12) | Better spatial locality, more overhead for deep trees |

```python
# For uniformly distributed entities
max_depth = 8  # Default, good balance

# For clustered entities (prevent over-subdivision)
max_depth = 6

# For very large worlds with sparse entities
max_depth = 12
```

### Bounds Selection

Choose bounds that tightly fit your world:

```python
# Too large - wasted subdivision levels
bad_bounds = QuadTreeBounds(0, 0, 100000, 100000)

# Just right - entities fill the space
good_bounds = QuadTreeBounds(500, 500, 500, 500)  # 0-1000 range
```

**Entities outside bounds are not indexed!** Ensure bounds cover all possible positions.

## Query Optimization

### Use ID Queries for Set Operations

When combining with other queries, use `*_ids` methods:

```python
# Slower - creates Entity objects
nearby = set(index.query_circle(x, y, r))
enemies = set(world.query().with_all([Enemy]).execute_entities())
result = nearby & enemies  # Set of entities

# Faster - uses lightweight IDs
nearby_ids = set(index.query_circle_ids(x, y, r))
enemy_ids = set(world.query().with_all([Enemy]).execute())
result_ids = nearby_ids & enemy_ids  # Set of IDs
```

### Batch Queries

If querying multiple regions, batch them:

```python
# Less efficient - multiple independent queries
for tower in towers:
    enemies = list(index.query_circle(tower.x, tower.y, tower.range))
    process(tower, enemies)

# More efficient - single large query + filtering
all_tower_positions = [(t.x, t.y, t.range) for t in towers]
max_range = max(r for _, _, r in all_tower_positions)

# One query for bounding region
candidates = set(index.query_rectangle(
    min_x - max_range, min_y - max_range,
    max_x + max_range, max_y + max_range
))

# Filter per tower
for tower in towers:
    nearby = [e for e in candidates
              if distance(tower.x, tower.y, e.x, e.y) <= tower.range]
    process(tower, nearby)
```

### Nearest Neighbor Optimization

The current nearest neighbor implementation scans all entities. For better performance:

```python
# Instead of finding all 100 nearest
results = index.query_nearest(x, y, count=100)

# Consider a circle query with estimated radius
estimated_radius = 200  # Based on entity density
nearby = list(index.query_circle(x, y, estimated_radius))
nearby.sort(key=lambda e: distance(x, y, e.get_component(Position2D)))
results = nearby[:100]
```

## Update Strategies

### Automatic Updates (Observer)

Best for: Most use cases where entities move occasionally.

```python
index = create_spatial_index_2d(
    world,
    bounds=bounds,
    auto_register_observer=True,  # Default
)
```

Updates trigger on:
- Component added (during spawn or add_component)
- Component changed (via @monitored setattr)
- Component removed

### Manual Updates

Best for: Batch position changes, physics simulations.

```python
index = create_spatial_index_2d(
    world,
    bounds=bounds,
    auto_register_observer=False,
)

# After physics step updates many positions
for entity in moved_entities:
    index.update(entity.id)

# Or rebuild entirely
index.invalidate()
```

### Deferred Updates

For many rapid changes, defer updates:

```python
# Collect changed entities
changed_entities = []

for entity in entities:
    pos = entity.get_component(Position2D)
    pos.x += vel.x * dt
    pos.y += vel.y * dt
    changed_entities.append(entity.id)

# Batch update at end of frame
for entity_id in changed_entities:
    index.update(entity_id)
```

## Memory Optimization

### Index Invalidation

For dynamic entity sets, invalidate instead of updating:

```python
# Many entities added/removed
for _ in range(1000):
    world.spawn("enemy", {...})

# One rebuild instead of 1000 inserts
index.invalidate()
```

### Lazy Initialization

Indexes initialize lazily on first access:

```python
# Create index (no initialization yet)
index = create_spatial_index_2d(world, bounds=bounds)

# Spawn many entities (no index updates)
for _ in range(10000):
    world.spawn("entity", {...})

# First query triggers initialization
results = index.query_circle(500, 500, 100)  # Builds tree here
```

### Shared Position Components

Non-monitored components share instances across entities:

```python
# Without @monitored - shared instances, lower memory
@dataclass
class StaticPosition(Component):
    x: float
    y: float

# With @monitored - unique instances, change tracking
@monitored
@dataclass
class DynamicPosition(Component):
    x: float
    y: float
```

Use non-monitored for static entities that never move.

## Benchmarking

### Measure Query Performance

```python
import time

def benchmark_query(index, iterations=100):
    start = time.perf_counter()
    for _ in range(iterations):
        list(index.query_circle(500, 500, 100))
    elapsed = time.perf_counter() - start
    return (elapsed / iterations) * 1000  # ms per query

print(f"Query time: {benchmark_query(index):.3f}ms")
```

### Measure Update Performance

```python
def benchmark_update(index, entities, iterations=10):
    start = time.perf_counter()
    for _ in range(iterations):
        for e in entities:
            index.update(e.id)
    elapsed = time.perf_counter() - start
    return (elapsed / iterations / len(entities)) * 1000  # ms per update

print(f"Update time: {benchmark_update(index, entities):.3f}ms per entity")
```

## Performance Targets

Based on benchmarks with reference hardware:

| Operation | 1K Entities | 10K Entities | 100K Entities |
|-----------|-------------|--------------|---------------|
| Circle Query | <1ms | <2ms | <5ms |
| Sphere Query | <2ms | <5ms | <10ms |
| Nearest (k=10) | <5ms | <20ms | <50ms |
| Single Update | <0.1ms | <0.1ms | <0.2ms |
| Full Rebuild | <10ms | <100ms | <1000ms |

## Common Pitfalls

### 1. Querying Before Tick

```python
entity = world.spawn("enemy", {Position2D: Position2D(100, 100)})
# Wrong - observer hasn't processed yet
results = list(index.query_circle(100, 100, 10))  # Empty!

# Correct
world.tick(0)  # Process observers
results = list(index.query_circle(100, 100, 10))  # Contains entity
```

### 2. Modifying Position Without Tick

```python
pos.x = 500
# Wrong - change notification queued but not processed
results = list(index.query_circle(500, 500, 10))  # Empty!

# Correct
pos.x = 500
world.tick(0)  # Process change notifications
results = list(index.query_circle(500, 500, 10))  # Contains entity
```

### 3. Entities Outside Bounds

```python
bounds = QuadTreeBounds(500, 500, 500, 500)  # 0-1000 range
index = create_spatial_index_2d(world, bounds=bounds)

# Entity at (1500, 1500) is outside bounds - not indexed!
world.spawn("entity", {Position2D: Position2D(1500, 1500)})
```

### 4. Forgetting to Enable Monitoring

```python
@dataclass  # Missing @monitored!
class Position(Component):
    x: float
    y: float

# Changes won't trigger on_component_changed
pos.x = 500  # Index not updated!
```

Add `@monitored` decorator:

```python
@monitored
@dataclass
class Position(Component):
    x: float
    y: float
```
