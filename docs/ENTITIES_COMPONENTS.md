# Entities & Components

> Entities are unique identifiers. Components are data attached to entities. Together they form the foundation of the ECS pattern.

---

## 📋 Prerequisites

Before reading this document, you should be familiar with:
- [Getting Started](GETTING_STARTED.md) - Basic concepts and setup
- [World](WORLD.md) - World creation and management

---

## 🎭 What are Entities?

An **Entity** is a unique identifier that groups components together. In Relics:

- Entities are identified by an `EntityId` (prefab name + sequence number)
- The `Entity` class is a **live handle** that provides access to components
- Entities are created from **prefabs** (templates)

```python
from relics import World

world = World()
world.register_prefab("player", {})

# Spawn creates an Entity handle
player = world.spawn("player")

# The Entity is just an ID with convenient methods
print(player.id)      # EntityId(prefab='player', sequence=1234567890)
print(player.prefab)  # 'player'
```

---

## 🆔 EntityId Structure

An `EntityId` consists of two parts:

| Field | Type | Description |
|-------|------|-------------|
| `prefab` | `str` | The prefab name this entity was created from |
| `sequence` | `int` | Unique timestamp + collision counter |

```python
from relics import EntityId

# EntityId is a frozen dataclass (immutable)
entity_id = EntityId(prefab="player", sequence=1234567890)

# IDs sort by prefab first, then by numeric sequence
ordered_ids = sorted(entity_ids)

# String representation
print(str(entity_id))  # "player_1234567890"

# Parse from string
parsed = EntityId.parse("player_1234567890")
assert parsed == entity_id

# Use as dictionary key
entity_data = {entity_id: {"score": 100}}
```

### Sequence Numbers

Sequence numbers use a hybrid timestamp + collision counter:

- Base: milliseconds since epoch * 1000
- If collision within same millisecond, increments

This ensures unique IDs without coordination, even at high spawn rates.

---

## 🎮 The Entity Handle

The `Entity` class is a **live reference** to an entity in the world. It:

- Validates the entity still exists on each operation
- Provides methods to access and modify components
- Manages relationships

```python
player = world.spawn("player")

# Entity validates existence on access
if world.has_entity(player.id):
    pos = player.get_component(Position)  # Validates here

# Multiple handles can reference the same entity
player2 = world.get_entity(player.id)
assert player == player2  # Same entity
```

### Handle Lifecycle

```python
player = world.spawn("player")

# Handle is valid
pos = player.get_component(Position)  # Works

# Remove the entity
world.remove(player)

# Handle is now stale
try:
    pos = player.get_component(Position)
except EntityNotFoundError:
    print("Entity no longer exists!")
```

---

## 🧱 What are Components?

**Components** are pure data containers. They define what an entity *is* or *has*.

> Components should have **no logic** - they are just data. All behavior goes in **Systems**.

```python
from dataclasses import dataclass
from relics import Component

@dataclass
class Position(Component):
    x: float
    y: float

@dataclass
class Velocity(Component):
    dx: float
    dy: float

@dataclass
class Health(Component):
    current: int
    maximum: int
```

---

## 📝 Defining Components

### Using Dataclasses (Recommended)

```python
from dataclasses import dataclass
from relics import Component

@dataclass
class Position(Component):
    x: float
    y: float
```

### Using Pydantic Dataclasses

```python
import pydantic.dataclasses

@pydantic.dataclasses.dataclass
class Position(Component):
    x: float
    y: float
```

### Immutable Components (Recommended)

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # Immutable
class Position(Component):
    x: float
    y: float
```

Immutable components are safer and work better with observers.

---

## ✅ Component Design Guidelines

### Good: Pure Data

```python
@dataclass
class Transform(Component):
    x: float
    y: float
    rotation: float
    scale: float = 1.0
```

### Good: Nested Data

```python
from typing import List

@dataclass
class Vector2:
    x: float
    y: float

@dataclass
class Polygon(Component):
    vertices: List[Vector2]
```

### ❌ Avoid: Logic in Components

```python
@dataclass
class Position(Component):
    x: float
    y: float

    def move(self, dx, dy):  # Don't do this!
        self.x += dx
        self.y += dy

    def distance_to(self, other):  # Don't do this!
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
```

### ❌ Avoid: References to Entities

```python
@dataclass
class Target(Component):
    entity: Entity  # Don't store Entity handles!
```

Instead, store EntityId:

```python
@dataclass
class Target(Component):
    target_id: EntityId  # Store the ID
```

Or better yet, use [Relationships](RELATIONSHIPS.md).

---

## ➕ Adding and Removing Components

### Adding Components

```python
# Add a single component
player.add_component(Position(x=10.0, y=20.0))

# Adding a duplicate raises an error
try:
    player.add_component(Position(x=0.0, y=0.0))
except DuplicateComponentError:
    print("Entity already has Position!")
```

### Removing Components

```python
# Remove by type
player.remove_component(Position)

# Removing non-existent raises an error
try:
    player.remove_component(Position)
except ComponentNotFoundError:
    print("Entity doesn't have Position!")
```

### Updating Components (Immutable Pattern)

Since components should be immutable, update by replacing:

```python
# Get current component
pos = player.get_component(Position)

