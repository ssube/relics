"""Observers for maintaining scene graph consistency."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Type, cast

from relics.observer import ComponentObserver, RelationshipObserver
from relics.types import Component, Edge

from .components import (
    LocalOffset,
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
)
from .edges import AttachedTo, ChildOf
from .utils import (
    _update_attached_entities,
    _update_node_world_transform,
    compute_path,
    propagate_transforms,
    update_descendant_paths,
)

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.observer import Observer

    from .index import PathIndex


class PathIndexObserver(ComponentObserver):
    """Maintains PathIndex when NodePath components change.

    This observer keeps the path index synchronized with the world
    state by tracking NodePath additions, changes, and removals.
    """

    component_type: ClassVar[Type[Component]] = NodePath

    def __init__(self, index: "PathIndex") -> None:
        """Initialize the observer.

        Args:
            index: The PathIndex to maintain.
        """
        super().__init__()
        self._index = index

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle NodePath addition."""
        path_comp = cast(NodePath, component)
        # Bind for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)
        self._index.add_node(entity.id, path_comp.path)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle NodePath change."""
        if field_name == "path":
            self._index.update_path(entity.id, old_value, new_value)

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle NodePath removal."""
        self._index.remove_node(entity.id)


class NodeNameObserver(ComponentObserver):
    """Updates NodePath when NodeName is added or changed.

    This observer ensures that adding or renaming a node triggers
    path updates for the node and all its descendants.
    """

    component_type: ClassVar[Type[Component]] = NodeName

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle NodeName addition - compute and set initial path."""
        # Bind for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)

        # Compute and set the path
        path = compute_path(self.world, entity)
        if entity.has_component(NodePath):
            entity.get_component(NodePath).path = path
        else:
            entity.add_component(NodePath(path=path))

        # Also set up world transform if local transform exists
        if entity.has_component(LocalTransform):
            _update_node_world_transform(self.world, entity)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle NodeName change - update paths for this node and descendants."""
        if field_name == "name":
            update_descendant_paths(self.world, entity)


class NodeHierarchyObserver(RelationshipObserver):
    """Updates NodePath and WorldTransform on ChildOf relationship changes.

    This observer handles reparenting operations, ensuring that:
    - Node paths are updated for the moved node and all descendants
    - World transforms are propagated through the new hierarchy
    """

    edge_type: ClassVar[Type[Edge]] = ChildOf

    def on_relationship_added(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle ChildOf addition (node gained a parent)."""
        # source is the child, target is the parent
        # Update paths for child and all its descendants
        update_descendant_paths(self.world, source)

        # Propagate transforms
        propagate_transforms(self.world, source)

    def on_relationship_removed(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle ChildOf removal (node lost a parent, becoming a root)."""
        # source is the child that was detached
        # Update paths (now becomes a root)
        update_descendant_paths(self.world, source)

        # Propagate transforms (now relative to world origin)
        propagate_transforms(self.world, source)


class LocalTransformObserver(ComponentObserver):
    """Propagates WorldTransform when LocalTransform changes.

    This observer ensures that changes to a node's local transform
    are propagated to its world transform and all descendants.
    """

    component_type: ClassVar[Type[Component]] = LocalTransform

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle LocalTransform addition."""
        # Bind for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)

        # Only update if this is a scene node
        if entity.has_component(NodeName):
            propagate_transforms(self.world, entity)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle LocalTransform change."""
        # Only propagate if this is a scene node
        if entity.has_component(NodeName):
            propagate_transforms(self.world, entity)


class AttachmentObserver(RelationshipObserver):
    """Updates attached entity transforms when AttachedTo relationships change.

    This observer handles entity attachment/detachment, ensuring that
    attached entities have their WorldTransform updated based on the
    node they're attached to.
    """

    edge_type: ClassVar[Type[Edge]] = AttachedTo

    def on_relationship_added(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle AttachedTo addition (entity attached to node)."""
        # source is the entity, target is the node
        if target.has_component(WorldTransform):
            _update_attached_entities(self.world, target)

    def on_relationship_removed(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle AttachedTo removal (entity detached from node)."""
        # source is the entity that was detached
        # The entity now has no automatic transform updates
        # Could optionally remove WorldTransform here
        pass


class LocalOffsetObserver(ComponentObserver):
    """Updates WorldTransform when LocalOffset changes on attached entities.

    This observer ensures that changes to an entity's local offset
    are reflected in its world transform.
    """

    component_type: ClassVar[Type[Component]] = LocalOffset

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle LocalOffset addition."""
        # Bind for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)

        # Update transform if attached to a node
        self._update_attached_entity(entity)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle LocalOffset change."""
        self._update_attached_entity(entity)

    def _update_attached_entity(self, entity: "Entity") -> None:
        """Update the entity's world transform based on its attachment."""
        from .utils import compute_attached_transform, get_node_of

        node = get_node_of(self.world, entity)
        if node is None or not node.has_component(WorldTransform):
            return

        node_world = node.get_component(WorldTransform)
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


class WorldTransformObserver(ComponentObserver):
    """Propagates WorldTransform changes to attached entities.

    This observer ensures that when a node's WorldTransform changes
    (which can happen from various sources), attached entities are
    also updated.
    """

    component_type: ClassVar[Type[Component]] = WorldTransform

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle WorldTransform addition."""
        # Bind for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle WorldTransform change - update attached entities."""
        # Only update attached entities if this is a scene node
        if entity.has_component(NodeName):
            _update_attached_entities(self.world, entity)


def create_all_observers(index: "PathIndex") -> list["Observer"]:
    """Create all scene graph observers.

    Args:
        index: The PathIndex to maintain.

    Returns:
        List of observer instances.
    """
    return [
        PathIndexObserver(index),
        NodeNameObserver(),
        NodeHierarchyObserver(),
        LocalTransformObserver(),
        AttachmentObserver(),
        LocalOffsetObserver(),
        WorldTransformObserver(),
    ]
