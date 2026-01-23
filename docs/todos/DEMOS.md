# Planned Demos

Additional demos to help users learn the Relics ECS framework progressively.

## Current Demos

| Demo | Focus | Complexity |
|------|-------|------------|
| `character_sheet` | Procedural prefabs, JSON loading, conditionals | Medium |
| `pygame` | Visual simulation, AI systems, movement, collision | High |

## Planned Demos

### 1. `hello_ecs` - The Minimal Introduction

**Purpose:** Absolute simplest possible demo for newcomers. No addons, no JSON, just pure ECS in ~60 lines.

**Features Demonstrated:**
- World creation
- Component definition with Pydantic
- Prefab registration
- Entity spawning
- System implementation
- The tick loop

**Scenario:** Particles with position and velocity bouncing in a box. Text output showing positions each tick.

**Target Length:** ~60 lines

**Dependencies:** Core library only

**Implementation:**

```python
"""
hello_ecs - Minimal ECS introduction

Run: python demos/hello_ecs/main.py
"""
import pydantic
from relics import World, Component, System, QueryBuilder

# Components are pure data containers
@pydantic.dataclasses.dataclass
class Position(Component):
    x: float
    y: float

@pydantic.dataclasses.dataclass
class Velocity(Component):
    dx: float
    dy: float

# Systems contain logic and process entities
class MovementSystem(System):
    def query(self) -> QueryBuilder:
        return self.q.with_all([Position, Velocity])

    def process(self, entities, components, delta):
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            # Update position
            pos.x += vel.dx * delta
            pos.y += vel.dy * delta

            # Bounce off walls (0-100 box)
            if pos.x <= 0 or pos.x >= 100:
                vel.dx *= -1
                pos.x = max(0, min(100, pos.x))
            if pos.y <= 0 or pos.y >= 100:
                vel.dy *= -1
                pos.y = max(0, min(100, pos.y))

def main():
    # Create world
    world = World()

    # Register prefab (entity template)
    world.register_prefab("particle", {
        Position: Position(x=50, y=50),
        Velocity: Velocity(dx=10, dy=10),
    })

    # Register system
    world.register_system(MovementSystem())

    # Spawn particles with different velocities
    import random
    random.seed(42)

    for i in range(5):
        world.spawn("particle", {
            Position: Position(x=random.uniform(10, 90), y=random.uniform(10, 90)),
            Velocity: Velocity(dx=random.uniform(-20, 20), dy=random.uniform(-20, 20)),
        })

    # Run simulation
    print("Particle Simulation")
    print("=" * 40)

    for tick in range(10):
        world.tick(0.1)  # 100ms per tick

        print(f"\nTick {tick + 1}:")
        for entity in world.query().with_all([Position]).execute_entities():
            pos = entity.get_component(Position)
            print(f"  {entity.id}: ({pos.x:.1f}, {pos.y:.1f})")

if __name__ == "__main__":
    main()
```

**Expected Output:**

```
Particle Simulation
========================================

Tick 1:
  particle_1: (52.3, 48.1)
  particle_2: (31.7, 65.2)
  particle_3: (78.4, 22.9)
  particle_4: (45.1, 89.3)
  particle_5: (12.8, 33.6)

Tick 2:
  particle_1: (54.6, 46.2)
  ...
```

**File Structure:**

```
demos/hello_ecs/
├── main.py      # Complete demo (~60 lines)
└── README.md    # Brief explanation
```

---

### 2. `spatial_aoe` - Spatial Index Showcase

**Purpose:** Demonstrate spatial queries without visual complexity. Text-based tactical combat.

**Features Demonstrated:**
- `Position2D` component
- `create_spatial_index_2d()` factory
- `QuadTreeBounds` configuration
- Circle queries (area of effect)
- Rectangle queries (zone control)
- Nearest neighbor queries (targeting)
- Index integration with queries

**Scenario:** Grid-based battlefield where units cast AoE spells, detect enemies in range, and find nearest targets.

**Target Length:** ~150 lines

**Dependencies:** `relics.addons.spatial`

**Implementation:**

