"""Tile grid addon for the Relics ECS framework.

This module provides a chunked tile system for building 2D and layered 3D
worlds. Chunks are ECS entities with layer components that store tile data,
elevation, and collision information.

Basic Usage:
    >>> from relics import World
    >>> from relics.addons.tilegrid import (
    ...     ChunkMetadata, TileVisualLayer, create_chunk_index
    ... )
    >>>
    >>> world = World()
    >>> index = create_chunk_index(world, chunk_size=32)
    >>>
    >>> # Create a chunk at grid position (0, 0)
    >>> chunk = world.create_entity()
    >>> chunk.add_component(ChunkMetadata(
    ...     chunk_size=32,
    ...     sprite_sheets=["overworld_tiles"],
    ...     grid_index=(0, 0)
    ... ))
    >>>
    >>> # Add visual layer
    >>> ground_tiles = [1] * (32 * 32)  # All grass
    >>> chunk.add_component(TileVisualLayer(
    ...     name="ground",
    ...     tiles=ground_tiles,
    ...     z_order=0
    ... ))

Coordinate Conversion:
    >>> from relics.addons.tilegrid import (
    ...     world_to_chunk_index, world_to_local, local_to_index
    ... )
    >>>
    >>> # Find which chunk contains a world position
    >>> grid_x, grid_y = world_to_chunk_index(150.0, 200.0, chunk_size=32)
    >>>
    >>> # Convert world position to local tile coordinates
    >>> local_x, local_y = world_to_local(150.0, 200.0, 160.0, 208.0, chunk_size=32)
    >>>
    >>> # Get flat array index for tile lookup
    >>> tile_idx = local_to_index(local_x, local_y, chunk_size=32)

Convenience Functions:
    >>> from relics.addons.tilegrid import get_chunk_at, get_tile_at
    >>>
    >>> # Get chunk entity at world position
    >>> chunk = get_chunk_at(world, 150.0, 200.0, index)
    >>>
    >>> # Get tile index at world position for a layer
    >>> tile = get_tile_at(world, 150.0, 200.0, "ground", index)
"""

# Components
from .components import (
    BakedChunk,
    ChunkMetadata,
    TileElevationLayer,
    TileCollisionLayer,
    TileVisualLayer,
)

# Exceptions
from .exceptions import (
    ChunkNotFoundError,
    InvalidTileIndexError,
    LayerNotFoundError,
    TileGridError,
)

# Factory functions
from .factory import create_chunk_index, setup_baking_observers

# Index
from .index import ChunkIndex

# Observers
from .observer import (
    BAKING_LAYER_TYPES,
    ChunkBakingObserver,
    ChunkIndexObserver,
    create_baking_observer,
    create_chunk_index_observer,
)

# Types and constants
from .types import EMPTY_TILE, LayerName, TileIndex

# Utilities
from .utilities import (
    chunk_center_from_grid_index,
    chunk_center_from_grid_index_3d,
    index_to_local,
    index_to_local_3d,
    local_to_index,
    local_to_index_3d,
    validate_tile_coords,
    validate_tile_coords_3d,
    world_to_chunk_index,
    world_to_chunk_index_3d,
    world_to_local,
    world_to_local_3d,
)

# Import TYPE_CHECKING for convenience function type hints
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World


def get_chunk_at(
    world: "World", x: float, y: float, index: ChunkIndex
) -> Optional["Entity"]:
    """Get the chunk entity containing a world position.

    Args:
        world: The World containing chunk entities.
        x: World X coordinate.
        y: World Y coordinate.
        index: The ChunkIndex to query.

    Returns:
        Entity handle if chunk exists, None otherwise.
    """
    return index.get_chunk_at_world_pos(x, y)


def get_tile_at(
    world: "World", x: float, y: float, layer_name: str, index: ChunkIndex
) -> Optional[int]:
    """Get the tile index at a world position for a specific layer.

    Args:
        world: The World containing chunk entities.
        x: World X coordinate.
        y: World Y coordinate.
        layer_name: Name of the TileVisualLayer to query.
        index: The ChunkIndex to query.

    Returns:
        Tile index if found, None if no chunk or layer exists.

    Raises:
        LayerNotFoundError: If the chunk exists but doesn't have the layer.
    """
    chunk = get_chunk_at(world, x, y, index)
    if chunk is None:
        return None

    # Get chunk metadata and position
    if not chunk.has_component(ChunkMetadata):
        return None

    metadata = chunk.get_component(ChunkMetadata)
    chunk_size = metadata.chunk_size

    # Calculate chunk center from grid index
    grid_x, grid_y = metadata.grid_index[0], metadata.grid_index[1]
    chunk_pos_x, chunk_pos_y = chunk_center_from_grid_index(grid_x, grid_y, chunk_size)

    # Convert to local coordinates
    local_x, local_y = world_to_local(x, y, chunk_pos_x, chunk_pos_y, chunk_size)

    # Validate coordinates
    try:
        validate_tile_coords(local_x, local_y, chunk_size)
    except InvalidTileIndexError:
        return None

    # Find the layer with the matching name by checking if entity has the layer
    if not chunk.has_component(TileVisualLayer):
        raise LayerNotFoundError(f"Layer '{layer_name}' not found on chunk")

    layer = chunk.get_component(TileVisualLayer)
    if layer.name == layer_name:
        tile_index = local_to_index(local_x, local_y, chunk_size)
        return layer.tiles[tile_index]

    raise LayerNotFoundError(f"Layer '{layer_name}' not found on chunk")


__all__ = [
    # Components
    "ChunkMetadata",
    "TileVisualLayer",
    "TileElevationLayer",
    "TileCollisionLayer",
    "BakedChunk",
    # Exceptions
    "TileGridError",
    "ChunkNotFoundError",
    "LayerNotFoundError",
    "InvalidTileIndexError",
    # Types and constants
    "EMPTY_TILE",
    "TileIndex",
    "LayerName",
    # Index
    "ChunkIndex",
    # Observers
    "ChunkIndexObserver",
    "ChunkBakingObserver",
    "create_chunk_index_observer",
    "create_baking_observer",
    "BAKING_LAYER_TYPES",
    # Utilities
    "world_to_chunk_index",
    "world_to_chunk_index_3d",
    "world_to_local",
    "world_to_local_3d",
    "local_to_index",
    "local_to_index_3d",
    "index_to_local",
    "index_to_local_3d",
    "validate_tile_coords",
    "validate_tile_coords_3d",
    "chunk_center_from_grid_index",
    "chunk_center_from_grid_index_3d",
    # Factory functions
    "create_chunk_index",
    "setup_baking_observers",
    # Convenience functions
    "get_chunk_at",
    "get_tile_at",
]
