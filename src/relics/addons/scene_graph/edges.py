"""Scene graph edge types for hierarchy and attachment relationships."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic.dataclasses

from relics.types import Edge

if TYPE_CHECKING:
    from relics.entity import Entity


@pydantic.dataclasses.dataclass
class ChildOf(Edge):
    """Node hierarchy relationship (child -> parent).

    This edge connects a child node to its parent node.
    Direction: (child_node, ChildOf, parent_node)

    The scene graph system uses this relationship to:
    - Build and maintain node paths
    - Propagate transforms through the hierarchy
    - Detect cycles during reparenting

    Example:
        # room_1 is a child of world_root
        world.add_relationship(room_1, ChildOf(), world_root)
    """

    def validate(self, source: "Entity", target: "Entity") -> bool:
        """Validate the parent-child relationship.

        Prevents:
        - Self-reference (node cannot be its own parent)
        - Cycles (target cannot be a descendant of source)

        Note: Full cycle detection is handled by the scene graph
        utilities since it requires traversing the hierarchy.

        Args:
            source: The child node entity.
            target: The parent node entity.

        Returns:
            True if the relationship is valid.
        """
        # Prevent self-reference
        if source.id == target.id:
            return False
        return True


@pydantic.dataclasses.dataclass
class AttachedTo(Edge):
    """Entity-to-node attachment relationship.

    This edge connects a game entity to a scene node. The entity's
    WorldTransform will be updated based on the node's WorldTransform
    plus any LocalOffset component on the entity.

    Direction: (entity, AttachedTo, node)

    Example:
        # Attach a chest entity to a table node
        world.add_relationship(chest, AttachedTo(), table_node)
    """

    pass
