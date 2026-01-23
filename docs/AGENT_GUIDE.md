# Relics Agent Guide

A comprehensive reference for AI code agents working with the Relics ECS framework.

## Quick Reference

### Project Overview

Relics is a Python ECS (Entity-Component-System) framework with graph database semantics.

**Tech Stack:**
- Python 3.11+
- Pydantic for dataclass validation
- pytest / pytest-cov for testing

### Import Patterns

```python
# Core library
from relics import (
    World, Entity, EntityId,
    Component, Edge, CustomEvent,
    QueryBuilder,
    System, Frequency, RunOrder,
    Observer, OnEntityCreated, OnEntityDestroyed,
    OnComponentAdded, OnComponentRemoved, OnComponentChanged,
    OnRelationshipAdded, OnRelationshipRemoved, OnCustomEvent,
    ComponentObserver, RelationshipObserver, EntityObserver,
    monitored, is_monitored,
    IndexView, LazyIndex, MaterializedIndex,
)

# Spatial addon
from relics.addons.spatial import (
    Position2D, Position3D, Bounds2D, AABB,
    Circle, Rectangle, Sphere, Box,
    distance_2d, distance_3d,
    LazySpatialIndex2D, MaterializedSpatialIndex2D,
    LazySpatialIndex3D, MaterializedSpatialIndex3D,
    create_spatial_index_2d, create_spatial_index_3d,
    QuadTreeBounds, OctreeBounds,
)

# Procedural prefabs addon
from relics.addons.procedural_prefabs import (
    ProceduralPrefabRegistry,
    HasEquipped, IsWearing, HasAttached,
    get_children, get_holder, get_root,
    destroy_with_children,
    register_edge_type, create_edge,
)
```

### Development Commands

```bash
# Virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/relics --cov-report=term-missing

# Run specific test
pytest tests/path/to/test_file.py::TestClass::test_method -v

# Type checking
mypy src/relics/

# Linting
flake8 src/relics/
```

---

## Core Library (`relics`)

### Core Types

#### EntityId
Structured entity identifier with prefab and sequence.

```python
# src/relics/types.py
class EntityId:
    prefab: str          # Prefab name entity was instantiated from
    sequence: int        # Per-prefab timestamp + collision counter

    def __str__(self) -> str: ...     # Format: '{prefab}_{sequence}'
    def __hash__(self) -> int: ...
    @staticmethod
    def parse(s: str) -> EntityId: ...  # Parse from string format
```

#### Component
Base class for all components - pure data containers with no logic.

```python
# src/relics/types.py
class Component:
    pass

# Usage with Pydantic
import pydantic

@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int
```

#### Edge
Base class for relationship edges - define typed relationships.

```python
# src/relics/types.py
class Edge:
    def validate(source: Entity, target: Entity) -> bool:
        """Validate relationship constraints. Default accepts all."""
```

#### CustomEvent
Base class for custom events - emitted via `World.emit()`.

```python
# src/relics/types.py
class CustomEvent:
    pass

@pydantic.dataclasses.dataclass
class DamageEvent(CustomEvent):
    target: EntityId
    amount: int
```

### World API

```python
# src/relics/world.py
class World:
    id: str                  # Unique world identifier
    epoch: int               # Current epoch number (property)

    # Entity Management
    def spawn(self, prefab: str, overrides: Optional[Dict[Type[Component], Component]] = None) -> Entity: ...
    def get_entity(self, entity_id: EntityId) -> Entity: ...
    def has_entity(self, entity_id: EntityId) -> bool: ...
    def remove(self, entity: Union[Entity, EntityId]) -> None: ...

    # Component Type Registry
    def register_component_type(self, component_type: Type[Component]) -> None: ...

    # Prefab Management
    def register_prefab(self, name: str, components: Dict[Type[Component], Component]) -> None: ...

    # Edge Type Registry
    def register_edge_type(self, edge_type: Type[Edge]) -> None: ...

    # Component Index
    def get_entities_with_component(self, component_type: Type[Component]) -> Set[EntityId]: ...

    # Events
    def emit(self, event: CustomEvent) -> None: ...

    # Queries
    def query(self) -> QueryBuilder: ...

    # Systems
    def register_system(self, system: System) -> None: ...

    # Observers
    def observe(self, observer: Observer) -> None: ...

    # Simulation Loop
    def tick(
        self,
        delta: float,
        *,
        include_groups: list[str] | None = None,  # Only run systems in these groups
        exclude_groups: list[str] | None = None,  # Skip systems in these groups
    ) -> None: ...  # Advance epoch, run systems, process observer queue

    # Secondary Indexes
    def create_index(self, name: str, query: QueryBuilder, watches: Optional[List[Type[Component]]] = None, materialized: bool = False) -> IndexView: ...
    def index(self, name: str) -> IndexView: ...

    # Export/Debugging
    def export_entity(self, entity_id: EntityId) -> Dict[str, Any]: ...
```

