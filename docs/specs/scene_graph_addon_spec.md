# Relics: Scene Graph Addon Specification

**Version:** 0.1  
**Status:** Draft  
**Type:** Addon  
**Requires:** Relics ECS Framework

---

## Overview

The Scene Graph addon provides hierarchical transform management for Relics. Nodes are lightweight entities that form a tree structure, with game entities attached to nodes via relationships. World transforms propagate through the hierarchy and are written to attached entities.

This enables spatial organization (rooms containing furniture containing items), camera hierarchies, UI layouts rendered to separate layers, and any other tree-structured transform scenario.

---

## Critical Constraint: Addon Architecture

This module MUST be implemented as a standalone addon that does not modify the core Relics codebase.

- Nodes are entities spawned from a reserved prefab
- Uses standard Relics relationships for parent-child and node-entity connections
- Provides its own components, systems, and path indexing
- Uses the public Relics API exclusively

---

## Design Goals

1. **Nodes as Entities**: Nodes are entities with a distinct prefab, enabling standard Relics relationships
2. **Path-Based Identification**: Nodes identified by materialized paths like `/world/room_1/table`
3. **Cascading Updates**: Reparenting updates all descendant paths
4. **Relationship-Driven Attachment**: Entities attach to nodes via edges
5. **Multi-Graph Support**: Multiple independent scene graphs per world

---

## Core Concepts

### Nodes

Nodes are entities spawned from the `_scene_node` prefab. They form tree structures via parent-child relationships.

```python
# Create a node
room = world.spawn("_scene_node")
room.add_component(NodeName(name="room_1"))
room.add_component(LocalTransform(
    position=Vec3(100, 0, 50),
    rotation=Quat.identity(),
    scale=Vec3(1, 1, 1)
))
```

**Node Components:**

| Component | Purpose |
|-----------|---------|
| `NodeName` | Local name within parent (e.g., `room_1`) |
| `NodePath` | Full materialized path (e.g., `/world/room_1`) — managed by system |
| `LocalTransform` | Position, rotation, scale relative to parent |
| `WorldTransform` | Computed absolute transform — managed by system |

### Scene Graphs

A scene graph is identified by its root node — a node with no parent. Multiple roots means multiple independent graphs.

```python
# Create a scene graph root
world_root = world.spawn("_scene_node")
world_root.add_component(NodeName(name="world"))
# No parent relationship = this is a root
# NodePath will be "/world"

# Create another graph for UI
ui_root = world.spawn("_scene_node")
ui_root.add_component(NodeName(name="ui"))
# NodePath will be "/ui"
```

### Node Hierarchy

Parent-child relationships between nodes use the `ChildOf` edge.

```python
# room_1 is a child of world
world.add_relationship(room, ChildOf(), world_root)
# NodePath updates: "/world/room_1"

# table is a child of room_1
world.add_relationship(table, ChildOf(), room)
# NodePath updates: "/world/room_1/table"
```

**Relationship Direction:**
- `(child_node, ChildOf, parent_node)` — child stores reference to parent
- Query children: find all nodes where `(?, ChildOf, parent_node)`

### Entity Attachment

Game entities attach to nodes via the `AttachedTo` edge.

```python
# Create a game entity
chest = world.spawn("chest")
chest.add_component(LocalOffset(position=Vec3(5, 0, 0)))

# Attach to a node
world.add_relationship(chest, AttachedTo(), table)
```

**Attachment Properties:**
- Multiple entities can attach to the same node
- An entity can attach to nodes in multiple graphs (use sparingly)
- Entities without attachment exist outside the scene graph (no world transform)
- Entities can have `LocalOffset` component for position relative to node

---

## Components

### NodeName

Local name of the node within its parent.

```python
@dataclass
class NodeName(Component):
    name: str  # e.g., "room_1", "table", "spawn_point"
```

### NodePath

Full materialized path from root. Managed by the scene graph system — do not set manually.

```python
@dataclass
class NodePath(Component):
    path: str  # e.g., "/world/room_1/table"
```

### LocalTransform

Transform relative to parent node.

```python
@dataclass
class LocalTransform(Component):
    position: Vec3
    rotation: Quat
    scale: Vec3
```

### WorldTransform

Computed absolute transform. Managed by the scene graph system.

```python
@dataclass
class WorldTransform(Component):
    position: Vec3
    rotation: Quat
    scale: Vec3
    matrix: Mat4  # Cached composite matrix
```

### LocalOffset

Optional offset for entities relative to their attached node.

```python
@dataclass
class LocalOffset(Component):
    position: Vec3 = Vec3(0, 0, 0)
    rotation: Quat = Quat.identity()
    scale: Vec3 = Vec3(1, 1, 1)
```

---

## Relationships

### ChildOf

Connects a child node to its parent node.

```python
@dataclass
class ChildOf(Edge):
    """Node hierarchy relationship."""
    pass
```

### AttachedTo

Connects a game entity to a node.

```python
@dataclass
class AttachedTo(Edge):
    """Entity-to-node attachment."""
    pass
```

---

## Path Index

The addon maintains a materialized secondary index mapping paths to entity IDs.

```python
class PathIndex:
    """O(1) lookup from path string to node entity."""
    
    def get(self, path: str) -> EntityId | None:
        """Returns the node entity at this path, or None."""
        
    def exists(self, path: str) -> bool:
        """Returns True if a node exists at this path."""
```

