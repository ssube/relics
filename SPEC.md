# Relic: ECS Graph Database Framework

## Specification v1.0

*A relic is a snapshot of a world at a particular epoch.*

---

## Overview

Relic is an engine-agnostic Entity-Component-System (ECS) framework with graph database semantics. It treats relationships as first-class citizens, supports multiple persistence backends, and is designed for high performance.

### Design Goals

1. **Engine Agnostic**: No coupling to rendering engines (PyGame, Godot, Raylib, Unreal)
2. **Graph Database Semantics**: Relationships modeled as `(source, edge, target)` tuples
3. **Performant Queries**: No anti-patterns like regex; prefix matching supported
4. **Multiple Persistence Backends**: JSON and SQLite initially
5. **Reactive Observers**: Event-driven responses to data changes
6. **Portable Design**: Python prototype with Rust port planned (avoid overly Pythonic idioms)

### Concurrency Model

- **Single-threaded per World**: Each World instance is accessed from one thread only
- **Multiple Worlds**: Can run in parallel threads (useful for testing)
- Thread-safety within a world is deferred to the Rust port

### Development Guide

- Pydantic dataclasses for data structures
- Type hints for clarity
- 95%+ unit test coverage
- Comprehensive documentation and examples
- CI/CD with automated testing and linting
- Semantic commit messages
- Do not worry about semantic versioning until v1.0 is stable
- Avoid abbreviations in names for clarity
- Avoid overly Pythonic idioms to facilitate Rust porting
- Use Result/Either return types for error handling in Rust port
- Fail-fast philosophy: return an error immediately on invalid operations
- Document all public APIs and behaviors
- Use consistent naming conventions (e.g., CamelCase for classes, snake_case for functions)
- Modular design: separate concerns into distinct modules/files
- Use the language's logging facilities for debug/info/error messages
- Write clear and descriptive commit messages
- Commit frequently with small, focused changes
- Write tests alongside implementation

---

## Core Concepts

### Entities

Entities are unique identifiers with no inherent data. They are instantiated from **prefabs**.

```python
@dataclass
class EntityId:
    """Structured entity identifier."""
    prefab: str
    sequence: int  # Per-prefab timestamp + collision counter

    def __str__(self) -> str:
        return f"{self.prefab}_{self.sequence}"

    @classmethod
    def parse(cls, s: str) -> "EntityId":
        """Parse string representation back to EntityId."""
        prefab, seq = s.rsplit("_", 1)
        return cls(prefab, int(seq))
```

**Sequence Generation**: Hybrid per-prefab timestamp + collision counter
- Base: milliseconds since epoch × 1000
- If collision within same millisecond, increment counter
- Example: `door_1705847293001000`, `door_1705847293001001`

### Prefabs

Prefabs are templates for entity creation, stored as JSON or in SQLite.

```python
# Prefab definition (stored)
{
    "name": "door",
    "components": {
        "Position": {"x": 0, "y": 0, "z": 0},
        "Health": {"current": 100, "maximum": 100},
        "Locked": {"is_locked": false}
    }
}

# Instantiation
entity = world.spawn("door")  # Creates with default components
entity = world.spawn("door", {
    Health: Health(current=50, maximum=100)  # Override defaults
})
```

### Components

Components are pure data containers with no logic. Defined code-first.

```python
from dataclasses import dataclass
from relic import Component, monitored

@dataclass
class Position(Component):
    x: float
    y: float
    z: float = 0.0

@monitored  # Enable change tracking for OnComponentChanged observers
@dataclass
class Health(Component):
    current: int
    maximum: int

@dataclass
class Team(Component):
    id: str
    name: str
```

**Field Validation**: Optional JSON Schema extension for constraints (future feature).

### Relationships / Edges

Relationships are first-class tuples: `(source: EntityId, edge: Edge, target: EntityId)`

```python
from dataclasses import dataclass
from relic import Edge, RelationshipValidationError

@dataclass
class AllyTo(Edge):
    trust_level: float = 1.0

    def validate(self, source: "Entity", target: "Entity") -> bool:
        """Called at relationship creation. Raise on invalid."""
        if not (source.has_component(Team) and target.has_component(Team)):
            raise RelationshipValidationError(
                "Both entities must have Team component"
            )
        if source.get_component(Team).id != target.get_component(Team).id:
            raise RelationshipValidationError(
                "Entities must be on same team"
            )
        return True

@dataclass
class ParentOf(Edge):
    """Hierarchical relationship with no additional data."""
    pass

@dataclass
class Attacking(Edge):
    damage_per_second: float
    started_at_epoch: int
```

