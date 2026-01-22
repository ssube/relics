# Planned Addons

Future addons to help game developers get up and running quickly with quality foundational blocks.

## High Priority

### 1. Stats & Modifiers (`relics.addons.stats`)

Attribute systems with buff/debuff stacking, essential for RPGs, strategy games, and most action games.

**Components:**

```python
@monitored
@dataclass
class Stats(Component):
    """Base stat values for an entity."""
    values: Dict[str, float]

@dataclass
class Modifier(Component):
    """A buff or debuff affecting a stat."""
    stat: str
    operation: Literal["add", "multiply", "set", "min", "max"]
    value: float
    priority: int = 0  # Order of application
    source: Optional[EntityId] = None  # What applied this modifier

@monitored
@dataclass
class ModifierExpiry(Component):
    """Optional expiration for timed modifiers."""
    remaining: float
```

**Index:**

```python
class StatsIndex:
    def __init__(self, world: World): ...

    def get_base(self, entity: Entity, stat: str) -> float: ...
    def get_effective(self, entity: Entity, stat: str) -> float: ...
    def get_modifiers(self, entity: Entity, stat: str) -> List[Tuple[Entity, Modifier]]: ...

    def add_modifier(self, target: Entity, modifier_entity: Entity) -> None: ...
    def remove_modifier(self, target: Entity, modifier_entity: Entity) -> None: ...
    def remove_modifiers_from_source(self, target: Entity, source: EntityId) -> int: ...
```

**Modifier Stacking Rules:**

| Operation | Description | Example |
|-----------|-------------|---------|
| `add` | Sum all add modifiers | +10 strength, +5 strength = +15 |
| `multiply` | Multiply after adds | 1.5x damage after flat bonuses |
| `set` | Override base value | Set speed to 0 (stun) |
| `min` | Floor value | Minimum 1 damage |
| `max` | Cap value | Maximum 100% crit chance |

**Application Order:** `set` → `add` → `multiply` → `min` → `max` (within same priority)

**Integration Points:**
- Procedural prefabs: equipment adds modifier entities as attachments
- Observers: recalculate cached effective values on modifier change
- Timers: `ModifierExpiry` component for timed buffs

**Example:**

```python
# Define base stats in prefab
{
    "type": "Stats",
    "fields": {
        "values": {"strength": 10, "agility": 8, "vitality": 12}
    }
}

# Equipment prefab adds modifier attachment
{
    "name": "iron_sword",
    "graph": {
        "components": [
            {"type": "Modifier", "fields": {"stat": "strength", "operation": "add", "value": 5}}
        ]
    }
}

# Query effective stats
stats_index = StatsIndex(world)
effective_str = stats_index.get_effective(character, "strength")  # 15 with sword equipped
```

---

### 2. Timers & Scheduling (`relics.addons.timers`)

Cooldowns, delayed effects, periodic actions, and timed state changes.

**Components:**

```python
@monitored
@dataclass
class Timer(Component):
    """A countdown timer."""
    remaining: float
    duration: float  # Original duration for reset
    paused: bool = False

@dataclass
class TimerEvent(Component):
    """Event to emit when timer completes."""
    event_type: str
    event_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TimerRepeat(Component):
    """Makes timer repeat after completion."""
    count: int = -1  # -1 = infinite

@dataclass
class TimerCallback(Component):
    """Alternative: reference a registered callback."""
    callback_name: str
```

**Custom Events:**

```python
@dataclass
class TimerStarted(CustomEvent):
    entity: EntityId
    timer_name: Optional[str]

@dataclass
class TimerCompleted(CustomEvent):
    entity: EntityId
    timer_name: Optional[str]

@dataclass
class TimerCancelled(CustomEvent):
    entity: EntityId
    timer_name: Optional[str]
```

**System:**

```python
class TimerSystem(System):
    """Decrements timers and emits events on completion."""

    def query(self) -> QueryBuilder:
        return self.q.with_all([Timer])

    def process(self, entities: List[Entity], components: List[List[Component]], delta: float) -> None:
        for entity in entities:
            timer = entity.get_component(Timer)
            if timer.paused:
                continue

            timer.remaining -= delta

            if timer.remaining <= 0:
                self._handle_completion(entity, timer)

    def _handle_completion(self, entity: Entity, timer: Timer) -> None:
        # Emit completion event
        # Check for repeat component
        # Remove timer or reset
```

