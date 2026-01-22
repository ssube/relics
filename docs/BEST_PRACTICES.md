# Best Practices

> Patterns, performance tips, and organization guidance for building with Relics.

---

## 📋 Overview

This document covers:
- Component design guidelines
- System organization patterns
- Query performance optimization
- Project structure recommendations
- Common game patterns
- Anti-patterns to avoid

---

## 🧱 Component Design

### Pure Data, No Logic

Components should be data containers only. All behavior belongs in Systems.

### ✅ Good

```python
@dataclass
class Position(Component):
    x: float
    y: float

@dataclass
class Velocity(Component):
    dx: float
    dy: float
```

### ❌ Avoid

```python
@dataclass
class Position(Component):
    x: float
    y: float

    def move(self, dx, dy):  # Logic doesn't belong here
        self.x += dx
        self.y += dy

    def distance_to(self, other):  # Move to a utility function
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
```

### Prefer Immutable Components

Immutable components are safer and work better with observers.

### ✅ Good

```python
@dataclass(frozen=True)
class Position(Component):
    x: float
    y: float

# Update by replacement
entity.remove_component(Position)
entity.add_component(Position(x=10, y=20))
```

### ❌ Avoid (unless using @monitored)

```python
@dataclass
class Position(Component):
    x: float
    y: float

pos = entity.get_component(Position)
pos.x = 10  # Mutation without tracking
```

### Use Flat Data Structures

```python
# ✅ Good - flat and simple
@dataclass
class Transform(Component):
    x: float
    y: float
    rotation: float
    scale_x: float = 1.0
    scale_y: float = 1.0

# ❌ Avoid - unnecessary nesting
@dataclass
class Transform(Component):
    position: Dict[str, float]
    rotation: float
    scale: Dict[str, float]
```

### Don't Store Entity Handles

```python
# ❌ Bad - handles can become stale
@dataclass
class Target(Component):
    entity: Entity

# ✅ Good - store ID, use relationships
@dataclass
class TargetId(Component):
    target_id: EntityId

# ✅ Better - use the relationship system
class Targets(Edge):
    pass
```

---

## ⚙️ System Organization

### Single Responsibility

Each system should do one thing well.

```python
# ✅ Good - focused systems
class MovementSystem(System): pass
class CollisionSystem(System): pass
class DamageSystem(System): pass
class AISystem(System): pass

# ❌ Avoid - monolithic systems
class GameplaySystem(System):
    """Handles movement, collision, damage, AI, rendering..."""
    pass
```

### Query Efficiency

Only query for components you need.

```python
# ✅ Good - minimal query
def query(self):
    return self.q.with_all([Position, Velocity])

# ❌ Avoid - querying unused components
def query(self):
    return self.q.with_all([Position, Velocity, Health, Name, Sprite])
```

### Use Dependency Ordering

Declare dependencies to ensure correct execution order.

```python
class InputSystem(System):
    def deps(self):
        return {}  # Runs early

class MovementSystem(System):
    def deps(self):
        return {RunOrder.AFTER: [InputSystem]}

class CollisionSystem(System):
    def deps(self):
        return {RunOrder.AFTER: [MovementSystem]}

class RenderSystem(System):
    def deps(self):
        return {RunOrder.AFTER: [CollisionSystem]}
```

### Group Related Logic

Use sub-systems for related functionality:

```python
class CombatSystem(System):
    def query(self):
        return self.q.with_all([Health, Position])

    def process(self, entities, components, delta):
        # Main combat logic
        pass

    def sub_systems(self):
        return [
            (self.q.with_all([Dead]), self._cleanup_dead),
            (self.q.with_all([Stunned]), self._process_stuns),
        ]
```

---

## 🔍 Query Performance

### Execution Method Comparison

| Method | Speed | Memory | Use Case |
|--------|-------|--------|----------|
| `execute_ids()` | Fastest | Lowest | When you only need IDs |
| `execute_entities()` | Fast | Medium | General entity processing |
| `execute_components()` | Fast | Higher | Batch processing with iterate() |

```python
# Fastest - just IDs
for entity_id in query.execute_ids():
    pass

# Good for most cases
for entity in query.execute_entities():
    pos = entity.get_component(Position)

# Best for batch processing
for entity_id, pos, vel in query.iterate([Position, Velocity]).execute_components():
    pass
```

### When to Use Indexes

Use indexes for frequently-accessed queries:

```python
# ✅ Good - create index for hot queries
world.create_index(
    "enemies",
    world.query().with_all([Position, Enemy]),
)

# Use the index
for enemy in world.index("enemies"):
    pass
```

### Lazy vs Materialized Indexes

| Type | Best For |
|------|----------|
| **Lazy** | Infrequent queries, small result sets |
| **Materialized** | Frequent queries, stable membership |

```python
# Lazy - re-executes each access
world.create_index("items", query, materialized=False)

# Materialized - cached, needs component watches
world.create_index(
    "active_players",
    world.query().with_all([Player, IsActive]),
    watches=[IsActive],
    materialized=True,
)
```

### Filter Optimization

Put cheap filters first:

