"""Performance tests for tile grid addon."""

import random
import time

import pytest

from relics import World
from relics.addons.tilegrid import (
    ChunkMetadata,
    TileVisualLayer,
    create_chunk_index,
)


class TestChunkLookupPerformance:
    """Tests for chunk lookup performance."""

    def test_lookup_is_constant_time(self) -> None:
        """Test that chunk lookup is O(1)."""
        random.seed(42)
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Create 1000 chunks
        for i in range(1000):
            gx = i % 100
            gy = i // 100
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(gx, gy),
                    )
                },
            )
            world.spawn(f"chunk{i}")
        world.tick(0)
        index.invalidate()

        # Warmup
        _ = index.get_chunk_by_grid(50, 5)

        # Measure lookup time for 10000 lookups
        start = time.perf_counter()
        for _ in range(10000):
            gx = random.randint(0, 99)
            gy = random.randint(0, 9)
            _ = index.get_chunk_by_grid(gx, gy)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\n10000 chunk lookups: {elapsed_ms:.3f}ms")
        # Should be very fast - less than 50ms for 10000 lookups (generous for CI)
        assert elapsed_ms < 50

    def test_lookup_scales_with_chunks(self) -> None:
        """Test that lookup time doesn't scale with chunk count."""
        random.seed(42)

        times = []
        for num_chunks in [100, 500, 1000]:
            world = World()
            index = create_chunk_index(
                world, chunk_size=32, auto_register_observer=False
            )

            # Create chunks
            for i in range(num_chunks):
                gx = i % 100
                gy = i // 100
                world.register_prefab(
                    f"chunk{i}",
                    {
                        ChunkMetadata: ChunkMetadata(
                            chunk_size=32,
                            sprite_sheets=["tiles"],
                            grid_index=(gx, gy),
                        )
                    },
                )
                world.spawn(f"chunk{i}")
            world.tick(0)
            index.invalidate()

            # Warmup
            _ = index.get_chunk_by_grid(0, 0)

            # Measure
            start = time.perf_counter()
            for _ in range(1000):
                gx = random.randint(0, 99)
                gy = random.randint(0, 9)
                _ = index.get_chunk_by_grid(gx, gy)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        print(f"\n1000 lookups with 100 chunks: {times[0]:.3f}ms")
        print(f"1000 lookups with 500 chunks: {times[1]:.3f}ms")
        print(f"1000 lookups with 1000 chunks: {times[2]:.3f}ms")

        # Times should be roughly similar (O(1) behavior)
        # Allow 3x variance for noise
        assert times[2] < times[0] * 3


class TestBulkInsertionPerformance:
    """Tests for bulk chunk insertion performance."""

    def test_bulk_insertion_1000_chunks(self) -> None:
        """Test inserting 1000 chunks."""
        random.seed(42)
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        start = time.perf_counter()
        for i in range(1000):
            gx = i % 100
            gy = i // 100
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(gx, gy),
                    )
                },
            )
            world.spawn(f"chunk{i}")
        world.tick(0)
        index.invalidate()
        # Force initialization
        _ = index.count()
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nCreating 1000 chunks: {elapsed_ms:.3f}ms")
        # Should complete in reasonable time
        assert elapsed_ms < 2000


class TestIterationPerformance:
    """Tests for chunk iteration performance."""

    def test_iterate_all_chunks(self) -> None:
        """Test iterating over all chunks."""
        random.seed(42)
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Create 500 chunks
        for i in range(500):
            gx = i % 50
            gy = i // 50
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=32,
                        sprite_sheets=["tiles"],
                        grid_index=(gx, gy),
                    )
                },
            )
            world.spawn(f"chunk{i}")
        world.tick(0)
        index.invalidate()

        # Measure iteration
        start = time.perf_counter()
        count = 0
        for chunk in index:
            count += 1
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nIterating 500 chunks: {elapsed_ms:.3f}ms")
        assert count == 500
        assert elapsed_ms < 100


class TestLargeChunkData:
    """Tests for performance with large chunk data."""

    def test_large_tile_arrays(self) -> None:
        """Test chunks with large tile arrays (128x128)."""
        random.seed(42)
        world = World()
        index = create_chunk_index(world, chunk_size=128, auto_register_observer=False)

        start = time.perf_counter()

        # Create 10 large chunks
        for i in range(10):
            # 128x128 = 16384 tiles per layer
            tiles = [random.randint(0, 100) for _ in range(128 * 128)]
            world.register_prefab(
                f"chunk{i}",
                {
                    ChunkMetadata: ChunkMetadata(
                        chunk_size=128,
                        sprite_sheets=["tiles"],
                        grid_index=(i, 0),
                    ),
                    TileVisualLayer: TileVisualLayer(name="ground", tiles=tiles),
                },
            )
            world.spawn(f"chunk{i}")

        world.tick(0)
        index.invalidate()
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nCreating 10 chunks with 128x128 tiles: {elapsed_ms:.3f}ms")
        assert index.count() == 10
        # Should complete reasonably fast
        assert elapsed_ms < 3000


class TestWorldPositionLookup:
    """Tests for world position to chunk lookup performance."""

    def test_world_position_lookup(self) -> None:
        """Test looking up chunks by world position."""
        random.seed(42)
        world = World()
        index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

        # Create 10x10 grid of chunks
        for gx in range(10):
            for gy in range(10):
                i = gx * 10 + gy
                world.register_prefab(
                    f"chunk{i}",
                    {
                        ChunkMetadata: ChunkMetadata(
                            chunk_size=32,
                            sprite_sheets=["tiles"],
                            grid_index=(gx, gy),
                        )
                    },
                )
                world.spawn(f"chunk{i}")
        world.tick(0)
        index.invalidate()

        # Warmup
        _ = index.get_chunk_at_world_pos(50.0, 50.0)

        # Measure world position lookups
        start = time.perf_counter()
        for _ in range(10000):
            x = random.uniform(0, 320)
            y = random.uniform(0, 320)
            _ = index.get_chunk_at_world_pos(x, y)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\n10000 world position lookups: {elapsed_ms:.3f}ms")
        assert elapsed_ms < 100