**Utilities:**

```python
def create_timer(world: World, duration: float, event_type: str, **event_data) -> Entity: ...
def create_cooldown(world: World, entity: Entity, ability: str, duration: float) -> Entity: ...
def is_on_cooldown(world: World, entity: Entity, ability: str) -> bool: ...
def get_cooldown_remaining(world: World, entity: Entity, ability: str) -> float: ...
def cancel_timer(world: World, timer_entity: Entity) -> None: ...
```

**Example:**

```python
# Create a 5-second respawn timer
timer = create_timer(world, 5.0, "respawn", entity_id=str(dead_entity.id))

# Ability cooldown
def use_fireball(caster: Entity):
    if is_on_cooldown(world, caster, "fireball"):
        return False

    # Cast fireball...
    create_cooldown(world, caster, "fireball", duration=3.0)
    return True

# Periodic damage (poison)
poison_timer = world.spawn("timer")
poison_timer.add_component(Timer(remaining=1.0, duration=1.0))
poison_timer.add_component(TimerRepeat(count=5))  # Tick 5 times
poison_timer.add_component(TimerEvent(
    event_type="poison_tick",
    event_data={"target": str(victim.id), "damage": 10}
))
```

---

### 3. Finite State Machines (`relics.addons.fsm`)

Entity AI, game states, animation states, and complex behavior modeling.

**Components:**

```python
@monitored
@dataclass
class StateMachine(Component):
    """Current state machine state."""
    current: str
    previous: Optional[str] = None
    time_in_state: float = 0.0

@dataclass
class StateDefinition(Component):
    """Definition of available states and transitions."""
    states: Dict[str, StateConfig]
    initial: str
```

**Data Classes:**

```python
@dataclass
class StateConfig:
    """Configuration for a single state."""
    on_enter: List[str] = field(default_factory=list)  # Actions/events
    on_exit: List[str] = field(default_factory=list)
    on_update: List[str] = field(default_factory=list)  # Per-tick actions
    transitions: Dict[str, TransitionConfig] = field(default_factory=dict)

@dataclass
class TransitionConfig:
    """Configuration for a state transition."""
    target: str
    conditions: List[str] = field(default_factory=list)  # All must be true
    actions: List[str] = field(default_factory=list)  # Run on transition
```

**Custom Events:**

```python
@dataclass
class StateEntered(CustomEvent):
    entity: EntityId
    state: str
    previous: Optional[str]

@dataclass
class StateExited(CustomEvent):
    entity: EntityId
    state: str
    next_state: str

@dataclass
class TransitionTriggered(CustomEvent):
    entity: EntityId
    trigger: str
    from_state: str
    to_state: str
```

**Index/Manager:**

```python
class FSMManager:
    def __init__(self, world: World): ...

    # State control
    def trigger(self, entity: Entity, event: str) -> bool: ...
    def force_state(self, entity: Entity, state: str) -> None: ...
    def reset(self, entity: Entity) -> None: ...

    # Queries
    def get_state(self, entity: Entity) -> str: ...
    def get_time_in_state(self, entity: Entity) -> float: ...
    def can_transition(self, entity: Entity, event: str) -> bool: ...

    # Condition/action registration
    def register_condition(self, name: str, predicate: Callable[[Entity], bool]) -> None: ...
    def register_action(self, name: str, action: Callable[[Entity], None]) -> None: ...
```

**JSON Schema:**

```json
{
    "type": "StateDefinition",
    "fields": {
        "initial": "idle",
        "states": {
            "idle": {
                "transitions": {
                    "enemy_spotted": {"target": "chase", "conditions": ["has_target"]},
                    "damaged": {"target": "flee", "conditions": ["health_low"]}
                }
            },
            "chase": {
                "on_enter": ["play_sound:alert"],
                "on_update": ["move_toward_target"],
                "transitions": {
                    "target_reached": {"target": "attack"},
                    "target_lost": {"target": "idle"}
                }
            },
            "attack": {
                "on_enter": ["start_attack_animation"],
                "transitions": {
                    "attack_complete": {"target": "chase"},
                    "target_died": {"target": "idle"}
                }
            },
            "flee": {
                "on_enter": ["play_sound:flee"],
                "on_update": ["move_away_from_target"],
                "transitions": {
                    "health_recovered": {"target": "idle"},
                    "safe_distance": {"target": "idle"}
                }
            }
        }
    }
}
```