**Query Patterns Supported**:
- `(source, edge, *)` — All targets of a source via edge type
- `(source, *, target)` — All edges between source and target
- `(*, edge, target)` — All sources pointing to target via edge type

---

## Entity Handle

Live handle that always reflects current world state.

```python
class Entity:
    """Live handle to an entity. Always reflects current world state."""

    @property
    def id(self) -> EntityId:
        """The entity's unique identifier."""
        ...

    @property
    def prefab(self) -> str:
        """The prefab this entity was instantiated from."""
        ...

    # Components
    def get_component(self, component_type: Type[T]) -> T:
        """Get component. Raises ComponentNotFoundError if missing."""
        ...

    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if entity has component."""
        ...

    def add_component(self, component: Component) -> None:
        """Add component. Raises DuplicateComponentError if exists."""
        ...

    def remove_component(self, component_type: Type[Component]) -> None:
        """Remove component. Raises ComponentNotFoundError if missing."""
        ...

    # Relationships (outgoing)
    def add_relationship(self, edge: Edge, target: EntityId) -> None:
        """Create relationship. Runs edge.validate() first."""
        ...

    def remove_relationship(self, edge_type: Type[Edge], target: EntityId) -> None:
        """Remove specific relationship."""
        ...

    def get_relationships(self, edge_type: Type[Edge]) -> List[Tuple[Edge, EntityId]]:
        """Get all outgoing relationships of this edge type."""
        ...

    # Relationships (incoming)
    def get_incoming_relationships(self, edge_type: Type[Edge]) -> List[Tuple[EntityId, Edge]]:
        """Get all incoming relationships of this edge type."""
        ...
```

---

## Query System

Queries use a builder pattern with three selector types: component, relationship, and predicate.

### Query Builder

```python
class QueryBuilder:
    # Component selectors
    def with_all(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Entities must have ALL of these components."""
        ...

    def with_any(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Entities must have AT LEAST ONE of these components."""
        ...

    def with_none(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Entities must have NONE of these components."""
        ...

    # Relationship selectors
    def with_relationship(
        self,
        edge_type: Type[Edge],
        target: Optional[EntityId] = None
    ) -> "QueryBuilder":
        """Entities must have outgoing relationship of this type.
        If target specified, must be to that specific entity."""
        ...

    def with_incoming(
        self,
        edge_type: Type[Edge],
        source: Optional[EntityId] = None
    ) -> "QueryBuilder":
        """Entities must have incoming relationship of this type."""
        ...

    # Predicate selectors
    def with_filter(self, predicate: Callable[[Entity], bool]) -> "QueryBuilder":
        """Entities must pass this predicate function."""
        ...

    # Batch optimization
    def iterate(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Prepare component arrays for batch processing."""
        ...

    # Execution
    def execute_ids(self) -> Iterator[EntityId]:
        """Return matching entity IDs only."""
        ...

    def execute_entities(self) -> Iterator[Entity]:
        """Return live Entity handles."""
        ...

    def execute_components(self) -> Iterator[Tuple[EntityId, ...]]:
        """Return entity ID with requested components (from iterate())."""
        ...
```

### Query Examples

```python
# All entities with Position and Velocity, excluding Dead
query = (world.query()
    .with_all([Position, Velocity])
    .with_none([Dead]))

for entity in query.execute_entities():
    pos = entity.get_component(Position)
    vel = entity.get_component(Velocity)
    pos.x += vel.x * delta

# All allies of a specific player
allies_query = (world.query()
    .with_incoming(AllyTo, source=player.id))

# Batch optimized iteration
query = (world.query()
    .with_all([Position, Velocity])
    .iterate([Position, Velocity]))

for entity_id, pos, vel in query.execute_components():
    pos.x += vel.x * delta

# Predicate-based filtering
low_health = (world.query()
    .with_all([Health])
    .with_filter(lambda e: e.get_component(Health).current < 20))

# Entities with specific prefab prefix (uses efficient prefix matching)
doors = (world.query()
    .with_filter(lambda e: e.prefab.startswith("door")))
```

---

## Systems

Systems contain game logic and process entities based on queries. They form a directed acyclic graph (DAG) based on dependencies.

### System Definition

