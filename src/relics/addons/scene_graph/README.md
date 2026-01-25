# Scene Graph Addon

Hierarchical transform management for Relics ECS with parent-child relationships and automatic transform propagation.

## Overview

The Scene Graph addon provides a tree-based spatial organization system where:
- **Nodes** are entities that form tree structures via parent-child relationships
- **Game entities** attach to nodes via relationships
- **World transforms** automatically propagate through the hierarchy
- **Paths** like `/world/room/table` provide O(1) node lookups

## Quick Start

```python
from relics import World
from relics.addons.scene_graph import (
    setup_scene_graph,
    create_root_node,
    create_child_node,
    LocalTransform,
    LocalOffset,
    AttachedTo,
    Vec3,
)

# Setup
world = World()
path_index = setup_scene_graph(world)

# Create scene graph
root = create_root_node(world, "world")
room = create_child_node(
    world, "tavern", root,
    local_transform=LocalTransform(position=Vec3(100, 0, 0))
)
table = create_child_node(
    world, "table", room,
    local_transform=LocalTransform(position=Vec3(10, 0, 5))
)
world.tick(0)

# Query by path
node = path_index.get("/world/tavern/table")

# Attach game entity
world.register_prefab("mug", {})
mug = world.spawn("mug")
mug.add_component(LocalOffset(position=Vec3(0, 1, 0)))  # On top of table
world.add_relationship(mug, AttachedTo(), table)
world.tick(0)

# Mug world position: (100, 0, 0) + (10, 0, 5) + (0, 1, 0) = (110, 1, 5)
```

## Components

| Component | Description |
|-----------|-------------|
| `NodeName` | Local name within parent (e.g., "table") |
| `NodePath` | Full materialized path (e.g., "/world/room/table") - managed by system |
| `LocalTransform` | Position, rotation, scale relative to parent |
| `WorldTransform` | Absolute transform in world space - managed by system |
| `LocalOffset` | Optional offset for attached entities |

## Math Types

| Type | Description |
|------|-------------|
| `Vec3` | Immutable 3D vector (x, y, z) |
| `Quat` | Immutable quaternion for rotations (x, y, z, w) |
| `Mat4` | Immutable 4x4 transformation matrix |

```python
from relics.addons.scene_graph import Vec3, Quat, Mat4
import math

# Vectors
pos = Vec3(10, 20, 30)
scaled = pos * 2.0
unit = pos.normalized()

# Quaternions
rot = Quat.from_axis_angle(Vec3.unit_y(), math.pi / 2)  # 90 deg around Y
rot2 = Quat.from_euler(0, math.pi / 4, 0)  # 45 deg around Y
combined = rot * rot2

# Matrices
mat = Mat4.from_trs(pos, rot, Vec3.one())
transformed = mat.transform_point(Vec3(1, 0, 0))
```

## Hierarchy Management

### Creating Nodes

```python
# Create root (no parent)
root = create_root_node(world, "world")

# Create child
room = create_child_node(world, "room", root)

# With custom transform
table = create_child_node(
    world, "table", room,
    local_transform=LocalTransform(
        position=Vec3(10, 0, 5),
        rotation=Quat.identity(),
        scale=Vec3.one()
    )
)
```

### Reparenting

```python
from relics.addons.scene_graph import ChildOf

# Move table from room1 to room2
world.remove_relationship(table, ChildOf(), room1)
world.add_relationship(table, ChildOf(), room2)
world.tick(0)
# Paths and transforms update automatically
```

### Detaching (Create New Root)

```python
# Detach room to become its own scene graph root
world.remove_relationship(room, ChildOf(), world_root)
world.tick(0)
# room.path is now "/room" instead of "/world/room"
```

## Entity Attachment

```python
from relics.addons.scene_graph import AttachedTo, LocalOffset, get_attached

# Attach entity to node
world.add_relationship(chest, AttachedTo(), table_node)

# With offset
chest.add_component(LocalOffset(position=Vec3(0, 1, 0)))
world.tick(0)

# Query attached entities
items = get_attached(world, table_node)

# Detach
world.remove_relationship(chest, AttachedTo(), table_node)
```

## Query Functions

```python
from relics.addons.scene_graph import (
    get_node, get_children, get_parent,
    get_attached, get_node_of, get_roots,
    get_descendants, get_ancestors,
    is_scene_node, compute_path, would_create_cycle
)

# Path lookup
node = get_node(world, "/world/room/table", path_index)

# Hierarchy traversal
children = get_children(world, room)
parent = get_parent(world, table)
roots = get_roots(world)

# Depth-first descendants
for descendant in get_descendants(world, root):
    print(descendant.get_component(NodePath).path)

# Ancestors (parent to root)
for ancestor in get_ancestors(world, leaf):
    print(ancestor.get_component(NodeName).name)

# Attachment queries
node = get_node_of(world, entity)  # What node is entity attached to?
entities = get_attached(world, node)  # What entities are attached?

# Utilities
is_node = is_scene_node(entity)  # Has NodeName?
path = compute_path(world, node)  # Compute path by traversing up
would_cycle = would_create_cycle(world, child, new_parent)
```

## Transform Propagation

Transforms update automatically via observers when:
- `LocalTransform` changes on any node
- `ChildOf` relationship added/removed (reparenting)
- `AttachedTo` relationship added/removed
- `LocalOffset` changes on attached entity

```python
# Child world transform = parent world transform * local transform
world_pos = parent_world.position + parent_world.rotation.rotate_vector(
    local.position.hadamard(parent_world.scale)
)
world_rot = parent_world.rotation * local.rotation
world_scale = parent_world.scale.hadamard(local.scale)
```

## Multiple Scene Graphs

Multiple roots create independent scene graphs:

```python
# World scene graph
world_root = create_root_node(world, "world")
room = create_child_node(world, "room", world_root)

# UI scene graph (separate coordinate space)
ui_root = create_root_node(world, "ui")
panel = create_child_node(world, "panel", ui_root)

# Each has independent paths
# /world/room
# /ui/panel
```

## API Reference

### Factory Functions

| Function | Description |
|----------|-------------|
| `setup_scene_graph(world)` | Initialize addon, returns PathIndex |
| `create_root_node(world, name)` | Create a root node (new scene graph) |
| `create_child_node(world, name, parent)` | Create child node under parent |

### PathIndex Methods

| Method | Description |
|--------|-------------|
| `get(path)` | Get Entity at path, or None |
| `exists(path)` | Check if path exists |
| `get_id(path)` | Get EntityId at path |
| `count()` | Number of indexed nodes |

### Edges

| Edge | Direction | Description |
|------|-----------|-------------|
| `ChildOf` | child → parent | Node hierarchy |
| `AttachedTo` | entity → node | Entity attachment |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `SceneGraphError` | Base exception |
| `DuplicatePathError` | Path already exists |
| `CycleDetectedError` | Reparenting would create cycle |
| `InvalidNodeError` | Entity missing NodeName |
