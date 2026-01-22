# Relics: Procedural Graph Prefabs Specification

**Version:** 0.1  
**Status:** Draft  
**Type:** Addon  
**Requires:** Relics ECS Framework

---

## Overview

This specification defines an **addon module** for the Relics ECS framework that adds procedural entity generation via graph walks. A `ProceduralPrefab` defines a directed graph where nodes contain parameterized component templates and edges define conditional paths and attachment points for child entities.

The primary use case is spawning complex entity hierarchies (characters with equipment, vehicles with components, trees with seasonal foliage) from a single spawn call with runtime parameters.

---

## Critical Constraint: Addon Architecture

**This module MUST be implemented as a standalone addon that does not modify the core Relics codebase.**

- **No changes** to `World`, `Entity`, `Component`, `Edge`, or any core classes
- **No changes** to existing prefab loading, storage, or spawning logic
- **No changes** to the core JSON schema or persistence backends
- The addon provides its own `ProceduralPrefab` class, registry, and spawner
- The addon **uses** the public API of Relics (e.g., `world.spawn()`, `entity.add_component()`, `entity.add_relationship()`)
- The addon can be imported separately and registered with a World instance

This constraint ensures:
1. Core Relics remains stable and testable independently
2. Users can opt-in to procedural prefabs without bloating the core
3. The addon can evolve on its own release cycle
4. Other addons can follow the same pattern

---

## Design Goals

1. **Pure Addon**: Zero modifications to Relics core codebase
2. **Data-Driven**: Procedural prefabs are defined in JSON with no embedded code strings
3. **Parameter Accumulation**: Entities derive new parameters during generation that affect siblings and children
4. **Composable**: Attachments can reference static prefabs (via core) or other procedural prefabs
5. **Tool-Friendly**: JSON schema supports validation and editor tooling
6. **Deterministic**: World-level RNG seed ensures reproducible generation for testing and save/load

---

## Core Concepts

### ProceduralPrefab Class

A `ProceduralPrefab` is a separate class from the core `Prefab`. It is loaded, stored, and validated independently.

```python
# Addon class - does NOT inherit from core Prefab
@dataclass
class ProceduralPrefab:
    """A procedural prefab template for graph-based entity generation."""
    name: str
    params: Dict[str, ParamDefinition]
    graph: GraphDefinition
```

**JSON structure** (stored in separate files or a separate registry):

```json
{
  "name": "character",
  "params": { ... },
  "graph": {
    "root": { ... }
  }
}
```

Note: There is no `"procedural": true` flag. The file format and class type distinguish procedural prefabs from static prefabs.

### Parameter Flow

Parameters flow through the generation graph with accumulation:

| Scope | Description | Visibility |
|-------|-------------|------------|
| `params` | Passed to `world.spawn()` or inherited from parent | Read-only to current node |
| `derived` | Added by current node via `derive` clauses | Passed to younger siblings and all children |

Children see the merged context: `{...params, ...derived}`.

**Example flow:**
```
spawn("character", {race: "dwarf", class: "warrior"})
    │
    ├─► root evaluates conditionals → derives {weapon_type: "axe"}
    │
    ├─► main_hand attachment receives {race, class, weapon_type}
    │       └─► spawns battle_axe → derives {wielding: "two_handed"}
    │
    ├─► off_hand attachment receives {race, class, weapon_type, wielding}
    │       └─► skipped (when: {wielding: "two_handed"} matches skip rule)
    │
    └─► head attachment receives full context
            └─► spawns horned_helmet
```

### Attached Entity Lifecycle

Entities spawned via attachments exist within the same ECS World as their holder. For v0.1, attached entities are added and removed along with the holder entity. Detaching entities before holder removal can be handled via helper functions or observers.

---

## JSON Schema

### Param Definitions

The `params` field declares expected parameters with types and constraints.

```json
"params": {
  "race": { 
    "type": "enum", 
    "values": ["human", "dwarf", "elf"], 
    "required": true 
  },
  "class": { 
    "type": "enum", 
    "values": ["warrior", "mage", "rogue"], 
    "required": true 
  },
  "level": { 
    "type": "int", 
    "default": 1 
  },
  "name": { 
    "type": "string", 
    "default": null 
  }
}
```