```python
"""
spatial_aoe - Spatial index demonstration

Run: python demos/spatial_aoe/main.py
"""
import pydantic
from relics import World, Component, monitored
from relics.addons.spatial import (
    Position2D, create_spatial_index_2d, distance_2d
)

@pydantic.dataclasses.dataclass
class Unit(Component):
    name: str
    team: str  # "player" or "enemy"

@monitored
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int

def print_battlefield(world, spatial_index):
    """Print ASCII representation of the battlefield."""
    print("\nBattlefield (20x20):")
    print("+" + "-" * 20 + "+")

    grid = [["." for _ in range(20)] for _ in range(20)]

    for entity in spatial_index:
        pos = entity.get_component(Position2D)
        unit = entity.get_component(Unit)
        x, y = int(pos.x), int(pos.y)
        if 0 <= x < 20 and 0 <= y < 20:
            grid[y][x] = "P" if unit.team == "player" else "E"

    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * 20 + "+")

def cast_fireball(world, spatial_index, caster, target_x, target_y, radius, damage):
    """Cast an AoE fireball at target location."""
    caster_unit = caster.get_component(Unit)
    print(f"\n{caster_unit.name} casts Fireball at ({target_x}, {target_y}) radius {radius}!")

    hits = 0
    for entity in spatial_index.query_circle(target_x, target_y, radius):
        if entity.id == caster.id:
            continue  # Don't hit self

        unit = entity.get_component(Unit)
        health = entity.get_component(Health)
        pos = entity.get_component(Position2D)

        dist = distance_2d(target_x, target_y, pos.x, pos.y)
        health.current -= damage

        print(f"  Hit: {unit.name} at ({pos.x:.1f}, {pos.y:.1f}) - {damage} damage (dist: {dist:.1f})")
        hits += 1

        if health.current <= 0:
            print(f"    -> {unit.name} defeated!")

    if hits == 0:
        print("  No targets in range!")

    return hits

def find_nearest_enemy(spatial_index, unit_entity):
    """Find the nearest enemy to a unit."""
    pos = unit_entity.get_component(Position2D)
    unit = unit_entity.get_component(Unit)

    nearest = spatial_index.query_nearest(pos.x, pos.y, count=10)

    for entity, distance in nearest:
        target_unit = entity.get_component(Unit)
        if target_unit.team != unit.team:
            return entity, distance

    return None, None

def detect_in_zone(spatial_index, min_x, min_y, max_x, max_y, team_filter=None):
    """Detect all units in a rectangular zone."""
    print(f"\nScanning zone ({min_x}, {min_y}) to ({max_x}, {max_y}):")

    units = []
    for entity in spatial_index.query_rectangle(min_x, min_y, max_x, max_y):
        unit = entity.get_component(Unit)
        pos = entity.get_component(Position2D)

        if team_filter and unit.team != team_filter:
            continue

        units.append((entity, unit, pos))
        print(f"  Found: {unit.name} ({unit.team}) at ({pos.x:.1f}, {pos.y:.1f})")

    if not units:
        print("  Zone is clear!")

    return units

def main():
    # Setup world
    world = World()

    # Register prefabs
    world.register_prefab("player_unit", {
        Position2D: Position2D(x=0, y=0),
        Unit: Unit(name="Unit", team="player"),
        Health: Health(current=100, maximum=100),
    })

    world.register_prefab("enemy_unit", {
        Position2D: Position2D(x=0, y=0),
        Unit: Unit(name="Enemy", team="enemy"),
        Health: Health(current=50, maximum=50),
    })

    # Create spatial index
    bounds = (0, 0, 20, 20)
    spatial_index = create_spatial_index_2d(
        world,
        materialized=True,
        auto_register_observer=True,
        bounds=bounds,
    )

    # Spawn player units
    mage = world.spawn("player_unit", {
        Position2D: Position2D(x=5, y=10),
        Unit: Unit(name="Mage", team="player"),
    })

    warrior = world.spawn("player_unit", {
        Position2D: Position2D(x=3, y=10),
        Unit: Unit(name="Warrior", team="player"),
    })

    # Spawn enemy units
    for i, (x, y, name) in enumerate([
        (12, 9, "Goblin Scout"),
        (14, 11, "Goblin Archer"),
        (15, 10, "Goblin Warrior"),
        (18, 5, "Orc Brute"),
        (17, 15, "Orc Shaman"),
    ]):
        world.spawn("enemy_unit", {
            Position2D: Position2D(x=x, y=y),
            Unit: Unit(name=name, team="enemy"),
        })

    world.tick(0)

    # Demo: Print battlefield
    print("=" * 50)
    print("SPATIAL QUERIES DEMONSTRATION")
    print("=" * 50)
    print_battlefield(world, spatial_index)

    # Demo: AoE attack
    print("\n" + "=" * 50)
    print("1. AREA OF EFFECT (Circle Query)")
    print("=" * 50)
    cast_fireball(world, spatial_index, mage, 14, 10, radius=3, damage=30)

    # Demo: Zone detection
    print("\n" + "=" * 50)
    print("2. ZONE DETECTION (Rectangle Query)")
    print("=" * 50)
    detect_in_zone(spatial_index, 10, 8, 16, 12, team_filter="enemy")

    # Demo: Nearest enemy targeting
    print("\n" + "=" * 50)
    print("3. NEAREST ENEMY (K-Nearest Query)")
    print("=" * 50)

    warrior_unit = warrior.get_component(Unit)
    warrior_pos = warrior.get_component(Position2D)
    print(f"\n{warrior_unit.name} at ({warrior_pos.x}, {warrior_pos.y}) searches for nearest enemy:")

    target, distance = find_nearest_enemy(spatial_index, warrior)
    if target:
        target_unit = target.get_component(Unit)
        target_pos = target.get_component(Position2D)
        print(f"  Target acquired: {target_unit.name} at ({target_pos.x}, {target_pos.y})")
        print(f"  Distance: {distance:.1f} units")
    else:
        print("  No enemies found!")

    # Demo: All enemies sorted by distance
    print("\n" + "=" * 50)
    print("4. ALL ENEMIES BY DISTANCE")
    print("=" * 50)
    print(f"\nEnemies sorted by distance from {warrior_unit.name}:")

    for entity, distance in spatial_index.query_nearest(warrior_pos.x, warrior_pos.y, count=10):
        unit = entity.get_component(Unit)
        if unit.team == "enemy":
            pos = entity.get_component(Position2D)
            health = entity.get_component(Health)
            print(f"  {distance:5.1f} units - {unit.name} at ({pos.x:.0f}, {pos.y:.0f}) HP: {health.current}/{health.maximum}")

if __name__ == "__main__":
    main()
```

