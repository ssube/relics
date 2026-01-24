# Procedural Prefabs Addon

Graph-based entity generation with conditional components, parameter inheritance, and automatic child entity spawning.

## Quick Start

```python
from relics import World
from relics.addons.procedural_prefabs import (
    ProceduralPrefabRegistry,
    HasEquipped,
    create_cascade_observer,
    get_children,
)

# Create world and registry
world = World()
registry = ProceduralPrefabRegistry(world, rng_seed=42)

# Register component types
registry.register_component_type("Health", Health)
registry.register_component_type("Damage", Damage)

# Load procedural prefabs from JSON/YAML
registry.load_directory("prefabs/procedural/")

# Register prefab lists for attachment selection
registry.register_list("weapons_axe", ["battle_axe", "war_hammer"])
registry.register_list("weapons_sword", ["longsword", "shortsword"])

# Optional: register cascade deletion observer
world.observe(create_cascade_observer())

# Spawn procedural entity with parameters
character = registry.spawn("character", {
    "race": "dwarf",
    "class": "warrior",
})
world.tick(0)

# Query generated attachments
for equipped in get_children(character, HasEquipped):
    print(f"Equipped: {equipped.id}")
```

## Features

- **JSON/YAML prefab definitions** for data-driven entity generation
- **Conditional components** with `when` clauses based on parameters
- **Parameter inheritance** from parent entities
- **Parameter derivation** (compute new params from existing ones)
- **Automatic child spawning** via attachment definitions
- **Cascade deletion** for cleaning up entity hierarchies
- **Deterministic RNG** for reproducible generation

## Prefab Definition Format

Procedural prefabs are defined in JSON or YAML:

```json
{
  "name": "character",
  "params": {
    "race": {"type": "string", "required": true},
    "class": {"type": "string", "default": "warrior"},
    "level": {"type": "int", "default": 1}
  },
  "components": {
    "Health": {
      "base": {"current": 100, "maximum": 100},
      "variants": [
        {
          "when": {"race": "dwarf"},
          "add": {"maximum": 20}
        },
        {
          "when": {"class": "warrior"},
          "add": {"maximum": 50}
        }
      ]
    }
  },
  "conditionals": [
    {
      "when": {"class": "warrior"},
      "components": {
        "Armor": {"defense": 10}
      }
    }
  ],
  "attachments": [
    {
      "slot": "weapon",
      "edge_type": "HasEquipped",
      "select": {
        "when": {"class": "warrior", "race": "dwarf"},
        "from_list": "weapons_axe"
      }
    }
  ]
}
```

## Parameter System

### Parameter Types

```json
{
  "params": {
    "name": {"type": "string", "required": true},
    "level": {"type": "int", "default": 1, "min": 1, "max": 100},
    "health_mult": {"type": "float", "default": 1.0},
    "is_elite": {"type": "bool", "default": false}
  }
}
```

### Parameter Derivation

Compute new parameters from existing ones:

```json
{
  "derive": [
    {
      "param": "max_health",
      "from": ["base_health", "level"],
      "formula": "base_health + (level * 10)"
    }
  ]
}
```

### When Clauses

Conditional matching based on parameters:

```json
{
  "when": {"race": "elf", "class": "ranger"},
  "add": {"dexterity": 5}
}
```

Supported operators:
- Equality: `{"race": "elf"}`
- Not equal: `{"race": {"$ne": "dwarf"}}`
- Greater than: `{"level": {"$gt": 10}}`
- Less than: `{"level": {"$lt": 5}}`
- In list: `{"class": {"$in": ["warrior", "paladin"]}}`

## Component Variants

Define base components with conditional modifications:

```json
{
  "components": {
    "Stats": {
      "base": {
        "strength": 10,
        "dexterity": 10,
        "intelligence": 10
      },
      "variants": [
        {
          "when": {"race": "orc"},
          "add": {"strength": 5},
          "derive": {"dexterity": -2}
        },
        {
          "when": {"class": "mage"},
          "add": {"intelligence": 10}
        }
      ]
    }
  }
}
```

## Attachments

Automatically spawn and attach child entities:

```json
{
  "attachments": [
    {
      "slot": "main_hand",
      "edge_type": "HasEquipped",
      "select": {
        "when": {"class": "warrior"},
        "from_list": "weapons_melee",
        "fallback": "fists"
      },
      "inherit_params": ["level", "quality"]
    },
    {
      "slot": "armor",
      "edge_type": "IsWearing",
      "prefab": "leather_armor",
      "count": 1
    }
  ]
}
```

### Edge Types

Built-in edge types for attachments:

| Edge Type | Description |
|-----------|-------------|
| `HasEquipped` | Equipment in hand (weapons, tools) |
| `IsWearing` | Worn items (armor, clothing) |
| `HasAttached` | Generic attachment |

Register custom edge types:

```python
from relics.addons.procedural_prefabs import register_edge_type

@dataclass
class HasInventory(Edge):
    slot: int = 0

register_edge_type("HasInventory", HasInventory)
```

## Utility Functions

### Querying Hierarchies

```python
from relics.addons.procedural_prefabs import (
    get_children,
    get_child_ids,
    get_children_recursive,
    get_holder,
    get_holder_id,
    get_root,
    get_slot,
)

# Get direct children
for child in get_children(entity, HasEquipped):
    print(f"Equipped: {child.id}")

# Get all descendants
for descendant in get_children_recursive(entity):
    print(f"Descendant: {descendant.id}")

# Find holder (parent)
holder = get_holder(item, HasEquipped)

# Find root of hierarchy
root = get_root(entity)

# Get slot name
slot = get_slot(entity, HasEquipped)  # e.g., "main_hand"
```

### Managing Hierarchies

```python
from relics.addons.procedural_prefabs import (
    detach,
    destroy_with_children,
)

# Detach from holder
detach(item, HasEquipped)

# Delete entity and all children
destroy_with_children(world, entity)
```

### Cascade Deletion Observer

Automatically delete children when parent is destroyed:

```python
from relics.addons.procedural_prefabs import create_cascade_observer

world.observe(create_cascade_observer())

# Now when an entity is destroyed, all its children are too
world.remove(character)  # Also removes equipped items
```

## API Reference

### ProceduralPrefabRegistry

```python
registry = ProceduralPrefabRegistry(
    world,              # World instance
    rng_seed=None,      # Optional seed for deterministic generation
)

# Register types
registry.register_component_type("Health", Health)
registry.register_edge_type("HasEquipped", HasEquipped)

# Register prefab lists
registry.register_list("weapons", ["sword", "axe", "mace"])

# Load definitions
registry.load_file("prefabs/character.json")
registry.load_directory("prefabs/procedural/")

# Spawn entities
entity = registry.spawn("character", {"race": "elf", "level": 5})
```

### GenerationContext

Access generation context during spawning:

```python
from relics.addons.procedural_prefabs import GenerationContext

context = GenerationContext(
    registry=registry,
    params={"race": "elf"},
    parent_entity=None,
    depth=0,
)

# Access resolved parameters
value = context.get_param("race")
```

## Error Handling

```python
from relics.addons.procedural_prefabs import (
    ProceduralPrefabError,
    ProcPrefabNotFoundError,
    ParamValidationError,
    PrefabListNotFoundError,
    AttachmentSelectionError,
    CyclicAttachmentError,
)

try:
    entity = registry.spawn("unknown_prefab", {})
except ProcPrefabNotFoundError as e:
    print(f"Prefab not found: {e}")

try:
    entity = registry.spawn("character", {"level": "invalid"})
except ParamValidationError as e:
    print(f"Invalid parameter: {e}")
```