**Supported types:** `enum`, `string`, `int`, `float`, `bool`

**Validation:** If `required` is true and no value is provided at spawn time, raise `ParamValidationError`.

### Component Definitions

Components can be defined as a single object (unconditional) or an array of conditional variants evaluated in order, with the first match winning.

**Unconditional:**
```json
"Position": { "values": { "x": 0, "y": 0, "z": 0 } }
```

**Conditional (ordered, first-match):**
```json
"Health": [
  { "when": { "race": "dwarf" }, "values": { "current": 100, "maximum": 100 } },
  { "when": { "race": "elf" }, "values": { "current": 60, "maximum": 60 } },
  { "values": { "current": 80, "maximum": 80 } }
]
```

The final entry with no `when` clause serves as the fallback. If no variant matches and no fallback exists, the component is not added.

### The `when` Clause

The `when` clause performs exact-match comparison against the current parameter context.

**v0.1 Syntax (exact match only):**
```json
{ "when": { "race": "dwarf" } }
{ "when": { "race": "dwarf", "class": "warrior" } }
```

Multiple keys in a single `when` clause are AND-ed together.

**Reserved for v0.2+:**
```json
{ "when": { "race": { "in": ["dwarf", "gnome"] } } }
{ "when": { "level": { "gte": 5 } } }
{ "when": { "any": [{ "race": "dwarf" }, { "class": "warrior" }] } }
{ "when": { "expr": "race == 'dwarf' and level > 3" } }
```

### Conditionals Block

The `conditionals` block adds components and derives parameters based on rules. All matching conditionals are applied in order (unlike components, which use first-match).

```json
"conditionals": [
  {
    "when": { "race": "dwarf" },
    "add": {
      "Trait": { "values": { "hair": "bearded" } },
      "Resistance": { "values": { "poison": 0.5 } }
    }
  },
  {
    "when": { "class": "warrior", "race": "dwarf" },
    "derive": { "weapon_type": "axe", "armor_class": "heavy" }
  },
  {
    "when": { "class": "warrior" },
    "derive": { "weapon_type": "sword", "armor_class": "medium" }
  }
]
```

**Behavior:**
- `add`: Attach additional components to the entity
- `derive`: Add parameters to the context for younger siblings and children
- Both can appear in the same conditional
- Derived parameters from earlier conditionals are visible to later conditionals

### Attachments Block

Attachments define named slots that spawn child entities. The `@` sigil references parameter values.

**Simple attachment:**
```json
"attachments": {
  "main_hand": {
    "template": "weapon",
    "select": { "allowed_for": "@race", "type": "@weapon_type" }
  }
}
```

**Conditional attachment (ordered, first-match):**
```json
"off_hand": [
  { "when": { "wielding": "two_handed" }, "skip": true },
  { "template": "shield", "select": { "allowed_for": "@race" } }
]
```

**Attachment fields:**

| Field | Type | Description |
|-------|------|-------------|
| `template` | string | Name of prefab to spawn |
| `select` | object | Selection criteria (see Selection below) |
| `optional` | bool | If true, no error when no matching prefab found |
| `skip` | bool | If true, do not spawn anything for this attachment |
| `when` | object | Condition for this attachment variant |

### Selection Criteria

Selection determines which prefab to spawn when multiple could match.

**v0.1: Named Lists**
```json
"select": { "from_list": "weapons_dwarf" }
```

The prefab registry maintains named lists:
```python
world.register_prefab_list("weapons_dwarf", ["battle_axe", "war_hammer", "throwing_axe"])
```

**v0.2: Tag-Based Queries**
```json
"select": { "allowed_for": "@race", "type": "@weapon_type" }
```

Prefabs declare tags:
```json
{
  "name": "battle_axe",
  "tags": { "allowed_for": ["dwarf", "human"], "type": "axe", "weapon_class": "two_handed" }
}
```

**v0.2: Combined**
```json
"select": {
  "from_list": "starter_weapons",
  "where": { "allowed_for": "@race" }
}
```

**Selection behavior when multiple prefabs match:** Use the world's seeded RNG to select one randomly.

---

## Complete Example

