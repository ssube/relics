"""Tile grid components for chunk-based tile systems.

These components define the data structures for chunked tile maps
with support for multiple visual layers, elevation, and collision.
"""

from __future__ import annotations

from typing import List, Tuple

from pydantic.dataclasses import dataclass

from relics.monitored import monitored
from relics.types import Component


@monitored
@dataclass
class ChunkMetadata(Component):
    """Core metadata for a chunk entity.

    Attributes:
        chunk_size: Number of tiles per edge (e.g., 16, 32, 128).
        sprite_sheets: List of sprite sheet references. Single item in v0.1.
        grid_index: Grid position as (x, y) for 2D or (x, y, z) for 3D.
    """

    chunk_size: int
    sprite_sheets: List[str]
    grid_index: Tuple[int, ...]


@monitored
@dataclass
class TileVisualLayer(Component):
    """Visual tile layer storing tile indices for rendering.

    Multiple visual layers can be added to a chunk for layered rendering
    (e.g., ground, decor, objects).

    Attributes:
        name: Layer identifier (e.g., "ground", "decor", "objects").
        tiles: Flat array of tile indices in row-major order. -1 = empty.
        z_order: Render priority within chunk. Higher = rendered later.
        affected_by_elevation: Whether elevation offsets this layer.
    """

    name: str
    tiles: List[int]
    z_order: int = 0
    affected_by_elevation: bool = True


@monitored
@dataclass
class TileElevationLayer(Component):
    """Per-tile elevation values for vertical offset rendering.

    Elevation values offset sprite rendering to create cliff/step effects.

    Attributes:
        values: Elevation values (0.0-1.0) per tile, same indexing as visual layers.
    """

    values: List[float]


@monitored
@dataclass
class TileCollisionLayer(Component):
    """Per-tile movement speed multipliers for collision/pathfinding.

    Attributes:
        values: Speed multipliers per tile.
                0.0 = impassable (wall)
                0.5 = half speed (mud, water)
                1.0 = full speed (normal ground)
                >1.0 = speed boost (roads, ice)
    """

    values: List[float]


@monitored
@dataclass
class BakedChunk(Component):
    """Baking output tracking for a chunk entity.

    Added after baking to track rendered textures and dirty state.

    Attributes:
        visual_texture_id: Reference to baked visual sprite.
        elevation_texture_id: Reference to elevation debug texture.
        collision_texture_id: Reference to collision debug texture.
        dirty: True if the chunk needs rebaking.
    """

    visual_texture_id: str = ""
    elevation_texture_id: str = ""
    collision_texture_id: str = ""
    dirty: bool = True
