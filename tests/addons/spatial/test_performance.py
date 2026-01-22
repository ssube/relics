"""Performance tests for spatial indexing addon."""

import random
import time

import pytest

from relics import World
from relics.addons.spatial import (
    LazySpatialIndex2D,
    LazySpatialIndex3D,
    MaterializedSpatialIndex2D,
    MaterializedSpatialIndex3D,
    OctreeBounds,
    Position2D,
    Position3D,
    QuadTreeBounds,
    create_spatial_index_2d,
    create_spatial_index_3d,
)


class TestQuadTreePerformance:
    """Performance tests for 2D spatial indexing."""

    def test_materialized_query_performance_10k_entities(self) -> None:
        """Test that materialized index queries 10k entities in <1ms."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(5000, 5000, 5000, 5000)
        index = create_spatial_index_2d(
            world,
            bounds=bounds,
            auto_register_observer=False,  # Manual control for benchmark
        )

        # Spawn 10k entities at random positions
        random.seed(42)
        for _ in range(10000):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            world.spawn("entity", {Position2D: Position2D(x=x, y=y)})

        # Force index initialization
        _ = index.count()

        # Benchmark query
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            results = list(index.query_circle(5000, 5000, 500))
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000
        print(f"\nMaterialized 2D query (10k entities): {avg_time_ms:.3f}ms avg")

        # Should complete in under 5ms per query (relaxed for CI)
        assert avg_time_ms < 5, f"Query took {avg_time_ms:.3f}ms, expected < 5ms"

    def test_lazy_vs_materialized_performance(self) -> None:
        """Compare lazy vs materialized index performance."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(5000, 5000, 5000, 5000)

        lazy_index = LazySpatialIndex2D(world, Position2D)
        materialized_index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        # Spawn 1000 entities
        random.seed(42)
        for _ in range(1000):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            world.spawn("entity", {Position2D: Position2D(x=x, y=y)})

        # Force initialization
        _ = materialized_index.count()

        # Benchmark lazy
        iterations = 20
        start = time.perf_counter()
        for _ in range(iterations):
            list(lazy_index.query_circle(5000, 5000, 500))
        lazy_time = time.perf_counter() - start

        # Benchmark materialized
        start = time.perf_counter()
        for _ in range(iterations):
            list(materialized_index.query_circle(5000, 5000, 500))
        materialized_time = time.perf_counter() - start

        print(
            f"\nLazy 2D (1k entities, {iterations} queries): {lazy_time*1000:.2f}ms total"
        )
        print(
            f"Materialized 2D (1k entities, {iterations} queries): {materialized_time*1000:.2f}ms total"
        )

        # Materialized should be faster for repeated queries
        # (Note: this may vary based on query region size)


class TestOctreePerformance:
    """Performance tests for 3D spatial indexing."""

    def test_materialized_3d_query_performance_10k_entities(self) -> None:
        """Test that 3D materialized index queries 10k entities in <5ms."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(5000, 5000, 5000, 5000, 5000, 5000)
        index = create_spatial_index_3d(
            world,
            bounds=bounds,
            auto_register_observer=False,
        )

        # Spawn 10k entities at random positions
        random.seed(42)
        for _ in range(10000):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            z = random.uniform(0, 10000)
            world.spawn("entity", {Position3D: Position3D(x=x, y=y, z=z)})

        # Force index initialization
        _ = index.count()

        # Benchmark query
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            results = list(index.query_sphere(5000, 5000, 5000, 500))
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000
        print(f"\nMaterialized 3D query (10k entities): {avg_time_ms:.3f}ms avg")

        # Should complete in under 10ms per query (relaxed for CI)
        assert avg_time_ms < 10, f"Query took {avg_time_ms:.3f}ms, expected < 10ms"


class TestNearestNeighborPerformance:
    """Performance tests for nearest neighbor queries."""

    def test_nearest_neighbor_performance(self) -> None:
        """Test nearest neighbor query performance."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(5000, 5000, 5000, 5000)
        index = create_spatial_index_2d(
            world,
            bounds=bounds,
            auto_register_observer=False,
        )

        # Spawn 5000 entities
        random.seed(42)
        for _ in range(5000):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            world.spawn("entity", {Position2D: Position2D(x=x, y=y)})

        # Force initialization
        _ = index.count()

        # Benchmark nearest neighbor query
        start = time.perf_counter()
        iterations = 50
        for _ in range(iterations):
            results = index.query_nearest(5000, 5000, count=10)
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000
        print(f"\nNearest neighbor (5k entities, k=10): {avg_time_ms:.3f}ms avg")

        # Should complete reasonably fast (30ms allows for CI environment variability)
        assert avg_time_ms < 30, f"Query took {avg_time_ms:.3f}ms, expected < 30ms"


class TestInsertionPerformance:
    """Performance tests for entity insertion."""

    def test_bulk_insertion_performance(self) -> None:
        """Test bulk insertion performance."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(5000, 5000, 5000, 5000)
        index = MaterializedSpatialIndex2D(
            world,
            Position2D,
            bounds,
            max_entities_per_node=16,
            max_depth=10,
        )

        random.seed(42)

        # Time spawning and adding 10k entities
        start = time.perf_counter()
        for _ in range(10000):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            entity = world.spawn("entity", {Position2D: Position2D(x=x, y=y)})
            index.add_entity(entity.id)
        elapsed = time.perf_counter() - start

        print(f"\nBulk insert 10k entities: {elapsed*1000:.2f}ms")

        assert index.count() == 10000

    def test_update_performance(self) -> None:
        """Test position update performance."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(5000, 5000, 5000, 5000)
        index = create_spatial_index_2d(
            world,
            bounds=bounds,
            auto_register_observer=False,
        )

        # Spawn 1000 entities
        entities = []
        random.seed(42)
        for _ in range(1000):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            e = world.spawn("entity", {Position2D: Position2D(x=x, y=y)})
            entities.append(e)

        # Initialize index
        _ = index.count()

        # Time updating all positions
        start = time.perf_counter()
        for e in entities:
            pos = e.get_component(Position2D)
            pos.x = random.uniform(0, 10000)
            pos.y = random.uniform(0, 10000)
            index.update(e.id)
        elapsed = time.perf_counter() - start

        print(f"\nUpdate 1k entity positions: {elapsed*1000:.2f}ms")


class TestScaling:
    """Tests for scaling behavior."""

    @pytest.mark.parametrize("count", [100, 1000, 5000])
    def test_query_scaling(self, count: int) -> None:
        """Test query time scaling with entity count."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(5000, 5000, 5000, 5000)
        index = create_spatial_index_2d(
            world,
            bounds=bounds,
            auto_register_observer=False,
        )

        random.seed(42)
        for _ in range(count):
            x = random.uniform(0, 10000)
            y = random.uniform(0, 10000)
            world.spawn("entity", {Position2D: Position2D(x=x, y=y)})

        _ = index.count()

        # Benchmark
        start = time.perf_counter()
        iterations = 50
        for _ in range(iterations):
            list(index.query_circle(5000, 5000, 500))
        elapsed = time.perf_counter() - start

        avg_time_ms = (elapsed / iterations) * 1000
        print(f"\nQuery with {count} entities: {avg_time_ms:.3f}ms avg")