**File: `prefabs/procedural/character.procprefab.json`**

```json
{
  "name": "character",
  "params": {
    "race": { "type": "enum", "values": ["human", "dwarf", "elf"], "required": true },
    "class": { "type": "enum", "values": ["warrior", "mage", "rogue"], "required": true }
  },
  "graph": {
    "root": {
      "components": {
        "Position": { "values": { "x": 0, "y": 0, "z": 0 } },
        "Health": [
          { "when": { "race": "dwarf" }, "values": { "current": 100, "maximum": 100 } },
          { "when": { "race": "elf" }, "values": { "current": 60, "maximum": 60 } },
          { "values": { "current": 80, "maximum": 80 } }
        ],
        "Scale": [
          { "when": { "race": "dwarf" }, "values": { "x": 1.0, "y": 0.7, "z": 1.0 } },
          { "when": { "race": "elf" }, "values": { "x": 0.9, "y": 1.15, "z": 0.9 } },
          { "values": { "x": 1.0, "y": 1.0, "z": 1.0 } }
        ]
      },
      
      "conditionals": [
        {
          "when": { "race": "dwarf" },
          "add": {
            "Trait": { "values": { "hair": "bearded" } },
            "Resistance": { "values": { "poison": 0.5 } }
          }
        },
        {
          "when": { "class": "warrior", "race": "dwarf" },
          "derive": { "weapon_type": "axe", "armor_class": "heavy" }
        },
        {
          "when": { "class": "warrior" },
          "derive": { "weapon_type": "sword", "armor_class": "medium" }
        },
        {
          "when": { "class": "mage" },
          "derive": { "weapon_type": "staff", "armor_class": "light" }
        }
      ],
      
      "attachments": {
        "main_hand": {
          "template": "weapon",
          "select": { "from_list": "weapons_@weapon_type" }
        },
        "off_hand": [
          { "when": { "wielding": "two_handed" }, "skip": true },
          { "when": { "class": "mage" }, "template": "tome", "optional": true },
          { "template": "shield", "select": { "from_list": "shields_@armor_class" } }
        ],
        "head": {
          "template": "helmet",
          "select": { "from_list": "helmets_@armor_class" },
          "optional": true
        }
      }
    }
  }
}
```

---

## Addon API

The addon provides its own classes and registry that work alongside the core Relics API. **No core classes are modified.**

### ProceduralPrefabRegistry

The addon maintains its own registry, separate from the core prefab system.

```python
class ProceduralPrefabRegistry:
    """Registry for procedural prefabs. Does not touch core Relics."""
    
    def __init__(self, world: World, rng_seed: Optional[int] = None):
        """
        Initialize the registry.
        
        Args:
            world: The Relics World instance (used for spawning entities)
            rng_seed: Seed for deterministic random selection
        """
        self._world = world
        self._rng = Random(rng_seed)
        self._prefabs: Dict[str, ProceduralPrefab] = {}
        self._lists: Dict[str, List[str]] = {}
    
    def register(self, prefab: ProceduralPrefab) -> None:
        """Register a procedural prefab."""
        ...
    
    def load(self, path: str) -> None:
        """Load procedural prefabs from a JSON file."""
        ...
    
    def load_directory(self, directory: str) -> None:
        """Load all .procprefab.json files from a directory."""
        ...
    
    def get(self, name: str) -> ProceduralPrefab:
        """Get a procedural prefab by name. Raises ProceduralPrefabNotFoundError if not found."""
        ...
    
    def register_list(self, name: str, prefab_names: List[str]) -> None:
        """Register a named list for attachment selection."""
        ...
    
    def get_list(self, name: str) -> List[str]:
        """Get a registered prefab list. Raises PrefabListNotFoundError if not found."""
        ...
    
    def spawn(
        self, 
        prefab_name: str, 
        params: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[Type[Component], Component]] = None
    ) -> Entity:
        """
        Spawn an entity from a procedural prefab.
        
        This method:
        1. Resolves the ProceduralPrefab by name
        2. Validates params against the prefab's param definitions
        3. Walks the graph, resolving components and conditionals
        4. Calls world.spawn() for the root entity (using a static prefab or raw components)
        5. Recursively spawns attachments
        6. Creates relationship edges between holder and attached entities
        
        Returns the root entity.
        """
        ...
    
    def spawn_tree(
        self, 
        prefab_name: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Entity, Dict[str, Entity]]:
        """
        Spawn and return both the root entity and a dict of attached entities by slot.
        Useful for debugging and testing.
        """
        ...
```