**Index Maintenance:**
- Updated via observer on `NodePath` component changes
- Validated on insert — duplicate paths raise `DuplicatePathError`

---

## Transform Propagation

Transforms update when changed, not on-demand. The system uses observers to track changes and propagate updates efficiently.

### Triggers

- `LocalTransform` modified on any node
- `ChildOf` relationship added, removed, or changed (reparenting)
- `AttachedTo` relationship added, removed, or changed
- `LocalOffset` modified on any entity

### Propagation Order

1. Mark dirty node and all descendants
2. Walk dirty nodes in depth-first order
3. Compute `WorldTransform = parent.WorldTransform * LocalTransform`
4. For attached entities: `entity.WorldTransform = node.WorldTransform * LocalOffset`

### Batching

Multiple changes within a single frame are batched. Propagation runs once after all changes are applied, avoiding redundant computation.

---

## Reparenting

Nodes and entities can move within or between graphs at runtime.

### Reparenting a Node

```python
# Move table from room_1 to room_2
world.remove_relationship(table_node, ChildOf(), room_1)
world.add_relationship(table_node, ChildOf(), room_2)
# Triggers:
# 1. NodePath update for table_node and all descendants
# 2. WorldTransform update for table_node and all descendants
# 3. WorldTransform update for all attached entities
```

### Detaching a Node (Create New Root)

```python
# Detach room_1 from world, making it its own graph
world.remove_relationship(room_1, ChildOf(), world_root)
# room_1 NodePath is now "/room_1" (becomes a root)
```

### Reparenting an Entity

```python
# Move chest from table to floor
world.remove_relationship(chest, AttachedTo(), table_node)
world.add_relationship(chest, AttachedTo(), floor_node)
```

### Detaching an Entity

```python
# Remove chest from scene graph entirely
world.remove_relationship(chest, AttachedTo(), table_node)
# chest no longer has WorldTransform updates
```

---

## Queries

### By Path

```python
def get_node(world: World, path: str) -> Entity | None:
    """Get node entity by path."""
    return world.scene_graph.path_index.get(path)
```

### Children of Node

```python
def get_children(world: World, node: Entity) -> list[Entity]:
    """Get all child nodes of a node."""
    return world.query_sources(ChildOf, target=node)
```

### Parent of Node

```python
def get_parent(world: World, node: Entity) -> Entity | None:
    """Get parent node, or None if root."""
    targets = world.query_targets(ChildOf, source=node)
    return targets[0] if targets else None
```

### Attached Entities

```python
def get_attached(world: World, node: Entity) -> list[Entity]:
    """Get all entities attached to a node."""
    return world.query_sources(AttachedTo, target=node)
```

### Node of Entity

```python
def get_node_of(world: World, entity: Entity) -> Entity | None:
    """Get the node an entity is attached to."""
    targets = world.query_targets(AttachedTo, source=entity)
    return targets[0] if targets else None
```

### All Roots (All Scene Graphs)

```python
def get_roots(world: World) -> list[Entity]:
    """Get all root nodes (scene graph roots)."""
    all_nodes = world.query(NodeName)
    return [n for n in all_nodes if get_parent(world, n) is None]
```

---

## Error Handling

```python
class SceneGraphError(RelicError):
    """Base exception for scene graph errors."""
    pass

class DuplicatePathError(SceneGraphError):
    """A node with this path already exists."""
    pass

class CycleDetectedError(SceneGraphError):
    """Reparenting would create a cycle in the hierarchy."""
    pass

class InvalidNodeError(SceneGraphError):
    """Entity is not a scene node (wrong prefab)."""
    pass
```

---

## Usage Example

```python
from relics import World
from relics_scene_graph import (
    NodeName, LocalTransform, LocalOffset,
    ChildOf, AttachedTo, SceneGraphSystem,
    get_node, get_attached
)

# Setup
world = World()
world.register_system(SceneGraphSystem())

# Create scene graph
root = world.spawn("_scene_node")
root.add_component(NodeName(name="world"))
root.add_component(LocalTransform.identity())

room = world.spawn("_scene_node")
room.add_component(NodeName(name="tavern"))
room.add_component(LocalTransform(position=Vec3(100, 0, 0)))
world.add_relationship(room, ChildOf(), root)
# Path: /world/tavern

table = world.spawn("_scene_node")
table.add_component(NodeName(name="table_1"))
table.add_component(LocalTransform(position=Vec3(10, 0, 5)))
world.add_relationship(table, ChildOf(), room)
# Path: /world/tavern/table_1

# Attach game entities
mug = world.spawn("mug")
mug.add_component(LocalOffset(position=Vec3(0, 1, 0)))  # On top of table
world.add_relationship(mug, AttachedTo(), table)

# Query
table_node = get_node(world, "/world/tavern/table_1")
items_on_table = get_attached(world, table_node)

# Mug's WorldTransform is now:
# root(0,0,0) + room(100,0,0) + table(10,0,5) + offset(0,1,0)
# = (110, 1, 5)
```

---

## Version Roadmap

### v0.1 (Current)
- Node hierarchy with `ChildOf` relationships
- Entity attachment with `AttachedTo` relationships
- Path-based node identification with materialized index
- Transform propagation via observers
- Reparenting support

### v0.2 (Planned)
- Transform inheritance flags (inherit position but not rotation)
- Visibility propagation (hidden parent hides children)
- Node tags/groups for batch operations
- Path wildcards for queries (`/world/*/table_*`)
