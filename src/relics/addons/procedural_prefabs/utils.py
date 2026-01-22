"""Utility functions for procedural prefabs."""

from typing import TYPE_CHECKING, Iterator, List, Optional, Tuple, Type

from relics.types import Edge, EntityId

from relics.addons.procedural_prefabs.edges import (
    HasAttached,
    HasEquipped,
    IsWearing,
)

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World

# Default edge types to consider for attachment operations
DEFAULT_EDGE_TYPES: List[Type[Edge]] = [HasEquipped, IsWearing, HasAttached]


def get_children(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> Iterator["Entity"]:
    """Get child entities attached to this entity.

    Args:
        entity: Parent entity.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Yields:
        Child entities.
    """
    for child_id in get_child_ids(entity, edge_type):
        yield entity._world.get_entity(child_id)


def get_child_ids(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> Iterator[EntityId]:
    """Get IDs of child entities attached to this entity.

    Args:
        entity: Parent entity.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Yields:
        Child entity IDs.
    """
    edge_types = [edge_type] if edge_type else DEFAULT_EDGE_TYPES

    for et in edge_types:
        for edge, target_id in entity.get_relationships(et):
            yield target_id


def get_holder(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> Optional["Entity"]:
    """Get the parent entity holding this entity.

    Args:
        entity: Child entity.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Returns:
        Parent entity or None if not attached.
    """
    holder_id = get_holder_id(entity, edge_type)
    if holder_id is not None:
        return entity._world.get_entity(holder_id)
    return None


def get_holder_id(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> Optional[EntityId]:
    """Get the ID of the parent entity holding this entity.

    Args:
        entity: Child entity.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Returns:
        Parent entity ID or None if not attached.
    """
    edge_types = [edge_type] if edge_type else DEFAULT_EDGE_TYPES

    for et in edge_types:
        incoming = entity.get_incoming_relationships(et)
        if incoming:
            # Return first holder found
            source_id, edge = incoming[0]
            return source_id

    return None


def detach(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> Optional[Tuple[EntityId, Edge]]:
    """Detach an entity from its holder.

    Removes the incoming attachment relationship.

    Args:
        entity: Entity to detach.
        edge_type: Specific edge type to detach (None = all attachment types).

    Returns:
        Tuple of (holder_id, edge) if detached, None if not attached.
    """
    edge_types = [edge_type] if edge_type else DEFAULT_EDGE_TYPES

    for et in edge_types:
        incoming = entity.get_incoming_relationships(et)
        for source_id, edge in incoming:
            # Get holder entity
            holder = entity._world.get_entity(source_id)
            # Remove relationship
            holder.remove_relationship(et, entity.id)
            return (source_id, edge)

    return None


def destroy_with_children(
    world: "World",
    entity: "Entity",
    recursive: bool = True,
) -> int:
    """Destroy an entity and all its attached children.

    Args:
        world: World containing the entities.
        entity: Entity to destroy.
        recursive: If True, also destroy children's children.

    Returns:
        Number of entities destroyed.
    """
    count = 0

    # Get all children first to avoid modification during iteration
    children = list(get_children(entity))

    if recursive:
        # Recursively destroy children
        for child in children:
            count += destroy_with_children(world, child, recursive=True)
    else:
        # Just destroy immediate children
        for child in children:
            world.remove(child)
            count += 1

    # Destroy the entity itself
    world.remove(entity)
    count += 1

    return count


def get_children_recursive(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> Iterator["Entity"]:
    """Get all descendant entities via depth-first traversal.

    Args:
        entity: Root entity.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Yields:
        All descendant entities.
    """
    for child in get_children(entity, edge_type):
        yield child
        yield from get_children_recursive(child, edge_type)


def get_all_children_ids(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> List[EntityId]:
    """Get IDs of all descendant entities.

    Args:
        entity: Root entity.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Returns:
        List of all descendant entity IDs.
    """
    return [child.id for child in get_children_recursive(entity, edge_type)]


def get_root(
    entity: "Entity",
    edge_type: Optional[Type[Edge]] = None,
) -> "Entity":
    """Get the root entity in an attachment hierarchy.

    Traverses up through holders until finding an entity with no holder.

    Args:
        entity: Entity to start from.
        edge_type: Specific edge type to filter by (None = all attachment types).

    Returns:
        Root entity (may be the same entity if not attached).
    """
    current = entity

    while True:
        holder = get_holder(current, edge_type)
        if holder is None:
            return current
        current = holder


def get_slot(entity: "Entity") -> Optional[str]:
    """Get the slot name this entity is attached to.

    Args:
        entity: Entity to check.

    Returns:
        Slot name or None if not attached.
    """
    for et in DEFAULT_EDGE_TYPES:
        incoming = entity.get_incoming_relationships(et)
        for source_id, edge in incoming:
            if hasattr(edge, "slot"):
                return str(edge.slot)

    return None
