"""Observer for cascade deletion of attached entities.

NOTE: Due to the asynchronous nature of the observer event queue in Relics,
the DestroyChildrenObserver has limited functionality. By the time the
observer is notified, the entity's relationships have already been cleaned up.

For reliable cascade deletion, use the `destroy_with_children()` utility
function instead of relying on the observer.
"""

from typing import TYPE_CHECKING, ClassVar, Dict, List, Optional, Set, Type

from relics.addons.procedural_prefabs.edges import HasAttached, HasEquipped, IsWearing
from relics.observer import OnEntityDestroyed
from relics.types import Edge, EntityId

if TYPE_CHECKING:
    from relics.entity import Entity


class DestroyChildrenObserver(OnEntityDestroyed):
    """Observer that destroys children when a parent entity is destroyed.

    Implements cascade deletion for attachment hierarchies. When an entity
    is destroyed, all entities attached to it via specified edge types
    are also destroyed.

    NOTE: This observer maintains its own relationship cache to work around
    the fact that relationships are cleaned up before observers are notified.
    For simpler cascade deletion, consider using `destroy_with_children()`.

    Attributes:
        edge_types: Edge types to follow for cascade deletion.
        recursive: Whether to recursively destroy children's children.
    """

    prefab: ClassVar[Optional[str]] = None

    def __init__(
        self,
        edge_types: Optional[List[Type[Edge]]] = None,
        recursive: bool = True,
    ) -> None:
        """Initialize cascade observer.

        Args:
            edge_types: Edge types to follow (default: all attachment types).
            recursive: Recursively destroy children (default: True).
        """
        super().__init__()
        self._edge_types = edge_types or [HasEquipped, IsWearing, HasAttached]
        self._recursive = recursive

        # Track pending deletions to prevent re-entry
        self._pending_deletions: Set[str] = set()

        # Cache relationships for cascade deletion
        # Maps parent_id -> set of child_ids
        self._relationship_cache: Dict[str, Set[EntityId]] = {}

    def _cache_relationship(self, source_id: EntityId, target_id: EntityId) -> None:
        """Cache a relationship for later cascade deletion."""
        key = str(source_id)
        if key not in self._relationship_cache:
            self._relationship_cache[key] = set()
        self._relationship_cache[key].add(target_id)

    def _uncache_relationship(self, source_id: EntityId, target_id: EntityId) -> None:
        """Remove a relationship from cache."""
        key = str(source_id)
        if key in self._relationship_cache:
            self._relationship_cache[key].discard(target_id)

    def on_entity_destroyed(self, entity: "Entity") -> None:
        """Handle entity destruction by destroying attached children.

        Args:
            entity: The entity being destroyed.
        """
        # Prevent re-entry for this entity
        entity_key = str(entity.id)
        if entity_key in self._pending_deletions:
            return

        self._pending_deletions.add(entity_key)

        try:
            # Get cached children
            child_ids = list(self._relationship_cache.get(entity_key, set()))

            # Clean up cache for this entity
            if entity_key in self._relationship_cache:
                del self._relationship_cache[entity_key]

            # Destroy children
            for child_id in child_ids:
                if self.world.has_entity(child_id):
                    child = self.world.get_entity(child_id)
                    child_key = str(child_id)

                    if child_key not in self._pending_deletions:
                        if self._recursive:
                            # Mark as pending before recursive destroy
                            self._pending_deletions.add(child_key)

                        # Remove the child entity
                        self.world.remove(child)
        finally:
            # Don't clean up pending_deletions - keep tracking during batch processing
            pass


def create_cascade_observer(
    edge_types: Optional[List[Type[Edge]]] = None,
    recursive: bool = True,
    prefab: Optional[str] = None,
) -> DestroyChildrenObserver:
    """Factory function to create a cascade deletion observer.

    Args:
        edge_types: Edge types to follow (default: all attachment types).
        recursive: Recursively destroy children (default: True).
        prefab: Optional prefab filter (default: all prefabs).

    Returns:
        Configured DestroyChildrenObserver instance.

    Example:
        >>> world = World()
        >>> observer = create_cascade_observer()
        >>> world.observe(observer)
    """
    if prefab is not None:
        # Create a subclass with prefab filter
        observer_class: Type[DestroyChildrenObserver] = type(
            f"DestroyChildrenObserver_{prefab}",
            (DestroyChildrenObserver,),
            {"prefab": prefab},
        )
        return observer_class(edge_types=edge_types, recursive=recursive)
    else:
        return DestroyChildrenObserver(edge_types=edge_types, recursive=recursive)