**Key Pattern:** `world.observe(observer)` - NOT `register_observer`

### Entity API

```python
# src/relics/entity.py
class Entity:
    id: EntityId             # Entity's unique identifier (property)
    prefab: str              # Prefab entity was instantiated from (property)

    # Components
    def get_component(self, component_type: Type[T]) -> T: ...
    def has_component(self, component_type: Type[Component]) -> bool: ...
    def add_component(self, component: Component) -> None: ...
    def remove_component(self, component_type: Type[Component]) -> None: ...

    # Relationships (Outgoing)
    def add_relationship(self, edge: Edge, target: EntityId) -> None: ...
    def remove_relationship(self, edge_type: Type[Edge], target: EntityId) -> None: ...
    def get_relationships(self, edge_type: Type[E]) -> List[Tuple[E, EntityId]]: ...
    def has_relationship(self, edge_type: Type[Edge], target: Optional[EntityId] = None) -> bool: ...

    # Relationships (Incoming)
    def get_incoming_relationships(self, edge_type: Type[E]) -> List[Tuple[EntityId, E]]: ...
    def has_incoming_relationship(self, edge_type: Type[Edge], source: Optional[EntityId] = None) -> bool: ...
```

### Query System

```python
# src/relics/query.py
class QueryBuilder:
    # Component Selection (chainable)
    def with_all(self, component_types: List[Type[Component]]) -> QueryBuilder: ...
    def with_any(self, component_types: List[Type[Component]]) -> QueryBuilder: ...
    def with_none(self, component_types: List[Type[Component]]) -> QueryBuilder: ...

    # Filtering
    def with_filter(self, predicate: Callable[[Entity], bool]) -> QueryBuilder: ...

    # Component Iteration
    def iterate(self, component_types: List[Type[Component]]) -> QueryBuilder: ...

    # Relationships
    def with_relationship(self, edge_type: Type[Edge], target: Optional[EntityId] = None) -> QueryBuilder: ...
    def with_incoming(self, edge_type: Type[Edge], source: Optional[EntityId] = None) -> QueryBuilder: ...

    # Secondary Indexes
    def with_index(self, index: IndexView) -> QueryBuilder: ...
    def without_index(self, index: IndexView) -> QueryBuilder: ...

    # Execution
    def execute_ids(self) -> Iterator[EntityId]: ...
    def execute_entities(self) -> Iterator[Entity]: ...
    def execute_components(self) -> Iterator[Tuple[Any, ...]]: ...  # Requires iterate()
```

**Example:**
```python
# Find all entities with Health and Position2D
for entity in world.query().with_all([Health, Position2D]).execute_entities():
    health = entity.get_component(Health)

# Iterate component arrays
for entity_id, health, pos in world.query().with_all([Health, Position2D]).iterate([Health, Position2D]).execute_components():
    print(f"{entity_id}: health={health.current}, pos=({pos.x}, {pos.y})")
```

### Observer System

