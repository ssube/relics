# World

> The World is the central manager in Relics. It holds all entities, components, relationships, systems, and observers.

---

## 📋 Prerequisites

Before reading this document, you should be familiar with:
- [Getting Started](GETTING_STARTED.md) - Basic concepts and setup

---

## 🌍 What is a World?

A **World** is the container for your entire ECS simulation. Think of it as a database that:

- Stores all **entities** and their **components**
- Manages **relationships** between entities (graph edges)
- Executes **systems** in dependency order
- Dispatches events to **observers**
- Tracks **epochs** (simulation steps)

```python
from relics import World

world = World()
```

> **Important**: A World is **single-threaded**. Each instance should only be accessed from one thread. For parallel processing, use multiple World instances.

---

## 🎯 Creating a World

### Basic Creation

```python
from relics import World

# Auto-generated UUID
world = World()
print(world.id)  # e.g., "550e8400-e29b-41d4-a716-446655440000"

# Custom world ID
world = World(world_id="my-game-world")
print(world.id)  # "my-game-world"
```

### World Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique world identifier |
| `epoch` | `int` | Current epoch number (incremented by `tick()`) |

---

## 📦 Prefab Registration

Prefabs are templates for creating entities. Register them before spawning:

```python
from dataclasses import dataclass
from relics import Component

@dataclass
class Position(Component):
    x: float
    y: float

@dataclass
class Health(Component):
    current: int
    maximum: int

# Register a prefab
world.register_prefab("player", {
    Position: Position(x=0.0, y=0.0),
    Health: Health(current=100, maximum=100),
})
```

### Loading Prefabs from JSON

```python
from relics import load_prefabs_from_json

component_registry = {
    "Position": Position,
    "Health": Health,
}

load_prefabs_from_json(world, "prefabs.json", component_registry)
```

Example `prefabs.json`:
```json
{
    "player": {
        "components": {
            "Position": {"x": 0.0, "y": 0.0},
            "Health": {"current": 100, "maximum": 100}
        }
    },
    "enemy": {
        "components": {
            "Position": {"x": 10.0, "y": 10.0},
            "Health": {"current": 50, "maximum": 50}
        }
    }
}
```

---

## 🎭 Entity Spawning

### spawn()

Create entities from registered prefabs:

```python
# Basic spawn
player = world.spawn("player")

# Spawn with component overrides
enemy = world.spawn("enemy", overrides={
    Position: Position(x=100.0, y=50.0),
    Health: Health(current=75, maximum=75),
})

# Add extra components not in prefab
@dataclass
class Shield(Component):
    amount: int

boss = world.spawn("enemy", overrides={
    Shield: Shield(amount=50),  # Not in "enemy" prefab
})
```

### Entity Retrieval

```python
from relics import EntityId

# Get entity by ID
entity_id = player.id
same_player = world.get_entity(entity_id)

# Check if entity exists
if world.has_entity(entity_id):
    print("Entity exists!")

# Parse entity ID from string
entity_id = EntityId.parse("player_1234567890")
```

### Entity Removal

```python
# Remove by Entity handle
world.remove(player)

# Remove by EntityId
world.remove(entity_id)
```

> Removing an entity also cleans up all its relationships (both outgoing and incoming).

---

## ⏰ The Tick Cycle

The `tick()` method advances the simulation:

```python
# Game loop
delta = 1/60  # 60 FPS
while game_running:
    world.tick(delta)
```

### What Happens During a Tick

1. **Epoch increments** - `world.epoch` increases by 1
2. **Systems execute** - In topologically-sorted order based on dependencies (filtered by groups)
3. **Observer queue processes** - Queued events are dispatched