### Usage Example

```python
from relic import World
from relic_procedural import ProceduralPrefabRegistry

# Create core world (unchanged)
world = World()
world.load_prefabs("prefabs/static/")  # Core static prefabs

# Create addon registry
procedural = ProceduralPrefabRegistry(world, rng_seed=42)
procedural.load_directory("prefabs/procedural/")
procedural.register_list("weapons_axe", ["battle_axe", "war_hammer", "throwing_axe"])

# Spawn using the addon
character = procedural.spawn("character", {"race": "dwarf", "class": "warrior"})

# The returned entity is a normal Relics entity
position = character.get_component(Position)
equipped = world.query().with_relationship(HasEquipped, source=character).execute()
```

### Entity Navigation Helpers

The addon provides utility functions for navigating attachment relationships. These do **not** modify the Entity class.

```python
def get_attached(world: World, entity: Entity, slot: Optional[str] = None) -> List[Entity]:
    """
    Get entities attached to this entity via HasEquipped, IsWearing, or HasAttached edges.
    If slot is specified, return only the entity from that slot.
    
    This is a utility function, not a method on Entity.
    """
    ...

def get_holder(world: World, entity: Entity) -> Optional[Entity]:
    """
    Get the entity this is attached to (if any).
    
    This is a utility function, not a method on Entity.
    """
    ...

def detach(world: World, entity: Entity) -> None:
    """
    Remove the attachment relationship between an entity and its holder.
    The entity remains in the world but is no longer attached.
    """
    ...

def destroy_with_attached(world: World, entity: Entity) -> None:
    """
    Destroy an entity and all entities attached to it.
    This is the default behavior when the addon spawns entities.
    
    Can be registered as an observer for OnEntityDestroyed if desired.
    """
    ...
```

### Attachment Relationship Edges

Attachments define their relationship edge type contextually. The framework provides built-in edges, and users can define custom edges.

**Built-in edges:**

```python
@dataclass
class HasEquipped(Edge):
    """Entity has another entity equipped (weapons, tools)."""
    slot: str  # Name of the attachment slot
    
    def validate(self, source, target) -> bool:
        return True  # Managed by framework

@dataclass
class IsWearing(Edge):
    """Entity is wearing another entity (armor, clothing)."""
    slot: str  # Name of the attachment slot
    
    def validate(self, source, target) -> bool:
        return True  # Managed by framework

@dataclass
class HasAttached(Edge):
    """Generic parent-child attachment (fallback)."""
    slot: str  # Name of the attachment slot
    
    def validate(self, source, target) -> bool:
        return True  # Managed by framework
```

**Edge direction:** Parent → Child (source has/wears target)

**Example relationships:**
- `(character, HasEquipped(slot="main_hand"), battle_axe)`
- `(character, IsWearing(slot="head"), horned_helmet)`
- `(wagon, HasAttached(slot="wheel_fl"), wheel_entity)`

**Specifying edge type in attachments:**

```json
"attachments": {
  "main_hand": {
    "template": "weapon",
    "edge": "HasEquipped",
    "select": { "from_list": "weapons_@weapon_type" }
  },
  "head": {
    "template": "helmet",
    "edge": "IsWearing",
    "optional": true
  }
}
```

If `edge` is omitted, defaults to `HasAttached`.

### Addon Exceptions

These exceptions are defined in the addon module, not in core Relics.

```python
class ProceduralPrefabError(Exception):
    """Base exception for procedural prefab addon errors."""
    pass

class ProceduralPrefabNotFoundError(ProceduralPrefabError):
    """Procedural prefab does not exist in registry."""
    pass

class ParamValidationError(ProceduralPrefabError):
    """Procedural prefab params failed validation."""
    pass

class PrefabListNotFoundError(ProceduralPrefabError):
    """Referenced prefab list does not exist."""
    pass

class AttachmentSelectionError(ProceduralPrefabError):
    """No matching prefab found for non-optional attachment."""
    pass
```