**Example:**

```python
# Setup
fsm = FSMManager(world)

# Register conditions
fsm.register_condition("has_target", lambda e: e.has_component(Target))
fsm.register_condition("health_low", lambda e: e.get_component(Health).current < 20)

# Register actions
fsm.register_action("move_toward_target", lambda e: move_toward(e, e.get_component(Target).entity_id))

# Trigger transitions
fsm.trigger(enemy, "enemy_spotted")  # idle -> chase
fsm.trigger(enemy, "target_reached")  # chase -> attack

# Query state
if fsm.get_state(enemy) == "attack":
    deal_damage(player)
```

---

### 4. Tags & Groups (`relics.addons.tags`)

Lightweight entity categorization without full component overhead.

**API:**

```python
class TagIndex:
    def __init__(self, world: World): ...

    # Tag management
    def add(self, entity: Entity, tag: str) -> None: ...
    def remove(self, entity: Entity, tag: str) -> None: ...
    def has(self, entity: Entity, tag: str) -> bool: ...
    def get_tags(self, entity: Entity) -> Set[str]: ...

    # Group queries
    def get_entities(self, tag: str) -> Iterator[Entity]: ...
    def get_entity_ids(self, tag: str) -> Set[EntityId]: ...
    def count(self, tag: str) -> int: ...

    # Multi-tag queries
    def get_with_all(self, tags: List[str]) -> Iterator[Entity]: ...
    def get_with_any(self, tags: List[str]) -> Iterator[Entity]: ...
    def get_with_none(self, tags: List[str]) -> Iterator[Entity]: ...
```

**Query Integration:**

```python
# Extend QueryBuilder
class QueryBuilder:
    def with_tag(self, tag: str) -> QueryBuilder: ...
    def with_any_tag(self, tags: List[str]) -> QueryBuilder: ...
    def without_tag(self, tag: str) -> QueryBuilder: ...

# Usage
enemies = world.query().with_tag("enemy").with_all([Health]).execute_entities()
flying_enemies = world.query().with_tag("enemy").with_tag("flying").execute_entities()
```

**Prefab Integration:**

```json
{
    "name": "goblin",
    "tags": ["enemy", "humanoid", "small"],
    "graph": {
        "components": [...]
    }
}
```

**Observer:**

```python
class OnTagAdded(Observer):
    tag: ClassVar[str]

    @abstractmethod
    def on_tag_added(self, entity: Entity, tag: str) -> None: ...

class OnTagRemoved(Observer):
    tag: ClassVar[str]

    @abstractmethod
    def on_tag_removed(self, entity: Entity, tag: str) -> None: ...
```

**Example:**

```python
tags = TagIndex(world)

# Categorize entities
tags.add(goblin, "enemy")
tags.add(goblin, "hostile")
tags.add(chest, "interactable")
tags.add(chest, "container")

# Quick checks
if tags.has(target, "invulnerable"):
    return  # Can't damage

# Group operations
for enemy in tags.get_entities("enemy"):
    if tags.has(enemy, "boss"):
        enemy.get_component(Health).current *= 2  # Bosses heal

# Combined with spatial queries
nearby_enemies = [
    e for e in spatial_index.query_circle(player_x, player_y, 100)
    if tags.has(e, "enemy")
]
```

---

### 5. Regenerating Resources (`relics.addons.resources`)

Health, mana, stamina, and other regenerating pools common in RPGs and action games.

**Components:**

```python
@monitored
@dataclass
class Resource(Component):
    """A regenerating resource pool."""
    current: float
    maximum: float
    regen_rate: float = 0.0  # Per second
    regen_delay: float = 0.0  # Seconds after damage before regen starts

@monitored
@dataclass
class ResourceRegen(Component):
    """Tracks regeneration state."""
    time_since_depleted: float = 0.0
    paused: bool = False

@dataclass
class ResourceType(Component):
    """Identifies the resource type."""
    name: str  # "health", "mana", "stamina"
```