**Expected Output:**

```
==================================================
SPATIAL QUERIES DEMONSTRATION
==================================================

Battlefield (20x20):
+--------------------+
|....................|
|....................|
|....................|
|....................|
|....................|
|..................E.|
|....................|
|....................|
|....................|
|...P.......E..E.....|
|...PP..........E....|
|..............E.....|
|....................|
|....................|
|....................|
|.................E..|
|....................|
|....................|
|....................|
|....................|
+--------------------+

==================================================
1. AREA OF EFFECT (Circle Query)
==================================================

Mage casts Fireball at (14, 10) radius 3!
  Hit: Goblin Scout at (12.0, 9.0) - 30 damage (dist: 2.2)
  Hit: Goblin Archer at (14.0, 11.0) - 30 damage (dist: 1.0)
  Hit: Goblin Warrior at (15.0, 10.0) - 30 damage (dist: 1.0)

==================================================
2. ZONE DETECTION (Rectangle Query)
==================================================

Scanning zone (10, 8) to (16, 12):
  Found: Goblin Scout (enemy) at (12.0, 9.0)
  Found: Goblin Archer (enemy) at (14.0, 11.0)
  Found: Goblin Warrior (enemy) at (15.0, 10.0)

...
```

**File Structure:**

```
demos/spatial_aoe/
├── main.py      # Complete demo (~150 lines)
└── README.md    # Explanation of spatial queries
```

---

### 3. `chain_reaction` - Observers and Events

**Purpose:** Demonstrate the reactive observer system with cascading effects.

**Features Demonstrated:**
- `@monitored` decorator for change tracking
- `OnComponentChanged` observer
- `OnEntityDestroyed` observer
- `CustomEvent` definition
- `OnCustomEvent` observer
- Event propagation with `world.emit()`
- Observer registration with `world.observe()`

**Scenario:** Explosive barrels that trigger chain reactions when destroyed.

**Target Length:** ~200 lines

**Dependencies:** Core library only (optionally spatial for blast radius)

**Implementation:**