---

## Implementation Plan

### Critical Reminder

**Do NOT modify any files in the core `relic/` directory.** This addon must be implemented as a separate module that imports from and uses the public Relics API.

### v0.1 Scope

Implement the procedural prefab addon as a standalone module:

1. **Create addon module structure** (`relic_procedural/`)
2. **Implement `ProceduralPrefab` class** with params and graph definitions
3. **Implement `GenerationContext`** with `params` (inherited) and `derived` (accumulated) scopes
4. **Implement `when` clause matching** with exact-match semantics only
5. **Implement component resolution** with conditional variants (first-match)
6. **Implement `conditionals` block** with `add` and `derive` operations
7. **Implement `attachments` block** with named list selection (`from_list`)
8. **Define attachment edge types** (`HasEquipped`, `IsWearing`, `HasAttached`)
9. **Implement `ProceduralPrefabRegistry`** with load, register, spawn methods
10. **Implement utility functions** (`get_attached`, `get_holder`, `detach`, `destroy_with_attached`)
11. **Add JSON schema validation** for procedural prefabs
12. **Implement cascade deletion** via observer registration

### v0.1 Implementation Order

1. **Module structure** - Create `relic_procedural/` with `__init__.py`, verify it can import from `relic`
2. **Data classes** - `ProceduralPrefab`, `ParamDefinition`, `GraphDefinition`, `NodeDefinition`
3. **Generation context** - `GenerationContext` class with param/derived merge semantics
4. **When-clause matcher** - Utility function to evaluate `when` clauses against context
5. **Component resolver** - Process component definitions (unconditional and conditional variants)
6. **Conditionals processor** - Apply matching conditionals, updating context
7. **Edge types** - Define `HasEquipped`, `IsWearing`, `HasAttached` edge classes
8. **Prefab list management** - Add to registry class
9. **Attachment spawner** - Recursive spawning with selection logic, edge creation
10. **Registry class** - `ProceduralPrefabRegistry` tying everything together
11. **JSON loading** - Parse `.procprefab.json` files into `ProceduralPrefab` instances
12. **Utility functions** - `get_attached`, `get_holder`, `detach`, `destroy_with_attached`
13. **Cascade deletion observer** - Optional observer for automatic cleanup
14. **Tests** - Unit tests for each component, integration test with character example

### v0.2 Scope (Future)

- Tag-based prefab queries for attachment selection
- Extended `when` clause operators: `in`, `gte`, `lte`, `any`, `all`
- Prefab `tags` field for query-based selection
- Combined selection: `from_list` + `where` filter

### v0.3 Scope (Future)

- Configurable attached entity lifecycle per attachment point
- `on_spawn` hooks for feeding attached entity properties back to context
- Expression language for complex conditionals (`expr` field)

---

## Test Cases

### Required Tests

**Addon Isolation:**
1. **No core modifications**: Verify `relic/` directory is unchanged after running addon tests
2. **Import separation**: Verify addon can be imported independently from core
3. **Interoperability**: Static prefabs from core can be used as attachments in procedural prefabs

**Parameter Handling:**
4. **Basic procedural spawn**: Spawn character with race=dwarf, verify Scale component has y=0.7
5. **Param validation**: Missing required param raises `ParamValidationError`
6. **Default params**: Params with defaults are applied when not provided
7. **Derive ordering**: Verify derived params are visible to younger siblings

**Component Resolution:**
8. **Conditional components**: Verify first-match semantics (dwarf gets 100 health, elf gets 60, human gets 80)
9. **Fallback components**: When no `when` clause matches, fallback (no `when`) is used
10. **No match, no fallback**: Component not added when nothing matches

**Conditionals Block:**
11. **Add components**: Verify `add` attaches additional components
12. **Derive params**: Verify `derive` updates context for siblings and children
13. **Multiple matching**: All matching conditionals apply in order