**Prefab Pattern:**

```json
{
    "name": "character",
    "graph": {
        "components": [
            {
                "type": "Resource",
                "fields": {"current": 100, "maximum": 100, "regen_rate": 5, "regen_delay": 3}
            },
            {"type": "ResourceType", "fields": {"name": "health"}}
        ],
        "attachments": [
            {
                "prefab": "mana_pool",
                "edge_type": "HasAttached",
                "slot": "mana"
            },
            {
                "prefab": "stamina_pool",
                "edge_type": "HasAttached",
                "slot": "stamina"
            }
        ]
    }
}
```

**System:**

```python
class ResourceRegenSystem(System):
    """Handles resource regeneration over time."""

    def query(self) -> QueryBuilder:
        return self.q.with_all([Resource, ResourceRegen])

    def process(self, entities: List[Entity], components: List[List[Component]], delta: float) -> None:
        for entity in entities:
            resource = entity.get_component(Resource)
            regen = entity.get_component(ResourceRegen)

            if regen.paused or resource.regen_rate <= 0:
                continue

            regen.time_since_depleted += delta

            if regen.time_since_depleted >= resource.regen_delay:
                resource.current = min(
                    resource.maximum,
                    resource.current + resource.regen_rate * delta
                )
```

**Custom Events:**

```python
@dataclass
class ResourceDepleted(CustomEvent):
    """Fired when resource reaches 0."""
    entity: EntityId
    resource_type: str

@dataclass
class ResourceFull(CustomEvent):
    """Fired when resource reaches maximum."""
    entity: EntityId
    resource_type: str

@dataclass
class ResourceChanged(CustomEvent):
    """Fired on any resource change."""
    entity: EntityId
    resource_type: str
    old_value: float
    new_value: float
    change: float  # Positive = gain, negative = loss
```

**Utilities:**

```python
class ResourceManager:
    def __init__(self, world: World): ...

    # Resource access
    def get(self, entity: Entity, resource_type: str) -> Optional[Resource]: ...
    def get_current(self, entity: Entity, resource_type: str) -> float: ...
    def get_percent(self, entity: Entity, resource_type: str) -> float: ...

    # Modification
    def modify(self, entity: Entity, resource_type: str, amount: float) -> float: ...
    def set_current(self, entity: Entity, resource_type: str, value: float) -> None: ...
    def set_maximum(self, entity: Entity, resource_type: str, value: float) -> None: ...

    # Convenience
    def damage(self, entity: Entity, amount: float) -> float: ...  # Modifies "health"
    def heal(self, entity: Entity, amount: float) -> float: ...
    def spend_mana(self, entity: Entity, amount: float) -> bool: ...  # Returns False if insufficient
    def spend_stamina(self, entity: Entity, amount: float) -> bool: ...

    # Queries
    def is_alive(self, entity: Entity) -> bool: ...
    def is_full(self, entity: Entity, resource_type: str) -> bool: ...
    def can_afford(self, entity: Entity, resource_type: str, cost: float) -> bool: ...
```

**Example:**

```python
resources = ResourceManager(world)

# Combat
damage_dealt = resources.damage(enemy, 25)
print(f"Dealt {damage_dealt} damage")

if not resources.is_alive(enemy):
    world.remove(enemy)

# Ability usage
def cast_fireball(caster: Entity, target: Entity):
    mana_cost = 30

    if not resources.can_afford(caster, "mana", mana_cost):
        return False

    resources.spend_mana(caster, mana_cost)
    resources.damage(target, 50)
    return True

# Stamina-based actions
def swing_sword(character: Entity):
    stamina_cost = 10

    if not resources.spend_stamina(character, stamina_cost):
        return False  # Too tired

    # Perform attack...
    return True

# Query low health entities
for entity_id in world.get_entities_with_component(Resource):
    entity = world.get_entity(entity_id)
    if resources.get_percent(entity, "health") < 0.25:
        # Trigger low health warning
        pass
```

**Integration with Stats Addon:**

```python
# Maximum health affected by vitality stat
base_max_health = 100
vitality_bonus = stats_index.get_effective(entity, "vitality") * 10
resources.set_maximum(entity, "health", base_max_health + vitality_bonus)

# Regen rate affected by spirit stat
base_regen = 5
spirit_bonus = stats_index.get_effective(entity, "spirit") * 0.5
resource = resources.get(entity, "mana")
resource.regen_rate = base_regen + spirit_bonus
```