# Create new component with updated values
new_pos = Position(x=pos.x + 10, y=pos.y + 5)

# Replace
player.remove_component(Position)
player.add_component(new_pos)
```

---

## 🔍 Checking and Getting Components

### has_component()

```python
if player.has_component(Health):
    health = player.get_component(Health)
    print(f"Health: {health.current}/{health.maximum}")
```

### get_component()

```python
# Returns the component instance
pos = player.get_component(Position)
print(f"Position: ({pos.x}, {pos.y})")

# Raises ComponentNotFoundError if not present
try:
    vel = player.get_component(Velocity)
except ComponentNotFoundError:
    print("No velocity component!")
```

### Type-Safe Access

```python
from typing import TypeVar

# get_component preserves the type
pos: Position = player.get_component(Position)
pos.x  # IDE knows this is a float
```

---

## 📦 Prefabs as Templates

Prefabs define default components for entities:

```python
# Register a prefab with default components
world.register_prefab("player", {
    Position: Position(x=0.0, y=0.0),
    Velocity: Velocity(dx=0.0, dy=0.0),
    Health: Health(current=100, maximum=100),
})

# Spawn with defaults
player = world.spawn("player")

# Spawn with overrides
player2 = world.spawn("player", overrides={
    Position: Position(x=50.0, y=50.0),
    Health: Health(current=200, maximum=200),
})

# Spawn with extra components not in prefab
player3 = world.spawn("player", overrides={
    Shield: Shield(amount=50),  # Not in prefab
})
```

### Listing Prefabs

```python
from relics import list_prefabs, get_prefab

# List all registered prefabs
for name in list_prefabs(world):
    print(f"Prefab: {name}")

# Get prefab definition
prefab_components = get_prefab(world, "player")
for comp_type, default_instance in prefab_components.items():
    print(f"  {comp_type.__name__}: {default_instance}")
```

---

## 🔄 Component Lifecycle

Components trigger events that observers can react to:

| Event | When Fired |
|-------|------------|
| `OnComponentAdded` | When `add_component()` is called |
| `OnComponentRemoved` | When `remove_component()` is called |
| `OnComponentChanged` | When a `@monitored` component's field changes |

```python
from relics import OnComponentAdded, OnComponentRemoved

class HealthTracker(OnComponentAdded):
    component_type = Health

    def on_component_added(self, entity, component):
        print(f"{entity.id} gained health: {component.current}")

class HealthLossTracker(OnComponentRemoved):
    component_type = Health

    def on_component_removed(self, entity, component):
        print(f"{entity.id} lost health component")
```

### Change Tracking with @monitored

For mutable components that need change tracking:

```python
from relics import monitored, OnComponentChanged

@monitored
@dataclass
class Health(Component):
    current: int
    maximum: int

class HealthWatcher(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        if field_name == "current" and new_value < old_value:
            print(f"{entity.id} took damage!")
```

See [Observers](OBSERVERS.md) for more on the `@monitored` decorator.

---

## ⚠️ Common Pitfalls

### 1. Storing Entity Handles in Components

```python
# ❌ Bad - handle may become stale
@dataclass
class Target(Component):
    entity: Entity

# ✅ Good - store ID, look up when needed
@dataclass
class Target(Component):
    target_id: EntityId
```

### 2. Mutating Frozen Components

```python
@dataclass(frozen=True)
class Position(Component):
    x: float
    y: float

pos = player.get_component(Position)
pos.x = 10  # Error! Frozen dataclass
```

### 3. Forgetting to Remove Before Adding

```python
# ❌ Raises DuplicateComponentError
player.add_component(Position(x=10, y=20))
player.add_component(Position(x=20, y=30))  # Error!

# ✅ Remove first, then add
player.remove_component(Position)
player.add_component(Position(x=20, y=30))
```

### 4. Using Components for Relationships

```python
# ❌ Bad - manually tracking relationships
@dataclass
class TeamMembership(Component):
    team_id: EntityId
    members: List[EntityId]

# ✅ Good - use the relationship system
from relics import Edge

@dataclass
class BelongsTo(Edge):
    role: str
```

See [Relationships](RELATIONSHIPS.md) for the proper way to handle entity connections.

---

## 📚 API Summary

### EntityId

| Method/Property | Description |
|-----------------|-------------|
| `EntityId(prefab, sequence)` | Create an entity ID |
| `EntityId.parse(string)` | Parse from string format |
| `str(entity_id)` | Convert to "prefab_sequence" format |
| `entity_id.prefab` | Get prefab name |
| `entity_id.sequence` | Get sequence number |

### Entity

| Method/Property | Description |
|-----------------|-------------|
| `entity.id` | Get the EntityId |
| `entity.prefab` | Get prefab name (shortcut) |
| `has_component(type)` | Check if component exists |
| `get_component(type)` | Get component instance |
| `add_component(instance)` | Add a component |
| `remove_component(type)` | Remove a component |

### Component

| Item | Description |
|------|-------------|
| `Component` | Base class for all components |
| `@monitored` | Decorator for change tracking |
| `is_monitored(obj)` | Check if class/instance is monitored |