```python
# ✅ Good - component checks are cheap
def query(self):
    return (
        self.q
        .with_all([Position])      # Cheap
        .with_none([Dead])         # Cheap
        .with_filter(is_in_range)  # Expensive - last
    )
```

---

## 📁 Project Organization

### Recommended File Structure

```
my_game/
├── components/
│   ├── __init__.py
│   ├── transform.py      # Position, Velocity, Rotation
│   ├── combat.py         # Health, Damage, Shield
│   └── ai.py             # AIState, Patrol, Target
├── systems/
│   ├── __init__.py
│   ├── movement.py       # MovementSystem
│   ├── combat.py         # CombatSystem, DamageSystem
│   └── ai.py             # AISystem, PathfindingSystem
├── observers/
│   ├── __init__.py
│   ├── audio.py          # Sound effect observers
│   └── ui.py             # UI update observers
├── edges/
│   ├── __init__.py
│   └── relationships.py  # BelongsTo, Targets, etc.
├── prefabs/
│   ├── __init__.py
│   └── entities.json     # Prefab definitions
├── events/
│   ├── __init__.py
│   └── custom.py         # Custom event types
└── main.py               # Game entry point
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase noun | `Position`, `Health`, `AIState` |
| Systems | PascalCase + "System" | `MovementSystem`, `CombatSystem` |
| Observers | PascalCase + purpose | `HealthWatcher`, `SpawnLogger` |
| Edges | PascalCase verb/noun | `BelongsTo`, `Targets`, `ParentOf` |
| Prefabs | snake_case | `"player"`, `"enemy_goblin"`, `"item_sword"` |

---

## 🎮 Common Game Patterns

### Player Entity Pattern

```python
# Components for the player
@dataclass
class Player(Component):
    """Marker component for player entity."""
    player_id: str = "player1"

@dataclass
class Input(Component):
    move_x: float = 0.0
    move_y: float = 0.0
    fire: bool = False

# Prefab
world.register_prefab("player", {
    Position: Position(x=0, y=0),
    Velocity: Velocity(dx=0, dy=0),
    Health: Health(current=100, maximum=100),
    Player: Player(),
    Input: Input(),
})

# Find player easily
def get_player(world):
    for entity in world.query().with_all([Player]).execute_entities():
        return entity
    return None
```

### Enemy AI Pattern

```python
from enum import Enum, auto

class AIStateType(Enum):
    IDLE = auto()
    PATROL = auto()
    CHASE = auto()
    ATTACK = auto()
    FLEE = auto()

@dataclass
class AIState(Component):
    state: AIStateType = AIStateType.IDLE
    target_id: Optional[EntityId] = None

class AISystem(System):
    def query(self):
        return self.q.with_all([AIState, Position])

    def process(self, entities, components, delta):
        for entity in entities:
            ai = entity.get_component(AIState)

            if ai.state == AIStateType.IDLE:
                self._process_idle(entity, ai)
            elif ai.state == AIStateType.PATROL:
                self._process_patrol(entity, ai)
            elif ai.state == AIStateType.CHASE:
                self._process_chase(entity, ai)
            # etc.
```

### Inventory System

```python
@dataclass
class Item(Component):
    name: str
    weight: float

@dataclass
class Inventory(Component):
    max_weight: float = 100.0

class OwnedBy(Edge):
    slot: str = "inventory"

# Pick up item
def pick_up_item(player, item):
    item.add_relationship(OwnedBy(slot="inventory"), player.id)

# Get inventory
def get_inventory(player):
    items = []
    for entity in world.query().with_relationship(OwnedBy, player.id).execute_entities():
        items.append(entity)
    return items

# Equip item
def equip_item(player, item, slot):
    # Remove old ownership
    for edge, owner_id in item.get_relationships(OwnedBy):
        item.remove_relationship(OwnedBy, owner_id)
    # Add with new slot
    item.add_relationship(OwnedBy(slot=slot), player.id)
```

### Status Effects

```python
@dataclass
class StatusEffect(Component):
    effect_type: str
    duration: float
    stacks: int = 1
    tick_rate: float = 1.0
    time_since_tick: float = 0.0

class StatusEffectSystem(System):
    def query(self):
        return self.q.with_all([StatusEffect, Health])

    def process(self, entities, components, delta):
        to_remove = []

        for entity in entities:
            effect = entity.get_component(StatusEffect)

            # Update duration
            new_duration = effect.duration - delta
            new_time = effect.time_since_tick + delta

            # Apply effect on tick
            if new_time >= effect.tick_rate:
                self._apply_effect(entity, effect)
                new_time = 0.0

            if new_duration <= 0:
                to_remove.append((entity, StatusEffect))
            else:
                # Update effect
                entity.remove_component(StatusEffect)
                entity.add_component(StatusEffect(
                    effect_type=effect.effect_type,
                    duration=new_duration,
                    stacks=effect.stacks,
                    tick_rate=effect.tick_rate,
                    time_since_tick=new_time,
                ))

        for entity, comp_type in to_remove:
            entity.remove_component(comp_type)

    def _apply_effect(self, entity, effect):
        health = entity.get_component(Health)
        if effect.effect_type == "poison":
            new_health = Health(
                current=max(0, health.current - 5 * effect.stacks),
                maximum=health.maximum
            )
            entity.remove_component(Health)
            entity.add_component(new_health)