```python
from enum import Enum, auto
from typing import Dict, List, Type, Callable, Tuple

class RunOrder(Enum):
    BEFORE = auto()
    AFTER = auto()

class Frequency:
    """Execution frequency configuration."""
    EVERY_TICK: ClassVar["Frequency"]

    @staticmethod
    def every_n_ticks(n: int) -> "Frequency": ...

    @staticmethod
    def fixed_interval(seconds: float) -> "Frequency": ...

class System:
    """Base class for all systems."""

    # Wildcard for dependency ordering
    WILDCARD: ClassVar[Type["System"]]

    @property
    def q(self) -> QueryBuilder:
        """Convenience accessor for fresh query builder."""
        return self.world.query()

    def query(self) -> QueryBuilder:
        """Override: Define which entities this system processes."""
        raise NotImplementedError

    def deps(self) -> Dict[RunOrder, List[Type["System"]]]:
        """Override: Declare execution order dependencies."""
        return {}

    def frequency(self) -> Frequency:
        """Override: Control execution frequency."""
        return Frequency.EVERY_TICK

    def process(
        self,
        entities: List[Entity],
        components: List[List[Component]],
        delta: float
    ) -> None:
        """Override: Implement system logic."""
        raise NotImplementedError

    def sub_systems(self) -> List[Tuple[QueryBuilder, Callable]]:
        """Override: Define sub-systems with separate queries."""
        return []
```

### System Examples

```python
class MovementSystem(System):
    """Applies velocity to position."""

    def query(self) -> QueryBuilder:
        return (self.q
            .with_all([Position, Velocity])
            .with_none([Dead])
            .iterate([Position, Velocity]))

    def deps(self) -> Dict[RunOrder, List[Type[System]]]:
        return {
            RunOrder.AFTER: [InputSystem],
            RunOrder.BEFORE: [CollisionSystem],
        }

    def process(self, entities, components, delta):
        positions, velocities = components
        for i, entity in enumerate(entities):
            positions[i].x += velocities[i].x * delta
            positions[i].y += velocities[i].y * delta
            positions[i].z += velocities[i].z * delta


class DamageSystem(System):
    """Handles damage and health regeneration via sub-systems."""

    def sub_systems(self):
        return [
            (self.q.with_all([Health, DamageReceived]), self.apply_damage),
            (self.q.with_all([Health, Regenerating])
                .with_none([Dead])
                .iterate([Health, Regenerating]), self.regenerate),
        ]

    def apply_damage(self, entities, components, delta):
        for entity in entities:
            health = entity.get_component(Health)
            damage = entity.get_component(DamageReceived)
            health.current -= damage.amount
            entity.remove_component(DamageReceived)

            if health.current <= 0:
                entity.add_component(Dead())

    def regenerate(self, entities, components, delta):
        healths, regens = components
        for i, entity in enumerate(entities):
            healths[i].current = min(
                healths[i].current + regens[i].rate * delta,
                healths[i].maximum
            )


class CleanupSystem(System):
    """Runs after all other systems."""

    def query(self):
        return self.q.with_all([MarkedForDeletion])

    def deps(self):
        return {RunOrder.AFTER: [System.WILDCARD]}

    def process(self, entities, components, delta):
        for entity in entities:
            self.world.remove(entity)
```

### Dependency Resolution

- Systems form a DAG based on `deps()` declarations
- **Cycles are fatal errors** at world initialization
- `System.WILDCARD` means "all other systems" (for first/last execution)
- Systems without dependencies can run in any order relative to each other

---

## Observers

Observers react to events. They are queued by default (processed at end of tick).

### Observer Base Classes

```python
class Observer:
    """Base class for all observers."""

    # Future: immediate vs queued execution
    # queued: bool = True  # Default: process at end of tick


class OnComponentAdded(Observer):
    """Triggered when a component is added to an entity."""
    component_type: Type[Component]  # Override in subclass

    def on_component_added(self, entity: Entity, component: Component) -> None:
        ...


class OnComponentRemoved(Observer):
    """Triggered when a component is removed from an entity."""
    component_type: Type[Component]

    def on_component_removed(self, entity: Entity, component: Component) -> None:
        ...


class OnComponentChanged(Observer):
    """Triggered when a @monitored component changes.
    Requires the component class to have @monitored decorator.
    """
    component_type: Type[Component]

    def on_component_changed(
        self,
        entity: Entity,
        old_value: Component,
        new_value: Component
    ) -> None:
        ...


class OnRelationshipAdded(Observer):
    """Triggered when a relationship is created."""
    edge_type: Type[Edge]

    def on_relationship_added(
        self,
        source: Entity,
        edge: Edge,
        target: Entity
    ) -> None:
        ...


class OnRelationshipRemoved(Observer):
    """Triggered when a relationship is destroyed."""
    edge_type: Type[Edge]

    def on_relationship_removed(
        self,
        source: Entity,
        edge: Edge,
        target: Entity
    ) -> None:
        ...


class OnEntityCreated(Observer):
    """Triggered when an entity is spawned."""
    prefab: Optional[str] = None  # None = all prefabs

    def on_entity_created(self, entity: Entity) -> None:
        ...


class OnEntityDestroyed(Observer):
    """Triggered when an entity is removed."""
    prefab: Optional[str] = None

    def on_entity_destroyed(self, entity: Entity) -> None:
        ...


class OnCustomEvent(Observer):
    """Triggered by user-defined events."""
    event_type: Type["CustomEvent"]

    def on_event(self, event: "CustomEvent") -> None:
        ...
```

