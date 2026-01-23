"""Integration tests for tile grid addon."""

import pytest

from relics import World
from relics.addons.tilegrid import (
    EMPTY_TILE,
    BakedChunk,
    ChunkMetadata,
    LayerNotFoundError,
    TileCollisionLayer,
    TileElevationLayer,
    TileVisualLayer,
    create_chunk_index,
    get_chunk_at,
    get_tile_at,
    local_to_index,
    setup_baking_observers,
)


class TestBasicWorkflow:
    """Tests for basic tile grid workflow."""

    def test_create_chunk_with_layers(self) -> None:
        """Test creating a chunk with multiple layers."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        # Register and spawn a chunk
        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["overworld_tiles"],
                    grid_index=(0, 0),
                )
            },
        )
        chunk = world.spawn("chunk")
        world.tick(0)

        # Add layers
        ground_tiles = [1] * (32 * 32)  # All grass
        ground_tiles[0] = 5  # Corner is water
        chunk.add_component(
            TileVisualLayer(name="ground", tiles=ground_tiles, z_order=0)
        )
        world.tick(0)

        # Verify chunk is in index
        result = index.get_chunk_by_grid(0, 0)
        assert result is not None
        assert result.id == chunk.id

        # Verify layer
        layer = chunk.get_component(TileVisualLayer)
        assert layer.name == "ground"
        assert layer.tiles[0] == 5
        assert layer.tiles[1] == 1

    def test_query_tile_at_position(self) -> None:
        """Test querying a tile at a world position."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        # Ground layer with specific tile at (5, 3)
        tiles = [0] * (32 * 32)
        tile_index = local_to_index(5, 3, 32)
        tiles[tile_index] = 42

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                ),
                TileVisualLayer: TileVisualLayer(name="ground", tiles=tiles),
            },
        )
        world.spawn("chunk")
        world.tick(0)

        # Query at world position (5, 3) which should be in chunk (0, 0)
        tile = get_tile_at(world, 5.0, 3.0, "ground", index)
        assert tile == 42

    def test_query_tile_empty(self) -> None:
        """Test querying a tile that is empty."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        # All tiles empty
        tiles = [EMPTY_TILE] * (32 * 32)
        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                ),
                TileVisualLayer: TileVisualLayer(name="ground", tiles=tiles),
            },
        )
        world.spawn("chunk")
        world.tick(0)

        tile = get_tile_at(world, 10.0, 10.0, "ground", index)
        assert tile == EMPTY_TILE


class TestMultiLayerChunks:
    """Tests for chunks with multiple layers."""

    def test_multiple_visual_layers(self) -> None:
        """Test chunk with multiple visual layers."""
        world = World()
        index = create_chunk_index(world, chunk_size=16)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=16,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                ),
                TileVisualLayer: TileVisualLayer(
                    name="ground", tiles=[1] * 256, z_order=0
                ),
            },
        )
        world.spawn("chunk")
        world.tick(0)

        # Query ground layer
        ground_tile = get_tile_at(world, 8.0, 8.0, "ground", index)
        assert ground_tile == 1

    def test_elevation_and_collision_layers(self) -> None:
        """Test chunk with elevation and collision layers."""
        world = World()

        # Elevation layer
        elevation = [0.0] * 256
        elevation[0] = 1.0  # Corner is elevated

        # Collision layer
        collision = [1.0] * 256
        collision[0] = 0.0  # Corner is impassable

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=16,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                ),
                TileElevationLayer: TileElevationLayer(values=elevation),
                TileCollisionLayer: TileCollisionLayer(values=collision),
            },
        )
        chunk = world.spawn("chunk")
        world.tick(0)

        # Verify layers
        elev = chunk.get_component(TileElevationLayer)
        assert elev.values[0] == 1.0

        coll = chunk.get_component(TileCollisionLayer)
        assert coll.values[0] == 0.0


class TestBakingObservers:
    """Tests for baking observer integration."""

    def test_setup_baking_observers(self) -> None:
        """Test setting up all baking observers."""
        world = World()
        observers = setup_baking_observers(world)

        assert len(observers) == 3  # Visual, Elevation, Collision

    def test_baking_workflow(self) -> None:
        """Test full baking workflow with observers."""
        world = World()
        setup_baking_observers(world)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=16,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                )
            },
        )
        chunk = world.spawn("chunk")
        world.tick(0)

        # Add visual layer - should trigger dirty
        chunk.add_component(TileVisualLayer(name="ground", tiles=[0] * 256))
        world.tick(0)

        # Should have BakedChunk with dirty=True
        assert chunk.has_component(BakedChunk)
        baked = chunk.get_component(BakedChunk)
        assert baked.dirty is True

        # Simulate baking (game would do this)
        baked.dirty = False
        baked.visual_texture_id = "baked_0_0"
        world.tick(0)

        # Modify layer - should mark dirty again
        layer = chunk.get_component(TileVisualLayer)
        layer.tiles = [1] * 256
        world.tick(0)

        baked = chunk.get_component(BakedChunk)
        assert baked.dirty is True


class TestEntityRemoval:
    """Tests for entity removal cleanup."""

    def test_remove_chunk_cleans_index(self) -> None:
        """Test that removing a chunk updates the index."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                )
            },
        )
        chunk = world.spawn("chunk")
        world.tick(0)

        assert index.count() == 1

        # Remove the component
        chunk.remove_component(ChunkMetadata)
        world.tick(0)

        assert index.count() == 0


