"""Scene Graph addon for hierarchical transform management.

This addon provides a scene graph system where nodes are entities
forming tree structures, with game entities attached to nodes via
relationships. World transforms propagate through the hierarchy.

Quick Start:
    from relics import World
    from relics.addons.scene_graph import (
        setup_scene_graph,
        NodeName, LocalTransform, Vec3, Quat,
        ChildOf, AttachedTo,
        get_node, get_children,
    )

    # Setup
    world = World()
    path_index = setup_scene_graph(world)

    # Create root node
    root = world.spawn("_scene_node")
    root.add_component(NodeName(name="world"))
    root.add_component(LocalTransform.identity())

    # Create child node
    room = world.spawn("_scene_node")
    room.add_component(NodeName(name="tavern"))
    room.add_component(LocalTransform(position=Vec3(100, 0, 0)))
    world.add_relationship(room, ChildOf(), root)
    # Path is now "/world/tavern"

    # Query by path
    node = path_index.get("/world/tavern")

    # Attach game entities
    mug = world.spawn("mug")
    world.add_relationship(mug, AttachedTo(), room)
"""

# Components
from .components import (
    LocalOffset,
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
)

# Edges
from .edges import AttachedTo, ChildOf

# Exceptions
from .exceptions import (
    CycleDetectedError,
    DuplicatePathError,
    InvalidNodeError,
    SceneGraphError,
)

# Factory
from .factory import (
    SCENE_NODE_PREFAB,
    create_child_node,
    create_root_node,
    setup_scene_graph,
)

# Index
from .index import PathIndex

# Observers
from .observer import (
    AttachmentObserver,
    LocalOffsetObserver,
    LocalTransformObserver,
    NodeHierarchyObserver,
    NodeNameObserver,
    PathIndexObserver,
    WorldTransformObserver,
    create_all_observers,
)

# Types
from .types import NUMPY_AVAILABLE, Mat4, Quat, QuatLike, Vec3, Vec3Like

# Utilities
from .utils import (
    compute_attached_transform,
    compute_path,
    compute_world_transform,
    get_ancestors,
    get_attached,
    get_children,
    get_descendants,
    get_node,
    get_node_of,
    get_parent,
    get_roots,
    is_scene_node,
    propagate_transforms,
    update_descendant_paths,
    update_node_path,
    would_create_cycle,
)

__all__ = [
    # Types
    "Vec3",
    "Vec3Like",
    "Quat",
    "QuatLike",
    "Mat4",
    "NUMPY_AVAILABLE",
    # Components
    "NodeName",
    "NodePath",
    "LocalTransform",
    "WorldTransform",
    "LocalOffset",
    # Edges
    "ChildOf",
    "AttachedTo",
    # Exceptions
    "SceneGraphError",
    "DuplicatePathError",
    "CycleDetectedError",
    "InvalidNodeError",
    # Index
    "PathIndex",
    # Factory
    "SCENE_NODE_PREFAB",
    "setup_scene_graph",
    "create_root_node",
    "create_child_node",
    # Utilities
    "is_scene_node",
    "get_node",
    "get_children",
    "get_parent",
    "get_attached",
    "get_node_of",
    "get_roots",
    "get_descendants",
    "get_ancestors",
    "compute_path",
    "would_create_cycle",
    "compute_world_transform",
    "compute_attached_transform",
    "propagate_transforms",
    "update_node_path",
    "update_descendant_paths",
    # Observers
    "PathIndexObserver",
    "NodeNameObserver",
    "NodeHierarchyObserver",
    "LocalTransformObserver",
    "AttachmentObserver",
    "LocalOffsetObserver",
    "WorldTransformObserver",
    "create_all_observers",
]