### Custom Events

```python
from dataclasses import dataclass
from relic import CustomEvent

@dataclass
class EntityDied(CustomEvent):
    entity: EntityId
    killer: Optional[EntityId] = None

@dataclass
class LevelCompleted(CustomEvent):
    level_id: str
    completion_time: float

# Emitting events
world.emit(EntityDied(entity_id, killer_id))
```

### Observer Examples

```python
class DeathObserver(OnComponentAdded):
    """Emit EntityDied event when Dead component is added."""
    component_type = Dead

    def on_component_added(self, entity: Entity, component: Dead):
        self.world.emit(EntityDied(entity.id))


class HealthBarObserver(OnComponentChanged):
    """Update UI when health changes."""
    component_type = Health

    def on_component_changed(self, entity, old_health, new_health):
        if new_health.current < old_health.current:
            # Took damage - flash red
            self.world.emit(DamageTaken(entity.id, old_health.current - new_health.current))


class ScoreObserver(OnCustomEvent):
    """Track score when entities die."""
    event_type = EntityDied

    def on_event(self, event: EntityDied):
        if event.killer:
            killer = self.world.get_entity(event.killer)
            if killer.has_component(Score):
                score = killer.get_component(Score)
                score.value += 100


# Registration
world.observe(DeathObserver())
world.observe(HealthBarObserver())
world.observe(ScoreObserver())
```

### Observer Execution

- **Default**: Queued execution (processed at end of tick, after all systems)
- Observers can modify components, which may trigger other observers
- Event cascading follows same queued rules (added to end of queue)
- Future enhancement: configurable immediate execution per observer

---

## Secondary Indexes

Indexes provide fast access to entity subsets based on queries.

### Index Types

| Mode | Description | Use Case |
|------|-------------|----------|
| **Materialized** | Auto-updates on change | Frequently accessed, rarely changing |
| **Lazy** | Computes on query | Rarely accessed, frequently changing |

### Index Definition

```python
# Materialized index - updates automatically when Health or Dead changes
world.create_index(
    name="alive_entities",
    query=world.query().with_all([Health]).with_none([Dead]),
    watches=[Health, Dead],  # Components that trigger re-evaluation
    materialized=True
)

# Lazy index - recomputes each access
world.create_index(
    name="low_health",
    query=world.query()
        .with_all([Health])
        .with_filter(lambda e: e.get_component(Health).current < 20),
    watches=[Health],
    materialized=False
)

# Usage
for entity in world.index("alive_entities"):
    ...

count = world.index("alive_entities").count()
```

---

## Spatial Indexes

Spatial indexes enable efficient spatial queries using tree structures.

### Spatial Index Types

| Structure | Dimensions | Use Case |
|-----------|------------|----------|
| **Quadtree** | 2D | Top-down games, maps |
| **Octree** | 3D | 3D worlds |
| **Sphere** | 2D/3D | Radius queries |
| **AABB** | 2D/3D | Box/region queries |

### Spatial Index Definition

```python
# Create spatial index bound to Position component
world.create_spatial_index(
    name="world_positions",
    component=Position,
    fields=["x", "y", "z"],  # 3D
    structure="octree"
)

# 2D variant
world.create_spatial_index(
    name="map_positions",
    component=Position,
    fields=["x", "y"],  # 2D only
    structure="quadtree"
)
```

### Spatial Queries

```python
spatial = world.spatial("world_positions")

# Radius query
nearby = spatial.query_radius(center=(10, 20, 0), radius=5.0)

# Box query
in_region = spatial.query_box(min=(0, 0, 0), max=(100, 100, 100))

# K-nearest neighbors
closest = spatial.query_nearest(point=(10, 20, 0), k=5)

# Distance sorting helper
sorted_enemies = spatial.sort_by_distance(
    entities=enemies_query.execute_entities(),
    origin=player_position
)
```

---

## Persistence

### Backends

| Backend | Use Case |
|---------|----------|
| **JSON** | Human-readable, debugging, simple projects |
| **SQLite** | Production, large worlds, relational queries |

### Persistence Triggers

| Trigger | Description |
|---------|-------------|
| `ON_CHANGE` | Persist immediately after each change |
| `ON_EPOCH` | Persist at end of each tick |
| `INTERVAL(n)` | Persist every N epochs |
| `INTERVAL_TIME(sec)` | Persist every N seconds |

