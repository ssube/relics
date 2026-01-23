# Chain Reaction - Explosive Barrels

Explosive barrels that trigger chain reactions when destroyed.

## Features Demonstrated

- **@monitored decorator** - Enable change tracking on components
- **OnComponentChanged observer** - React to component value changes
- **OnEntityDestroyed observer** - React to entity removal
- **CustomEvent definition** - Create user-defined events
- **OnCustomEvent observer** - Handle custom events
- **world.emit()** - Emit custom events for propagation
- **world.observe()** - Register observers

## Running

```bash
cd /path/to/relics
source .venv/bin/activate
python demos/chain_reaction/main.py
```

## Key Concepts

### Monitored Components

Use `@monitored` to enable change tracking:

```python
@monitored
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int
```

### Custom Events

Define custom event types:

```python
@pydantic.dataclasses.dataclass
class ExplosionEvent(CustomEvent):
    origin_x: float
    origin_y: float
    radius: float
    damage: int
    source_id: str
```

### Component Change Observer

React to component changes:

```python
class HealthMonitor(OnComponentChanged):
    component_type = Health

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        if field_name == "current" and old_value > 0 and new_value <= 0:
            print(f"{entity.id} died!")
            # Trigger explosion...
```

### Custom Event Observer

Handle custom events:

```python
class ExplosionHandler(OnCustomEvent):
    event_type = ExplosionEvent

    def on_event(self, event):
        # Apply blast damage to nearby entities
        for entity in self.world.query().with_all([Health, Position]).execute_entities():
            # Check distance and apply damage...
```

### Emitting Events

Emit events from observers:

```python
self.world.emit(ExplosionEvent(
    origin_x=pos.x,
    origin_y=pos.y,
    radius=explosive.blast_radius,
    damage=explosive.blast_damage,
    source_id=str(entity.id),
))
```

### Entity Destruction Observer

Log or react to entity removal:

```python
class DestructionLogger(OnEntityDestroyed):
    prefab = "barrel"  # Only watch barrels

    def on_entity_destroyed(self, entity):
        print(f"Barrel {entity.id} removed")
```

## How It Works

1. Barrels are spawned in a cluster
2. The center barrel is damaged, triggering `OnComponentChanged`
3. When health reaches 0, an `ExplosionEvent` is emitted
4. `ExplosionHandler` applies damage to nearby barrels
5. Those barrels may die, triggering more explosions
6. The chain continues until no more barrels are in blast range

## Next Demo

Continue to [inventory_tree](../inventory_tree/) to learn about relationships and hierarchy.