```python
"""
chain_reaction - Observer and event demonstration

Run: python demos/chain_reaction/main.py
"""
import pydantic
from dataclasses import field
from typing import List, Tuple
from relics import (
    World, Component, Entity, EntityId, CustomEvent,
    OnComponentChanged, OnEntityDestroyed, OnCustomEvent,
    monitored,
)

# Components
@pydantic.dataclasses.dataclass
class Position(Component):
    x: float
    y: float

@monitored
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int

@pydantic.dataclasses.dataclass
class Explosive(Component):
    blast_radius: float
    blast_damage: int

@pydantic.dataclasses.dataclass
class Barrel(Component):
    """Marker component for barrels."""
    pass

# Custom Events
@pydantic.dataclasses.dataclass
class ExplosionEvent(CustomEvent):
    """Emitted when something explodes."""
    origin: Tuple[float, float]
    radius: float
    damage: int
    source_id: str

@pydantic.dataclasses.dataclass
class ChainReactionComplete(CustomEvent):
    """Emitted when chain reaction finishes."""
    total_explosions: int
    entities_destroyed: List[str]

# Observers
class HealthMonitor(OnComponentChanged):
    """Monitors health changes and triggers explosions at zero health."""
    component_type = Health

    def __init__(self):
        self.pending_explosions: List[EntityId] = []

    def on_component_changed(self, entity: Entity, component: Health, field_name: str, old_value: Any, new_value: Any):
        if field_name != "current":
            return
        print(f"  [Health] {entity.id}: {old_value} -> {new_value}")

        # Low health warning
        if new_value < component.maximum * 0.3 and old_value >= component.maximum * 0.3:
            print(f"    WARNING: {entity.id} health critical!")

        # Track entities that should explode
        if new_value <= 0 and old_value > 0:
            if entity.has_component(Explosive):
                self.pending_explosions.append(entity.id)

class ExplosionHandler(OnCustomEvent):
    """Handles explosion events and applies damage to nearby entities."""
    event_type = ExplosionEvent

    def __init__(self, get_entities_in_range):
        self.get_entities_in_range = get_entities_in_range
        self.explosion_count = 0
        self.destroyed_entities: List[str] = []

    def on_event(self, event: ExplosionEvent):
        self.explosion_count += 1
        print(f"\n  [EXPLOSION #{self.explosion_count}] at ({event.origin[0]:.1f}, {event.origin[1]:.1f})")
        print(f"    Radius: {event.radius}, Damage: {event.damage}")

        # Find entities in blast radius
        nearby = self.get_entities_in_range(event.origin, event.radius)

        for entity in nearby:
            if str(entity.id) == event.source_id:
                continue  # Don't damage self

            if entity.has_component(Health):
                health = entity.get_component(Health)
                pos = entity.get_component(Position)

                print(f"    -> Blast hits {entity.id} at ({pos.x:.1f}, {pos.y:.1f})")
                health.current -= event.damage

class DestructionLogger(OnEntityDestroyed):
    """Logs entity destruction."""
    prefab = None  # All prefabs

    def __init__(self, explosion_handler: ExplosionHandler):
        self.explosion_handler = explosion_handler

    def on_entity_destroyed(self, entity: Entity):
        print(f"  [Destroyed] {entity.id}")
        self.explosion_handler.destroyed_entities.append(str(entity.id))

def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

def main():
    world = World()

    # Register prefab
    world.register_prefab("barrel", {
        Position: Position(x=0, y=0),
        Health: Health(current=100, maximum=100),
        Explosive: Explosive(blast_radius=3.0, blast_damage=60),
        Barrel: Barrel(),
    })

    # Helper to find entities in range (simple brute force)
    def get_entities_in_range(origin: Tuple[float, float], radius: float) -> List[Entity]:
        result = []
        for entity in world.query().with_all([Position, Health]).execute_entities():
            pos = entity.get_component(Position)
            if distance(origin, (pos.x, pos.y)) <= radius:
                result.append(entity)
        return result

    # Create and register observers
    health_monitor = HealthMonitor()
    explosion_handler = ExplosionHandler(get_entities_in_range)
    destruction_logger = DestructionLogger(explosion_handler)

    world.observe(health_monitor)
    world.observe(explosion_handler)
    world.observe(destruction_logger)

    # Spawn barrels in a cluster
    barrel_positions = [
        (10, 10),  # Initial target
        (12, 11),  # Close to first
        (8, 9),    # Close to first
        (14, 12),  # Chain from second
        (6, 8),    # Chain from third
        (5, 6),    # Chain from fifth
        (20, 20),  # Far away - should not be hit
    ]

    barrels = []
    for i, (x, y) in enumerate(barrel_positions):
        barrel = world.spawn("barrel", {
            Position: Position(x=x, y=y),
        })
        barrels.append(barrel)

    world.tick(0)

    # Print initial state
    print("=" * 60)
    print("CHAIN REACTION DEMONSTRATION")
    print("=" * 60)
    print("\nInitial barrel positions:")
    for barrel in barrels:
        pos = barrel.get_component(Position)
        health = barrel.get_component(Health)
        print(f"  {barrel.id}: ({pos.x}, {pos.y}) HP: {health.current}")

    # Trigger the chain reaction
    print("\n" + "=" * 60)
    print("Shooting barrel at (10, 10) with 150 damage...")
    print("=" * 60)

    target = barrels[0]
    health = target.get_component(Health)
    health.current -= 150  # Overkill to ensure destruction

    # Process chain reaction
    max_iterations = 20
    iteration = 0

    while health_monitor.pending_explosions and iteration < max_iterations:
        iteration += 1
        print(f"\n--- Processing explosions (iteration {iteration}) ---")

        # Get pending explosions and clear the list
        to_explode = health_monitor.pending_explosions[:]
        health_monitor.pending_explosions.clear()

        for entity_id in to_explode:
            if not world.has_entity(entity_id):
                continue

            entity = world.get_entity(entity_id)
            pos = entity.get_component(Position)
            explosive = entity.get_component(Explosive)

            # Emit explosion event
            world.emit(ExplosionEvent(
                origin=(pos.x, pos.y),
                radius=explosive.blast_radius,
                damage=explosive.blast_damage,
                source_id=str(entity_id),
            ))

            # Remove the exploded entity
            world.remove(entity)

        # Process all queued events
        world.tick(0)

    # Final summary
    print("\n" + "=" * 60)
    print("CHAIN REACTION COMPLETE")
    print("=" * 60)
    print(f"\nTotal explosions: {explosion_handler.explosion_count}")
    print(f"Entities destroyed: {len(explosion_handler.destroyed_entities)}")
    for entity_id in explosion_handler.destroyed_entities:
        print(f"  - {entity_id}")

    print(f"\nSurviving barrels:")
    survivors = list(world.query().with_all([Barrel]).execute_entities())
    if survivors:
        for barrel in survivors:
            pos = barrel.get_component(Position)
            health = barrel.get_component(Health)
            print(f"  {barrel.id}: ({pos.x}, {pos.y}) HP: {health.current}")
    else:
        print("  None!")

if __name__ == "__main__":
    main()
```