class TestMultipleChunks:
    """Tests for multiple chunk scenarios."""

    def test_grid_of_chunks(self) -> None:
        """Test creating a grid of chunks."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        # Create a 3x3 grid of chunks
        chunks = {}
        for gx in range(3):
            for gy in range(3):
                world.register_prefab(
                    f"chunk_{gx}_{gy}",
                    {
                        ChunkMetadata: ChunkMetadata(
                            chunk_size=32,
                            sprite_sheets=["tiles"],
                            grid_index=(gx, gy),
                        )
                    },
                )
                chunk = world.spawn(f"chunk_{gx}_{gy}")
                chunks[(gx, gy)] = chunk
        world.tick(0)

        assert index.count() == 9

        # Verify each chunk is accessible
        for gx in range(3):
            for gy in range(3):
                result = index.get_chunk_by_grid(gx, gy)
                assert result is not None
                assert result.id == chunks[(gx, gy)].id

    def test_sparse_grid(self) -> None:
        """Test sparse chunk grid (not all positions filled)."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        # Only create chunks at (0,0), (2,0), (0,2)
        positions = [(0, 0), (2, 0), (0, 2)]
        for gx, gy in positions:
            world.register_prefab(
                f"chunk_{gx}_{gy}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(gx, gy),
                    )
                },
            )
            world.spawn(f"chunk_{gx}_{gy}")
        world.tick(0)

        assert index.count() == 3

        # (1, 1) should be empty
        result = index.get_chunk_by_grid(1, 1)
        assert result is None


class TestErrorCases:
    """Tests for error handling."""

    def test_layer_not_found_error(self) -> None:
        """Test LayerNotFoundError when layer doesn't exist."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                ),
                # Add only ground layer
                TileVisualLayer: TileVisualLayer(name="ground", tiles=[0] * 1024),
            },
        )
        world.spawn("chunk")
        world.tick(0)

        # Query non-existent layer
        with pytest.raises(LayerNotFoundError):
            get_tile_at(world, 5.0, 5.0, "nonexistent", index)

    def test_no_chunk_returns_none(self) -> None:
        """Test that querying empty position returns None."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        result = get_chunk_at(world, 100.0, 100.0, index)
        assert result is None

        tile = get_tile_at(world, 100.0, 100.0, "ground", index)
        assert tile is None


class TestWithPrefabs:
    """Tests for prefab-based chunk spawning."""

    def test_spawn_chunk_prefab(self) -> None:
        """Test spawning chunks from prefab."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        # Register chunk prefab
        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["default_tiles"],
                    grid_index=(0, 0),
                ),
            },
        )

        # Spawn with override
        world.spawn("chunk", {})
        world.spawn(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["default_tiles"],
                    grid_index=(1, 0),
                )
            },
        )
        world.tick(0)

        assert index.count() == 2
