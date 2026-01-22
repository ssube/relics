# Spatial Index Architecture

This document describes the internal architecture of the spatial indexing addon.

## Module Structure

```
spatial/
├── __init__.py          # Public API exports
├── components.py        # Position2D, Position3D, Bounds2D, AABB
├── types.py             # Circle, Rectangle, Sphere, Box, distance functions
├── quadtree.py          # QuadTree data structure for 2D
├── octree.py            # Octree data structure for 3D
├── index.py             # SpatialIndexView2D, Lazy/Materialized implementations
├── index3d.py           # SpatialIndexView3D, Lazy/Materialized implementations
├── observer.py          # Auto-update observers
├── factory.py           # create_spatial_index_2d/3d helpers
├── README.md            # Main documentation
└── docs/                # Additional documentation
    ├── architecture.md  # This file
    └── performance.md   # Performance tuning guide
```

## Class Hierarchy

### Index Classes

```
IndexView (from relics.index)
└── SpatialIndexView2D (abstract)
    ├── query_circle()
    ├── query_rectangle()
    ├── query_region()
    ├── query_nearest()
    │
    ├── LazySpatialIndex2D
    │   └── Brute-force O(n) implementation
    │
    └── MaterializedSpatialIndex2D
        └── QuadTree-backed O(log n) implementation

SpatialIndexView3D (abstract)
    ├── query_sphere()
    ├── query_box()
    ├── query_region()
    ├── query_nearest()
    │
    ├── LazySpatialIndex3D
    │   └── Brute-force O(n) implementation
    │
    └── MaterializedSpatialIndex3D
        └── Octree-backed O(log n) implementation
```

### Observer Classes

```
ComponentObserver (from relics.observer)
├── SpatialIndexObserver2D
│   ├── on_component_added()   → add_entity + bind
│   ├── on_component_changed() → update
│   └── on_component_removed() → remove_entity
│
└── SpatialIndexObserver3D
    └── Same pattern for 3D
```

## Data Structures

### QuadTree

The QuadTree divides 2D space into four quadrants recursively.

```
         +-------+-------+
         |  NW   |  NE   |
         |   0   |   1   |
         +-------+-------+
         |  SW   |  SE   |
         |   2   |   3   |
         +-------+-------+
```

**QuadTreeBounds**: Defines a rectangular region using center point and half-extents.
- `center_x`, `center_y`: Center of the region
- `half_width`, `half_height`: Distance from center to edge

**QuadTreeNode**: A node in the tree containing:
- `bounds`: The spatial region this node covers
- `entities`: Dict mapping entity IDs to (x, y) positions
- `children`: Optional list of 4 child nodes [NW, NE, SW, SE]
- `max_entities`: Threshold before subdivision
- `max_depth`: Maximum tree depth
- `depth`: Current depth

**Subdivision Logic**:
1. When `len(entities) > max_entities` and `depth < max_depth`
2. Create 4 child nodes with subdivided bounds
3. Redistribute all entities to appropriate children
4. Clear parent's entity dict

### Octree

The Octree extends the QuadTree concept to 3D with 8 octants.

```
     Front Face        Back Face
    +-------+-------+ +-------+-------+
    |   4   |   5   | |   0   |   1   |
    +-------+-------+ +-------+-------+
    |   6   |   7   | |   2   |   3   |
    +-------+-------+ +-------+-------+
```

**Octant numbering** (binary: ZYX):
- 0 = -X, -Y, -Z (back-bottom-left)
- 1 = +X, -Y, -Z (back-bottom-right)
- 2 = -X, +Y, -Z (back-top-left)
- 3 = +X, +Y, -Z (back-top-right)
- 4 = -X, -Y, +Z (front-bottom-left)
- 5 = +X, -Y, +Z (front-bottom-right)
- 6 = -X, +Y, +Z (front-top-left)
- 7 = +X, +Y, +Z (front-top-right)

## Query Regions

All query regions implement the `SpatialRegion` protocol:

```python
class SpatialRegion(ABC):
    @abstractmethod
    def contains_point(self, x: float, y: float, z: float = 0) -> bool:
        """Check if a point is inside this region."""

    @abstractmethod
    def intersects_bounds(
        self,
        min_x: float, min_y: float, min_z: float,
        max_x: float, max_y: float, max_z: float,
    ) -> bool:
        """Check if this region intersects an axis-aligned bounding box."""
```

**2D Regions**:
- `Circle`: Point-radius distance check
- `Rectangle`: Min/max bounds check