**Expected Output:**

```
============================================================
CHAIN REACTION DEMONSTRATION
============================================================

Initial barrel positions:
  barrel_1: (10, 10) HP: 100
  barrel_2: (12, 11) HP: 100
  barrel_3: (8, 9) HP: 100
  barrel_4: (14, 12) HP: 100
  barrel_5: (6, 8) HP: 100
  barrel_6: (5, 6) HP: 100
  barrel_7: (20, 20) HP: 100

============================================================
Shooting barrel at (10, 10) with 150 damage...
============================================================
  [Health] barrel_1: 100 -> -50

--- Processing explosions (iteration 1) ---

  [EXPLOSION #1] at (10.0, 10.0)
    Radius: 3.0, Damage: 60
    -> Blast hits barrel_2 at (12.0, 11.0)
  [Health] barrel_2: 100 -> 40
    -> Blast hits barrel_3 at (8.0, 9.0)
  [Health] barrel_3: 100 -> 40
    WARNING: barrel_3 health critical!
  [Destroyed] barrel_1

--- Processing explosions (iteration 2) ---
...

============================================================
CHAIN REACTION COMPLETE
============================================================

Total explosions: 5
Entities destroyed: 5
  - barrel_1
  - barrel_2
  - barrel_3
  - barrel_5
  - barrel_6

Surviving barrels:
  barrel_4: (14, 12) HP: 40
  barrel_7: (20, 20) HP: 100
```

**File Structure:**

```
demos/chain_reaction/
├── main.py      # Complete demo (~200 lines)
└── README.md    # Explanation of observer patterns
```

---

### 4. `inventory_tree` - Relationships and Hierarchy

**Purpose:** Demonstrate the graph/relationship system with entity hierarchies.

**Features Demonstrated:**
- Custom `Edge` types
- `add_relationship()` / `remove_relationship()`
- `get_relationships()` / `get_incoming_relationships()`
- `has_relationship()` checks
- Hierarchy traversal
- Cascade deletion patterns
- Query filtering by relationship

