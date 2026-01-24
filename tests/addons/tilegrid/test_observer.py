"""Tests for tile grid observers."""

from relics import World
from relics.addons.tilegrid import (
    BAKING_LAYER_TYPES,
    BakedChunk,
    ChunkIndexObserver,
    ChunkMetadata,
    TileCollisionLayer,
    TileElevationLayer,
    TileVisualLayer,
    create_baking_observer,
    create_chunk_index,
    create_chunk_index_observer,
)


class TestChunkIndexObserver:
    """Tests for ChunkIndexObserver."""

    def test_observer_adds_chunk_on_component_added(self) -> None:
        """Test that observer adds chunk when ChunkMetadata is added."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=True)

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
        entity = world.spawn("chunk")
        world.tick(0)

        # Should be in index via observer
        result = index.get_chunk_by_grid(0, 0)
        assert result is not None
        assert result.id == entity.id

    def test_on_component_added_binds_monitored_component(self) -> None:
        """Test that adding a monitored component triggers world binding."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=True)

        # Create entity first without ChunkMetadata
        world.register_prefab("empty", {})
        entity = world.spawn("empty")
        world.tick(0)

        # Add ChunkMetadata component via add_component (triggers OnComponentAdded)
        metadata = ChunkMetadata(
            chunk_size=32,
            sprite_sheets=["tiles"],
            grid_index=(1, 1),
        )
        entity.add_component(metadata)
        world.tick(0)

        # Verify the chunk was added to the index (observer processed it)
        result = index.get_chunk_by_grid(1, 1)
        assert result is not None
        assert result.id == entity.id

        # If ChunkMetadata is monitored, it should be bound
        # The _bind_to_world path is covered by the observer's on_component_added
        loaded_meta = entity.get_component(ChunkMetadata)
        assert loaded_meta.grid_index == (1, 1)

    def test_observer_removes_chunk_on_component_removed(self) -> None:
        """Test that observer removes chunk when ChunkMetadata is removed."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=True)

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
        entity = world.spawn("chunk")
        world.tick(0)

        # Verify it's there
        assert index.get_chunk_by_grid(0, 0) is not None

        # Remove the component
        entity.remove_component(ChunkMetadata)
        world.tick(0)

        # Should be gone
        assert index.get_chunk_by_grid(0, 0) is None

    def test_observer_updates_on_grid_index_change(self) -> None:
        """Test that observer updates index when grid_index changes."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=True)

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
        entity = world.spawn("chunk")
        world.tick(0)

        # Change grid index
        meta = entity.get_component(ChunkMetadata)
        meta.grid_index = (5, 5)
        world.tick(0)

        # Old position should be empty
        assert index.get_chunk_by_grid(0, 0) is None
        # New position should have the chunk
        assert index.get_chunk_by_grid(5, 5) is not None

    def test_create_chunk_index_observer_function(self) -> None:
        """Test create_chunk_index_observer factory function."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)
        observer = create_chunk_index_observer(index)

        assert isinstance(observer, ChunkIndexObserver)
        assert observer.component_type == ChunkMetadata


class TestChunkBakingObserver:
    """Tests for ChunkBakingObserver."""

    def test_marks_dirty_on_visual_layer_added(self) -> None:
        """Test that adding TileVisualLayer marks chunk dirty."""
        world = World()
        observer = create_baking_observer(TileVisualLayer)
        world.observe(observer)

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
        entity = world.spawn("chunk")
        world.tick(0)

        # Add visual layer
        entity.add_component(TileVisualLayer(name="ground", tiles=[0] * 1024))
        world.tick(0)

        # Should have BakedChunk with dirty=True
        assert entity.has_component(BakedChunk)
        baked = entity.get_component(BakedChunk)
        assert baked.dirty is True

    def test_marks_dirty_on_elevation_layer_added(self) -> None:
        """Test that adding TileElevationLayer marks chunk dirty."""
        world = World()
        observer = create_baking_observer(TileElevationLayer)
        world.observe(observer)

        world.register_prefab(
            "entity",
            {BakedChunk: BakedChunk(dirty=False)},
        )
        entity = world.spawn("entity")
        world.tick(0)

        # Add elevation layer
        entity.add_component(TileElevationLayer(values=[0.0] * 1024))
        world.tick(0)

        baked = entity.get_component(BakedChunk)
        assert baked.dirty is True

    def test_marks_dirty_on_collision_layer_added(self) -> None:
        """Test that adding TileCollisionLayer marks chunk dirty."""
        world = World()
        observer = create_baking_observer(TileCollisionLayer)
        world.observe(observer)

        world.register_prefab(
            "entity",
            {BakedChunk: BakedChunk(dirty=False)},
        )
        entity = world.spawn("entity")
        world.tick(0)

        entity.add_component(TileCollisionLayer(values=[1.0] * 1024))
        world.tick(0)

        baked = entity.get_component(BakedChunk)
        assert baked.dirty is True

    def test_marks_dirty_on_layer_changed(self) -> None:
        """Test that modifying a layer marks chunk dirty."""
        world = World()
        observer = create_baking_observer(TileVisualLayer)
        world.observe(observer)

        tiles = [0] * 1024
        world.register_prefab(
            "entity",
            {
                TileVisualLayer: TileVisualLayer(name="ground", tiles=tiles),
                BakedChunk: BakedChunk(dirty=False),
            },
        )
        entity = world.spawn("entity")
        world.tick(0)

        # Modify the layer
        layer = entity.get_component(TileVisualLayer)
        layer.tiles = [1] * 1024  # Change all tiles
        world.tick(0)

        baked = entity.get_component(BakedChunk)
        assert baked.dirty is True

    def test_marks_dirty_on_layer_removed(self) -> None:
        """Test that removing a layer marks chunk dirty."""
        world = World()
        observer = create_baking_observer(TileVisualLayer)
        world.observe(observer)

        world.register_prefab(
            "entity",
            {
                TileVisualLayer: TileVisualLayer(name="ground", tiles=[0] * 1024),
                BakedChunk: BakedChunk(dirty=False),
            },
        )
        entity = world.spawn("entity")
        world.tick(0)

        # Remove the layer
        entity.remove_component(TileVisualLayer)
        world.tick(0)

        baked = entity.get_component(BakedChunk)
        assert baked.dirty is True

    def test_dynamic_observer_class_name(self) -> None:
        """Test that dynamic observer class has correct name."""
        observer = create_baking_observer(TileVisualLayer)
        assert "TileVisualLayer" in type(observer).__name__

    def test_dynamic_observer_component_type(self) -> None:
        """Test that dynamic observer has correct component_type."""
        observer = create_baking_observer(TileElevationLayer)
        assert observer.component_type == TileElevationLayer


class TestBakingLayerTypes:
    """Tests for BAKING_LAYER_TYPES constant."""

    def test_contains_all_layer_types(self) -> None:
        """Test that BAKING_LAYER_TYPES contains all layer types."""
        assert TileVisualLayer in BAKING_LAYER_TYPES
        assert TileElevationLayer in BAKING_LAYER_TYPES
        assert TileCollisionLayer in BAKING_LAYER_TYPES

    def test_count(self) -> None:
        """Test the number of layer types."""
        assert len(BAKING_LAYER_TYPES) == 3
