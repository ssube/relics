"""Tests for tile grid coordinate utilities."""

import pytest

from relics.addons.tilegrid import (
    InvalidTileIndexError,
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


class TestWorldToChunkIndex:
    """Tests for world_to_chunk_index function."""

    def test_origin_chunk(self) -> None:
        """Test position at origin maps to chunk (0, 0)."""
        result = world_to_chunk_index(0.0, 0.0, chunk_size=32)
        assert result == (0, 0)

    def test_within_first_chunk(self) -> None:
        """Test position within first chunk."""
        result = world_to_chunk_index(15.0, 20.0, chunk_size=32)
        assert result == (0, 0)

    def test_second_chunk_x(self) -> None:
        """Test position in second chunk along X."""
        result = world_to_chunk_index(32.0, 0.0, chunk_size=32)
        assert result == (1, 0)

    def test_second_chunk_y(self) -> None:
        """Test position in second chunk along Y."""
        result = world_to_chunk_index(0.0, 32.0, chunk_size=32)
        assert result == (0, 1)

    def test_negative_position(self) -> None:
        """Test negative world position."""
        result = world_to_chunk_index(-1.0, -1.0, chunk_size=32)
        assert result == (-1, -1)

    def test_large_position(self) -> None:
        """Test large world position."""
        result = world_to_chunk_index(1000.0, 500.0, chunk_size=32)
        assert result == (31, 15)

    def test_boundary_position(self) -> None:
        """Test position exactly at chunk boundary."""
        result = world_to_chunk_index(64.0, 64.0, chunk_size=32)
        assert result == (2, 2)


class TestWorldToChunkIndex3D:
    """Tests for world_to_chunk_index_3d function."""

    def test_3d_origin(self) -> None:
        """Test 3D position at origin."""
        result = world_to_chunk_index_3d(0.0, 0.0, 0.0, chunk_size=16)
        assert result == (0, 0, 0)

    def test_3d_second_layer(self) -> None:
        """Test 3D position in second Z layer."""
        result = world_to_chunk_index_3d(10.0, 10.0, 20.0, chunk_size=16)
        assert result == (0, 0, 1)


class TestWorldToLocal:
    """Tests for world_to_local function."""

    def test_chunk_center(self) -> None:
        """Test conversion at chunk center."""
        # Chunk at grid (0, 0) with size 32 has center at (16, 16)
        result = world_to_local(16.0, 16.0, 16.0, 16.0, chunk_size=32)
        assert result == (16, 16)

    def test_chunk_corner(self) -> None:
        """Test conversion at chunk corner."""
        # Chunk at grid (0, 0) with size 32 has center at (16, 16)
        # World (0, 0) maps to local (0, 0)
        result = world_to_local(0.0, 0.0, 16.0, 16.0, chunk_size=32)
        assert result == (0, 0)

    def test_chunk_opposite_corner(self) -> None:
        """Test conversion at opposite corner."""
        # Chunk at grid (0, 0) with size 32 has center at (16, 16)
        # World (31, 31) maps to local (31, 31)
        result = world_to_local(31.0, 31.0, 16.0, 16.0, chunk_size=32)
        assert result == (31, 31)

    def test_second_chunk(self) -> None:
        """Test conversion for second chunk."""
        # Chunk at grid (1, 0) with size 32 has center at (48, 16)
        result = world_to_local(32.0, 0.0, 48.0, 16.0, chunk_size=32)
        assert result == (0, 0)


class TestWorldToLocal3D:
    """Tests for world_to_local_3d function."""

    def test_3d_conversion(self) -> None:
        """Test 3D world to local conversion."""
        # Chunk at grid (0, 0, 0) with size 16 has center at (8, 8, 8)
        result = world_to_local_3d(0.0, 0.0, 0.0, 8.0, 8.0, 8.0, chunk_size=16)
        assert result == (0, 0, 0)


class TestLocalToIndex:
    """Tests for local_to_index function."""

    def test_origin_tile(self) -> None:
        """Test index at local (0, 0)."""
        result = local_to_index(0, 0, chunk_size=32)
        assert result == 0

    def test_row_major_order(self) -> None:
        """Test row-major ordering."""
        # y * chunk_size + x
        result = local_to_index(1, 0, chunk_size=32)
        assert result == 1
        result = local_to_index(0, 1, chunk_size=32)
        assert result == 32
        result = local_to_index(1, 1, chunk_size=32)
        assert result == 33

    def test_last_tile(self) -> None:
        """Test index of last tile."""
        result = local_to_index(31, 31, chunk_size=32)
        assert result == 32 * 32 - 1


class TestLocalToIndex3D:
    """Tests for local_to_index_3d function."""

    def test_3d_origin(self) -> None:
        """Test 3D index at origin."""
        result = local_to_index_3d(0, 0, 0, chunk_size=16)
        assert result == 0

    def test_3d_z_layer(self) -> None:
        """Test 3D index in second Z layer."""
        result = local_to_index_3d(0, 0, 1, chunk_size=16)
        assert result == 16 * 16

    def test_3d_full(self) -> None:
        """Test 3D index with all coordinates."""
        # z * (size * size) + y * size + x
        result = local_to_index_3d(2, 3, 1, chunk_size=16)
        assert result == 1 * 256 + 3 * 16 + 2


class TestIndexToLocal:
    """Tests for index_to_local function."""

    def test_origin_index(self) -> None:
        """Test conversion of index 0."""
        result = index_to_local(0, chunk_size=32)
        assert result == (0, 0)

    def test_roundtrip(self) -> None:
        """Test roundtrip conversion."""
        for x in range(4):
            for y in range(4):
                idx = local_to_index(x, y, chunk_size=32)
                result = index_to_local(idx, chunk_size=32)
                assert result == (x, y)


class TestIndexToLocal3D:
    """Tests for index_to_local_3d function."""

    def test_3d_roundtrip(self) -> None:
        """Test 3D roundtrip conversion."""
        for x in range(4):
            for y in range(4):
                for z in range(4):
                    idx = local_to_index_3d(x, y, z, chunk_size=16)
                    result = index_to_local_3d(idx, chunk_size=16)
                    assert result == (x, y, z)


class TestValidateTileCoords:
    """Tests for validate_tile_coords function."""

    def test_valid_origin(self) -> None:
        """Test valid coordinates at origin."""
        validate_tile_coords(0, 0, chunk_size=32)  # Should not raise

    def test_valid_max(self) -> None:
        """Test valid coordinates at max."""
        validate_tile_coords(31, 31, chunk_size=32)  # Should not raise

    def test_invalid_x_negative(self) -> None:
        """Test invalid negative X coordinate."""
        with pytest.raises(InvalidTileIndexError):
            validate_tile_coords(-1, 0, chunk_size=32)

    def test_invalid_y_negative(self) -> None:
        """Test invalid negative Y coordinate."""
        with pytest.raises(InvalidTileIndexError):
            validate_tile_coords(0, -1, chunk_size=32)

    def test_invalid_x_too_large(self) -> None:
        """Test invalid X coordinate too large."""
        with pytest.raises(InvalidTileIndexError):
            validate_tile_coords(32, 0, chunk_size=32)

    def test_invalid_y_too_large(self) -> None:
        """Test invalid Y coordinate too large."""
        with pytest.raises(InvalidTileIndexError):
            validate_tile_coords(0, 32, chunk_size=32)


class TestValidateTileCoords3D:
    """Tests for validate_tile_coords_3d function."""

    def test_valid_3d_coords(self) -> None:
        """Test valid 3D coordinates."""
        validate_tile_coords_3d(0, 0, 0, chunk_size=16)  # Should not raise
        validate_tile_coords_3d(15, 15, 15, chunk_size=16)  # Should not raise

    def test_invalid_z_negative(self) -> None:
        """Test invalid negative Z coordinate."""
        with pytest.raises(InvalidTileIndexError):
            validate_tile_coords_3d(0, 0, -1, chunk_size=16)

    def test_invalid_z_too_large(self) -> None:
        """Test invalid Z coordinate too large."""
        with pytest.raises(InvalidTileIndexError):
            validate_tile_coords_3d(0, 0, 16, chunk_size=16)


class TestChunkCenterFromGridIndex:
    """Tests for chunk_center_from_grid_index function."""

    def test_origin_chunk(self) -> None:
        """Test center of chunk at grid (0, 0)."""
        result = chunk_center_from_grid_index(0, 0, chunk_size=32)
        assert result == (16.0, 16.0)

    def test_second_chunk(self) -> None:
        """Test center of chunk at grid (1, 0)."""
        result = chunk_center_from_grid_index(1, 0, chunk_size=32)
        assert result == (48.0, 16.0)

    def test_negative_grid(self) -> None:
        """Test center of chunk at negative grid index."""
        result = chunk_center_from_grid_index(-1, -1, chunk_size=32)
        assert result == (-16.0, -16.0)


class TestChunkCenterFromGridIndex3D:
    """Tests for chunk_center_from_grid_index_3d function."""

    def test_3d_origin_chunk(self) -> None:
        """Test center of 3D chunk at grid (0, 0, 0)."""
        result = chunk_center_from_grid_index_3d(0, 0, 0, chunk_size=16)
        assert result == (8.0, 8.0, 8.0)

    def test_3d_second_layer(self) -> None:
        """Test center of 3D chunk at grid (0, 0, 1)."""
        result = chunk_center_from_grid_index_3d(0, 0, 1, chunk_size=16)
        assert result == (8.0, 8.0, 24.0)