**Scenario:** A character with equipment slots and a backpack containing nested containers.

**Target Length:** ~250 lines

**Dependencies:** Core library only

**Implementation:**

```python
"""
inventory_tree - Relationship and hierarchy demonstration

Run: python demos/inventory_tree/main.py
"""
import pydantic
from typing import Optional, Iterator, List
from relics import World, Component, Entity, EntityId, Edge

# Edge types for different relationship kinds
@pydantic.dataclasses.dataclass
class Equipped(Edge):
    """Item equipped in a slot."""
    slot: str

@pydantic.dataclasses.dataclass
class Contains(Edge):
    """Container holds an item."""
    pass

# Components
@pydantic.dataclasses.dataclass
class Item(Component):
    name: str
    weight: float = 1.0

@pydantic.dataclasses.dataclass
class Stackable(Component):
    count: int
    max_stack: int = 99

@pydantic.dataclasses.dataclass
class Container(Component):
    capacity: int
    name: str = "Container"

@pydantic.dataclasses.dataclass
class Character(Component):
    name: str

# Utility functions for hierarchy traversal
def get_children(entity: Entity, edge_type: type = None) -> Iterator[Entity]:
    """Get all child entities."""
    edge_types = [edge_type] if edge_type else [Equipped, Contains]

    for et in edge_types:
        for edge, child_id in entity.get_relationships(et):
            yield entity._world.get_entity(child_id)

def get_parent(entity: Entity) -> Optional[Entity]:
    """Get parent entity if any."""
    for edge_type in [Equipped, Contains]:
        incoming = entity.get_incoming_relationships(edge_type)
        if incoming:
            parent_id, edge = incoming[0]
            return entity._world.get_entity(parent_id)
    return None

def get_slot(entity: Entity) -> Optional[str]:
    """Get the equipment slot this entity is in."""
    incoming = entity.get_incoming_relationships(Equipped)
    if incoming:
        parent_id, edge = incoming[0]
        return edge.slot
    return None

def get_all_descendants(entity: Entity) -> Iterator[Entity]:
    """Recursively get all descendants."""
    for child in get_children(entity):
        yield child
        yield from get_all_descendants(child)

def destroy_with_children(world: World, entity: Entity) -> int:
    """Destroy entity and all descendants. Returns count destroyed."""
    count = 0
    for descendant in list(get_all_descendants(entity)):
        world.remove(descendant)
        count += 1
    world.remove(entity)
    return count + 1

def print_inventory_tree(entity: Entity, indent: int = 0):
    """Print entity hierarchy as a tree."""
    prefix = "  " * indent

    if entity.has_component(Character):
        char = entity.get_component(Character)
        print(f"{prefix}Character: {char.name}")
    elif entity.has_component(Item):
        item = entity.get_component(Item)
        slot = get_slot(entity)
        slot_str = f"[{slot}] " if slot else ""

        stack_str = ""
        if entity.has_component(Stackable):
            stack = entity.get_component(Stackable)
            stack_str = f" (x{stack.count})"

        container_str = ""
        if entity.has_component(Container):
            container = entity.get_component(Container)
            children = list(get_children(entity, Contains))
            container_str = f" [{len(children)}/{container.capacity}]"

        print(f"{prefix}├── {slot_str}{item.name}{stack_str}{container_str}")

    # Print children
    for child in get_children(entity):
        print_inventory_tree(child, indent + 1)

def main():
    world = World()

    # Register edge types
    world.register_edge_type(Equipped)
    world.register_edge_type(Contains)

    # Register prefabs
    world.register_prefab("character", {
        Character: Character(name="Hero"),
    })

    world.register_prefab("item", {
        Item: Item(name="Item", weight=1.0),
    })

    world.register_prefab("container", {
        Item: Item(name="Container", weight=0.5),
        Container: Container(capacity=10),
    })

    world.register_prefab("stackable", {
        Item: Item(name="Stackable", weight=0.1),
        Stackable: Stackable(count=1),
    })

    # Create character
    hero = world.spawn("character", {
        Character: Character(name="Aldric the Bold"),
    })

    # Create and equip items
    sword = world.spawn("item", {
        Item: Item(name="Iron Sword", weight=3.0),
    })
    hero.add_relationship(Equipped(slot="main_hand"), sword.id)

    shield = world.spawn("item", {
        Item: Item(name="Wooden Shield", weight=4.0),
    })
    hero.add_relationship(Equipped(slot="off_hand"), shield.id)

    armor = world.spawn("item", {
        Item: Item(name="Leather Armor", weight=8.0),
    })
    hero.add_relationship(Equipped(slot="body"), armor.id)

    # Create backpack (container)
    backpack = world.spawn("container", {
        Item: Item(name="Backpack", weight=1.0),
        Container: Container(capacity=10, name="Backpack"),
    })
    hero.add_relationship(Equipped(slot="back"), backpack.id)

    # Add items to backpack
    potions = world.spawn("stackable", {
        Item: Item(name="Health Potion", weight=0.3),
        Stackable: Stackable(count=3, max_stack=10),
    })
    backpack.add_relationship(Contains(), potions.id)

    gold = world.spawn("stackable", {
        Item: Item(name="Gold Coins", weight=0.01),
        Stackable: Stackable(count=50, max_stack=1000),
    })
    backpack.add_relationship(Contains(), gold.id)

    # Create nested container (pouch inside backpack)
    pouch = world.spawn("container", {
        Item: Item(name="Small Pouch", weight=0.2),
        Container: Container(capacity=5, name="Pouch"),
    })
    backpack.add_relationship(Contains(), pouch.id)

    # Add items to pouch
    lockpicks = world.spawn("stackable", {
        Item: Item(name="Lockpick", weight=0.05),
        Stackable: Stackable(count=5, max_stack=20),
    })
    pouch.add_relationship(Contains(), lockpicks.id)

    gem = world.spawn("item", {
        Item: Item(name="Ruby Gemstone", weight=0.1),
    })
    pouch.add_relationship(Contains(), gem.id)

    world.tick(0)

    # Demo: Print inventory tree
    print("=" * 50)
    print("INVENTORY TREE DEMONSTRATION")
    print("=" * 50)
    print("\nCurrent inventory:")
    print_inventory_tree(hero)

    # Demo: Calculate total weight
    print("\n" + "=" * 50)
    print("WEIGHT CALCULATION")
    print("=" * 50)

    total_weight = 0.0
    for entity in get_all_descendants(hero):
        if entity.has_component(Item):
            item = entity.get_component(Item)
            count = 1
            if entity.has_component(Stackable):
                count = entity.get_component(Stackable).count
            weight = item.weight * count
            total_weight += weight
            print(f"  {item.name}: {weight:.2f} lbs")

    print(f"\nTotal carry weight: {total_weight:.2f} lbs")

    # Demo: Find item by name
    print("\n" + "=" * 50)
    print("ITEM SEARCH")
    print("=" * 50)

    search_name = "Ruby Gemstone"
    print(f"\nSearching for '{search_name}'...")

    for entity in get_all_descendants(hero):
        if entity.has_component(Item):
            item = entity.get_component(Item)
            if item.name == search_name:
                parent = get_parent(entity)
                parent_name = "unknown"
                if parent and parent.has_component(Item):
                    parent_name = parent.get_component(Item).name
                elif parent and parent.has_component(Character):
                    parent_name = parent.get_component(Character).name

                print(f"  Found in: {parent_name}")

    # Demo: Unequip item
    print("\n" + "=" * 50)
    print("UNEQUIP ITEM")
    print("=" * 50)

    print("\nUnequipping shield and moving to backpack...")
    hero.remove_relationship(Equipped, shield.id)
    backpack.add_relationship(Contains(), shield.id)

    print("\nUpdated inventory:")
    print_inventory_tree(hero)

    # Demo: Drop backpack (cascade delete)
    print("\n" + "=" * 50)
    print("DROP BACKPACK (CASCADE DELETE)")
    print("=" * 50)

    print("\nDropping backpack and all contents...")
    items_before = len(list(world.query().with_all([Item]).execute_entities()))

    # First, unequip the backpack
    hero.remove_relationship(Equipped, backpack.id)

    # Then destroy it with all children
    destroyed = destroy_with_children(world, backpack)
    print(f"  Destroyed {destroyed} entities")

    items_after = len(list(world.query().with_all([Item]).execute_entities()))
    print(f"  Items before: {items_before}, Items after: {items_after}")

    world.tick(0)

    print("\nFinal inventory:")
    print_inventory_tree(hero)

    # Demo: Query by relationship
    print("\n" + "=" * 50)
    print("QUERY EQUIPPED ITEMS")
    print("=" * 50)

    print("\nItems currently equipped:")
    for edge, item_id in hero.get_relationships(Equipped):
        item_entity = world.get_entity(item_id)
        item = item_entity.get_component(Item)
        print(f"  [{edge.slot}] {item.name}")

if __name__ == "__main__":
    main()
```