**3D Regions**:
- `Sphere`: Point-radius distance check in 3D
- `Box`: Min/max bounds check in 3D

## Lazy vs Materialized

### Lazy Index

```python
class LazySpatialIndex2D:
    def query_circle(self, cx, cy, radius):
        # Iterate ALL entities every time
        for entity_id, components in self._world._entities.items():
            if self._component_type in components:
                x, y = self._position_extractor(components[self._component_type])
                if distance_2d(cx, cy, x, y) <= radius:
                    yield Entity(self._world, entity_id)
```

- **Pros**: No memory overhead, always current, no bounds required
- **Cons**: O(n) every query

### Materialized Index

```python
class MaterializedSpatialIndex2D:
    def __init__(self, ...):
        self._quadtree = QuadTree(bounds, ...)
        self._initialized = False

    def _ensure_initialized(self):
        if not self._initialized:
            self._rebuild()
            self._initialized = True

    def query_circle(self, cx, cy, radius):
        self._ensure_initialized()
        circle = Circle(cx, cy, radius)
        for entity_id in self._quadtree.query(circle):
            yield Entity(self._world, entity_id)
```

- **Pros**: O(log n + k) queries, efficient for large datasets
- **Cons**: Memory overhead, requires bounds, needs updates

## Observer Integration

The spatial observer keeps materialized indexes synchronized:

```python
class SpatialIndexObserver2D(ComponentObserver):
    component_type = Position2D  # Set dynamically

    def on_component_added(self, entity, component):
        # Bind for change tracking (enables on_component_changed)
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)
        self._spatial_index.add_entity(entity.id)

    def on_component_changed(self, entity, old_value, new_value):
        self._spatial_index.update(entity.id)

    def on_component_removed(self, entity, component):
        self._spatial_index.remove_entity(entity.id)
```

**Important**: The observer is dynamically created with the correct `component_type`:

```python
def create_spatial_observer_2d(index, component_type):
    # Create subclass with component_type set
    observer_class = type(
        f"SpatialIndexObserver2D_{component_type.__name__}",
        (SpatialIndexObserver2D,),
        {"component_type": component_type},
    )
    return observer_class(index)
```

## Monitored Component Binding

For change tracking to work, components must be bound to the world:

1. **During Spawn**: World automatically binds monitored components
2. **During Add**: `_add_component` binds monitored components
3. **During Rebuild**: Index binds existing components

The binding connects the component to the world's change notification system:

```python
# In monitored component's __setattr__:
def monitored_setattr(self, name, value):
    if self._monitored_world is not None:
        old_value = copy.copy(self)
        object.__setattr__(self, name, value)
        self._notify_change(old_value, self)  # Queues OnComponentChanged
```

## Query Execution Flow

### Circle Query on MaterializedSpatialIndex2D

```
1. query_circle(cx, cy, radius)
   │
2. _ensure_initialized()
   │  └─ _rebuild() if not initialized
   │        └─ Iterates world entities
   │        └─ Inserts into QuadTree
   │        └─ Binds monitored components
   │
3. Create Circle region
   │
4. _quadtree.query(circle)
   │  └─ Recursive descent
   │        ├─ Check if node bounds intersect circle
   │        │     └─ Skip entire subtree if no intersection
   │        ├─ Check each entity in node
   │        │     └─ Yield if circle.contains_point(x, y)
   │        └─ Recurse into children
   │
5. For each entity_id from QuadTree:
   │  └─ Verify entity still exists in world
   │  └─ Yield Entity handle
```

## Thread Safety

The spatial index addon is **not thread-safe**. All operations should occur on the same thread as the World.

For concurrent access:
- Use separate World instances per thread
- Or implement external synchronization
- Or use read-only snapshots for queries

## Memory Layout

```
MaterializedSpatialIndex2D
├── _world: World reference
├── _component_type: Type[Component]
├── _position_extractor: Callable
├── _quadtree: QuadTree
│   ├── _bounds: QuadTreeBounds
│   ├── _root: QuadTreeNode
│   │   ├── bounds: QuadTreeBounds
│   │   ├── entities: Dict[EntityId, (float, float)]
│   │   └── children: Optional[List[QuadTreeNode]]
│   └── _entity_positions: Dict[EntityId, (float, float)]
└── _initialized: bool
```

The `_entity_positions` dict in QuadTree enables O(1) position lookups for updates,
avoiding tree traversal to find an entity's current location.