```python
# src/relics/observer.py

# Base class
class Observer(ABC):
    _world: World | None

    @property
    def world(self) -> World: ...

# Entity lifecycle
class OnEntityCreated(Observer):
    prefab: ClassVar[Optional[str]] = None  # Filter for specific prefab

    @abstractmethod
    def on_entity_created(self, entity: Entity) -> None: ...

class OnEntityDestroyed(Observer):
    prefab: ClassVar[Optional[str]] = None

    @abstractmethod
    def on_entity_destroyed(self, entity: Entity) -> None: ...

# Component lifecycle
class OnComponentAdded(Observer):
    component_type: ClassVar[Type[Component]]

    @abstractmethod
    def on_component_added(self, entity: Entity, component: Component) -> None: ...

class OnComponentRemoved(Observer):
    component_type: ClassVar[Type[Component]]

    @abstractmethod
    def on_component_removed(self, entity: Entity, component: Component) -> None: ...

class OnComponentChanged(Observer):
    component_type: ClassVar[Type[Component]]

    @abstractmethod
    def on_component_changed(self, entity: Entity, component: Component, field_name: str, old_value: Any, new_value: Any) -> None: ...

# Relationship lifecycle
class OnRelationshipAdded(Observer):
    edge_type: ClassVar[Type[Edge]]

    @abstractmethod
    def on_relationship_added(self, source: Entity, edge: Edge, target: Entity) -> None: ...

class OnRelationshipRemoved(Observer):
    edge_type: ClassVar[Type[Edge]]

    @abstractmethod
    def on_relationship_removed(self, source: Entity, edge: Edge, target: Entity) -> None: ...

# Custom events
class OnCustomEvent(Observer):
    event_type: ClassVar[Type[CustomEvent]]

    @abstractmethod
    def on_event(self, event: CustomEvent) -> None: ...
```

**Multi-Event Observers (optional base methods):**
```python
class ComponentObserver(Observer):
    component_type: ClassVar[Type[Component]]

    def on_component_added(self, entity: Entity, component: Component) -> None: pass
    def on_component_changed(self, entity: Entity, component: Component, field_name: str, old_value: Any, new_value: Any) -> None: pass
    def on_component_removed(self, entity: Entity, component: Component) -> None: pass

class RelationshipObserver(Observer):
    edge_type: ClassVar[Type[Edge]]

    def on_relationship_added(self, source: Entity, edge: Edge, target: Entity) -> None: pass
    def on_relationship_removed(self, source: Entity, edge: Edge, target: Entity) -> None: pass

class EntityObserver(Observer):
    prefab: ClassVar[Optional[str]] = None

    def on_entity_created(self, entity: Entity) -> None: pass
    def on_entity_destroyed(self, entity: Entity) -> None: pass
```

### Monitored Components

The `@monitored` decorator enables change tracking on component classes.

```python
# src/relics/monitored.py
from relics import monitored, is_monitored, Component
import pydantic

@monitored
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int

# Check if a component is monitored
is_monitored(Health)  # True
is_monitored(health_instance)  # True
```

**Behavior:**
- Triggers `OnComponentChanged` observers when field values change
- Components are deep copied during spawn (not shared between entities)
- Components automatically bind to world for change tracking

**MonitoredMixin methods (added to decorated classes):**
```python
def _bind_to_world(self, world: World, entity_id: EntityId) -> None: ...
def _unbind_from_world(self) -> None: ...
def _notify_change(self, old_value: Any, new_value: Any) -> None: ...
```

### Systems

```python
# src/relics/system.py
class Frequency:
    EVERY_TICK: ClassVar[Frequency]  # Singleton

    @classmethod
    def every_n_ticks(cls, n: int) -> Frequency: ...
    @classmethod
    def fixed_interval(cls, seconds: float) -> Frequency: ...

    def should_run(self, epoch: int, delta: float) -> bool: ...

class RunOrder(Enum):
    BEFORE = auto()
    AFTER = auto()

class System(ABC):
    WILDCARD: ClassVar[Type[System]]  # Sentinel for "all systems"
    group: str = "default"            # System group for selective execution

    @property
    def world(self) -> World: ...

    @property
    def q(self) -> QueryBuilder: ...  # Convenience for fresh query builder

    @property
    def paused(self) -> bool: ...     # Whether system is paused

    @paused.setter
    def paused(self, value: bool) -> None: ...

    @abstractmethod
    def query(self) -> QueryBuilder: ...

    @abstractmethod
    def process(self, entities: List[Entity], components: List[List[Component]], delta: float) -> None: ...

    def deps(self) -> Dict[RunOrder, List[Type[System]]]:
        return {}

    def frequency(self) -> Frequency:
        return Frequency.EVERY_TICK

    def sub_systems(self) -> List[Tuple[QueryBuilder, Callable]]:
        return []
```