**Expected Output:**

```
==================================================
INVENTORY TREE DEMONSTRATION
==================================================

Current inventory:
Character: Aldric the Bold
  ├── [main_hand] Iron Sword
  ├── [off_hand] Wooden Shield
  ├── [body] Leather Armor
  ├── [back] Backpack [3/10]
    ├── Health Potion (x3)
    ├── Gold Coins (x50)
    ├── Small Pouch [2/5]
      ├── Lockpick (x5)
      ├── Ruby Gemstone

==================================================
WEIGHT CALCULATION
==================================================
  Iron Sword: 3.00 lbs
  Wooden Shield: 4.00 lbs
  Leather Armor: 8.00 lbs
  Backpack: 1.00 lbs
  Health Potion: 0.90 lbs
  Gold Coins: 0.50 lbs
  Small Pouch: 0.20 lbs
  Lockpick: 0.25 lbs
  Ruby Gemstone: 0.10 lbs

Total carry weight: 17.95 lbs

==================================================
ITEM SEARCH
==================================================

Searching for 'Ruby Gemstone'...
  Found in: Small Pouch

==================================================
UNEQUIP ITEM
==================================================

Unequipping shield and moving to backpack...

Updated inventory:
Character: Aldric the Bold
  ├── [main_hand] Iron Sword
  ├── [body] Leather Armor
  ├── [back] Backpack [4/10]
    ├── Health Potion (x3)
    ├── Gold Coins (x50)
    ├── Small Pouch [2/5]
      ├── Lockpick (x5)
      ├── Ruby Gemstone
    ├── Wooden Shield

==================================================
DROP BACKPACK (CASCADE DELETE)
==================================================

Dropping backpack and all contents...
  Destroyed 6 entities
  Items before: 9, Items after: 3

Final inventory:
Character: Aldric the Bold
  ├── [main_hand] Iron Sword
  ├── [body] Leather Armor

==================================================
QUERY EQUIPPED ITEMS
==================================================

Items currently equipped:
  [main_hand] Iron Sword
  [body] Leather Armor
```

