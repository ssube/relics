# Relationships

> Relationships connect entities with typed, validated edges. They bring graph database semantics to the ECS pattern.

---

## 📋 Prerequisites

Before reading this document, you should be familiar with:
- [Getting Started](GETTING_STARTED.md) - Basic concepts and setup
- [Entities & Components](ENTITIES_COMPONENTS.md) - Entity and component patterns

---

## 🔗 What are Relationships?

**Relationships** are typed connections between entities. Unlike components (which describe what an entity *is*), relationships describe how entities *relate* to each other.

```python
player.add_relationship(BelongsTo(role="member"), team.id)
enemy.add_relationship(Targets(), player.id)
item.add_relationship(OwnedBy(), player.id)
```

Key features:
- **Typed edges** - Each relationship has a type (class)
- **Directed** - From source to target
- **Validated** - Custom validation rules
- **Queryable** - Find entities by their relationships
- **Observable** - React to relationship changes

---

## 🎯 Defining Edge Types

Edges are defined by subclassing `Edge`:

```python
from dataclasses import dataclass
from relics import Edge

# Simple edge (no data)
class Targets(Edge):
    pass

# Edge with data
@dataclass
class BelongsTo(Edge):
    role: str = "member"
    joined_at: float = 0.0

# Edge with numeric data
@dataclass
class DistanceTo(Edge):
    distance: float
```

### Edge Data

Edges can carry data, just like components:

```python
@dataclass
class Follows(Edge):
    priority: int = 0
    distance: float = 5.0

@dataclass
class Damages(Edge):
    amount: float
    damage_type: str = "physical"
```

---

## ✅ Edge Validation

Override `validate()` to enforce constraints on relationships:

```python
from relics import Edge, Entity

@dataclass
class BelongsTo(Edge):
    role: str = "member"

    def validate(self, source: Entity, target: Entity) -> bool:
        # Target must be a team
        return target.prefab == "team"

@dataclass
class Targets(Edge):
    def validate(self, source: Entity, target: Entity) -> bool:
        # Can't target yourself
        if source.id == target.id:
            return False
        # Target must have Health
        return target.has_component(Health)

@dataclass
class ParentOf(Edge):
    def validate(self, source: Entity, target: Entity) -> bool:
        # Prevent self-parenting
        if source.id == target.id:
            return False
        # Check for cycles (simple version)
        # In production, you'd want a more thorough check
        return not target.has_relationship(ParentOf, source.id)
```

### Validation Errors

If validation fails, `RelationshipValidationError` is raised:

```python
from relics.errors import RelationshipValidationError

try:
    player.add_relationship(Targets(), player.id)  # Self-targeting
except RelationshipValidationError as e:
    print(f"Invalid relationship: {e}")
```

---

## ➕ Creating Relationships

### add_relationship()

```python
# Add a relationship from player to team
player.add_relationship(BelongsTo(role="captain"), team.id)

# Add a targeting relationship
attacker.add_relationship(Targets(), defender.id)

# Multiple relationships of the same type
player.add_relationship(Follows(), npc1.id)
player.add_relationship(Follows(), npc2.id)
```

### Requirements

- Both entities must exist
- Validation must pass

```python
# ❌ Target doesn't exist
player.add_relationship(Targets(), non_existent_id)
# Raises EntityNotFoundError

# ❌ Validation fails
player.add_relationship(Targets(), player.id)  # Self-targeting
# Raises RelationshipValidationError
```

---

## ➖ Removing Relationships

### remove_relationship()

```python
# Remove by edge type and target
player.remove_relationship(BelongsTo, team.id)

# Remove targeting relationship
attacker.remove_relationship(Targets, defender.id)
```

### Automatic Cleanup

When an entity is removed, all its relationships (both outgoing and incoming) are automatically cleaned up:

```python
# player has: player -> team (BelongsTo)
# enemy has: enemy -> player (Targets)

world.remove(player)
# Automatically removes:
# - player -> team relationship
# - enemy -> player relationship
```

---

## 🔍 Querying Relationships

### Outgoing: get_relationships()

Get all relationships of a specific type from an entity:

```python
# Get all "Follows" relationships from player
follows = player.get_relationships(Follows)
for edge, target_id in follows:
    print(f"Following {target_id} with priority {edge.priority}")
```

Returns: `List[Tuple[Edge, EntityId]]`

### Incoming: get_incoming_relationships()

Get all relationships of a specific type TO an entity:

```python
# Find everyone targeting this player
targeting_player = player.get_incoming_relationships(Targets)
for source_id, edge in targeting_player:
    print(f"{source_id} is targeting this player")
```