```

---

## 🚀 Performance Tips

### Batch Processing with iterate()

```python
def query(self):
    return self.q.with_all([Position, Velocity]).iterate([Position, Velocity])

def process(self, entities, components, delta):
    positions, velocities = components

    # Process in batch - more cache-friendly
    for i, entity in enumerate(entities):
        pos = positions[i]
        vel = velocities[i]
        # Update...
```

### Use Markers Instead of Filters

```python
# ❌ Slow - filter function called for every entity
def query(self):
    return self.q.with_all([Health]).with_filter(lambda e: e.get_component(Health).current <= 0)

# ✅ Fast - marker component check
@dataclass
class Dead(Component):
    pass

def query(self):
    return self.q.with_all([Dead])
```

### Materialized Indexes for Hot Paths

```python
# Create once at startup
world.create_index(
    "active_enemies",
    world.query().with_all([Enemy, Position]).with_none([Dead]),
    watches=[Dead],
    materialized=True,
)

# Fast access in hot path
def get_nearby_enemies(position, radius):
    for enemy in world.index("active_enemies"):
        pos = enemy.get_component(Position)
        if distance(position, pos) < radius:
            yield enemy
```

### System Frequency Tuning

```python
# Physics - every tick
class PhysicsSystem(System):
    def frequency(self):
        return Frequency.EVERY_TICK

# AI - every 3 ticks
class AISystem(System):
    def frequency(self):
        return Frequency.every_n_ticks(3)

# Autosave - every 5 minutes
class AutosaveSystem(System):
    def frequency(self):
        return Frequency.fixed_interval(300.0)
```

---

## ⚠️ Anti-Patterns to Avoid

### 1. God Component

```python
# ❌ Bad - too many responsibilities
@dataclass
class Entity(Component):
    x: float
    y: float
    health: int
    mana: int
    name: str
    sprite: str
    ai_state: str
    inventory: List[str]
    # ...50 more fields...
```

**Fix**: Split into focused components.

### 2. Logic in Components

```python
# ❌ Bad
@dataclass
class Damageable(Component):
    health: int

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.die()  # Logic doesn't belong here!
```

**Fix**: Put logic in systems.

### 3. System-to-System Communication

```python
# ❌ Bad - direct coupling
class MovementSystem(System):
    def __init__(self, collision_system):
        self.collision_system = collision_system

    def process(self, ...):
        self.collision_system.check(...)
```

**Fix**: Use components, events, or query results instead.

### 4. Querying in Observers

```python
# ❌ Bad - observers shouldn't do heavy queries
class BadObserver(OnComponentAdded):
    component_type = Position

    def on_component_added(self, entity, component):
        # Heavy query in observer
        for other in self.world.query().with_all([Position]).execute_entities():
            if distance(entity, other) < 10:
                # ...
```

**Fix**: Use observers for simple reactions; complex logic belongs in systems.

### 5. Mutating During Iteration

```python
# ❌ Bad - modifying while iterating
def process(self, entities, components, delta):
    for entity in entities:
        if should_die(entity):
            self.world.remove(entity)  # Modifies collection!
```

**Fix**: Collect changes, apply after iteration.

```python
# ✅ Good
def process(self, entities, components, delta):
    to_remove = []
    for entity in entities:
        if should_die(entity):
            to_remove.append(entity)

    for entity in to_remove:
        self.world.remove(entity)
```

### 6. Ignoring Delta Time

```python
# ❌ Bad - frame-rate dependent
def process(self, entities, components, delta):
    pos.x += velocity.dx  # Speed varies with FPS!

# ✅ Good - frame-rate independent
def process(self, entities, components, delta):
    pos.x += velocity.dx * delta
```

### 7. Circular Dependencies

```python
# ❌ Bad - will crash
class A(System):
    def deps(self):
        return {RunOrder.AFTER: [B]}

class B(System):
    def deps(self):
        return {RunOrder.AFTER: [A]}
```

**Fix**: Restructure dependencies or merge systems.

---

## 📚 Quick Reference

### Component Checklist

- [ ] Pure data, no methods
- [ ] Use `@dataclass` or Pydantic
- [ ] Prefer `frozen=True` for immutability
- [ ] No Entity/World references
- [ ] Use relationships for entity connections

### System Checklist

- [ ] Single responsibility
- [ ] Minimal query
- [ ] Proper dependency declarations
- [ ] Use delta time
- [ ] No direct system-to-system calls
- [ ] Collect modifications, apply after iteration

### Query Checklist

- [ ] Use appropriate execution method
- [ ] Put cheap filters first
- [ ] Consider indexes for hot queries
- [ ] Use markers instead of filter functions

### Observer Checklist

- [ ] Simple, focused reactions
- [ ] No heavy queries
- [ ] Handle stale entities
- [ ] Guard against infinite loops
