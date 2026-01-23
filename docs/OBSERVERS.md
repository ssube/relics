# Observers

> Observers react to events in the world. They enable event-driven programming patterns for UI updates, audio, spawning reactions, and more.

---

## 📋 Prerequisites

Before reading this document, you should be familiar with:
- [Getting Started](GETTING_STARTED.md) - Basic concepts and setup
- [Entities & Components](ENTITIES_COMPONENTS.md) - Entity and component patterns

---

## 👁️ What are Observers?

**Observers** are event handlers that react to changes in the world:

- Entity creation and destruction
- Component addition, removal, and changes
- Relationship creation and removal
- Custom events

```python
from relics import OnEntityCreated

class SpawnLogger(OnEntityCreated):
    prefab = "player"

    def on_entity_created(self, entity):
        print(f"Player spawned: {entity.id}")

world.observe(SpawnLogger())
```

> **Note**: Observer callbacks are **queued** and processed at the end of `tick()`, not immediately when events occur.

---

## 🎯 Observer Event Types

| Observer Class | Event | Trigger |
|----------------|-------|---------|
| `OnEntityCreated` | Entity spawned | `world.spawn()` |
| `OnEntityDestroyed` | Entity removed | `world.remove()` |
| `OnComponentAdded` | Component added | `entity.add_component()` |
| `OnComponentRemoved` | Component removed | `entity.remove_component()` |
| `OnComponentChanged` | Component changed | Field assignment on `@monitored` component |
| `OnRelationshipAdded` | Relationship created | `entity.add_relationship()` |
| `OnRelationshipRemoved` | Relationship removed | `entity.remove_relationship()` |
| `OnCustomEvent` | Custom event | `world.emit()` |

---

## 🎮 Single-Event Observers

These observers respond to one specific event type.

### OnEntityCreated

Triggered when an entity is spawned.

```python
from relics import OnEntityCreated

class AllEntitiesLogger(OnEntityCreated):
    """Logs all entity creations."""
    prefab = None  # None = all prefabs

    def on_entity_created(self, entity):
        print(f"Entity created: {entity.id}")

class PlayerSpawnHandler(OnEntityCreated):
    """Only watches player entities."""
    prefab = "player"

    def on_entity_created(self, entity):
        print(f"Player spawned at epoch {self.world.epoch}")
        # Initialize player-specific state
```

### OnEntityDestroyed

Triggered when an entity is removed.

```python
from relics import OnEntityDestroyed

class DeathLogger(OnEntityDestroyed):
    prefab = "enemy"

    def on_entity_destroyed(self, entity):
        print(f"Enemy destroyed: {entity.id}")
        # Award points, spawn loot, etc.
```

### OnComponentAdded

Triggered when a component is added to an entity.

```python
from relics import OnComponentAdded

class HealthAddedHandler(OnComponentAdded):
    component_type = Health

    def on_component_added(self, entity, component):
        print(f"{entity.id} gained health: {component.current}/{component.maximum}")
```

### OnComponentRemoved

Triggered when a component is removed from an entity.

```python
from relics import OnComponentRemoved

class ShieldRemovedHandler(OnComponentRemoved):
    component_type = Shield

    def on_component_removed(self, entity, component):
        print(f"{entity.id} lost shield of {component.amount}")
```

### OnComponentChanged

Triggered when a `@monitored` component's field changes.

```python
from relics import OnComponentChanged, monitored
from dataclasses import dataclass

@monitored
@dataclass
class Health(Component):
    current: int
    maximum: int

class HealthChangeHandler(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        if field_name == "current":
            damage = old_value - new_value
            if damage > 0:
                print(f"{entity.id} took {damage} damage!")
            elif damage < 0:
                print(f"{entity.id} healed {-damage}!")
```

### OnRelationshipAdded

Triggered when a relationship is created between entities.

```python
from relics import OnRelationshipAdded

class TeamJoinHandler(OnRelationshipAdded):
    edge_type = BelongsTo

    def on_relationship_added(self, source, edge, target):
        print(f"{source.id} joined team {target.id}")
```

### OnRelationshipRemoved

Triggered when a relationship is removed.

```python
from relics import OnRelationshipRemoved

class TeamLeaveHandler(OnRelationshipRemoved):
    edge_type = BelongsTo

    def on_relationship_removed(self, source, edge, target):
        print(f"{source.id} left team {target.id}")
```

### OnCustomEvent

Triggered when a custom event is emitted.

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
        print(f"{event.target_id} took {event.amount} damage from {event.source_id}")