### Configuration

```python
from relic import PersistenceTrigger

# Configure persistence
world.configure_persistence(
    backend="sqlite",  # or "json"
    path="game.db",
    trigger=PersistenceTrigger.ON_EPOCH
)

# Or interval-based
world.configure_persistence(
    backend="json",
    path="game.json",
    trigger=PersistenceTrigger.INTERVAL_TIME(30.0)  # Every 30 seconds
)
```

### Relics (Snapshots)

```python
# Save named snapshot
world.save_relic("before_boss_fight")
world.save_relic("autosave", overwrite=True)

# List available relics
relics = world.list_relics()
# Returns: [RelicInfo(name="before_boss_fight", epoch=42, created_at=...), ...]

# Load specific relic
world.load_relic("before_boss_fight")

# Load most recent state
world.load("game.db")
```

### Export for Tooling

```python
# Export single entity as structured JSON (for editors/debugging)
entity_data = world.export_entity(entity_id)
# Returns entity-centric format suitable for editing
```

### SQLite Schema

```sql
-- Core tables
CREATE TABLE _entities (
    entity_id TEXT PRIMARY KEY,
    prefab TEXT NOT NULL,
    created_epoch INTEGER NOT NULL
);

CREATE TABLE _prefabs (
    name TEXT PRIMARY KEY,
    components_json TEXT NOT NULL
);

CREATE TABLE _relics (
    name TEXT PRIMARY KEY,
    epoch INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE _metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One table per component type (auto-generated)
CREATE TABLE Position (
    entity_id TEXT PRIMARY KEY REFERENCES _entities(entity_id) ON DELETE CASCADE,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE Health (
    entity_id TEXT PRIMARY KEY REFERENCES _entities(entity_id) ON DELETE CASCADE,
    current INTEGER NOT NULL,
    maximum INTEGER NOT NULL
);

-- One table per edge type (auto-generated)
CREATE TABLE AllyTo (
    source_id TEXT NOT NULL REFERENCES _entities(entity_id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES _entities(entity_id) ON DELETE CASCADE,
    trust_level REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id)
);

-- Indexes for common queries
CREATE INDEX idx_entities_prefab ON _entities(prefab);
CREATE INDEX idx_allyto_target ON AllyTo(target_id);
```

### JSON Format (Type-Grouped)

```json
{
  "metadata": {
    "version": "1.0",
    "epoch": 1234,
    "created_at": "2025-01-21T12:00:00Z"
  },
  "prefabs": {
    "player": {
      "components": {
        "Position": {"x": 0, "y": 0, "z": 0},
        "Health": {"current": 100, "maximum": 100},
        "Team": {"id": "heroes", "name": "Heroes"}
      }
    },
    "door": {
      "components": {
        "Position": {"x": 0, "y": 0, "z": 0},
        "Health": {"current": 50, "maximum": 50}
      }
    }
  },
  "entities": {
    "player_1705847293001": {"prefab": "player", "created_epoch": 1},
    "player_1705847293002": {"prefab": "player", "created_epoch": 1},
    "door_1705847294001": {"prefab": "door", "created_epoch": 5}
  },
  "components": {
    "Position": {
      "player_1705847293001": {"x": 10.5, "y": 20.0, "z": 0.0},
      "player_1705847293002": {"x": 15.0, "y": 20.0, "z": 0.0},
      "door_1705847294001": {"x": 50.0, "y": 50.0, "z": 0.0}
    },
    "Health": {
      "player_1705847293001": {"current": 80, "maximum": 100},
      "player_1705847293002": {"current": 100, "maximum": 100},
      "door_1705847294001": {"current": 50, "maximum": 50}
    },
    "Team": {
      "player_1705847293001": {"id": "heroes", "name": "Heroes"},
      "player_1705847293002": {"id": "heroes", "name": "Heroes"}
    }
  },
  "relationships": {
    "AllyTo": [
      {"source": "player_1705847293001", "target": "player_1705847293002", "trust_level": 1.0},
      {"source": "player_1705847293002", "target": "player_1705847293001", "trust_level": 0.8}
    ]
  },
  "relics": [
    {"name": "autosave", "epoch": 1000, "created_at": "2025-01-21T11:00:00Z"}
  ]
}
```

---

## Archetypes (Implementation Detail)

Archetypes are an internal optimization, not exposed to users.

- Entities with identical component signatures share an archetype
- Component data is stored contiguously per archetype for cache efficiency
- Adding/removing components may migrate entity to different archetype
- Framework manages this transparently
- Enables efficient batch iteration in systems

---

## Error Handling

All errors are exceptions (fail-fast philosophy).

