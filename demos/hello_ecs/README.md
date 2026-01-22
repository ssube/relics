# Hello ECS - Bouncing Particles

The simplest possible Relics demo: particles bouncing in a box.

## Features Demonstrated

- **World creation** - The central manager for all ECS state
- **Component definition** - Using Pydantic dataclasses for type-safe components
- **Prefab registration** - Creating reusable entity templates
- **Entity spawning** - Instantiating entities from prefabs with overrides
- **System implementation** - Processing entities with queries
- **Tick loop** - Running the simulation with delta time

## Running

```bash
cd /path/to/relics
source .venv/bin/activate
python demos/hello_ecs/main.py
```

## Key Concepts

### Components

Components are pure data containers with no logic:

```python
@pydantic.dataclasses.dataclass
class Position(Component):
    x: float
    y: float
```

### Prefabs

Prefabs are templates for creating entities:

```python
world.register_prefab("particle", {
    Position: Position(x=0.0, y=0.0),
    Velocity: Velocity(dx=0.0, dy=0.0),
})
```

### Spawning

Create entities from prefabs with optional overrides:

```python
particle = world.spawn("particle", {
    Position: Position(x=50.0, y=50.0),
})
```

### Systems

Systems contain the logic that processes entities:

```python
class MovementSystem(System):
    def query(self):
        """Define which entities to process."""
        return self.world.query().with_all([Position, Velocity])

    def process(self, entities, components, delta):
        """Process matching entities."""
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)
            pos.x += vel.dx * delta
            pos.y += vel.dy * delta
```

### Tick Loop

The world advances time through ticks:

```python
for _ in range(10):
    world.tick(0.1)  # 100ms per tick
```

## Next Demo

Continue to [chain_reaction](../chain_reaction/) to learn about observers and events.