---

### 6. Inventory & Containers (`relics.addons.inventory`)

Builds on procedural prefabs attachment system with game-specific constraints.

**Components:**

```python
@dataclass
class Container(Component):
    """Defines inventory constraints."""
    slots: int
    weight_limit: Optional[float] = None
    allowed_tags: Optional[List[str]] = None  # Requires tags addon

@dataclass
class Stackable(Component):
    """Item can stack."""
    count: int = 1
    max_stack: int = 99

@dataclass
class ItemWeight(Component):
    """Weight per unit."""
    weight: float

@dataclass
class SlotRestriction(Component):
    """Item can only go in specific slots."""
    allowed_slots: List[str]
```

**Manager:**

```python
class InventoryManager:
    def __init__(self, world: World): ...

    # Item operations
    def add_item(self, container: Entity, item: Entity) -> bool: ...
    def remove_item(self, container: Entity, item: Entity) -> bool: ...
    def transfer(self, source: Entity, target: Entity, item: Entity) -> bool: ...
    def drop(self, container: Entity, item: Entity) -> Entity: ...  # Creates world item

    # Stack operations
    def add_stack(self, container: Entity, item: Entity, count: int) -> int: ...  # Returns overflow
    def split_stack(self, item: Entity, count: int) -> Entity: ...
    def merge_stacks(self, target: Entity, source: Entity) -> bool: ...

    # Queries
    def get_items(self, container: Entity) -> Iterator[Entity]: ...
    def get_items_by_tag(self, container: Entity, tag: str) -> Iterator[Entity]: ...
    def find_item(self, container: Entity, prefab: str) -> Optional[Entity]: ...
    def count_items(self, container: Entity, prefab: str) -> int: ...
    def get_total_weight(self, container: Entity) -> float: ...
    def get_free_slots(self, container: Entity) -> int: ...

    # Validation
    def can_add(self, container: Entity, item: Entity) -> bool: ...
    def can_add_count(self, container: Entity, item: Entity, count: int) -> bool: ...
```

**Example:**

```python
inventory = InventoryManager(world)

# Add item (handles stacking automatically)
if inventory.can_add(player, potion):
    inventory.add_item(player, potion)

# Check weight before picking up
if inventory.get_total_weight(player) + item_weight <= weight_limit:
    inventory.add_item(player, heavy_item)

# Find and use item
health_potion = inventory.find_item(player, "health_potion")
if health_potion:
    resources.heal(player, 50)
    stackable = health_potion.get_component(Stackable)
    if stackable.count > 1:
        stackable.count -= 1
    else:
        inventory.remove_item(player, health_potion)
        world.remove(health_potion)
```

---

## Medium Priority

### 7. Pathfinding (`relics.addons.pathfinding`)

Natural companion to the spatial index addon.

**Components:**

```python
@dataclass
class NavAgent(Component):
    """Entity that can navigate."""
    speed: float
    radius: float  # For obstacle avoidance

@monitored
@dataclass
class Path(Component):
    """Current navigation path."""
    waypoints: List[Tuple[float, float]]
    current_index: int = 0

@dataclass
class NavObstacle(Component):
    """Static or dynamic obstacle."""
    radius: float
```

**Index:**

```python
class PathfindingIndex:
    def __init__(self, world: World, spatial_index: SpatialIndexView2D): ...

    # Grid-based
    def set_grid(self, width: int, height: int, cell_size: float) -> None: ...
    def set_walkable(self, x: int, y: int, walkable: bool) -> None: ...

    # Pathfinding
    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]: ...
    def find_path_avoiding(self, start, goal, avoid_entities: Iterable[Entity]) -> Optional[List[...]]: ...

    # Line of sight
    def has_line_of_sight(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool: ...

    # Utilities
    def smooth_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]: ...
    def get_nearest_walkable(self, point: Tuple[float, float]) -> Tuple[float, float]: ...
```

---

### 8. Trigger Volumes (`relics.addons.triggers`)

Spatial regions that fire events on entity enter/exit.

**Components:**