**Attachments:**
14. **Attachment spawning**: Verify attached entity created with appropriate edge
15. **Edge type selection**: Verify correct edge type (HasEquipped, IsWearing, HasAttached) is used
16. **Attachment selection**: Verify correct prefab selected from list
17. **Optional attachment**: Verify no error when optional attachment has no match
18. **Skip attachment**: Verify `skip: true` prevents spawning
19. **Conditional attachment**: Verify first-match on attachment variants
20. **Nested procedural**: Procedural prefab spawns another procedural prefab as attachment

**Lifecycle:**
21. **Holder destruction**: Verify attached entities removed when holder is destroyed
22. **Detach utility**: Verify `detach()` removes relationship but keeps entity

**Determinism:**
23. **Deterministic RNG**: Same seed produces same selection results across runs
24. **Different seeds**: Different seeds produce different (but valid) results

**Error Handling:**
25. **Prefab not found**: Missing procedural prefab raises `ProceduralPrefabNotFoundError`
26. **List not found**: Missing prefab list raises `PrefabListNotFoundError`
27. **Required attachment fails**: Non-optional attachment with no match raises `AttachmentSelectionError`

---

## File Structure

The addon is a **separate module** alongside (not inside) the core `relic/` directory.

```
relic/                          # CORE - DO NOT MODIFY
├── __init__.py
├── world.py
├── entity.py
├── component.py
├── edge.py
├── prefab/
│   └── ...
└── ...

relic_procedural/               # ADDON - ALL NEW CODE GOES HERE
├── __init__.py                 # Public exports
├── prefab.py                   # ProceduralPrefab, ParamDefinition, GraphDefinition
├── registry.py                 # ProceduralPrefabRegistry
├── context.py                  # GenerationContext
├── matcher.py                  # When-clause matching
├── resolver.py                 # Component and conditional resolution
├── spawner.py                  # Graph walker and attachment spawning
├── edges.py                    # HasEquipped, IsWearing, HasAttached
├── utils.py                    # get_attached, get_holder, detach, destroy_with_attached
├── exceptions.py               # Addon-specific exceptions
├── schema.py                   # JSON schema validation
└── observer.py                 # Optional cascade deletion observer

prefabs/
├── static/                     # Core prefabs (loaded by world.load_prefabs)
│   ├── battle_axe.json
│   ├── war_hammer.json
│   └── ...
└── procedural/                 # Addon prefabs (loaded by registry.load_directory)
    ├── character.procprefab.json
    ├── vehicle.procprefab.json
    └── ...
```

**File naming convention:** Procedural prefabs use `.procprefab.json` extension to distinguish from static `.json` prefabs.

---

## Notes for Implementation

### Addon Constraints (CRITICAL)

- **DO NOT** create, modify, or delete any files in the `relic/` directory
- **DO NOT** monkey-patch or extend core Relics classes
- **DO** use only the public API of Relics (`world.spawn()`, `entity.add_component()`, `entity.add_relationship()`, `world.query()`, etc.)
- **DO** define all new classes, functions, and exceptions in the `relic_procedural/` module
- **DO** use composition over inheritance when integrating with Relics

### Implementation Details

- The `@` sigil in selection criteria (e.g., `"from_list": "weapons_@weapon_type"`) should be interpolated using the current context. If `weapon_type` is `"axe"`, resolve to `"weapons_axe"`.
- When evaluating conditionals, process them in array order. All matching conditionals apply (not first-match like components).
- The registry's RNG should be used for any random selection. Store as `self._rng` and use for deterministic behavior.
- Attached entities are fully functional ECS entities with their own components and relationships. The only special behavior is cascade deletion when the holder is destroyed.
- For spawning the root entity, the addon can either:
  - Create a temporary static prefab and call `world.spawn()`
  - Use lower-level APIs to create an entity and add components directly
  - The latter is preferred to avoid polluting the core prefab registry
- The `destroy_with_attached()` utility should query for all outgoing `HasEquipped`, `IsWearing`, and `HasAttached` relationships and recursively destroy those entities before destroying the holder.
- Consider providing a `CascadeDeletionObserver` class that users can register with `world.observe()` to automatically handle cleanup.

### Testing

- Tests should verify the addon works correctly without any modifications to core Relics
- Create a fresh `World` instance for each test
- Test that entities spawned by the addon are indistinguishable from entities spawned by core Relics
- Test interoperability: static prefabs can be used as attachments for procedural prefabs