```python
class RelicError(Exception):
    """Base exception for all Relic errors."""
    pass

class EntityNotFoundError(RelicError):
    """Entity does not exist in world."""
    pass

class ComponentNotFoundError(RelicError):
    """Entity does not have the requested component."""
    pass

class DuplicateComponentError(RelicError):
    """Entity already has this component type."""
    pass

class RelationshipValidationError(RelicError):
    """Edge validation failed."""
    pass

class SystemDependencyCycleError(RelicError):
    """System dependencies form a cycle (fatal at registration)."""
    pass

class PrefabNotFoundError(RelicError):
    """Prefab does not exist."""
    pass
```

---

## World API

```python
class World:
    """Central manager for all entities, systems, and observers."""
    id: str  # Unique world identifier

    # Entity management
    def spawn(
        self,
        prefab: str,
        components: Optional[Dict[Type[Component], Component]] = None
    ) -> Entity:
        """Create entity from prefab with optional component overrides."""
        ...

    def get_entity(self, entity_id: EntityId) -> Entity:
        """Get live handle to entity. Raises EntityNotFoundError."""
        ...

    def remove(self, entity: Union[Entity, EntityId]) -> None:
        """Remove entity from world."""
        ...

    def has_entity(self, entity_id: EntityId) -> bool:
        """Check if entity exists."""
        ...

    # Queries
    def query(self) -> QueryBuilder:
        """Create new query builder."""
        ...

    # Systems
    def register_system(self, system: System) -> None:
        """Register system. Raises SystemDependencyCycleError on cycle."""
        ...

    # Observers
    def observe(self, observer: Observer) -> None:
        """Register observer for events."""
        ...

    # Custom events
    def emit(self, event: CustomEvent) -> None:
        """Emit custom event to observers."""
        ...

    # Indexes
    def create_index(
        self,
        name: str,
        query: QueryBuilder,
        watches: List[Type[Component]],
        materialized: bool = False
    ) -> None:
        """Create secondary index."""
        ...

    def index(self, name: str) -> IndexView:
        """Access named index."""
        ...

    # Spatial indexes
    def create_spatial_index(
        self,
        name: str,
        component: Type[Component],
        fields: List[str],
        structure: str = "octree"  # "quadtree", "octree", "sphere", "aabb"
    ) -> None:
        """Create spatial index."""
        ...

    def spatial(self, name: str) -> SpatialIndex:
        """Access named spatial index."""
        ...

    # Execution
    def tick(self, delta: float) -> None:
        """Advance epoch, run systems, process observer queue."""
        ...

    @property
    def epoch(self) -> int:
        """Current epoch number."""
        ...

    # Persistence
    def configure_persistence(
        self,
        backend: str,
        path: str,
        trigger: PersistenceTrigger
    ) -> None:
        """Configure automatic persistence."""
        ...

    def save(self, path: Optional[str] = None) -> None:
        """Manual save to configured or specified path."""
        ...

    def load(self, path: str) -> None:
        """Load world state from file."""
        ...

    def save_relic(self, name: str, overwrite: bool = False) -> None:
        """Save named snapshot."""
        ...

    def load_relic(self, name: str) -> None:
        """Load named snapshot."""
        ...

    def list_relics(self) -> List[RelicInfo]:
        """List available relics."""
        ...

    # Export
    def export_entity(self, entity_id: EntityId) -> Dict:
        """Export single entity as structured dict (for tooling)."""
        ...

    # Prefabs
    def register_prefab(self, name: str, components: Dict[Type[Component], Component]) -> None:
        """Register prefab programmatically."""
        ...

    def load_prefabs(self, path: str) -> None:
        """Load prefabs from JSON file."""
        ...
```

---

## Complete Example

