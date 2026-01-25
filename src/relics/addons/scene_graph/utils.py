"""Query utilities for scene graph traversal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, List, Optional

from .components import (
    LocalOffset,
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
)
from .edges import AttachedTo, ChildOf
from .types import Mat4

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World

    from .index import PathIndex


def is_scene_node(entity: "Entity") -> bool:
    """Check if an entity is a scene node.

    A scene node is any entity that has the NodeName component.

    Args:
        entity: The entity to check.

    Returns:
        True if the entity has NodeName component.
    """
    return entity.has_component(NodeName)


def get_node(world: "World", path: str, index: "PathIndex") -> Optional["Entity"]:
    """Get a node by its path using the path index.

    Args:
        world: The World to query.
        path: The full node path (e.g., "/world/room_1/table").
        index: The PathIndex to use for lookup.

    Returns:
        The Entity at that path, or None if not found.
    """
    return index.get(path)


def get_children(world: "World", node: "Entity") -> List["Entity"]:
    """Get all child nodes of a node.

    Args:
        world: The World to query.
        node: The parent node entity.

    Returns:
        List of child node entities.
    """
    # Query for entities that have (child, ChildOf, node) relationship
    incoming = node.get_incoming_relationships(ChildOf)
    return [world.get_entity(source_id) for source_id, _ in incoming]


def get_parent(world: "World", node: "Entity") -> Optional["Entity"]:
    """Get the parent node of a node.

    Args:
        world: The World to query.
        node: The child node entity.

    Returns:
        The parent Entity, or None if this is a root node.
    """
    # Query for (node, ChildOf, parent) relationship
    relationships = node.get_relationships(ChildOf)
    if not relationships:
        return None
    # A node can only have one parent
    _, target_id = relationships[0]
    return world.get_entity(target_id)


def get_attached(world: "World", node: "Entity") -> List["Entity"]:
    """Get all entities attached to a node.

    Args:
        world: The World to query.
        node: The node entity.

    Returns:
        List of entities attached to the node.
    """
    # Query for entities that have (entity, AttachedTo, node) relationship
    incoming = node.get_incoming_relationships(AttachedTo)
    return [world.get_entity(source_id) for source_id, _ in incoming]


def get_node_of(world: "World", entity: "Entity") -> Optional["Entity"]:
    """Get the node an entity is attached to.

    Args:
        world: The World to query.
        entity: The entity to check.

    Returns:
        The node Entity it's attached to, or None if not attached.
    """
    # Query for (entity, AttachedTo, node) relationship
    relationships = entity.get_relationships(AttachedTo)
    if not relationships:
        return None
    _, target_id = relationships[0]
    return world.get_entity(target_id)


def get_roots(world: "World") -> List["Entity"]:
    """Get all root nodes (scene graph roots).

    Root nodes are nodes with NodeName but no ChildOf relationship.

    Args:
        world: The World to query.

    Returns:
        List of root node entities.
    """
    roots = []
    # Get all entities with NodeName component
    for entity in world.query().with_all([NodeName]).execute_entities():
        # Check if it has no parent
        if not entity.has_relationship(ChildOf):
            roots.append(entity)
    return roots


def get_descendants(world: "World", node: "Entity") -> Iterator["Entity"]:
    """Get all descendant nodes (depth-first traversal).

    Args:
        world: The World to query.
        node: The root node to start from.

    Yields:
        Descendant node entities in depth-first order.
    """
    stack = list(get_children(world, node))
    while stack:
        current = stack.pop()
        yield current
        # Add children to stack (reversed for proper DFS order)
        children = get_children(world, current)
        stack.extend(reversed(children))


def get_ancestors(world: "World", node: "Entity") -> Iterator["Entity"]:
    """Get all ancestor nodes from parent to root.

    Args:
        world: The World to query.
        node: The node to start from.

    Yields:
        Ancestor node entities from immediate parent to root.
    """
    current = get_parent(world, node)
    while current is not None:
        yield current
        current = get_parent(world, current)


def compute_path(world: "World", node: "Entity") -> str:
    """Compute the full path for a node by traversing up to root.

    Args:
        world: The World to query.
        node: The node to compute path for.

    Returns:
        The full path string (e.g., "/world/room_1/table").
    """
    if not node.has_component(NodeName):
        return ""

    # Build path from node to root
    path_parts = [node.get_component(NodeName).name]
    current = get_parent(world, node)
    while current is not None:
        path_parts.append(current.get_component(NodeName).name)
        current = get_parent(world, current)

    # Reverse and join
    path_parts.reverse()
    return "/" + "/".join(path_parts)


def would_create_cycle(world: "World", child: "Entity", new_parent: "Entity") -> bool:
    """Check if reparenting would create a cycle.

    A cycle would be created if new_parent is the child itself
    or any of child's descendants.

    Args:
        world: The World to query.
        child: The node being reparented.
        new_parent: The proposed new parent.

    Returns:
        True if reparenting would create a cycle.
    """
    # Self-reference check
    if child.id == new_parent.id:
        return True

    # Check if new_parent is a descendant of child
    for descendant in get_descendants(world, child):
        if descendant.id == new_parent.id:
            return True

    return False


def compute_world_transform(
    local: LocalTransform,
    parent_world: Optional[WorldTransform],
) -> WorldTransform:
    """Compute world transform from local transform and parent's world transform.

    Args:
        local: The local transform.
        parent_world: The parent's world transform, or None if root.

    Returns:
        The computed world transform.
    """
    if parent_world is None:
        # Root node - world transform equals local transform
        return WorldTransform(
            position=local.position,
            rotation=local.rotation,
            scale=local.scale,
            matrix=Mat4.from_trs(local.position, local.rotation, local.scale),
        )

    # Combine with parent transform
    # World position = parent_pos + parent_rot * (parent_scale * local_pos)
    scaled_local = local.position.hadamard(parent_world.scale)
    rotated = parent_world.rotation.rotate_vector(scaled_local)
    world_position = parent_world.position + rotated

    # World rotation = parent_rotation * local_rotation
    world_rotation = parent_world.rotation * local.rotation

    # World scale = parent_scale * local_scale (component-wise)
    world_scale = parent_world.scale.hadamard(local.scale)

    # Compute matrix
    world_matrix = Mat4.from_trs(world_position, world_rotation, world_scale)

    return WorldTransform(
        position=world_position,
        rotation=world_rotation,
        scale=world_scale,
        matrix=world_matrix,
    )


def compute_attached_transform(
    node_world: WorldTransform,
    offset: Optional[LocalOffset],
) -> WorldTransform:
    """Compute world transform for an entity attached to a node.

    Args:
        node_world: The node's world transform.
        offset: The entity's local offset, or None for identity.

    Returns:
        The computed world transform for the attached entity.
    """
    if offset is None:
        return node_world

    # Apply offset similar to local transform computation
    scaled_offset = offset.position.hadamard(node_world.scale)
    rotated = node_world.rotation.rotate_vector(scaled_offset)
    world_position = node_world.position + rotated

    world_rotation = node_world.rotation * offset.rotation
    world_scale = node_world.scale.hadamard(offset.scale)
    world_matrix = Mat4.from_trs(world_position, world_rotation, world_scale)

    return WorldTransform(
        position=world_position,
        rotation=world_rotation,
        scale=world_scale,
        matrix=world_matrix,
    )


def propagate_transforms(world: "World", node: "Entity") -> None:
    """Propagate transform updates to a node and all its descendants.

    This updates WorldTransform for the node, all descendant nodes,
    and all entities attached to affected nodes.

    Args:
        world: The World containing the nodes.
        node: The node whose transform changed.
    """
    # Update the node's world transform
    _update_node_world_transform(world, node)

    # Update all descendants
    for descendant in get_descendants(world, node):
        _update_node_world_transform(world, descendant)


def _update_node_world_transform(world: "World", node: "Entity") -> None:
    """Update a single node's world transform and attached entities.

    Args:
        world: The World containing the node.
        node: The node to update.
    """
    # Get local transform (or identity if not present)
    if node.has_component(LocalTransform):
        local = node.get_component(LocalTransform)
    else:
        local = LocalTransform.identity()

    # Get parent's world transform
    parent = get_parent(world, node)
    parent_world = None
    if parent is not None and parent.has_component(WorldTransform):
        parent_world = parent.get_component(WorldTransform)

    # Compute and set world transform
    new_world = compute_world_transform(local, parent_world)

    if node.has_component(WorldTransform):
        wt = node.get_component(WorldTransform)
        wt.position = new_world.position
        wt.rotation = new_world.rotation
        wt.scale = new_world.scale
        wt.matrix = new_world.matrix
    else:
        node.add_component(new_world)

    # Update attached entities
    _update_attached_entities(world, node)


def _update_attached_entities(world: "World", node: "Entity") -> None:
    """Update WorldTransform for all entities attached to a node.

    Args:
        world: The World containing the entities.
        node: The node they are attached to.
    """
    if not node.has_component(WorldTransform):
        return

    node_world = node.get_component(WorldTransform)

    for entity in get_attached(world, node):
        # Get local offset if present
        offset = None
        if entity.has_component(LocalOffset):
            offset = entity.get_component(LocalOffset)

        new_world = compute_attached_transform(node_world, offset)

        if entity.has_component(WorldTransform):
            wt = entity.get_component(WorldTransform)
            wt.position = new_world.position
            wt.rotation = new_world.rotation
            wt.scale = new_world.scale
            wt.matrix = new_world.matrix
        else:
            entity.add_component(new_world)


def update_node_path(world: "World", node: "Entity") -> str:
    """Update a node's path based on its current hierarchy position.

    Args:
        world: The World containing the node.
        node: The node to update.

    Returns:
        The new path.
    """
    new_path = compute_path(world, node)

    if node.has_component(NodePath):
        node_path = node.get_component(NodePath)
        node_path.path = new_path
    else:
        node.add_component(NodePath(path=new_path))

    return new_path


def update_descendant_paths(world: "World", node: "Entity") -> None:
    """Update paths for a node and all its descendants.

    Args:
        world: The World containing the nodes.
        node: The node whose path changed.
    """
    update_node_path(world, node)
    for descendant in get_descendants(world, node):
        update_node_path(world, descendant)