```

---

## 🔄 Multi-Event Observers (Lifecycle Bundles)

These observers can respond to multiple related events with a single class.

### EntityObserver

Handles both creation and destruction of entities.

```python
from relics import EntityObserver

class PlayerLifecycleHandler(EntityObserver):
    prefab = "player"

    def on_entity_created(self, entity):
        print(f"Player {entity.id} joined the game")

    def on_entity_destroyed(self, entity):
        print(f"Player {entity.id} left the game")
```

### ComponentObserver

Handles added, changed, and removed events for a component type.

```python
from relics import ComponentObserver

class HealthObserver(ComponentObserver):
    component_type = Health

    def on_component_added(self, entity, component):
        print(f"{entity.id}: Health initialized to {component.current}")

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        print(f"{entity.id}: {field_name} changed {old_value} -> {new_value}")

    def on_component_removed(self, entity, component):
        print(f"{entity.id}: Health component removed")
```

### RelationshipObserver

Handles added and removed events for a relationship type.

```python
from relics import RelationshipObserver

class TeamMembershipObserver(RelationshipObserver):
    edge_type = BelongsTo

    def on_relationship_added(self, source, edge, target):
        print(f"{source.id} joined {target.id} as {edge.role}")

    def on_relationship_removed(self, source, edge, target):
        print(f"{source.id} left {target.id}")
```

---

## 📡 Custom Events

Define your own event types for game-specific events.

### Defining Custom Events

```python
from dataclasses import dataclass
from relics import CustomEvent

@dataclass
class DamageEvent(CustomEvent):
    source_id: str
    target_id: str
    amount: float
    damage_type: str = "physical"

@dataclass
class LevelUpEvent(CustomEvent):
    entity_id: str
    old_level: int
    new_level: int

@dataclass
class ItemPickedUpEvent(CustomEvent):
    picker_id: str
    item_id: str
```

### Emitting Events

```python
# Emit from anywhere with world access
world.emit(DamageEvent(
    source_id=str(attacker.id),
    target_id=str(target.id),
    amount=25.0,
    damage_type="fire"
))

# Emit from a system
class CombatSystem(System):
    def process(self, entities, components, delta):
        # ... combat logic ...
        self.world.emit(DamageEvent(...))
```

### Handling Events

```python
class DamageEffectHandler(OnCustomEvent):
    event_type = DamageEvent

    def on_event(self, event):
        # Play damage sound
        # Show damage numbers
        # Apply visual effects
        print(f"Damage effect: {event.amount} {event.damage_type}")

world.observe(DamageEffectHandler())
```

---

## 🔧 The @monitored Decorator

The `@monitored` decorator enables change tracking on components.

### Basic Usage

```python
from relics import monitored, is_monitored
from dataclasses import dataclass

@monitored
@dataclass
class Health(Component):
    current: int
    maximum: int

# Check if a component is monitored
print(is_monitored(Health))  # True
```

### How It Works

1. The decorator adds change tracking to `__setattr__`
2. When a field changes, it notifies the world
3. `OnComponentChanged` observers are queued

```python
# This triggers OnComponentChanged observers
health = entity.get_component(Health)
health.current = 50  # Change detected!
```

### Important Notes

- Only works with **mutable** components (not `frozen=True`)
- Changes are tracked **per-field**
- Multiple changes in one tick may trigger multiple events

```python
@monitored
@dataclass
class Position(Component):  # Note: not frozen
    x: float
    y: float

pos = entity.get_component(Position)
pos.x = 10  # One change event
pos.y = 20  # Another change event
```

---

## ⏰ Observer Execution Model

### Event Queuing

Events are **queued** when they occur and **processed** at the end of `tick()`:

```
player = world.spawn("player")    # OnEntityCreated queued
player.add_component(Health(...)) # OnComponentAdded queued
world.tick(delta)                 # Events processed here
```

### Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│                     world.tick(delta)                       │
├─────────────────────────────────────────────────────────────┤
│  1. Increment epoch                                         │
│  2. Run systems (in dependency order)                       │
│     - Systems may queue more events                         │
│  3. Process observer queue:                                 │
│     - Events processed in FIFO order                        │
│     - Observers may queue more events                       │
│     - Queue is drained completely                           │
└─────────────────────────────────────────────────────────────┘
```

### Cascading Events

Observers can trigger more events:

```python
class DeathHandler(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        if field_name == "current" and new_value <= 0:
            # This will queue OnEntityDestroyed events
            self.world.remove(entity)
```

---

## 💡 Common Patterns

### UI Updates

```python
class HealthBarUpdater(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        # Update health bar UI on any health field change
        ui.update_health_bar(entity.id, component.current, component.maximum)
```