```python
from dataclasses import dataclass
from typing import Dict, List, Type, Optional
from relic import (
    World, Component, Edge, System, Observer,
    OnComponentAdded, OnEntityDestroyed, CustomEvent,
    QueryBuilder, RunOrder, Frequency, monitored
)

# Components
@dataclass
class Position(Component):
    x: float
    y: float
    z: float = 0.0

@dataclass
class Velocity(Component):
    x: float
    y: float
    z: float = 0.0

@monitored
@dataclass
class Health(Component):
    current: int
    maximum: int

@dataclass
class Dead(Component):
    pass

@dataclass
class Team(Component):
    id: str

# Edges
@dataclass
class AllyTo(Edge):
    trust_level: float = 1.0

    def validate(self, source, target):
        if not (source.has_component(Team) and target.has_component(Team)):
            raise RelationshipValidationError("Both need Team")
        return True

# Custom Events
@dataclass
class EntityDied(CustomEvent):
    entity_id: EntityId
    killer_id: Optional[EntityId] = None

# Systems
class MovementSystem(System):
    def query(self):
        return (self.q
            .with_all([Position, Velocity])
            .with_none([Dead])
            .iterate([Position, Velocity]))

    def deps(self):
        return {RunOrder.BEFORE: [CollisionSystem]}

    def process(self, entities, components, delta):
        positions, velocities = components
        for i in range(len(entities)):
            positions[i].x += velocities[i].x * delta
            positions[i].y += velocities[i].y * delta

class CollisionSystem(System):
    def query(self):
        return self.q.with_all([Position, Collider])

    def process(self, entities, components, delta):
        # Collision detection logic
        pass

# Observers
class DeathObserver(OnComponentAdded):
    component_type = Dead

    def on_component_added(self, entity, component):
        self.world.emit(EntityDied(entity.id))

# Main
def main():
    world = World()

    # Load prefabs
    world.load_prefabs("prefabs.json")

    # Register systems (order doesn't matter - deps() determines order)
    world.register_system(MovementSystem())
    world.register_system(CollisionSystem())

    # Register observers
    world.observe(DeathObserver())

    # Create spatial index
    world.create_spatial_index(
        name="positions",
        component=Position,
        fields=["x", "y", "z"],
        structure="octree"
    )

    # Configure persistence
    world.configure_persistence(
        backend="sqlite",
        path="game.db",
        trigger=PersistenceTrigger.ON_EPOCH
    )

    # Spawn entities
    player = world.spawn("player")
    ally = world.spawn("player", {Position: Position(10, 0, 0)})

    # Create relationship
    player.add_relationship(AllyTo(trust_level=1.0), ally.id)

    # Game loop
    running = True
    while running:
        delta = 1/60  # 60 FPS
        world.tick(delta)

        # Query nearby allies
        nearby = world.spatial("positions").query_radius(
            center=(player.get_component(Position).x,
                    player.get_component(Position).y,
                    player.get_component(Position).z),
            radius=10.0
        )

    # Save on exit
    world.save_relic("final_save")

if __name__ == "__main__":
    main()
```

---

## Implementation Roadmap

### v0.1 — Prototype Core
- [ ] EntityId with prefab + sequence
- [ ] Component base class and registration
- [ ] Entity handles (live)
- [ ] Basic queries: `with_all`, `with_none`, `with_any`, `with_filter`
- [ ] Query execution: `execute_ids`, `execute_entities`, `execute_components`
- [ ] Systems with `query()`, `deps()`, `frequency()`
- [ ] System DAG resolution and cycle detection
- [ ] Observers: `OnComponentAdded`, `OnComponentRemoved`, `OnEntityCreated`, `OnEntityDestroyed`
- [ ] `@monitored` decorator and `OnComponentChanged`
- [ ] JSON persistence (type-grouped format)
- [ ] Relics: `save_relic`, `load_relic`, `list_relics`
- [ ] Prefabs: load from JSON, spawn with overrides

### v0.2 — Prototype Extended
- [ ] Relationships (Edges) with validation
- [ ] Edge queries: `with_relationship`, `with_incoming`
- [ ] Relationship observers: `OnRelationshipAdded`, `OnRelationshipRemoved`
- [ ] Custom events and `OnCustomEvent`
- [ ] SQLite backend
- [ ] Secondary indexes (lazy and materialized)
- [ ] Archetypes (internal optimization)
- [ ] Sub-systems
- [ ] `export_entity` for tooling
- [ ] `iterate()` batch optimization

### v0.3 — Pygame Demo
- [ ] Simple 2D world with wandering animals
- [ ] Demonstrates core ECS patterns in a visual context
- [ ] Uses Pygame for rendering (framework remains engine-agnostic)
- [ ] Sprite-based rendering system
- [ ] Basic AI behaviors (wandering, flocking, etc.)
- [ ] See "Demo Application" section for full requirements

### Deferred to Rust Port
- [ ] Spatial indexes (quadtree, octree)
- [ ] Persistence triggers (interval-based)
- [ ] Thread-safety within world
- [ ] Zero-copy optimizations
- [ ] JSON Schema validation for components
- [ ] Immediate observer execution option

---

## Demo Application: Animal World

A simple 2D demo using Pygame to validate the framework and demonstrate core ECS patterns.

### Purpose

1. **Validate Framework**: Ensure the ECS design works in a real-time visual context
2. **Demonstrate Patterns**: Showcase systems, observers, queries, and relationships
3. **Engine-Agnostic Proof**: Pygame is just a rendering layer; ECS logic is decoupled
4. **Development Test Bed**: Visual debugging during framework development

### Demo Requirements