**File Structure:**

```
demos/inventory_tree/
├── main.py      # Complete demo (~250 lines)
└── README.md    # Explanation of relationships
```

---

## Demo Progression

Recommended learning order:

| Order | Demo | Focus | Builds On |
|-------|------|-------|-----------|
| 1 | `hello_ecs` | Core ECS basics | - |
| 2 | `chain_reaction` | Observers & events | Core concepts |
| 3 | `inventory_tree` | Relationships | Core concepts |
| 4 | `spatial_aoe` | Spatial queries | Core concepts |
| 5 | `character_sheet` | Procedural prefabs | Relationships |
| 6 | `pygame` | Full visual simulation | All of the above |

## Implementation Notes

### Guiding Principles

1. **Self-contained** - Each demo runs standalone with no external dependencies (except spatial addon for `spatial_aoe`)
2. **Readable output** - Clear text output that explains what's happening
3. **Commented code** - Key concepts explained inline
4. **Progressive complexity** - Each demo builds on concepts from earlier ones
5. **Copy-paste friendly** - Users can extract patterns for their own projects

### README Template

Each demo should have a README.md with:

```markdown
# Demo Name

Brief description of what this demo shows.

## Features Demonstrated

- Feature 1
- Feature 2
- Feature 3

## Running the Demo

\`\`\`bash
python demos/demo_name/main.py
\`\`\`

## Key Concepts

### Concept 1

Explanation with code snippet.

### Concept 2

Explanation with code snippet.

## Next Steps

Links to related demos or documentation.
```

### Testing

Each demo should be testable:

```bash
# Verify demo runs without error
python demos/hello_ecs/main.py > /dev/null && echo "OK"

# Verify deterministic output (if seeded)
python demos/hello_ecs/main.py | md5sum
```

Add demos to CI to catch regressions:

```yaml
- name: Run demos
  run: |
    python demos/hello_ecs/main.py
    python demos/chain_reaction/main.py
    python demos/inventory_tree/main.py
    python demos/spatial_aoe/main.py
```
