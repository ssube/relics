"""Tests for tile grid components."""

import pydantic
import pytest

from relics.addons.tilegrid import (
    BakedChunk,
    ChunkMetadata,
    TileCollisionLayer,
    TileElevationLayer,
    TileVisualLayer,
)
from relics.monitored import is_monitored


class TestChunkMetadata:
    """Tests for ChunkMetadata component."""

    def test_create_chunk_metadata(self) -> None:
        """Test creating a ChunkMetadata component."""
        meta = ChunkMetadata(
            chunk_size=32,
            sprite_sheets=["overworld_tiles"],
            grid_index=(5, 10),
        )
        assert meta.chunk_size == 32
        assert meta.sprite_sheets == ["overworld_tiles"]
        assert meta.grid_index == (5, 10)

    def test_chunk_metadata_is_monitored(self) -> None:
        """Test that ChunkMetadata has the @monitored decorator."""
        assert is_monitored(ChunkMetadata)

    def test_chunk_metadata_requires_all_fields(self) -> None:
        """Test that ChunkMetadata requires all fields."""
        with pytest.raises(pydantic.ValidationError):
            ChunkMetadata()  # type: ignore

    def test_chunk_metadata_3d_grid_index(self) -> None:
        """Test ChunkMetadata with 3D grid index."""
        meta = ChunkMetadata(
            chunk_size=16,
            sprite_sheets=["dungeon_tiles"],
            grid_index=(1, 2, 3),
        )
        assert meta.grid_index == (1, 2, 3)


class TestTileVisualLayer:
    """Tests for TileVisualLayer component."""

    def test_create_visual_tile_layer(self) -> None:
        """Test creating a TileVisualLayer component."""
        tiles = [1, 2, 3, 4]
        layer = TileVisualLayer(
            name="ground",
            tiles=tiles,
            z_order=0,
            affected_by_elevation=True,
        )
        assert layer.name == "ground"
        assert layer.tiles == [1, 2, 3, 4]
        assert layer.z_order == 0
        assert layer.affected_by_elevation is True

    def test_visual_tile_layer_is_monitored(self) -> None:
        """Test that TileVisualLayer has the @monitored decorator."""
        assert is_monitored(TileVisualLayer)

    def test_visual_tile_layer_default_values(self) -> None:
        """Test TileVisualLayer default values."""
        layer = TileVisualLayer(name="decor", tiles=[0])
        assert layer.z_order == 0
        assert layer.affected_by_elevation is True

    def test_visual_tile_layer_custom_z_order(self) -> None:
        """Test TileVisualLayer with custom z_order."""
        layer = TileVisualLayer(name="objects", tiles=[5, 6], z_order=10)
        assert layer.z_order == 10

    def test_visual_tile_layer_affected_by_elevation_false(self) -> None:
        """Test TileVisualLayer with affected_by_elevation=False."""
        layer = TileVisualLayer(
            name="ui_overlay",
            tiles=[1],
            affected_by_elevation=False,
        )
        assert layer.affected_by_elevation is False


class TestTileElevationLayer:
    """Tests for TileElevationLayer component."""

    def test_create_elevation_layer(self) -> None:
        """Test creating an TileElevationLayer component."""
        values = [0.0, 0.5, 1.0]
        layer = TileElevationLayer(values=values)
        assert layer.values == [0.0, 0.5, 1.0]

    def test_elevation_layer_is_monitored(self) -> None:
        """Test that TileElevationLayer has the @monitored decorator."""
        assert is_monitored(TileElevationLayer)

    def test_elevation_layer_requires_values(self) -> None:
        """Test that TileElevationLayer requires values."""
        with pytest.raises(pydantic.ValidationError):
            TileElevationLayer()  # type: ignore


class TestTileCollisionLayer:
    """Tests for TileCollisionLayer component."""

    def test_create_tile_collision_layer(self) -> None:
        """Test creating a TileCollisionLayer component."""
        values = [1.0, 0.5, 0.0]
        layer = TileCollisionLayer(values=values)
        assert layer.values == [1.0, 0.5, 0.0]

    def test_tile_collision_layer_is_monitored(self) -> None:
        """Test that TileCollisionLayer has the @monitored decorator."""
        assert is_monitored(TileCollisionLayer)

    def test_tile_collision_layer_speed_boost(self) -> None:
        """Test TileCollisionLayer with speed boost values."""
        layer = TileCollisionLayer(values=[1.5, 2.0])
        assert layer.values[0] == 1.5
        assert layer.values[1] == 2.0


class TestBakedChunk:
    """Tests for BakedChunk component."""

    def test_create_baked_chunk_defaults(self) -> None:
        """Test creating a BakedChunk with defaults."""
        baked = BakedChunk()
        assert baked.visual_texture_id == ""
        assert baked.elevation_texture_id == ""
        assert baked.collision_texture_id == ""
        assert baked.dirty is True

    def test_create_baked_chunk_with_values(self) -> None:
        """Test creating a BakedChunk with custom values."""
        baked = BakedChunk(
            visual_texture_id="tex_visual_0_0",
            elevation_texture_id="tex_elev_0_0",
            collision_texture_id="tex_coll_0_0",
            dirty=False,
        )
        assert baked.visual_texture_id == "tex_visual_0_0"
        assert baked.elevation_texture_id == "tex_elev_0_0"
        assert baked.collision_texture_id == "tex_coll_0_0"
        assert baked.dirty is False

    def test_baked_chunk_is_monitored(self) -> None:
        """Test that BakedChunk has the @monitored decorator."""
        assert is_monitored(BakedChunk)