#### World
- 2D top-down view
- Bounded world area (animals stay within bounds)
- Simple environment (grass background, optional obstacles)

#### Entities
- Multiple animal types (sprites provided by user)
- Each animal is an entity spawned from a prefab

#### Components (Suggested)
```python
@dataclass
class Position(Component):
    x: float
    y: float

@dataclass
class Velocity(Component):
    x: float
    y: float

@dataclass
class Sprite(Component):
    image_id: str  # Reference to loaded sprite
    width: int
    height: int

@dataclass
class Wandering(Component):
    """AI state for wandering behavior."""
    direction_change_timer: float
    speed: float

@dataclass
class Animal(Component):
    """Marker component with animal metadata."""
    species: str
```

#### Systems (Suggested)
```python
class WanderingAISystem(System):
    """Updates velocity based on wandering behavior."""
    def query(self):
        return self.q.with_all([Wandering, Velocity])

class MovementSystem(System):
    """Applies velocity to position."""
    def query(self):
        return self.q.with_all([Position, Velocity])

class BoundsSystem(System):
    """Keeps entities within world bounds."""
    def query(self):
        return self.q.with_all([Position])

class RenderSystem(System):
    """Draws sprites at positions (Pygame-specific)."""
    def query(self):
        return self.q.with_all([Position, Sprite])
```

#### Behaviors to Demonstrate
- **Wandering**: Animals move randomly, changing direction periodically
- **Predator/prey**: Optional simple interaction (e.g., fox chases rabbit)
- **Boundary avoidance**: Animals turn away from world edges
- **Optional enhancements** (if time permits):
  - Flocking behavior (relationships between nearby animals)
  - Predator/prey dynamics (demonstrates observers and custom events)
  - Click to spawn new animals (demonstrates runtime entity creation)

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Main Loop                        │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ Handle      │  │ world.tick()│  │ Pygame     │  │
│  │ Pygame      │→ │ (runs ECS   │→ │ render     │  │
│  │ events      │  │  systems)   │  │ (draw)     │  │
│  └─────────────┘  └─────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────┘

ECS (engine-agnostic):
├── WanderingAISystem (pure logic)
├── MovementSystem (pure logic)
└── BoundsSystem (pure logic)

Pygame Layer (rendering only):
├── InputSystem (reads Pygame events and queues actions)
└── RenderSystem (reads Position + Sprite, draws to screen)
```

### File Structure (Suggested)
```
demo/
├── main.py              # Entry point, Pygame setup, main loop
├── components.py        # Demo-specific components
├── systems.py           # Demo-specific systems
├── prefabs.json         # Animal prefab definitions
├── assets/
│   └── sprites/         # User-provided sprite images
│       ├── rabbit.png
│       ├── fox.png
│       └── ...
└── README.md            # Demo instructions
```

### Stretch Goals
- Save/load world state (demonstrates persistence)
- Pause simulation, inspect entities (demonstrates queries)
- Add/remove animals via UI (demonstrates entity lifecycle)
- Simple spatial queries ("find nearest animal")

### Sprites
User will provide sprite assets. Demo should support:
- PNG images with transparency
- Configurable sprite dimensions per prefab
- Optional: sprite rotation based on velocity direction

---

## Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Entity IDs | Structured (prefab + sequence) | Efficient prefix queries, debuggable |
| Sequence generation | Per-prefab timestamp + counter | Unique, sortable, survives reload |
| Components | Code-first dataclasses | Type safety, IDE support, Rust-portable |
| Change detection | Setter/proxy (language idiomatic) | Clean API, automatic event emission |
| Relationships | First-class tuples | Graph database semantics |
| Edge validation | Fail-fast exceptions | Early error detection |
| Query results | Multiple modes | Flexibility for different use cases |
| Systems | DAG with deps() | Explicit ordering, cycle detection |
| Observers | Queued by default | Safer, batchable, debuggable |
| Archetypes | Implicit/internal | User simplicity, implementation freedom |
| JSON format | Type-grouped | Matches SQLite schema, fast serialization |
| Worlds | Isolated, single-threaded | Simplicity, parallel testing |

---

## Appendix: Terminology

| Term | Definition |
|------|------------|
| **Entity** | Unique identifier with no inherent data |
| **Component** | Pure data container attached to entities |
| **System** | Logic that processes entities based on queries |
| **Observer** | Reactive handler triggered by events |
| **Edge** | Typed relationship data between two entities |
| **Prefab** | Template for spawning entities |
| **Archetype** | Internal grouping of entities by component signature |
| **Relic** | Named snapshot of world state at an epoch |
| **Epoch** | Discrete time unit, advanced by `world.tick()` |
| **World** | Container for all entities, systems, and state |
