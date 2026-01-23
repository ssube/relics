"""Tests for ChunkIndex implementation."""

from relics import World
from relics.addons.tilegrid import ChunkIndex, ChunkMetadata, create_chunk_index


class TestChunkIndexCreation:
    """Tests for ChunkIndex creation."""

    def test_create_chunk_index(self) -> None:
        """Test creating a ChunkIndex."""
        world = World()
        index = ChunkIndex(world, chunk_size=32)
        assert index.chunk_size == 32

    def test_create_via_factory(self) -> None:
        """Test creating ChunkIndex via factory function."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)
        assert index.chunk_size == 32


class TestChunkIndexLazyInit:
    """Tests for lazy initialization."""

    def test_not_initialized_on_creation(self) -> None:
        """Test that index is not initialized on creation."""
        world = World()
        index = ChunkIndex(world, chunk_size=32)
        assert index._initialized is False

    def test_initialized_on_first_access(self) -> None:
        """Test that index initializes on first access."""
        world = World()
        index = ChunkIndex(world, chunk_size=32)
        _ = index.count()  # Trigger initialization
        assert index._initialized is True


class TestChunkIndexLookup:
    """Tests for chunk lookup operations."""

    def test_get_chunk_by_grid_existing(self) -> None:
        """Test looking up an existing chunk by grid index."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Register and spawn a chunk
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

        # Force rebuild
        index.invalidate()

        result = index.get_chunk_by_grid(0, 0)
        assert result is not None
        assert result.id == entity.id

    def test_get_chunk_by_grid_missing(self) -> None:
        """Test looking up a non-existent chunk."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        result = index.get_chunk_by_grid(5, 5)
        assert result is None

    def test_get_chunk_at_world_pos(self) -> None:
        """Test looking up chunk by world position."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Create a chunk at grid (1, 1)
        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(1, 1),
                )
            },
        )
        entity = world.spawn("chunk")
        world.tick(0)
        index.invalidate()

        # World position (40, 40) should be in chunk (1, 1)
        result = index.get_chunk_at_world_pos(40.0, 40.0)
        assert result is not None
        assert result.id == entity.id

    def test_get_chunk_by_grid_3d(self) -> None:
        """Test looking up chunk with 3D grid index."""
        world = World()
        index = create_chunk_index(world, chunk_size=16, auto_register_observer=False)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=16,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0, 1),
                )
            },
        )
        entity = world.spawn("chunk")
        world.tick(0)
        index.invalidate()

        result = index.get_chunk_by_grid_3d(0, 0, 1)
        assert result is not None
        assert result.id == entity.id


class TestChunkIndexModification:
    """Tests for index modification operations."""

    def test_add_chunk(self) -> None:
        """Test adding a chunk to the index."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(2, 3),
                )
            },
        )
        entity = world.spawn("chunk")
        world.tick(0)

        # Manually add
        index.add_chunk(entity.id)

        result = index.get_chunk_by_grid(2, 3)
        assert result is not None

    def test_remove_chunk(self) -> None:
        """Test removing a chunk from the index."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

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
        index.invalidate()

        # Verify it exists
        assert index.get_chunk_by_grid(0, 0) is not None

        # Remove it
        index.remove_chunk(entity.id)

        # Verify it's gone
        assert index.get_chunk_by_grid(0, 0) is None

    def test_update_chunk_grid_index(self) -> None:
        """Test updating a chunk's grid index."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

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
        index.invalidate()

        # Change the grid index on the component
        meta = entity.get_component(ChunkMetadata)
        old_index = meta.grid_index
        meta.grid_index = (1, 1)

        # Update the index
        index.update_chunk(entity.id, old_index)

        # Old position should be empty
        assert index.get_chunk_by_grid(0, 0) is None
        # New position should have the chunk
        assert index.get_chunk_by_grid(1, 1) is not None

    def test_invalidate(self) -> None:
        """Test invalidating the index."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

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
        world.spawn("chunk")
        world.tick(0)
        index.invalidate()

        # Access to force initialization
        _ = index.count()
        assert index._initialized is True

        # Invalidate
        index.invalidate()
        assert index._initialized is False


class TestChunkIndexIndexView:
    """Tests for IndexView interface implementation."""

    def test_iter(self) -> None:
        """Test iterating over chunks."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Create 3 chunks with different grid indices
        entities = []
        for i in range(3):
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(i, 0),
                    )
                },
            )
            entity = world.spawn(f"chunk{i}")
            entities.append(entity)
        world.tick(0)
        index.invalidate()

        result = list(index)
        assert len(result) == 3
        result_ids = {e.id for e in result}
        for entity in entities:
            assert entity.id in result_ids

    def test_count(self) -> None:
        """Test counting chunks."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Create 5 chunks
        for i in range(5):
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(i, 0),
                    )
                },
            )
            world.spawn(f"chunk{i}")
        world.tick(0)
        index.invalidate()

        assert index.count() == 5

    def test_get_entity_ids(self) -> None:
        """Test getting entity IDs."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        entities = []
        for i in range(3):
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(i, 0),
                    )
                },
            )
            entity = world.spawn(f"chunk{i}")
            entities.append(entity)
        world.tick(0)
        index.invalidate()

        result = index.get_entity_ids()
        assert len(result) == 3
        for entity in entities:
            assert entity.id in result

    def test_len(self) -> None:
        """Test __len__ method."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        for i in range(4):
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(i, 0),
                    )
                },
            )
            world.spawn(f"chunk{i}")
        world.tick(0)
        index.invalidate()

        assert len(index) == 4


class TestChunkIndexEdgeCases:
    """Tests for edge cases."""

    def test_empty_index(self) -> None:
        """Test behavior with no chunks."""
        world = World()
        index = create_chunk_index(world, chunk_size=32)

        assert index.count() == 0
        assert list(index) == []
        assert index.get_entity_ids() == set()

    def test_multiple_chunks_same_position_overwrites(self) -> None:
        """Test that adding a chunk at same position overwrites."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        world.register_prefab(
            "chunk1",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                )
            },
        )
        world.spawn("chunk1")
        world.tick(0)
        index.invalidate()

        # Add second chunk at same position
        world.register_prefab(
            "chunk2",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(0, 0),
                )
            },
        )
        e2 = world.spawn("chunk2")
        world.tick(0)
        index.add_chunk(e2.id)

        # Should have the second entity
        result = index.get_chunk_by_grid(0, 0)
        assert result is not None
        assert result.id == e2.id

    def test_negative_grid_indices(self) -> None:
        """Test chunks at negative grid indices."""
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        world.register_prefab(
            "chunk",
            {
                ChunkMetadata: ChunkMetadata(
                    chunk_size=32,
                    sprite_sheets=["tiles"],
                    grid_index=(-5, -3),
                )
            },
        )
        entity = world.spawn("chunk")
        world.tick(0)
        index.invalidate()

        result = index.get_chunk_by_grid(-5, -3)
        assert result is not None
        assert result.id == entity.id
