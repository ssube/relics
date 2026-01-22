# Systems

> Systems contain game logic. They query entities and process them each tick based on their components.

---

## 📋 Prerequisites

Before reading this document, you should be familiar with:
- [Getting Started](GETTING_STARTED.md) - Basic concepts and setup
- [Entities & Components](ENTITIES_COMPONENTS.md) - Entity and component patterns

---

## ⚙️ What are Systems?

A **System** encapsulates game logic that operates on entities with specific components. Systems:

- Define a **query** to select entities
- **Process** those entities each tick
- Run in **dependency order** (DAG-based)
- Can run at different **frequencies**

```python
from relics import System

class MovementSystem(System):
    def query(self):
        return self.q.with_all([Position, Velocity])

    def process(self, entities, components, delta):
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)
            # Update logic...
```

> **Philosophy**: Components hold data. Systems hold logic. Keep them separate.

---

## 🔧 Creating a System

Every system must implement two methods:

### query() - What Entities to Process

```python
def query(self):
    """Return a QueryBuilder that selects entities."""
    return self.q.with_all([Position, Velocity])
```

The `self.q` property gives you a fresh QueryBuilder for the world.

### process() - What to Do

```python
def process(self, entities, components, delta):
    """Process the selected entities.

    Args:
        entities: List of matching Entity handles
        components: List of component lists (from iterate())
        delta: Time elapsed since last tick in seconds
    """
    for entity in entities:
        # Your logic here
        pass
```

### Complete Example

```python
from dataclasses import dataclass
from typing import List
from relics import System, Component

@dataclass
class Position(Component):
    x: float
    y: float

@dataclass
class Velocity(Component):
    dx: float
    dy: float

class MovementSystem(System):
    """Moves entities based on their velocity."""

    def query(self):
        return self.q.with_all([Position, Velocity])

    def process(self, entities: List, components: List[List], delta: float):
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            # Create new position (immutable pattern)
            new_pos = Position(
                x=pos.x + vel.dx * delta,
                y=pos.y + vel.dy * delta
            )

            # Update the component
            entity.remove_component(Position)
            entity.add_component(new_pos)
```

---

## 🔍 System Queries

The query determines which entities the system processes.

### with_all() - Require Components

```python
def query(self):
    # Entities must have BOTH Position AND Velocity
    return self.q.with_all([Position, Velocity])
```

### with_any() - Require At Least One

```python
def query(self):
    # Entities must have Position AND (Weapon OR Shield)
    return self.q.with_all([Position]).with_any([Weapon, Shield])
```

### with_none() - Exclude Components

```python
def query(self):
    # Entities with Position but NOT Dead
    return self.q.with_all([Position]).with_none([Dead])
```

### with_filter() - Custom Predicates

```python
def query(self):
    def is_alive(entity):
        health = entity.get_component(Health)
        return health.current > 0

    return self.q.with_all([Health]).with_filter(is_alive)
```

### with_relationship() - Require Relationships

```python
def query(self):
    # Entities that target something
    return self.q.with_all([Position]).with_relationship(Targets)
```

### Combining Criteria

```python
def query(self):
    return (
        self.q
        .with_all([Position, Velocity])
        .with_any([Player, Enemy])
        .with_none([Dead, Disabled])
        .with_filter(lambda e: e.get_component(Health).current > 0)
    )
```

---

## 📊 Processing Entities

### Basic Processing

```python
def process(self, entities, components, delta):
    for entity in entities:
        pos = entity.get_component(Position)
        # Do something with pos...
```

### Using iterate() for Batch Processing

The `iterate()` method prepares component arrays for efficient access:

```python
def query(self):
    return self.q.with_all([Position, Velocity]).iterate([Position, Velocity])

def process(self, entities, components, delta):
    # components is now [List[Position], List[Velocity]]
    positions, velocities = components

    for i, entity in enumerate(entities):
        pos = positions[i]
        vel = velocities[i]
        # Process...
```

### Using execute_components() Directly

For maximum efficiency with large entity counts:

```python
def process(self, entities, components, delta):
    # Alternative: query directly
    for entity_id, pos, vel in self.q.with_all([Position, Velocity]).iterate([Position, Velocity]).execute_components():
        # Process with raw components
        pass
```

---

## 🔗 System Dependencies

Systems form a **Directed Acyclic Graph (DAG)** based on dependencies. Override `deps()` to declare ordering:

```python
from relics import RunOrder

class InputSystem(System):
    def deps(self):
        return {}  # No dependencies, runs early

class PhysicsSystem(System):
    def deps(self):
        return {
            RunOrder.AFTER: [InputSystem],  # Run after input
        }

class RenderSystem(System):
    def deps(self):
        return {
            RunOrder.AFTER: [PhysicsSystem],  # Run after physics
        }
```

### RunOrder Options

| Order | Meaning |
|-------|---------|
| `RunOrder.BEFORE` | This system runs **before** the listed systems |
| `RunOrder.AFTER` | This system runs **after** the listed systems |

### Complex Dependencies

```python
class CollisionSystem(System):
    def deps(self):
        return {
            RunOrder.AFTER: [MovementSystem],   # After movement
            RunOrder.BEFORE: [DamageSystem],    # Before damage
        }
```

### WILDCARD for Global Ordering

Use `System.WILDCARD` to run before/after **all** other systems:

```python
class TimingSystem(System):
    """Always runs first."""
    def deps(self):
        return {
            RunOrder.BEFORE: [System.WILDCARD],
        }

class CleanupSystem(System):
    """Always runs last."""
    def deps(self):
        return {
            RunOrder.AFTER: [System.WILDCARD],
        }
```

### Cycle Detection

Relics detects dependency cycles and raises `SystemDependencyCycleError`:

```python
class SystemA(System):
    def deps(self):
        return {RunOrder.AFTER: [SystemB]}

class SystemB(System):
    def deps(self):
        return {RunOrder.AFTER: [SystemA]}  # Cycle!

world.register_system(SystemA())
world.register_system(SystemB())  # Raises SystemDependencyCycleError
```

---

## ⏱️ Execution Frequency

Systems don't have to run every tick. Override `frequency()` to control execution:

### EVERY_TICK (Default)

```python
from relics import Frequency

class MovementSystem(System):
    def frequency(self):
        return Frequency.EVERY_TICK  # Default
```

### Every N Ticks

```python
class AISystem(System):
    def frequency(self):
        return Frequency.every_n_ticks(3)  # Run every 3 ticks
```

### Fixed Time Interval

```python
class NetworkSyncSystem(System):
    def frequency(self):
        return Frequency.fixed_interval(0.1)  # Run every 100ms
```

### Frequency Comparison

| Method | Use Case |
|--------|----------|
| `EVERY_TICK` | Physics, movement, input |
| `every_n_ticks(n)` | AI decisions, periodic checks |
| `fixed_interval(seconds)` | Network sync, autosave |

---

## 🎯 Sub-Systems

Systems can define **sub-systems** that run after the main process:

```python
class CombatSystem(System):
    def query(self):
        return self.q.with_all([Health, Position])

    def process(self, entities, components, delta):
        # Main combat logic
        pass

    def sub_systems(self):
        return [
            # (QueryBuilder, process_function)
            (
                self.q.with_all([Dead]),
                self._handle_dead_entities
            ),
            (
                self.q.with_all([Health]).with_filter(
                    lambda e: e.get_component(Health).current <= 0
                ),
                self._mark_as_dead
            ),
        ]

    def _handle_dead_entities(self, entities, components, delta):
        for entity in entities:
            # Cleanup dead entities
            self.world.remove(entity)

    def _mark_as_dead(self, entities, components, delta):
        for entity in entities:
            entity.add_component(Dead())
```

---

## 🏗️ System Design Patterns

### Single Responsibility

```python
# ✅ Good - one clear purpose
class MovementSystem(System):
    """Updates entity positions based on velocity."""
    pass

class CollisionSystem(System):
    """Detects and resolves collisions."""
    pass

# ❌ Bad - doing too much
class GameplaySystem(System):
    """Handles movement, collision, damage, AI, rendering..."""
    pass
```

### Query Caching

Queries are rebuilt each tick by default. For expensive queries, consider indexes:

```python
class TargetingSystem(System):
    def __init__(self):
        super().__init__()
        self._enemies_index = None

    def _ensure_index(self):
        if self._enemies_index is None:
            self._enemies_index = self.world.create_index(
                "enemies",
                self.world.query().with_all([Position, Enemy]),
            )
        return self._enemies_index

    def process(self, entities, components, delta):
        enemies = list(self._ensure_index())
        for entity in entities:
            # Find nearest enemy...
            pass
```

### Accessing the World

Systems have access to `self.world`:

```python
class SpawnSystem(System):
    def process(self, entities, components, delta):
        # Spawn new entities
        if should_spawn_enemy():
            self.world.spawn("enemy")

        # Query other entities
        players = list(self.world.query().with_all([Player]).execute_entities())

        # Emit events
        self.world.emit(WaveStartedEvent(wave_number=5))
```

---

## ⚠️ Common Pitfalls

### 1. Modifying Entities During Iteration

```python
def process(self, entities, components, delta):
    for entity in entities:
        if should_die(entity):
            self.world.remove(entity)  # May cause issues!
```

**Better**: Collect entities to remove, then remove after iteration:

```python
def process(self, entities, components, delta):
    to_remove = []
    for entity in entities:
        if should_die(entity):
            to_remove.append(entity)

    for entity in to_remove:
        self.world.remove(entity)
```

### 2. Forgetting to Use delta

```python
# ❌ Bad - speed depends on tick rate
def process(self, entities, components, delta):
    pos.x += velocity.dx

# ✅ Good - speed is consistent
def process(self, entities, components, delta):
    pos.x += velocity.dx * delta
```

### 3. Heavy Computation in query()

```python
# ❌ Bad - query() is called every tick
def query(self):
    self._expensive_computation()  # Don't do this!
    return self.q.with_all([Position])

# ✅ Good - do computation in __init__ or process()
```

### 4. Circular Dependencies

```python
# ❌ This will raise SystemDependencyCycleError
class A(System):
    def deps(self):
        return {RunOrder.AFTER: [B]}

class B(System):
    def deps(self):
        return {RunOrder.AFTER: [A]}
```

---

## 📚 API Summary

### System Base Class

| Method | Required | Description |
|--------|----------|-------------|
| `query()` | Yes | Return QueryBuilder for entity selection |
| `process(entities, components, delta)` | Yes | Process the selected entities |
| `deps()` | No | Declare execution order dependencies |
| `frequency()` | No | Control execution frequency |
| `sub_systems()` | No | Define additional sub-system queries |

### System Properties

| Property | Description |
|----------|-------------|
| `self.world` | The World this system is registered with |
| `self.q` | Shortcut for `self.world.query()` |

### Frequency Class

| Method | Description |
|--------|-------------|
| `Frequency.EVERY_TICK` | Run every tick (default) |
| `Frequency.every_n_ticks(n)` | Run every N ticks |
| `Frequency.fixed_interval(seconds)` | Run at fixed time intervals |

### RunOrder Enum

| Value | Description |
|-------|-------------|
| `RunOrder.BEFORE` | This system runs before listed systems |
| `RunOrder.AFTER` | This system runs after listed systems |

### Special Values

| Value | Description |
|-------|-------------|
| `System.WILDCARD` | Match all other systems in deps() |