```python
@dataclass
class TriggerVolume(Component):
    """Defines a trigger region."""
    shape: Literal["circle", "rectangle", "box", "sphere"]
    # Shape-specific dimensions stored separately

@dataclass
class TriggerCircle(Component):
    radius: float

@dataclass
class TriggerRectangle(Component):
    half_width: float
    half_height: float

@dataclass
class TriggerFilter(Component):
    """Optional filtering for what can trigger."""
    required_tags: List[str] = field(default_factory=list)
    excluded_tags: List[str] = field(default_factory=list)
    required_prefabs: List[str] = field(default_factory=list)

@dataclass
class TriggerState(Component):
    """Tracks entities currently inside."""
    inside: Set[EntityId] = field(default_factory=set)
```

**Events:**

```python
@dataclass
class TriggerEntered(CustomEvent):
    trigger: EntityId
    entity: EntityId

@dataclass
class TriggerExited(CustomEvent):
    trigger: EntityId
    entity: EntityId

@dataclass
class TriggerOccupied(CustomEvent):
    """First entity entered."""
    trigger: EntityId
    entity: EntityId

@dataclass
class TriggerVacated(CustomEvent):
    """Last entity exited."""
    trigger: EntityId
```

---

### 9. Turn Manager (`relics.addons.turns`)

Support for turn-based games with initiative ordering and action points.

**Components:**

```python
@monitored
@dataclass
class TurnActor(Component):
    """Entity that participates in turn order."""
    initiative: float
    action_points: int
    max_action_points: int

@dataclass
class TurnState(Component):
    """Current turn state for an actor."""
    is_current: bool = False
    actions_taken: int = 0
```

**Manager:**

```python
class TurnManager:
    def __init__(self, world: World): ...

    # Turn control
    def start_combat(self) -> None: ...
    def end_combat(self) -> None: ...
    def next_turn(self) -> Entity: ...
    def end_turn(self) -> None: ...

    # Action points
    def spend_action(self, entity: Entity, cost: int = 1) -> bool: ...
    def can_act(self, entity: Entity, cost: int = 1) -> bool: ...

    # Queries
    def get_current_actor(self) -> Optional[Entity]: ...
    def get_turn_order(self) -> List[Entity]: ...
    def is_in_combat(self) -> bool: ...
```

---

### 10. Entity Pooling (`relics.addons.pooling`)

Recycle entities for performance in bullet-hell, particle-heavy games.

**API:**

```python
class EntityPool:
    def __init__(self, world: World, prefab: str, initial_size: int = 0): ...

    def acquire(self, overrides: Optional[Dict[Type[Component], Component]] = None) -> Entity: ...
    def release(self, entity: Entity) -> None: ...

    def warm(self, count: int) -> None: ...
    def clear(self) -> None: ...

    @property
    def available(self) -> int: ...
    @property
    def in_use(self) -> int: ...
```

**Example:**

```python
bullet_pool = EntityPool(world, "bullet", initial_size=100)

def fire_bullet(position: Position2D, velocity: Velocity):
    bullet = bullet_pool.acquire({
        Position2D: Position2D(x=position.x, y=position.y),
        Velocity: velocity,
    })
    return bullet

def on_bullet_hit(bullet: Entity):
    bullet_pool.release(bullet)
```

---

## Implementation Order Recommendation

1. **Stats & Modifiers** - Foundation for RPG mechanics
2. **Timers & Scheduling** - Widely needed, simple to implement
3. **Tags & Groups** - Lightweight, high utility
4. **Regenerating Resources** - Builds on Stats, common need
5. **Finite State Machines** - AI foundation
6. **Inventory & Containers** - Builds on procedural prefabs
7. **Trigger Volumes** - Builds on spatial index
8. **Pathfinding** - Builds on spatial index
9. **Turn Manager** - Genre-specific but valuable
10. **Entity Pooling** - Performance optimization

## Design Principles

All addons should follow established patterns from the codebase:

1. **Lazy initialization** - Build indexes on first access
2. **Observer auto-registration** - Factory functions handle setup
3. **JSON-definable** - Data-driven where possible
4. **Monitored components** - Change tracking for reactive updates
5. **Prefab integration** - Work seamlessly with procedural prefabs
6. **Type-safe** - Full type hints and Pydantic validation