```
┌─────────────────────────────────────────────────────────────┐
│     world.tick(delta, include_groups=..., exclude_groups=...)│
├─────────────────────────────────────────────────────────────┤
│  1. epoch += 1                                              │
│  2. For each system (sorted by dependencies):               │
│     - Check group filter (include/exclude)                  │
│     - Check paused state                                    │
│     - Check frequency (should_run?)                         │
│     - Execute query                                         │
│     - Call process(entities, components, delta)             │
│     - Execute sub_systems                                   │
│  3. Process observer queue:                                 │
│     - OnEntityCreated, OnComponentAdded, etc.               │
│     - Custom events                                         │
└─────────────────────────────────────────────────────────────┘
```

### Delta Time

The `delta` parameter represents time elapsed since the last tick:

```python
# Fixed timestep (recommended for physics)
FIXED_DELTA = 1/60
world.tick(FIXED_DELTA)

# Variable timestep (for rendering)
import time
last_time = time.time()
while running:
    current_time = time.time()
    delta = current_time - last_time
    last_time = current_time
    world.tick(delta)
```

### System Group Filtering

Use `include_groups` and `exclude_groups` to selectively run systems:

```python
# Run all systems (default)
world.tick(delta)

# Only run specific groups
world.tick(delta, include_groups=["input", "render"])

# Exclude certain groups (useful for pausing)
world.tick(delta, exclude_groups=["game"])

# Combine both (must be in include AND not in exclude)
world.tick(delta, include_groups=["input", "game"], exclude_groups=["game"])
```

This is useful for implementing game pause:

```python
paused = False

while running:
    if paused:
        # Skip game logic, but keep input and rendering
        world.tick(delta, exclude_groups=["game"])
    else:
        world.tick(delta)
```

See [Systems](SYSTEMS.md) for details on defining system groups.

---

## 🔧 Registering Systems

Systems contain game logic and process entities:

```python
from relics import System

class MovementSystem(System):
    def query(self):
        return self.q.with_all([Position, Velocity])

    def process(self, entities, components, delta):
        for entity in entities:
            # Update logic here
            pass

# Register the system
world.register_system(MovementSystem())
```

### System Execution Order

Systems are automatically sorted based on their declared dependencies:

```python
from relics import RunOrder

class PhysicsSystem(System):
    def deps(self):
        return {
            RunOrder.BEFORE: [RenderSystem],  # Run before rendering
            RunOrder.AFTER: [InputSystem],    # Run after input
        }
```

See [Systems](SYSTEMS.md) for detailed documentation.

---

## 👁️ Registering Observers

Observers react to events in the world:

```python
from relics import OnEntityCreated

class SpawnLogger(OnEntityCreated):
    prefab = "player"

    def on_entity_created(self, entity):
        print(f"Player spawned: {entity.id}")

# Register the observer
world.observe(SpawnLogger())
```

### Custom Events

```python
from dataclasses import dataclass
from relics import CustomEvent, OnCustomEvent

@dataclass
class DamageEvent(CustomEvent):
    source_id: str
    target_id: str
    amount: float

class DamageHandler(OnCustomEvent):
    event_type = DamageEvent

    def on_event(self, event):
        print(f"Damage: {event.amount} from {event.source_id} to {event.target_id}")

world.observe(DamageHandler())

# Emit custom events
world.emit(DamageEvent(source_id="player_1", target_id="enemy_1", amount=25.0))
world.tick(0)  # Event processed here
```

See [Observers](OBSERVERS.md) for detailed documentation.

---

## 📊 Creating Indexes

Indexes provide efficient access to frequently-queried entity sets:

```python
# Create a lazy index (re-executes query each access)
enemies_query = world.query().with_all([Position, Health])
world.create_index("enemies", enemies_query)

# Create a materialized index (cached, watches component changes)
world.create_index(
    "active_players",
    world.query().with_all([Position, IsActive]),
    watches=[IsActive],
    materialized=True,
)

# Use an index
enemies_index = world.index("enemies")
print(f"Enemy count: {len(enemies_index)}")

for entity in enemies_index:
    print(f"Enemy: {entity.id}")
```

