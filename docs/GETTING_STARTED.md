# Getting Started with Relics

> Relics is an Entity-Component-System (ECS) framework with graph database semantics for Python.

This guide will walk you through the basics of using Relics to build data-driven applications and games.

---

## 📋 Prerequisites

- **Python 3.11+** - Relics uses modern Python features
- **pydantic** - For data validation and serialization

---

## 🚀 Installation

### From PyPI (when published)

```bash
pip install relics
```

### From Source

```bash
git clone https://github.com/ssube/relics.git
cd relics
pip install -e .
```

### For Development

```bash
pip install -e ".[dev]"
```

---

## 🎮 Your First World

A **World** is the central manager in Relics. It holds all entities, systems, and observers.

```python
from relics import World

# Create a new world
world = World()

print(f"World ID: {world.id}")
print(f"Current epoch: {world.epoch}")
```

> **Epoch** is a counter that increments each time you call `world.tick()`. It represents the simulation step.

---

## 🧱 Creating Components

**Components** are pure data containers. They define what an entity *is* or *has*.

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

### ✅ Good Component Design

```python
@dataclass
class Position(Component):
    x: float
    y: float
```

### ❌ Avoid Logic in Components

```python
@dataclass
class Position(Component):
    x: float
    y: float

    def move(self, dx, dy):  # Don't do this!
        self.x += dx
        self.y += dy
```

> Components should be pure data. Put logic in **Systems** instead.

---

## 📦 Registering Prefabs

**Prefabs** are templates for creating entities. They define which components an entity starts with.

```python
from relics import World

world = World()

# Register a "player" prefab
world.register_prefab("player", {
    Position: Position(x=0.0, y=0.0),
    Velocity: Velocity(dx=0.0, dy=0.0),
    Health: Health(current=100, maximum=100),
})

# Register an "enemy" prefab
world.register_prefab("enemy", {
    Position: Position(x=10.0, y=10.0),
    Health: Health(current=50, maximum=50),
})
```

---

## 🎭 Spawning Entities

Use `spawn()` to create entities from prefabs:

```python
# Spawn a player at the origin
player = world.spawn("player")
print(f"Player ID: {player.id}")
print(f"Player prefab: {player.prefab}")

# Spawn an enemy with custom position
enemy = world.spawn("enemy", overrides={
    Position: Position(x=50.0, y=30.0),
})

# Access components
pos = player.get_component(Position)
print(f"Player position: ({pos.x}, {pos.y})")
```

### Component Operations

```python
# Check if entity has a component
if player.has_component(Health):
    health = player.get_component(Health)
    print(f"Health: {health.current}/{health.maximum}")

# Add a new component
@dataclass
class Shield(Component):
    amount: int

player.add_component(Shield(amount=25))

# Remove a component
player.remove_component(Shield)
```

---

## 🔍 Querying Entities

Relics provides a powerful query system for finding entities:

```python
# Find all entities with Position and Velocity
for entity in world.query().with_all([Position, Velocity]).execute_entities():
    pos = entity.get_component(Position)
    vel = entity.get_component(Velocity)
    print(f"{entity.id}: pos=({pos.x}, {pos.y}), vel=({vel.dx}, {vel.dy})")

# Find entities with Health but NOT Position (e.g., abstract entities)
query = world.query().with_all([Health]).with_none([Position])
for entity in query.execute_entities():
    print(f"Entity without position: {entity.id}")

# Use filters for complex conditions
def is_low_health(entity):
    health = entity.get_component(Health)
    return health.current < health.maximum * 0.25

for entity in world.query().with_all([Health]).with_filter(is_low_health).execute_entities():
    print(f"Low health entity: {entity.id}")
```

### Query Execution Methods

| Method | Returns | Use Case |
|--------|---------|----------|
| `execute_ids()` | `Iterator[EntityId]` | When you only need IDs |
| `execute_entities()` | `Iterator[Entity]` | When you need to access components |
| `execute_components()` | `Iterator[Tuple]` | Batch processing with `iterate()` |

---

## ⚙️ Adding a System

**Systems** contain game logic. They process entities that match their query.

```python
from relics import System
from typing import List

class MovementSystem(System):
    """Moves entities based on their velocity."""

    def query(self):
        return self.q.with_all([Position, Velocity])

    def process(self, entities: List, components: List[List], delta: float):
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            # Update position (create new immutable component)
            new_pos = Position(
                x=pos.x + vel.dx * delta,
                y=pos.y + vel.dy * delta
            )

            # Replace the component
            entity.remove_component(Position)
            entity.add_component(new_pos)

# Register the system
world.register_system(MovementSystem())

# Run one tick (delta = 1/60 second for 60 FPS)
world.tick(1/60)
```