**Example:**
```python
class MovementSystem(System):
    def query(self) -> QueryBuilder:
        return self.q.with_all([Position2D, Velocity])

    def process(self, entities: List[Entity], components: List[List[Component]], delta: float) -> None:
        for entity in entities:
            pos = entity.get_component(Position2D)
            vel = entity.get_component(Velocity)
            pos.x += vel.dx * delta
            pos.y += vel.dy * delta

    def deps(self) -> Dict[RunOrder, List[Type[System]]]:
        return {RunOrder.AFTER: [InputSystem]}

    def frequency(self) -> Frequency:
        return Frequency.fixed_interval(0.016)  # 60 FPS
```

**System Groups:**
```python
class InputSystem(System):
    group = "input"  # Always runs, even when game is paused

class PhysicsSystem(System):
    group = "game"   # Skipped during pause

class RenderSystem(System):
    group = "render" # Always runs

# Normal gameplay - run all systems
world.tick(delta)

# Paused - skip "game" group but keep input and render
world.tick(delta, exclude_groups=["game"])

# Only run specific groups
world.tick(delta, include_groups=["input", "render"])
```

**Pausing Individual Systems:**
```python
ai_system = AISystem()
world.register_system(ai_system)

# Pause just this system (dynamically)
ai_system.paused = True   # System will be skipped during tick

# Resume
ai_system.paused = False
```

### Common Gotchas

| Issue | Explanation |
|-------|-------------|
| **Event timing** | Events are queued during operations, processed at end of `tick()` |
| **Component sharing** | Without `@monitored`, prefab components are shared between entities (same instance) |
| **Prefab components** | Components from prefabs do NOT trigger `OnComponentAdded` - use `OnEntityCreated` |
| **Lazy validation** | Entity handles validate existence when accessing, not at creation |
| **Delta required** | `world.tick(delta)` requires a delta parameter, use `tick(0)` for tests |
| **Observer method** | Use `world.observe(observer)` not `register_observer` |
| **System groups** | Default group is `"default"`. Use `include_groups`/`exclude_groups` in `tick()` to filter |
| **Paused vs groups** | `paused` property is per-system; group filtering applies to categories of systems |

---

## Spatial Index Addon (`relics.addons.spatial`)

### Position Components

All components are `@monitored` for change tracking.

```python
# src/relics/addons/spatial/components.py

# 2D Components
@monitored
class Position2D(Component):
    x: float
    y: float

@monitored
class Bounds2D(Component):
    center_x: float
    center_y: float
    half_width: float
    half_height: float

    # Properties: min_x, max_x, min_y, max_y

# 3D Components
@monitored
class Position3D(Component):
    x: float
    y: float
    z: float

@monitored
class AABB(Component):
    center_x: float
    center_y: float
    center_z: float
    half_width: float
    half_height: float
    half_depth: float

    # Properties: min_x, max_x, min_y, max_y, min_z, max_z
```

### Spatial Region Types

```python
# src/relics/addons/spatial/types.py

# Abstract base
class SpatialRegion(ABC):
    @abstractmethod
    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool: ...
    @abstractmethod
    def intersects_bounds(self, min_corner: Tuple[float, ...], max_corner: Tuple[float, ...]) -> bool: ...

# 2D Regions
class Circle(SpatialRegion):
    center_x: float
    center_y: float
    radius: float

class Rectangle(SpatialRegion):
    min_x: float
    min_y: float
    max_x: float
    max_y: float

# 3D Regions
class Sphere(SpatialRegion):
    center_x: float
    center_y: float
    center_z: float
    radius: float

class Box(SpatialRegion):
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

# Distance utilities
def distance_2d(x1: float, y1: float, x2: float, y2: float) -> float: ...
def distance_3d(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float: ...
def distance_squared_2d(...) -> float: ...  # Faster for comparisons
def distance_squared_3d(...) -> float: ...
```

### Index Types

#### 2D Indexes