### Lazy vs Materialized

| Type | Pros | Cons |
|------|------|------|
| **Lazy** | Always fresh, no memory overhead | Re-executes query each access |
| **Materialized** | Fast access, cached results | Needs manual invalidation, uses memory |

---

## 🔍 Querying Entities

Create queries using the fluent builder API:

```python
# Start a new query
query = world.query()

# Find all entities with Position AND Velocity
query = world.query().with_all([Position, Velocity])

# Find entities with at least one of these
query = world.query().with_any([Weapon, Shield])

# Exclude entities with certain components
query = world.query().with_none([Dead, Disabled])

# Custom filter functions
def is_nearby(entity):
    pos = entity.get_component(Position)
    return pos.x < 100 and pos.y < 100

query = world.query().with_all([Position]).with_filter(is_nearby)
```

### Execution Methods

```python
# Get only IDs (fastest)
for entity_id in query.execute_ids():
    print(entity_id)

# Get Entity handles
for entity in query.execute_entities():
    pos = entity.get_component(Position)
    print(f"{entity.id}: ({pos.x}, {pos.y})")

# Get components directly (for batch processing)
for entity_id, pos, vel in query.iterate([Position, Velocity]).execute_components():
    print(f"{entity_id}: pos=({pos.x}, {pos.y})")
```

---

## 🎛️ World Configuration

### Component Type Registration

Components are auto-registered when added to prefabs or entities, but you can also register manually:

```python
world.register_component_type(Position)
world.register_component_type(Velocity)
```

This is useful for persistence when loading worlds that may have components not yet seen.

### Edge Type Registration

Similarly for relationship edge types:

```python
world.register_edge_type(BelongsTo)
world.register_edge_type(Targets)
```

---

## 🔄 Common Patterns

### Game Loop Pattern

```python
def game_loop():
    world = World()

    # Setup
    setup_prefabs(world)
    setup_systems(world)
    setup_observers(world)

    # Spawn initial entities
    world.spawn("player")
    for _ in range(10):
        world.spawn("enemy")

    # Main loop
    delta = 1/60
    while not game_over:
        handle_input()
        world.tick(delta)
        render()
```

### Entity Export (Debugging)

```python
# Export entity data for debugging/tooling
data = world.export_entity(player.id)
print(data)
# {
#     "id": "player_1234567890",
#     "prefab": "player",
#     "components": {
#         "Position": {"x": 10.0, "y": 20.0},
#         "Health": {"current": 100, "maximum": 100}
#     },
#     "relationships": {},
#     "incoming_relationships": {}
# }
```

### Multiple Worlds

```python
# Run separate simulations
game_world = World(world_id="game")
ui_world = World(world_id="ui")

# Different tick rates
while running:
    game_world.tick(1/60)   # 60 FPS game logic
    if frame % 2 == 0:
        ui_world.tick(1/30)  # 30 FPS UI updates
```

---

## 📚 API Summary

| Method | Description |
|--------|-------------|
| `World(world_id=None)` | Create a new world |
| `world.id` | Get world UUID |
| `world.epoch` | Get current epoch |
| `register_prefab(name, components)` | Register an entity template |
| `spawn(prefab, overrides=None)` | Create entity from prefab |
| `get_entity(entity_id)` | Get entity handle by ID |
| `has_entity(entity_id)` | Check if entity exists |
| `remove(entity)` | Remove an entity |
| `register_system(system)` | Add a system |
| `observe(observer)` | Add an observer |
| `tick(delta)` | Advance simulation |
| `query()` | Start building a query |
| `emit(event)` | Emit a custom event |
| `create_index(name, query, ...)` | Create a secondary index |
| `index(name)` | Get an index by name |
| `export_entity(entity_id)` | Export entity data |
| `register_component_type(type)` | Register for persistence |
| `register_edge_type(type)` | Register for persistence |