Returns: `List[Tuple[EntityId, Edge]]`

### Checking: has_relationship()

```python
# Check if player has any BelongsTo relationship
if player.has_relationship(BelongsTo):
    print("Player belongs to a team")

# Check if player belongs to a specific team
if player.has_relationship(BelongsTo, team.id):
    print("Player is on this team")
```

### Checking: has_incoming_relationship()

```python
# Check if anyone is targeting this entity
if target.has_incoming_relationship(Targets):
    print("Someone is targeting this entity!")

# Check if a specific attacker is targeting
if target.has_incoming_relationship(Targets, attacker.id):
    print("The attacker is targeting this entity")
```

---

## 🔎 Relationship Queries

Find entities based on their relationships using query builders.

### with_relationship() - Outgoing

```python
# Find all entities that are targeting something
targeting_entities = world.query().with_relationship(Targets)
for entity in targeting_entities.execute_entities():
    print(f"{entity.id} is targeting something")

# Find entities targeting a specific entity
attackers = world.query().with_relationship(Targets, target.id)
for entity in attackers.execute_entities():
    print(f"{entity.id} is attacking the target")
```

### with_incoming() - Incoming

```python
# Find all entities that are being targeted
targeted_entities = world.query().with_incoming(Targets)
for entity in targeted_entities.execute_entities():
    print(f"{entity.id} is being targeted")

# Find entities targeted by a specific attacker
victims = world.query().with_incoming(Targets, attacker.id)
for entity in victims.execute_entities():
    print(f"{entity.id} is being attacked")
```

### Combining with Component Queries

```python
# Find enemies targeting players with low health
def is_low_health(entity):
    health = entity.get_component(Health)
    return health.current < health.maximum * 0.25

query = (
    world.query()
    .with_all([Health, Enemy])
    .with_incoming(Targets)  # Being targeted
    .with_filter(is_low_health)
)

for entity in query.execute_entities():
    print(f"Low health enemy being targeted: {entity.id}")
```

---

## 💡 Real-World Examples

### Team/Faction System

```python
@dataclass
class BelongsTo(Edge):
    role: str = "member"

    def validate(self, source: Entity, target: Entity) -> bool:
        return target.prefab == "team"

# Create teams
team_red = world.spawn("team")
team_blue = world.spawn("team")

# Assign players to teams
player1.add_relationship(BelongsTo(role="captain"), team_red.id)
player2.add_relationship(BelongsTo(role="member"), team_red.id)
player3.add_relationship(BelongsTo(role="captain"), team_blue.id)

# Find all members of a team
members = world.query().with_relationship(BelongsTo, team_red.id)
for entity in members.execute_entities():
    edges = entity.get_relationships(BelongsTo)
    for edge, _ in edges:
        print(f"{entity.id}: {edge.role}")
```

### Parent/Child Hierarchies

```python
@dataclass
class ParentOf(Edge):
    def validate(self, source: Entity, target: Entity) -> bool:
        # Prevent self-parenting
        return source.id != target.id

@dataclass
class ChildOf(Edge):
    def validate(self, source: Entity, target: Entity) -> bool:
        return source.id != target.id

# Create hierarchy
root = world.spawn("node")
child1 = world.spawn("node")
child2 = world.spawn("node")
grandchild = world.spawn("node")

root.add_relationship(ParentOf(), child1.id)
root.add_relationship(ParentOf(), child2.id)
child1.add_relationship(ParentOf(), grandchild.id)

# Reverse relationships for easy traversal
child1.add_relationship(ChildOf(), root.id)
child2.add_relationship(ChildOf(), root.id)
grandchild.add_relationship(ChildOf(), child1.id)

# Find all children of root
for edge, child_id in root.get_relationships(ParentOf):
    print(f"Child: {child_id}")

# Find parent of grandchild
for parent_id, edge in grandchild.get_incoming_relationships(ParentOf):
    print(f"Parent: {parent_id}")
```

### Ownership/Inventory

```python
@dataclass
class OwnedBy(Edge):
    slot: str = "inventory"

@dataclass
class Owns(Edge):
    pass

# Player picks up items
sword = world.spawn("item")
shield = world.spawn("item")

sword.add_relationship(OwnedBy(slot="weapon"), player.id)
shield.add_relationship(OwnedBy(slot="offhand"), player.id)
player.add_relationship(Owns(), sword.id)
player.add_relationship(Owns(), shield.id)

# Get player's inventory
for edge, item_id in player.get_relationships(Owns):
    item = world.get_entity(item_id)
    ownership = item.get_relationships(OwnedBy)
    for owned_edge, owner_id in ownership:
        print(f"Item {item_id} in slot {owned_edge.slot}")

# Get items in a specific slot
for edge, item_id in player.get_relationships(Owns):
    item = world.get_entity(item_id)
    for owned_edge, _ in item.get_relationships(OwnedBy):
        if owned_edge.slot == "weapon":
            print(f"Weapon: {item_id}")
```