```python
# src/relics/addons/spatial/index.py

# Type alias
PositionExtractor2D = Callable[[Component], Tuple[float, float]]

# Abstract base
class SpatialIndexView2D(IndexView):
    def query_circle(self, center_x: float, center_y: float, radius: float) -> Iterator[Entity]: ...
    def query_rectangle(self, min_x: float, min_y: float, max_x: float, max_y: float) -> Iterator[Entity]: ...
    def query_region(self, region: SpatialRegion) -> Iterator[Entity]: ...
    def query_nearest(self, x: float, y: float, count: int) -> List[Tuple[Entity, float]]: ...

    # ID variants
    def query_circle_ids(...) -> Iterator[EntityId]: ...
    def query_rectangle_ids(...) -> Iterator[EntityId]: ...
    def query_region_ids(...) -> Iterator[EntityId]: ...

# Lazy index - O(n) brute-force queries
class LazySpatialIndex2D(SpatialIndexView2D):
    def __init__(self, world: World, component_type: Type[Component], position_extractor: Optional[PositionExtractor2D] = None): ...
    def __iter__(self) -> Iterator[Entity]: ...
    def count(self) -> int: ...
    def get_entity_ids(self) -> Set[EntityId]: ...

# Materialized index - QuadTree O(log n) queries
class MaterializedSpatialIndex2D(SpatialIndexView2D):
    def __init__(self, world: World, component_type: Type[Component], bounds: QuadTreeBounds, position_extractor: Optional[PositionExtractor2D] = None, max_entities_per_node: int = 8, max_depth: int = 8): ...

    @property
    def bounds(self) -> QuadTreeBounds: ...

    def invalidate(self) -> None: ...      # Force rebuild on next access
    def update(self, entity_id: EntityId) -> None: ...
    def add_entity(self, entity_id: EntityId) -> None: ...
    def remove_entity(self, entity_id: EntityId) -> None: ...
```

#### 3D Indexes

```python
# src/relics/addons/spatial/index3d.py

PositionExtractor3D = Callable[[Component], Tuple[float, float, float]]

class SpatialIndexView3D(IndexView):
    def query_sphere(self, cx: float, cy: float, cz: float, radius: float) -> Iterator[Entity]: ...
    def query_box(self, min_x: float, min_y: float, min_z: float, max_x: float, max_y: float, max_z: float) -> Iterator[Entity]: ...
    def query_region(self, region: SpatialRegion) -> Iterator[Entity]: ...
    def query_nearest(self, x: float, y: float, z: float, count: int) -> List[Tuple[Entity, float]]: ...

class LazySpatialIndex3D(SpatialIndexView3D): ...
class MaterializedSpatialIndex3D(SpatialIndexView3D): ...  # Octree-based
```

### Factory Functions

```python
# src/relics/addons/spatial/factory.py

def create_spatial_index_2d(
    world: World,
    *,
    component_type: Type[Component] = Position2D,
    position_extractor: Optional[PositionExtractor2D] = None,
    materialized: bool = True,
    auto_register_observer: bool = True,
    bounds: Optional[QuadTreeBounds] = None,  # Required if materialized=True
    max_entities_per_node: int = 8,
    max_depth: int = 8,
) -> Union[LazySpatialIndex2D, MaterializedSpatialIndex2D]: ...

def create_spatial_index_3d(
    world: World,
    *,
    component_type: Type[Component] = Position3D,
    position_extractor: Optional[PositionExtractor3D] = None,
    materialized: bool = True,
    auto_register_observer: bool = True,
    bounds: Optional[OctreeBounds] = None,
    max_entities_per_node: int = 8,
    max_depth: int = 8,
) -> Union[LazySpatialIndex3D, MaterializedSpatialIndex3D]: ...
```

**QuadTreeBounds / OctreeBounds:**
```python
QuadTreeBounds = Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
OctreeBounds = Tuple[float, float, float, float, float, float]  # (min_x, min_y, min_z, max_x, max_y, max_z)
```

### Observers

```python
# src/relics/addons/spatial/observer.py

class SpatialIndexObserver2D(ComponentObserver):
    component_type: ClassVar[Type[Component]]  # Set dynamically

    def __init__(self, spatial_index: MaterializedSpatialIndex2D): ...
    def on_component_added(self, entity: Entity, component: Component) -> None: ...
    def on_component_changed(self, entity: Entity, component: Component, field_name: str, old_value: Any, new_value: Any) -> None: ...
    def on_component_removed(self, entity: Entity, component: Component) -> None: ...

def create_spatial_observer_2d(spatial_index: MaterializedSpatialIndex2D, component_type: Type[Component]) -> SpatialIndexObserver2D: ...

class SpatialIndexObserver3D(ComponentObserver): ...
def create_spatial_observer_3d(...) -> SpatialIndexObserver3D: ...
```

