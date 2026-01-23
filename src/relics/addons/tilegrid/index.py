"""Chunk index implementation for efficient chunk lookup.

Provides O(1) chunk lookup by grid position using a materialized index.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterator, Optional, Set, Tuple, cast

from relics.entity import Entity
from relics.index import IndexView
from relics.types import EntityId

from .components import ChunkMetadata
from .utilities import world_to_chunk_index

if TYPE_CHECKING:
    from relics.world import World


class ChunkIndex(IndexView):
    """Materialized index for O(1) chunk lookup by grid position.

    Maintains a mapping from grid indices to entity IDs for fast
    chunk lookups. Uses lazy initialization to defer initial build
    until first access.

    Attributes:
        chunk_size: Number of tiles per chunk edge.
    """

    def __init__(self, world: "World", chunk_size: int) -> None:
        """Create a chunk index.

        Args:
            world: The World containing chunk entities.
            chunk_size: Number of tiles per chunk edge.
        """
        self._world = world
        self._chunk_size = chunk_size
        self._grid_to_entity: Dict[Tuple[int, ...], EntityId] = {}
        self._initialized = False

    @property
    def chunk_size(self) -> int:
        """Get the chunk size for this index."""
        return self._chunk_size

    def _ensure_initialized(self) -> None:
        """Initialize the index if not already done."""
        if not self._initialized:
            self._rebuild()
            self._initialized = True

    def _rebuild(self) -> None:
        """Rebuild the index from the current world state.

        Also binds monitored components for change tracking.
        """
        self._grid_to_entity.clear()
        for entity_id, components in self._world._entities.items():
            if ChunkMetadata in components:
                component = cast(ChunkMetadata, components[ChunkMetadata])
                # Bind monitored components to world for change tracking
                if hasattr(component, "_bind_to_world"):
                    component._bind_to_world(self._world, entity_id)
                grid_index = component.grid_index
                self._grid_to_entity[grid_index] = entity_id

    def invalidate(self) -> None:
        """Invalidate the index, forcing a full rebuild on next access."""
        self._initialized = False
        self._grid_to_entity.clear()

    def get_chunk_by_grid(self, grid_x: int, grid_y: int) -> Optional[Entity]:
        """Get chunk entity by grid coordinates.

        Args:
            grid_x: Grid X index.
            grid_y: Grid Y index.

        Returns:
            Entity handle if chunk exists, None otherwise.
        """
        self._ensure_initialized()
        grid_index = (grid_x, grid_y)
        entity_id = self._grid_to_entity.get(grid_index)
        if entity_id is not None and entity_id in self._world._entities:
            return Entity(self._world, entity_id)
        return None

    def get_chunk_by_grid_3d(
        self, grid_x: int, grid_y: int, grid_z: int
    ) -> Optional[Entity]:
        """Get chunk entity by 3D grid coordinates.

        Args:
            grid_x: Grid X index.
            grid_y: Grid Y index.
            grid_z: Grid Z index.

        Returns:
            Entity handle if chunk exists, None otherwise.
        """
        self._ensure_initialized()
        grid_index = (grid_x, grid_y, grid_z)
        entity_id = self._grid_to_entity.get(grid_index)
        if entity_id is not None and entity_id in self._world._entities:
            return Entity(self._world, entity_id)
        return None

    def get_chunk_at_world_pos(self, x: float, y: float) -> Optional[Entity]:
        """Get chunk entity containing a world position.

        Args:
            x: World X coordinate.
            y: World Y coordinate.

        Returns:
            Entity handle if chunk exists, None otherwise.
        """
        grid_x, grid_y = world_to_chunk_index(x, y, self._chunk_size)
        return self.get_chunk_by_grid(grid_x, grid_y)

    def add_chunk(self, entity_id: EntityId) -> None:
        """Add a chunk entity to the index.

        Args:
            entity_id: The entity ID to add.
        """
        self._ensure_initialized()
        if entity_id in self._world._entities:
            components = self._world._entities[entity_id]
            if ChunkMetadata in components:
                component = cast(ChunkMetadata, components[ChunkMetadata])
                grid_index = component.grid_index
                self._grid_to_entity[grid_index] = entity_id

    def remove_chunk(self, entity_id: EntityId) -> None:
        """Remove a chunk entity from the index.

        Args:
            entity_id: The entity ID to remove.
        """
        self._ensure_initialized()
        # Find and remove the entity from the grid mapping
        to_remove = None
        for grid_index, eid in self._grid_to_entity.items():
            if eid == entity_id:
                to_remove = grid_index
                break
        if to_remove is not None:
            del self._grid_to_entity[to_remove]

    def update_chunk(
        self, entity_id: EntityId, old_grid_index: Tuple[int, ...]
    ) -> None:
        """Update a chunk's position in the index.

        Args:
            entity_id: The entity ID to update.
            old_grid_index: The previous grid index to remove.
        """
        self._ensure_initialized()
        # Remove old position
        if old_grid_index in self._grid_to_entity:
            if self._grid_to_entity[old_grid_index] == entity_id:
                del self._grid_to_entity[old_grid_index]
        # Add new position
        if entity_id in self._world._entities:
            components = self._world._entities[entity_id]
            if ChunkMetadata in components:
                component = cast(ChunkMetadata, components[ChunkMetadata])
                grid_index = component.grid_index
                self._grid_to_entity[grid_index] = entity_id

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over all chunk entities in the index."""
        self._ensure_initialized()
        for entity_id in list(self._grid_to_entity.values()):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def count(self) -> int:
        """Get the number of chunks in the index."""
        self._ensure_initialized()
        return len(self._grid_to_entity)

    def get_entity_ids(self) -> Set[EntityId]:
        """Get all entity IDs in the index.

        Returns:
            Set of entity IDs for all indexed chunks.
        """
        self._ensure_initialized()
        return set(self._grid_to_entity.values())