### Status Effects (Afflicted By)

```python
@dataclass
class AffectedBy(Edge):
    duration: float
    stacks: int = 1

# Apply poison effect
poison_source = world.spawn("effect_source")
player.add_relationship(
    AffectedBy(duration=10.0, stacks=3),
    poison_source.id
)

# System to process effects
class StatusEffectSystem(System):
    def query(self):
        return self.q.with_incoming(AffectedBy)

    def process(self, entities, components, delta):
        for entity in entities:
            effects = entity.get_incoming_relationships(AffectedBy)
            for source_id, edge in effects:
                # Apply effect damage
                # Reduce duration
                # Remove if expired
                pass
```

### Targeting System

```python
@dataclass
class Targets(Edge):
    priority: int = 0
    locked: bool = False

    def validate(self, source: Entity, target: Entity) -> bool:
        # Can't target yourself
        if source.id == target.id:
            return False
        # Target must be alive
        if target.has_component(Dead):
            return False
        # Target must be visible
        return target.has_component(Position)

# AI targeting
class AITargetingSystem(System):
    def query(self):
        return self.q.with_all([AI, Position]).with_none([Dead])

    def process(self, entities, components, delta):
        for entity in entities:
            # Find or update target
            if not entity.has_relationship(Targets):
                target = self._find_best_target(entity)
                if target:
                    entity.add_relationship(
                        Targets(priority=1, locked=False),
                        target.id
                    )

    def _find_best_target(self, entity):
        # Query for potential targets
        targets = (
            self.world.query()
            .with_all([Position, Health])
            .with_none([Dead])
            .execute_entities()
        )
        # Return nearest target
        # ...
```

---

## 🏗️ Best Practices

### 1. Use Bidirectional Relationships When Needed

```python
# For quick traversal in both directions
player.add_relationship(BelongsTo(), team.id)
team.add_relationship(HasMember(), player.id)
```

### 2. Validate Early and Often

```python
class CanAttack(Edge):
    def validate(self, source: Entity, target: Entity) -> bool:
        # Check all constraints upfront
        if source.id == target.id:
            return False
        if not target.has_component(Health):
            return False
        if source.get_component(Faction) == target.get_component(Faction):
            return False
        return True
```

### 3. Use Relationships Instead of EntityId in Components

```python
# ❌ Manual relationship tracking
@dataclass
class TeamMember(Component):
    team_id: EntityId

# ✅ Use proper relationships
@dataclass
class BelongsTo(Edge):
    role: str
```

### 4. Clean Up Stale Relationships

Relics handles this automatically when entities are removed, but you should still:

```python
# Remove relationship before it becomes invalid
if not world.has_entity(target_id):
    entity.remove_relationship(Targets, target_id)
```

### 5. Use Observers for Relationship Events

```python
from relics import RelationshipObserver

class TeamObserver(RelationshipObserver):
    edge_type = BelongsTo

    def on_relationship_added(self, source, edge, target):
        print(f"{source.id} joined team as {edge.role}")

    def on_relationship_removed(self, source, edge, target):
        print(f"{source.id} left the team")
```

---

## 📚 API Summary

### Edge Base Class

| Method | Description |
|--------|-------------|
| `validate(source, target)` | Override to add validation rules |

### Entity Relationship Methods

| Method | Description |
|--------|-------------|
| `add_relationship(edge, target_id)` | Create a relationship |
| `remove_relationship(edge_type, target_id)` | Remove a relationship |
| `get_relationships(edge_type)` | Get outgoing relationships |
| `get_incoming_relationships(edge_type)` | Get incoming relationships |
| `has_relationship(edge_type, target_id=None)` | Check for outgoing |
| `has_incoming_relationship(edge_type, source_id=None)` | Check for incoming |

### Query Methods

| Method | Description |
|--------|-------------|
| `with_relationship(edge_type, target=None)` | Filter by outgoing |
| `with_incoming(edge_type, source=None)` | Filter by incoming |

### Exceptions

| Exception | When Raised |
|-----------|-------------|
| `EntityNotFoundError` | Source or target doesn't exist |
| `RelationshipValidationError` | Edge validation fails |