### Usage Example

```python
from relics import World
from relics.addons.spatial import (
    Position2D, create_spatial_index_2d, QuadTreeBounds
)

# Create world and register components
world = World()
world.register_prefab("unit", {Position2D: Position2D(x=0, y=0)})

# Create materialized spatial index
bounds: QuadTreeBounds = (-1000, -1000, 1000, 1000)
index = create_spatial_index_2d(
    world,
    component_type=Position2D,
    materialized=True,
    auto_register_observer=True,  # Auto-updates on position changes
    bounds=bounds,
)

# Spawn entities
for i in range(100):
    world.spawn("unit", {Position2D: Position2D(x=i * 10, y=i * 10)})
world.tick(0)

# Query entities in circle
for entity in index.query_circle(50, 50, 100):
    pos = entity.get_component(Position2D)
    print(f"{entity.id}: ({pos.x}, {pos.y})")

# Find 5 nearest entities
for entity, distance in index.query_nearest(0, 0, 5):
    print(f"{entity.id} at distance {distance}")
```

---

## Procedural Prefabs Addon (`relics.addons.procedural_prefabs`)

### Registry API

```python
# src/relics/addons/procedural_prefabs/registry.py

class ProceduralPrefabRegistry:
    def __init__(self, world: World, component_registry: Optional[Dict[str, Type[Component]]] = None, rng_seed: Optional[int] = None): ...

    # Prefab management
    def register(self, prefab: ProceduralPrefab) -> None: ...
    def get(self, name: str) -> ProceduralPrefab: ...  # Raises ProcPrefabNotFoundError
    def has(self, name: str) -> bool: ...
    def list_prefabs(self) -> List[str]: ...

    # Prefab lists (for random selection)
    def register_list(self, name: str, prefab_names: List[str]) -> None: ...
    def get_list(self, name: str) -> List[str]: ...  # Raises PrefabListNotFoundError
    def has_list(self, name: str) -> bool: ...
    def list_prefab_lists(self) -> List[str]: ...

    # Component types
    def register_component_type(self, name: str, cls: Type[Component]) -> None: ...

    # Spawning
    def spawn(self, prefab_name: str, params: Optional[Dict[str, Any]] = None) -> Entity: ...

    # Loading from files
    def load(self, path: Union[str, Path]) -> None: ...  # Single .procprefab.json
    def load_directory(self, directory: Union[str, Path]) -> int: ...  # All .procprefab.json files

    # RNG control
    def set_seed(self, seed: int) -> None: ...
```

### JSON Schema Reference

Complete `.procprefab.json` structure:

```json
{
  "name": "string (required, unique prefab identifier)",
  "params": [
    {
      "name": "string (required, parameter name used with @syntax)",
      "type": "string (str|int|float|bool|list|any, default: str)",
      "required": "boolean (default: false)",
      "default": "any (default value if not provided)",
      "allowed_values": "array (optional whitelist)"
    }
  ],
  "graph": {
    "components": [
      {
        "type": "string (required, component type name)",
        "fields": {
          "field_name": "any (supports @param references)"
        },
        "when": {
          "param_name": "value (optional condition for variant)"
        }
      }
    ],
    "conditionals": [
      {
        "when": {
          "param_name": "value (all conditions must match)"
        },
        "derive": [
          {
            "target": "string (derived value name)",
            "operation": "set|add|multiply|append",
            "value": "any (supports @param references)"
          }
        ],
        "add": [
          {
            "type": "string (component type name)",
            "fields": { }
          }
        ]
      }
    ],
    "attachments": [
      {
        "prefab": "string (static prefab name, exclusive with from_list)",
        "from_list": "string (list name for random selection)",
        "edge_type": "string (HasEquipped|IsWearing|HasAttached)",
        "slot": "string (default: default)",
        "inherit_params": "array of strings (null = inherit all)",
        "override_params": { },
        "optional": "boolean (default: false)",
        "skip": "boolean (default: false)"
      }
    ],
    "lists": {
      "list_name": ["prefab1", "prefab2"]
    }
  },
  "base_prefab": "string (optional, inherited prefab)"
}
```