### Audio System

```python
class DamageSoundPlayer(OnCustomEvent):
    event_type = DamageEvent

    def on_event(self, event):
        if event.damage_type == "fire":
            audio.play("fire_damage.wav")
        else:
            audio.play("physical_damage.wav")
```

### Spawning Reactions

```python
class LootDropper(OnEntityDestroyed):
    prefab = "enemy"

    def on_entity_destroyed(self, entity):
        pos = entity.get_component(Position)
        loot = self.world.spawn("loot", overrides={
            Position: Position(x=pos.x, y=pos.y)
        })
```

### Achievement System

```python
class AchievementTracker(OnCustomEvent):
    event_type = EnemyKilledEvent

    def __init__(self):
        super().__init__()
        self.kill_count = 0

    def on_event(self, event):
        self.kill_count += 1
        if self.kill_count == 100:
            self.world.emit(AchievementUnlockedEvent(name="Centurion"))
```

### State Machine Transitions

```python
class StateMachineObserver(ComponentObserver):
    component_type = AIState

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        if field_name != "state":
            return
        # Log state transitions
        print(f"{entity.id}: {old_value} -> {new_value}")

        # Trigger entry actions
        if new_value == "attacking":
            entity.add_component(CombatMode())
        elif old_value == "attacking":
            entity.remove_component(CombatMode)
```

---

## ⚠️ Common Issues & Troubleshooting

### 1. Observer Not Firing

**Problem**: Observer isn't being called.

**Checklist**:
- Did you register the observer with `world.observe()`?
- Is the `component_type`, `prefab`, or `edge_type` correct?
- For `OnComponentChanged`, is the component `@monitored`?
- Did you call `world.tick()` to process the queue?

### 2. Component Not Monitored

```python
# ❌ Order matters - @monitored must be first
@dataclass
@monitored  # Wrong order!
class Health(Component):
    current: int

# ✅ Correct order
@monitored
@dataclass
class Health(Component):
    current: int
```

### 3. Infinite Event Loop

```python
# ❌ This creates an infinite loop
class BadObserver(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        # This triggers another change event!
        component.current = component.current + 1
```

**Solution**: Use guards or different components:

```python
class SafeObserver(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        if not entity.has_component(HealingProcessed):
            entity.add_component(HealingProcessed())
            # Safe to modify now
```

### 4. Stale Entity References

```python
class BadHandler(OnEntityDestroyed):
    def on_entity_destroyed(self, entity):
        # Entity is about to be removed - be careful!
        pos = entity.get_component(Position)  # Still works
        # But don't store the entity handle for later use
```

### 5. Missing prefab/component_type

```python
# ❌ Forgot to set component_type
class BadObserver(OnComponentAdded):
    def on_component_added(self, entity, component):
        pass  # This will never be called!

# ✅ Set the class variable
class GoodObserver(OnComponentAdded):
    component_type = Health

    def on_component_added(self, entity, component):
        pass
```

---

## 📚 API Summary

### Single-Event Observers

| Class | Attribute | Callback |
|-------|-----------|----------|
| `OnEntityCreated` | `prefab` | `on_entity_created(entity)` |
| `OnEntityDestroyed` | `prefab` | `on_entity_destroyed(entity)` |
| `OnComponentAdded` | `component_type` | `on_component_added(entity, component)` |
| `OnComponentRemoved` | `component_type` | `on_component_removed(entity, component)` |
| `OnComponentChanged` | `component_type` | `on_component_changed(entity, component, field_name, old_value, new_value)` |
| `OnRelationshipAdded` | `edge_type` | `on_relationship_added(source, edge, target)` |
| `OnRelationshipRemoved` | `edge_type` | `on_relationship_removed(source, edge, target)` |
| `OnCustomEvent` | `event_type` | `on_event(event)` |

### Multi-Event Observers

| Class | Attribute | Callbacks |
|-------|-----------|-----------|
| `EntityObserver` | `prefab` | `on_entity_created`, `on_entity_destroyed` |
| `ComponentObserver` | `component_type` | `on_component_added`, `on_component_changed`, `on_component_removed` |
| `RelationshipObserver` | `edge_type` | `on_relationship_added`, `on_relationship_removed` |

### Monitoring

| Item | Description |
|------|-------------|
| `@monitored` | Decorator to enable change tracking |
| `is_monitored(obj)` | Check if object/class is monitored |

### World Methods

| Method | Description |
|--------|-------------|
| `world.observe(observer)` | Register an observer |
| `world.emit(event)` | Emit a custom event |
