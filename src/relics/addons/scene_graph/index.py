"""PathIndex for O(1) path-to-node lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterator, Optional, Set, cast

from relics.index import IndexView

from .components import NodePath
from .exceptions import DuplicatePathError

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.types import EntityId
    from relics.world import World


class PathIndex(IndexView):
    """Materialized index mapping paths to node entities.

    Provides O(1) lookup from path string to node entity ID.
    Automatically maintained via observers on NodePath component.

    The index uses lazy initialization - it will rebuild from
    the current world state on first access.
    """

    def __init__(self, world: "World") -> None:
        """Initialize the path index.

        Args:
            world: The World to index.
        """
        self._world = world
        self._path_to_entity: Dict[str, "EntityId"] = {}
        self._entity_to_path: Dict["EntityId", str] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize the index from current world state if needed."""
        if not self._initialized:
            self._rebuild()
            self._initialized = True

    def _rebuild(self) -> None:
        """Rebuild the index from current world state."""
        self._path_to_entity.clear()
        self._entity_to_path.clear()

        for entity_id, components in self._world._entities.items():
            if NodePath in components:
                node_path = cast(NodePath, components[NodePath])
                # Bind monitored components for change tracking
                if hasattr(node_path, "_bind_to_world"):
                    node_path._bind_to_world(self._world, entity_id)
                path = node_path.path
                self._path_to_entity[path] = entity_id
                self._entity_to_path[entity_id] = path

    def get(self, path: str) -> Optional["Entity"]:
        """Get node entity at the given path.

        Args:
            path: The full node path (e.g., "/world/room_1/table").

        Returns:
            The Entity at that path, or None if not found.
        """
        self._ensure_initialized()
        entity_id = self._path_to_entity.get(path)
        if entity_id is None:
            return None
        return self._world.get_entity(entity_id)

    def get_id(self, path: str) -> Optional["EntityId"]:
        """Get node entity ID at the given path.

        Args:
            path: The full node path (e.g., "/world/room_1/table").

        Returns:
            The EntityId at that path, or None if not found.
        """
        self._ensure_initialized()
        return self._path_to_entity.get(path)

    def exists(self, path: str) -> bool:
        """Check if a node exists at the given path.

        Args:
            path: The full node path.

        Returns:
            True if a node exists at the path.
        """
        self._ensure_initialized()
        return path in self._path_to_entity

    def get_path(self, entity_id: "EntityId") -> Optional[str]:
        """Get the path for an entity.

        Args:
            entity_id: The entity ID.

        Returns:
            The path, or None if entity is not in the index.
        """
        self._ensure_initialized()
        return self._entity_to_path.get(entity_id)

    def add_node(self, entity_id: "EntityId", path: str) -> None:
        """Add or update a node in the index.

        Args:
            entity_id: The node's entity ID.
            path: The node's path.

        Raises:
            DuplicatePathError: If the path is already used by another node.
        """
        self._ensure_initialized()

        # Check for duplicate path (different entity)
        existing = self._path_to_entity.get(path)
        if existing is not None and existing != entity_id:
            raise DuplicatePathError(path)

        # Remove old path if entity was already indexed
        old_path = self._entity_to_path.get(entity_id)
        if old_path is not None and old_path != path:
            del self._path_to_entity[old_path]

        self._path_to_entity[path] = entity_id
        self._entity_to_path[entity_id] = path

    def remove_node(self, entity_id: "EntityId") -> None:
        """Remove a node from the index.

        Args:
            entity_id: The node's entity ID.
        """
        self._ensure_initialized()

        path = self._entity_to_path.pop(entity_id, None)
        if path is not None:
            self._path_to_entity.pop(path, None)

    def update_path(self, entity_id: "EntityId", old_path: str, new_path: str) -> None:
        """Update the path for a node.

        Args:
            entity_id: The node's entity ID.
            old_path: The previous path.
            new_path: The new path.

        Raises:
            DuplicatePathError: If the new path is already used by another node.
        """
        self._ensure_initialized()

        # Check for duplicate new path
        existing = self._path_to_entity.get(new_path)
        if existing is not None and existing != entity_id:
            raise DuplicatePathError(new_path)

        # Remove old path
        self._path_to_entity.pop(old_path, None)

        # Add new path
        self._path_to_entity[new_path] = entity_id
        self._entity_to_path[entity_id] = new_path

    def invalidate(self) -> None:
        """Invalidate the index, forcing a rebuild on next access."""
        self._initialized = False
        self._path_to_entity.clear()
        self._entity_to_path.clear()

    # IndexView interface

    def __iter__(self) -> Iterator["Entity"]:
        """Iterate over all indexed node entities."""
        self._ensure_initialized()
        for entity_id in self._entity_to_path:
            entity = self._world.get_entity(entity_id)
            if entity is not None:
                yield entity

    def count(self) -> int:
        """Get the number of indexed nodes."""
        self._ensure_initialized()
        return len(self._path_to_entity)

    def get_entity_ids(self) -> Set["EntityId"]:
        """Get the set of all indexed entity IDs."""
        self._ensure_initialized()
        return set(self._entity_to_path.keys())
