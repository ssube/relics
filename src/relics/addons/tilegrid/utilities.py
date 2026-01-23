"""Coordinate conversion utilities for the Tile Grid addon.

Provides functions for converting between world coordinates, chunk grid
indices, and local tile coordinates.
"""

from __future__ import annotations

from typing import Tuple

from .exceptions import InvalidTileIndexError


def world_to_chunk_index(x: float, y: float, chunk_size: int) -> Tuple[int, int]:
    """Convert world position to chunk grid index.

    Args:
        x: World X coordinate.
        y: World Y coordinate.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (grid_x, grid_y) chunk indices.
    """
    return (int(x // chunk_size), int(y // chunk_size))


def world_to_chunk_index_3d(
    x: float, y: float, z: float, chunk_size: int
) -> Tuple[int, int, int]:
    """Convert 3D world position to chunk grid index.

    Args:
        x: World X coordinate.
        y: World Y coordinate.
        z: World Z coordinate.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (grid_x, grid_y, grid_z) chunk indices.
    """
    return (int(x // chunk_size), int(y // chunk_size), int(z // chunk_size))


def world_to_local(
    world_x: float,
    world_y: float,
    chunk_pos_x: float,
    chunk_pos_y: float,
    chunk_size: int,
) -> Tuple[int, int]:
    """Convert world position to local tile coordinates within a chunk.

    Args:
        world_x: World X coordinate.
        world_y: World Y coordinate.
        chunk_pos_x: Chunk center X coordinate.
        chunk_pos_y: Chunk center Y coordinate.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (local_x, local_y) tile coordinates.
    """
    half = chunk_size / 2
    return (
        int(world_x - (chunk_pos_x - half)),
        int(world_y - (chunk_pos_y - half)),
    )


def world_to_local_3d(
    world_x: float,
    world_y: float,
    world_z: float,
    chunk_pos_x: float,
    chunk_pos_y: float,
    chunk_pos_z: float,
    chunk_size: int,
) -> Tuple[int, int, int]:
    """Convert 3D world position to local tile coordinates within a chunk.

    Args:
        world_x: World X coordinate.
        world_y: World Y coordinate.
        world_z: World Z coordinate.
        chunk_pos_x: Chunk center X coordinate.
        chunk_pos_y: Chunk center Y coordinate.
        chunk_pos_z: Chunk center Z coordinate.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (local_x, local_y, local_z) tile coordinates.
    """
    half = chunk_size / 2
    return (
        int(world_x - (chunk_pos_x - half)),
        int(world_y - (chunk_pos_y - half)),
        int(world_z - (chunk_pos_z - half)),
    )


def local_to_index(local_x: int, local_y: int, chunk_size: int) -> int:
    """Convert local tile coordinates to flat array index.

    Uses row-major ordering: index = y * chunk_size + x

    Args:
        local_x: Local X tile coordinate (0 to chunk_size - 1).
        local_y: Local Y tile coordinate (0 to chunk_size - 1).
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Flat array index for the tile.
    """
    return local_y * chunk_size + local_x


def local_to_index_3d(
    local_x: int, local_y: int, local_z: int, chunk_size: int
) -> int:
    """Convert 3D local tile coordinates to flat array index.

    Uses row-major ordering: index = z * (size * size) + y * size + x

    Args:
        local_x: Local X tile coordinate (0 to chunk_size - 1).
        local_y: Local Y tile coordinate (0 to chunk_size - 1).
        local_z: Local Z tile coordinate (0 to chunk_size - 1).
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Flat array index for the tile.
    """
    return local_z * (chunk_size * chunk_size) + local_y * chunk_size + local_x


def index_to_local(index: int, chunk_size: int) -> Tuple[int, int]:
    """Convert flat array index to local tile coordinates.

    Inverse of local_to_index.

    Args:
        index: Flat array index.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (local_x, local_y) tile coordinates.
    """
    local_y = index // chunk_size
    local_x = index % chunk_size
    return (local_x, local_y)


def index_to_local_3d(index: int, chunk_size: int) -> Tuple[int, int, int]:
    """Convert flat array index to 3D local tile coordinates.

    Inverse of local_to_index_3d.

    Args:
        index: Flat array index.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (local_x, local_y, local_z) tile coordinates.
    """
    plane_size = chunk_size * chunk_size
    local_z = index // plane_size
    remainder = index % plane_size
    local_y = remainder // chunk_size
    local_x = remainder % chunk_size
    return (local_x, local_y, local_z)


def validate_tile_coords(local_x: int, local_y: int, chunk_size: int) -> None:
    """Validate that tile coordinates are within chunk bounds.

    Args:
        local_x: Local X tile coordinate.
        local_y: Local Y tile coordinate.
        chunk_size: Number of tiles per chunk edge.

    Raises:
        InvalidTileIndexError: If coordinates are out of bounds.
    """
    if not (0 <= local_x < chunk_size and 0 <= local_y < chunk_size):
        raise InvalidTileIndexError(
            f"Tile coordinates ({local_x}, {local_y}) are outside "
            f"chunk bounds (0-{chunk_size - 1})"
        )


def validate_tile_coords_3d(
    local_x: int, local_y: int, local_z: int, chunk_size: int
) -> None:
    """Validate that 3D tile coordinates are within chunk bounds.

    Args:
        local_x: Local X tile coordinate.
        local_y: Local Y tile coordinate.
        local_z: Local Z tile coordinate.
        chunk_size: Number of tiles per chunk edge.

    Raises:
        InvalidTileIndexError: If coordinates are out of bounds.
    """
    if not (
        0 <= local_x < chunk_size
        and 0 <= local_y < chunk_size
        and 0 <= local_z < chunk_size
    ):
        raise InvalidTileIndexError(
            f"Tile coordinates ({local_x}, {local_y}, {local_z}) are outside "
            f"chunk bounds (0-{chunk_size - 1})"
        )


def chunk_center_from_grid_index(
    grid_x: int, grid_y: int, chunk_size: int
) -> Tuple[float, float]:
    """Calculate chunk center position from grid index.

    Args:
        grid_x: Grid X index.
        grid_y: Grid Y index.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (center_x, center_y) world coordinates.
    """
    half = chunk_size / 2
    return (grid_x * chunk_size + half, grid_y * chunk_size + half)


def chunk_center_from_grid_index_3d(
    grid_x: int, grid_y: int, grid_z: int, chunk_size: int
) -> Tuple[float, float, float]:
    """Calculate chunk center position from 3D grid index.

    Args:
        grid_x: Grid X index.
        grid_y: Grid Y index.
        grid_z: Grid Z index.
        chunk_size: Number of tiles per chunk edge.

    Returns:
        Tuple of (center_x, center_y, center_z) world coordinates.
    """
    half = chunk_size / 2
    return (
        grid_x * chunk_size + half,
        grid_y * chunk_size + half,
        grid_z * chunk_size + half,
    )