### System Groups

Systems can be assigned to **groups** for selective execution. This is useful for pausing game systems while keeping input/rendering active:

```python
class GameSystem(System):
    group = "game"  # Assign to "game" group
    # ...

class InputSystem(System):
    group = "input"  # Assign to "input" group
    # ...

# Normal tick - run all systems
world.tick(delta)

# Paused - skip "game" group
world.tick(delta, exclude_groups=["game"])
```

See [Systems](SYSTEMS.md) for more details on groups and pausing.

---

## 👀 Adding an Observer

**Observers** react to events like entity creation, component changes, etc.

```python
from relics import OnEntityCreated, OnComponentAdded

class PlayerSpawnLogger(OnEntityCreated):
    """Logs when a player is spawned."""

    prefab = "player"  # Only observe player entities

    def on_entity_created(self, entity):
        print(f"Player spawned: {entity.id}")

class HealthWatcher(OnComponentAdded):
    """Reacts when Health is added to any entity."""

    component_type = Health

    def on_component_added(self, entity, component):
        print(f"Entity {entity.id} gained health: {component.current}/{component.maximum}")

# Register observers
world.observe(PlayerSpawnLogger())
world.observe(HealthWatcher())

# Events are queued and processed at the end of tick()
player = world.spawn("player")
world.tick(0.0)  # Observer callbacks run here
```

---

## 💾 Saving and Loading

Relics supports JSON persistence for saving and loading world state:

```python
from relics import save, load, save_relic, load_relic, list_relics

# Save the entire world state
save(world, "game_state.json")

# Load into a world (requires component registry)
component_registry = {
    "Position": Position,
    "Velocity": Velocity,
    "Health": Health,
}

new_world = World()
load(new_world, "game_state.json", component_registry)

# Named snapshots (relics)
save_relic(world, "checkpoint_1", "./saves/")
save_relic(world, "checkpoint_2", "./saves/")

# List available relics
for relic in list_relics("./saves/"):
    print(f"{relic.name}: epoch {relic.epoch}, created {relic.created_at}")

# Load a specific relic
load_relic(world, "checkpoint_1", "./saves/", component_registry)
```

---

## 🎯 Complete Example

Here's a complete example putting it all together:

```python
from dataclasses import dataclass
from typing import List

from relics import (
    World,
    Component,
    System,
    OnEntityCreated,
)

# Define components
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

# Define a system
class MovementSystem(System):
    def query(self):
        return self.q.with_all([Position, Velocity])

    def process(self, entities: List, components: List[List], delta: float):
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            new_pos = Position(
                x=pos.x + vel.dx * delta,
                y=pos.y + vel.dy * delta
            )
            entity.remove_component(Position)
            entity.add_component(new_pos)

# Define an observer
class SpawnLogger(OnEntityCreated):
    prefab = None  # Watch all prefabs

    def on_entity_created(self, entity):
        print(f"Entity spawned: {entity.id}")

# Set up the world
world = World()

# Register prefabs
world.register_prefab("player", {
    Position: Position(x=0.0, y=0.0),
    Velocity: Velocity(dx=1.0, dy=0.5),
    Health: Health(current=100, maximum=100),
})

# Register systems and observers
world.register_system(MovementSystem())
world.observe(SpawnLogger())

# Spawn entities
player = world.spawn("player")

# Game loop
for frame in range(60):  # Run for 60 frames
    world.tick(1/60)  # 60 FPS

    if frame % 10 == 0:
        pos = player.get_component(Position)
        print(f"Frame {frame}: Player at ({pos.x:.2f}, {pos.y:.2f})")
```

---

## 🎯 Next Steps

Now that you understand the basics, explore these topics:

- **[World](WORLD.md)** - Deep dive into the World class and tick cycle
- **[Entities & Components](ENTITIES_COMPONENTS.md)** - Entity handles and component patterns
- **[Systems](SYSTEMS.md)** - System dependencies, frequency, and sub-systems
- **[Observers](OBSERVERS.md)** - Event types and the `@monitored` decorator
- **[Relationships](RELATIONSHIPS.md)** - Graph database semantics with edges
- **[Best Practices](BEST_PRACTICES.md)** - Patterns, performance tips, and anti-patterns

---

## 📚 API Reference

| Module | Key Classes |
|--------|-------------|
| `relics` | `World`, `Entity`, `Component`, `Edge` |
| `relics` | `System`, `Frequency`, `RunOrder` |
| `relics` | `OnEntityCreated`, `OnComponentAdded`, etc. |
| `relics` | `save`, `load`, `save_relic`, `load_relic` |