**Example:**
```json
{
  "name": "character",
  "params": [
    {"name": "name", "type": "str", "required": true},
    {"name": "race", "type": "str", "default": "human"},
    {"name": "cls", "type": "str", "default": "warrior"}
  ],
  "graph": {
    "components": [
      {"type": "Identity", "fields": {"name": "@name"}},
      {
        "type": "Appearance",
        "fields": {"height_cm": 127, "weight_kg": 75},
        "when": {"race": "dwarf"}
      },
      {
        "type": "Appearance",
        "fields": {"height_cm": 175, "weight_kg": 70}
      }
    ],
    "conditionals": [
      {
        "when": {"cls": "warrior"},
        "derive": [
          {"target": "weapon_list", "operation": "set", "value": "weapons_warrior"}
        ]
      }
    ],
    "attachments": [
      {
        "from_list": "@weapon_list",
        "edge_type": "HasEquipped",
        "slot": "main_hand"
      }
    ]
  }
}
```

### Edge Types

```python
# src/relics/addons/procedural_prefabs/edges.py

class HasEquipped(Edge):
    slot: str = "default"

class IsWearing(Edge):
    slot: str = "default"

class HasAttached(Edge):
    slot: str = "default"

# Edge management
def get_edge_class(edge_type_name: str) -> Type[Edge]: ...
def create_edge(edge_type_name: str, slot: str) -> Edge: ...
def register_edge_type(name: str, cls: Type[Edge]) -> None: ...
```

### Parameter Resolution

The `@param` syntax references parameters and derived values.

```python
# src/relics/addons/procedural_prefabs/context.py

class GenerationContext:
    def resolve_value(self, value: Any) -> Any: ...  # Recursively resolve @param
    def get_param(self, name: str, default: Any = None) -> Any: ...
    def get_derived(self, name: str, default: Any = None) -> Any: ...
    def set_derived(self, name: str, value: Any) -> None: ...
    def add_derived(self, name: str, value: Any) -> None: ...
    def multiply_derived(self, name: str, value: Any) -> None: ...
    def append_derived(self, name: str, value: Any) -> None: ...
    def child_context(self, inherit_params: Optional[List[str]], override_params: Optional[Dict[str, Any]]) -> GenerationContext: ...
```

**Resolution rules:**
- Full string match (`"@race"`) returns typed value
- Substring matches (`"prefix_@race"`) perform string substitution
- Derived values take precedence over parameters

### Utility Functions

```python
# src/relics/addons/procedural_prefabs/utils.py

def get_children(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Iterator[Entity]: ...
def get_child_ids(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Iterator[EntityId]: ...
def get_holder(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Optional[Entity]: ...
def get_holder_id(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Optional[EntityId]: ...
def detach(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Optional[Tuple[EntityId, Edge]]: ...
def destroy_with_children(world: World, entity: Entity, recursive: bool = True) -> int: ...
def get_children_recursive(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Iterator[Entity]: ...
def get_all_children_ids(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> List[EntityId]: ...
def get_root(entity: Entity, edge_type: Optional[Type[Edge]] = None) -> Entity: ...
def get_slot(entity: Entity) -> Optional[str]: ...
```

### Matching Semantics

| Context | Semantics |
|---------|-----------|
| **Component variants** | First-match: returns first variant where `when` matches |
| **Conditional blocks** | All-match: applies ALL blocks where `when` matches |
| **When clauses** | Exact-match: ALL conditions must match exactly |

### Usage Example

```python
import pydantic
from relics import World, Component
from relics.addons.procedural_prefabs import (
    ProceduralPrefabRegistry, HasEquipped,
    get_children, destroy_with_children,
)

@pydantic.dataclasses.dataclass
class Identity(Component):
    name: str

@pydantic.dataclasses.dataclass
class Stats(Component):
    strength: int
    agility: int

# Create world and registry
world = World()
registry = ProceduralPrefabRegistry(world, rng_seed=42)

# Register component types
registry.register_component_type("Identity", Identity)
registry.register_component_type("Stats", Stats)

# Load prefabs from directory
registry.load_directory("prefabs/")

# Register lists for random selection
registry.register_list("weapons_warrior", ["sword", "axe"])

# Spawn character
character = registry.spawn("character", {
    "name": "Thorin",
    "race": "dwarf",
    "cls": "warrior"
})
world.tick(0)

# Query attachments
for weapon in get_children(character, HasEquipped):
    print(f"Equipped: {weapon.id}")

# Cascade deletion
count = destroy_with_children(world, character)
print(f"Destroyed {count} entities")
```

