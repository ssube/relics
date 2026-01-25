"""Factory function for setting up scene graph addon."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .components import LocalTransform, NodeName
from .index import PathIndex
from .observer import create_all_observers

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World

# Reserved prefab name for scene nodes
SCENE_NODE_PREFAB = "_scene_node"


def setup_scene_graph(
    world: "World",
    *,
    auto_register_observers: bool = True,
    register_prefab: bool = True,
) -> PathIndex:
    """Set up the scene graph addon for a world.

    This function:
    - Optionally registers the _scene_node prefab with default components
    - Creates a PathIndex for O(1) path lookups
    - Optionally registers all scene graph observers

    Args:
        world: The World to set up.
        auto_register_observers: If True, register all scene graph observers.
        register_prefab: If True, register the _scene_node prefab.

    Returns:
        The PathIndex for path-based queries.

    Example:
        world = World()
        path_index = setup_scene_graph(world)

        # Create a root node
        root = world.spawn("_scene_node")
        root.add_component(NodeName(name="world"))
        root.add_component(LocalTransform.identity())

        # Query by path
        node = path_index.get("/world")
    """
    # Create the path index
    index = PathIndex(world)

    # Register the scene node prefab
    if register_prefab:
        world.register_prefab(
            SCENE_NODE_PREFAB,
            {
                # Basic components included in prefab
                # NodeName and LocalTransform will typically be added after spawn
            },
        )

    # Register observers
    if auto_register_observers:
        observers = create_all_observers(index)
        for observer in observers:
            world.observe(observer)

    return index


def create_root_node(
    world: "World",
    name: str,
    *,
    use_prefab: bool = True,
) -> "Entity":
    """Create a root scene node.

    A root node is a node with no parent. Multiple root nodes
    create multiple independent scene graphs.

    Args:
        world: The World to create the node in.
        name: The name for this root node (e.g., "world", "ui").
        use_prefab: If True, spawn from _scene_node prefab.

    Returns:
        The created root node entity.

    Example:
        # Create main scene graph
        root = create_root_node(world, "world")

        # Create UI scene graph
        ui_root = create_root_node(world, "ui")
    """
    if use_prefab:
        entity = world.spawn(SCENE_NODE_PREFAB)
    else:
        # Create a minimal entity without prefab
        entity = world.spawn("_scene_node")

    # Add node name (triggers path computation via observer)
    entity.add_component(NodeName(name=name))

    # Add identity transform
    entity.add_component(LocalTransform.identity())

    return entity


def create_child_node(
    world: "World",
    name: str,
    parent: "Entity",
    *,
    local_transform: "LocalTransform | None" = None,
    use_prefab: bool = True,
) -> "Entity":
    """Create a child node attached to a parent.

    Args:
        world: The World to create the node in.
        name: The local name for this node.
        parent: The parent node entity.
        local_transform: Optional local transform. Uses identity if None.
        use_prefab: If True, spawn from _scene_node prefab.

    Returns:
        The created child node entity.

    Example:
        room = create_child_node(world, "room_1", root)
        table = create_child_node(
            world, "table",
            room,
            local_transform=LocalTransform(position=Vec3(10, 0, 5))
        )
    """
    from .edges import ChildOf

    if use_prefab:
        entity = world.spawn(SCENE_NODE_PREFAB)
    else:
        entity = world.spawn("_scene_node")

    # Add node name
    entity.add_component(NodeName(name=name))

    # Add local transform
    if local_transform is None:
        entity.add_component(LocalTransform.identity())
    else:
        entity.add_component(local_transform)

    # Add parent relationship (triggers path and transform updates via observers)
    entity.add_relationship(ChildOf(), parent.id)

    return entity
