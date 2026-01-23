"""Factory functions for creating chunk indexes and setting up observers.

Provides convenient functions to create and configure chunk indexes
with optional automatic observer registration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from .index import ChunkIndex
from .observer import (
    BAKING_LAYER_TYPES,
    ChunkBakingObserver,
    create_baking_observer,
    create_chunk_index_observer,
)

if TYPE_CHECKING:
    from relics.world import World


def create_chunk_index(
    world: "World",
    chunk_size: int,
    auto_register_observer: bool = True,
) -> ChunkIndex:
    """Create a ChunkIndex for a World.

    Args:
        world: The World to index.
        chunk_size: Number of tiles per chunk edge.
        auto_register_observer: If True, automatically register an observer
                               to keep the index updated.

    Returns:
        A configured ChunkIndex instance.

    Example:
        >>> from relics import World
        >>> from relics.addons.tilegrid import create_chunk_index
        >>> world = World()
        >>> index = create_chunk_index(world, chunk_size=32)
    """
    index = ChunkIndex(world, chunk_size)

    if auto_register_observer:
        observer = create_chunk_index_observer(index)
        world.observe(observer)

    return index


def setup_baking_observers(world: "World") -> List[ChunkBakingObserver]:
    """Register baking observers for all layer component types.

    Creates and registers observers that mark chunks dirty when any
    layer component (VisualTileLayer, ElevationLayer, TileCollisionLayer)
    is added, changed, or removed.

    Args:
        world: The World to register observers on.

    Returns:
        List of registered ChunkBakingObserver instances.

    Example:
        >>> from relics import World
        >>> from relics.addons.tilegrid import setup_baking_observers
        >>> world = World()
        >>> observers = setup_baking_observers(world)
    """
    observers = []
    for layer_type in BAKING_LAYER_TYPES:
        observer = create_baking_observer(layer_type)
        world.observe(observer)
        observers.append(observer)
    return observers