---

## File Reference Index

### Core Library

| Module | Path |
|--------|------|
| Types | `src/relics/types.py` |
| World | `src/relics/world.py` |
| Entity | `src/relics/entity.py` |
| Query | `src/relics/query.py` |
| Observer | `src/relics/observer.py` |
| System | `src/relics/system.py` |
| Monitored | `src/relics/monitored.py` |
| Indexes | `src/relics/indexes.py` |
| Exports | `src/relics/__init__.py` |

### Spatial Addon

| Module | Path |
|--------|------|
| Components | `src/relics/addons/spatial/components.py` |
| Types (regions) | `src/relics/addons/spatial/types.py` |
| 2D Index | `src/relics/addons/spatial/index.py` |
| 3D Index | `src/relics/addons/spatial/index3d.py` |
| Lazy 2D | `src/relics/addons/spatial/lazy_index_2d.py` |
| Lazy 3D | `src/relics/addons/spatial/lazy_index_3d.py` |
| Factory | `src/relics/addons/spatial/factory.py` |
| Observers | `src/relics/addons/spatial/observer.py` |
| QuadTree | `src/relics/addons/spatial/quadtree.py` |
| Octree | `src/relics/addons/spatial/octree.py` |
| Exports | `src/relics/addons/spatial/__init__.py` |

### Procedural Prefabs Addon

| Module | Path |
|--------|------|
| Registry | `src/relics/addons/procedural_prefabs/registry.py` |
| Edges | `src/relics/addons/procedural_prefabs/edges.py` |
| Utils | `src/relics/addons/procedural_prefabs/utils.py` |
| Spawner | `src/relics/addons/procedural_prefabs/spawner.py` |
| Context | `src/relics/addons/procedural_prefabs/context.py` |
| Matcher | `src/relics/addons/procedural_prefabs/matcher.py` |
| Resolver | `src/relics/addons/procedural_prefabs/resolver.py` |
| Prefab | `src/relics/addons/procedural_prefabs/prefab.py` |
| Observer | `src/relics/addons/procedural_prefabs/observer.py` |
| Exceptions | `src/relics/addons/procedural_prefabs/exceptions.py` |
| Exports | `src/relics/addons/procedural_prefabs/__init__.py` |

### Test Files

| Area | Path |
|------|------|
| Core tests | `tests/test_*.py` |
| Spatial tests | `tests/addons/spatial/` |
| Procedural tests | `tests/addons/procedural_prefabs/` |

### Demo Files

| Demo | Path |
|------|------|
| Character sheet | `demos/character_sheet/` |

---

## Complete Integration Example

```python
import pydantic
from relics import World, Component, monitored
from relics.addons.spatial import (
    Position2D, create_spatial_index_2d, distance_2d
)
from relics.addons.procedural_prefabs import (
    ProceduralPrefabRegistry, HasEquipped,
    get_children, destroy_with_children,
)

# Define components
@monitored
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int

@pydantic.dataclasses.dataclass
class Identity(Component):
    name: str

# Create world
world = World()

# Setup spatial index
bounds = (-1000, -1000, 1000, 1000)
spatial_index = create_spatial_index_2d(
    world,
    materialized=True,
    auto_register_observer=True,
    bounds=bounds,
)

# Setup procedural prefabs
registry = ProceduralPrefabRegistry(world, rng_seed=42)
registry.register_component_type("Position2D", Position2D)
registry.register_component_type("Health", Health)
registry.register_component_type("Identity", Identity)
registry.load_directory("prefabs/")

# Spawn entities
player = registry.spawn("character", {"name": "Hero", "x": 100, "y": 100})
for i in range(10):
    registry.spawn("enemy", {"x": i * 50, "y": i * 50})

world.tick(0)

# Find enemies near player
player_pos = player.get_component(Position2D)
nearby = list(spatial_index.query_circle(player_pos.x, player_pos.y, 200))
print(f"Found {len(nearby)} entities within 200 units")

# Cleanup
destroy_with_children(world, player)
world.tick(0)
```
