"""Performance tests for Relics ECS library.

Run with: pytest -m perf tests/test_performance.py -v -s

These tests are skipped by default. They benchmark core operations at three scales:
- 100 entities (baseline)
- 10,000 entities (typical game)
- 1,000,000 entities (stress test)
"""

import time
from dataclasses import dataclass as stdlib_dataclass
from typing import Callable, List, Optional

import pytest

from relics import Component, World
from relics.system import Frequency, System

from .conftest import (
    AI,
    AllyTo,
    Health,
    Inventory,
    ParentOf,
    PERF_SCALE_IDS,
    PERF_SCALES,
    Position,
    Targets,
    Velocity,
    register_standard_prefabs,
)


# =============================================================================
# Performance Measurement Utilities
# =============================================================================


@stdlib_dataclass
class PerfResult:
    """Stores performance measurement results."""

    operation: str
    scale: int
    total_ops: int
    elapsed: float

    @property
    def ops_per_second(self) -> float:
        """Calculate operations per second."""
        if self.elapsed == 0:
            return float("inf")
        return self.total_ops / self.elapsed

    @property
    def ms_per_op(self) -> float:
        """Calculate milliseconds per operation."""
        if self.total_ops == 0:
            return 0.0
        return (self.elapsed * 1000) / self.total_ops

    def print_report(self) -> None:
        """Print a human-readable report."""
        print("\n" + "=" * 60)
        print(f"Operation: {self.operation}")
        print(f"Scale: {self.scale:,} entities")
        print(f"Total ops: {self.total_ops:,}")
        print(f"Elapsed: {self.elapsed:.4f}s")
        print(f"Throughput: {self.ops_per_second:,.0f} ops/sec")
        print(f"Latency: {self.ms_per_op:.6f} ms/op")
        print("=" * 60)


def measure_time(func: Callable[[], None], iterations: int = 1) -> float:
    """Measure execution time of a function.

    Args:
        func: Function to measure.
        iterations: Number of times to call the function.

    Returns:
        Total elapsed time in seconds.
    """
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    end = time.perf_counter()
    return end - start


def create_world_with_entities(scale: int, prefab: str = "simple") -> World:
    """Create a world populated with entities.

    Args:
        scale: Number of entities to create.
        prefab: Prefab name to use.

    Returns:
        World instance with entities.
    """
    world = World()
    register_standard_prefabs(world)
    for _ in range(scale):
        world.spawn(prefab)
    return world


# =============================================================================
# Test: Spawning Performance
# =============================================================================


@pytest.mark.perf
class TestSpawnPerformance:
    """Performance tests for entity spawning."""

    @pytest.mark.parametrize("scale", PERF_SCALES, ids=PERF_SCALE_IDS)
    def test_spawn_simple(self, scale: int) -> None:
        """Benchmark spawning entities with 1 component."""
        world = World()
        register_standard_prefabs(world)

        elapsed = measure_time(lambda: world.spawn("simple"), scale)

        result = PerfResult("spawn_simple_1_component", scale, scale, elapsed)
        result.print_report()

        # Basic sanity check
        assert len(world._entities) == scale

    @pytest.mark.parametrize("scale", PERF_SCALES, ids=PERF_SCALE_IDS)
    def test_spawn_complex(self, scale: int) -> None:
        """Benchmark spawning entities with 5 components."""
        world = World()
        register_standard_prefabs(world)

        elapsed = measure_time(lambda: world.spawn("complex"), scale)

        result = PerfResult("spawn_complex_5_components", scale, scale, elapsed)
        result.print_report()

        assert len(world._entities) == scale

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_spawn_with_overrides(self, scale: int) -> None:
        """Benchmark spawning with component overrides."""
        world = World()
        register_standard_prefabs(world)

        def spawn_with_override() -> None:
            world.spawn("simple", {Position: Position(x=1.0, y=2.0)})

        elapsed = measure_time(spawn_with_override, scale)

        result = PerfResult("spawn_with_overrides", scale, scale, elapsed)
        result.print_report()

        assert len(world._entities) == scale


# =============================================================================
# Test: Query Performance
# =============================================================================


@pytest.mark.perf
class TestQueryPerformance:
    """Performance tests for entity queries.

    NOTE: Current implementation uses O(n) full scan for all queries.
    See src/relics/query.py:204,219,240 - iterates ALL entities.
    """

    @pytest.mark.parametrize("scale", PERF_SCALES, ids=PERF_SCALE_IDS)
    def test_query_with_all_single(self, scale: int) -> None:
        """Benchmark query.with_all() for single component."""
        world = create_world_with_entities(scale, "movable")

        iterations = 100 if scale < 1_000_000 else 10

        def run_query() -> None:
            list(world.query().with_all([Position]).execute_ids())

        elapsed = measure_time(run_query, iterations)

        result = PerfResult(
            f"query_with_all_single (n={scale})", scale, iterations, elapsed
        )
        result.print_report()
        print("WARNING: O(n) full scan - grows linearly with entity count")

    @pytest.mark.parametrize("scale", PERF_SCALES, ids=PERF_SCALE_IDS)
    def test_query_with_all_multiple(self, scale: int) -> None:
        """Benchmark query.with_all() for multiple components."""
        world = create_world_with_entities(scale, "complex")

        iterations = 100 if scale < 1_000_000 else 10

        def run_query() -> None:
            list(world.query().with_all([Position, Velocity, Health]).execute_ids())

        elapsed = measure_time(run_query, iterations)

        result = PerfResult(
            f"query_with_all_multiple (n={scale})", scale, iterations, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_query_with_any(self, scale: int) -> None:
        """Benchmark query.with_any() for multiple components."""
        world = World()
        register_standard_prefabs(world)

        # Create mixed entities
        for i in range(scale):
            if i % 3 == 0:
                world.spawn("simple")
            elif i % 3 == 1:
                world.spawn("movable")
            else:
                world.spawn("complex")

        iterations = 100

        def run_query() -> None:
            list(world.query().with_any([Health, AI]).execute_ids())

        elapsed = measure_time(run_query, iterations)

        result = PerfResult(f"query_with_any (n={scale})", scale, iterations, elapsed)
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_query_with_none(self, scale: int) -> None:
        """Benchmark query.with_none() for component exclusion."""
        world = World()
        register_standard_prefabs(world)

        # Create mixed entities
        for i in range(scale):
            if i % 2 == 0:
                world.spawn("simple")
            else:
                world.spawn("complex")

        iterations = 100

        def run_query() -> None:
            list(world.query().with_all([Position]).with_none([AI]).execute_ids())

        elapsed = measure_time(run_query, iterations)

        result = PerfResult(f"query_with_none (n={scale})", scale, iterations, elapsed)
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_query_combined(self, scale: int) -> None:
        """Benchmark complex query with all filters."""
        world = World()
        register_standard_prefabs(world)

        # Create mixed entities
        for i in range(scale):
            if i % 4 == 0:
                world.spawn("simple")
            elif i % 4 == 1:
                world.spawn("movable")
            elif i % 4 == 2:
                world.spawn("player")
            else:
                world.spawn("npc")

        iterations = 100

        def run_query() -> None:
            list(
                world.query()
                .with_all([Position, Velocity])
                .with_any([Health, Inventory])
                .with_none([AI])
                .execute_ids()
            )

        elapsed = measure_time(run_query, iterations)

        result = PerfResult(f"query_combined (n={scale})", scale, iterations, elapsed)
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_query_execute_ids_vs_entities(self, scale: int) -> None:
        """Compare execute_ids() vs execute_entities() performance."""
        world = create_world_with_entities(scale, "complex")

        iterations = 100

        # Test execute_ids
        def run_ids_query() -> None:
            list(world.query().with_all([Position]).execute_ids())

        elapsed_ids = measure_time(run_ids_query, iterations)

        # Test execute_entities
        def run_entities_query() -> None:
            list(world.query().with_all([Position]).execute_entities())

        elapsed_entities = measure_time(run_entities_query, iterations)

        result_ids = PerfResult(
            f"execute_ids (n={scale})", scale, iterations, elapsed_ids
        )
        result_entities = PerfResult(
            f"execute_entities (n={scale})", scale, iterations, elapsed_entities
        )

        result_ids.print_report()
        result_entities.print_report()

        print(f"\nexecute_entities overhead: {elapsed_entities / elapsed_ids:.2f}x")


# =============================================================================
# Test: Component Access Performance
# =============================================================================


@pytest.mark.perf
class TestComponentAccessPerformance:
    """Performance tests for component access operations."""

    @pytest.mark.parametrize("scale", PERF_SCALES, ids=PERF_SCALE_IDS)
    def test_get_component(self, scale: int) -> None:
        """Benchmark get_component() - expected O(1)."""
        world = create_world_with_entities(scale, "complex")

        # Get a sample entity
        entity_id = next(iter(world._entities.keys()))
        entity = world.get_entity(entity_id)

        iterations = 100_000

        def get_component() -> None:
            entity.get_component(Position)

        elapsed = measure_time(get_component, iterations)

        result = PerfResult(
            f"get_component (n={scale})", scale, iterations, elapsed
        )
        result.print_report()
        print("EXPECTED: ~constant time (O(1) dict lookup)")

    @pytest.mark.parametrize("scale", PERF_SCALES, ids=PERF_SCALE_IDS)
    def test_has_component(self, scale: int) -> None:
        """Benchmark has_component() - expected O(1)."""
        world = create_world_with_entities(scale, "complex")

        entity_id = next(iter(world._entities.keys()))
        entity = world.get_entity(entity_id)

        iterations = 100_000

        def has_component() -> None:
            entity.has_component(Position)

        elapsed = measure_time(has_component, iterations)

        result = PerfResult(
            f"has_component (n={scale})", scale, iterations, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_add_component(self, scale: int) -> None:
        """Benchmark add_component()."""
        from pydantic.dataclasses import dataclass as pydantic_dataclass

        @pydantic_dataclass
        class Tag(Component):
            """Simple tag component for testing."""

            value: int = 0

        world = create_world_with_entities(scale, "simple")
        entities = list(world.query().with_all([Position]).execute_entities())

        def add_components() -> None:
            for i, entity in enumerate(entities):
                entity.add_component(Tag(value=i))

        elapsed = measure_time(add_components, 1)

        result = PerfResult(f"add_component (n={scale})", scale, scale, elapsed)
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_remove_component(self, scale: int) -> None:
        """Benchmark remove_component()."""
        world = create_world_with_entities(scale, "complex")
        entities = list(world.query().with_all([AI]).execute_entities())

        def remove_components() -> None:
            for entity in entities:
                entity.remove_component(AI)

        elapsed = measure_time(remove_components, 1)

        result = PerfResult(f"remove_component (n={scale})", scale, scale, elapsed)
        result.print_report()


# =============================================================================
# Test: Relationship Performance
# =============================================================================


@pytest.mark.perf
class TestRelationshipPerformance:
    """Performance tests for relationship operations.

    NOTE: Relationship removal uses O(k) linear search.
    See src/relics/world.py:401-406 - searches through edges list.
    """

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_add_relationship_chain(self, scale: int) -> None:
        """Benchmark adding relationships in a chain (A->B->C->...)."""
        world = create_world_with_entities(scale, "simple")
        entities = list(world.query().with_all([Position]).execute_entities())

        def add_chain() -> None:
            for i in range(len(entities) - 1):
                entities[i].add_relationship(ParentOf(), entities[i + 1].id)

        elapsed = measure_time(add_chain, 1)

        result = PerfResult(
            f"add_relationship_chain (n={scale})", scale, scale - 1, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_add_relationship_many_to_one(self, scale: int) -> None:
        """Benchmark adding many relationships to one target."""
        world = create_world_with_entities(scale, "simple")
        entities = list(world.query().with_all([Position]).execute_entities())
        target = entities[0]

        def add_many_to_one() -> None:
            for entity in entities[1:]:
                entity.add_relationship(Targets(priority=1), target.id)

        elapsed = measure_time(add_many_to_one, 1)

        result = PerfResult(
            f"add_relationship_many_to_one (n={scale})", scale, scale - 1, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", [100, 1000], ids=["100", "1k"])
    def test_remove_relationship(self, scale: int) -> None:
        """Benchmark removing relationships.

        NOTE: Uses smaller scale due to O(k) removal complexity.
        """
        world = create_world_with_entities(scale, "simple")
        entities = list(world.query().with_all([Position]).execute_entities())

        # First add relationships
        for i in range(len(entities) - 1):
            entities[i].add_relationship(ParentOf(), entities[i + 1].id)

        def remove_chain() -> None:
            for i in range(len(entities) - 1):
                entities[i].remove_relationship(ParentOf, entities[i + 1].id)

        elapsed = measure_time(remove_chain, 1)

        result = PerfResult(
            f"remove_relationship_chain (n={scale})", scale, scale - 1, elapsed
        )
        result.print_report()
        print("WARNING: O(k) linear search per removal")

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_query_outgoing_relationships(self, scale: int) -> None:
        """Benchmark querying outgoing relationships."""
        world = create_world_with_entities(scale, "simple")
        entities = list(world.query().with_all([Position]).execute_entities())

        # Create chain of relationships
        for i in range(len(entities) - 1):
            entities[i].add_relationship(ParentOf(), entities[i + 1].id)

        iterations = 1000

        def query_outgoing() -> None:
            for entity in entities[:100]:  # Sample first 100
                entity.get_relationships(ParentOf)

        elapsed = measure_time(query_outgoing, iterations)

        result = PerfResult(
            f"query_outgoing_relationships (n={scale})",
            scale,
            iterations * 100,
            elapsed,
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_query_incoming_relationships(self, scale: int) -> None:
        """Benchmark querying incoming relationships."""
        world = create_world_with_entities(scale, "simple")
        entities = list(world.query().with_all([Position]).execute_entities())
        target = entities[0]

        # All entities point to target
        for entity in entities[1:]:
            entity.add_relationship(Targets(priority=1), target.id)

        iterations = 10000

        def query_incoming() -> None:
            target.get_incoming_relationships(Targets)

        elapsed = measure_time(query_incoming, iterations)

        result = PerfResult(
            f"query_incoming_relationships (n={scale})", scale, iterations, elapsed
        )
        result.print_report()


# =============================================================================
# Test: Tick/Systems Performance
# =============================================================================


@pytest.mark.perf
class TestTickPerformance:
    """Performance tests for tick and system execution."""

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_tick_single_system(self, scale: int) -> None:
        """Benchmark tick with one system."""

        class MovementSystem(System):
            def query(self):
                return self.world.query().with_all([Position, Velocity])

            def process(self, entities, components, delta):
                for entity in entities:
                    pos = entity.get_component(Position)
                    vel = entity.get_component(Velocity)
                    # Simulated update (immutable, so just read)
                    _ = pos.x + vel.vx * delta
                    _ = pos.y + vel.vy * delta

        world = create_world_with_entities(scale, "movable")
        world.register_system(MovementSystem())

        iterations = 100

        def run_tick() -> None:
            world.tick(0.016)

        elapsed = measure_time(run_tick, iterations)

        result = PerfResult(
            f"tick_single_system (n={scale})", scale, iterations, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_tick_five_systems(self, scale: int) -> None:
        """Benchmark tick with 5 systems."""

        class System1(System):
            def query(self):
                return self.world.query().with_all([Position])

            def process(self, entities, components, delta):
                for e in entities:
                    e.get_component(Position)

        class System2(System):
            def query(self):
                return self.world.query().with_all([Velocity])

            def process(self, entities, components, delta):
                for e in entities:
                    e.get_component(Velocity)

        class System3(System):
            def query(self):
                return self.world.query().with_all([Health])

            def process(self, entities, components, delta):
                for e in entities:
                    e.get_component(Health)

        class System4(System):
            def query(self):
                return self.world.query().with_all([AI])

            def process(self, entities, components, delta):
                for e in entities:
                    e.get_component(AI)

        class System5(System):
            def query(self):
                return self.world.query().with_all([Position, Velocity])

            def process(self, entities, components, delta):
                pass

        world = create_world_with_entities(scale, "complex")
        for sys_class in [System1, System2, System3, System4, System5]:
            world.register_system(sys_class())

        iterations = 100

        def run_tick() -> None:
            world.tick(0.016)

        elapsed = measure_time(run_tick, iterations)

        result = PerfResult(
            f"tick_five_systems (n={scale})", scale, iterations, elapsed
        )
        result.print_report()


# =============================================================================
# Test: Index Performance
# =============================================================================


@pytest.mark.perf
class TestIndexPerformance:
    """Performance tests for secondary indexes."""

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_lazy_index_iteration(self, scale: int) -> None:
        """Benchmark lazy index iteration (re-executes query)."""
        world = create_world_with_entities(scale, "complex")

        query = world.query().with_all([Position, Health])
        index = world.create_index("test_lazy", query, materialized=False)

        iterations = 100

        def iterate_index() -> None:
            list(index)

        elapsed = measure_time(iterate_index, iterations)

        result = PerfResult(
            f"lazy_index_iteration (n={scale})", scale, iterations, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_materialized_index_iteration(self, scale: int) -> None:
        """Benchmark materialized index iteration (cached)."""
        world = create_world_with_entities(scale, "complex")

        query = world.query().with_all([Position, Health])
        index = world.create_index(
            "test_mat", query, watches=[Position, Health], materialized=True
        )

        # Force initialization
        list(index)

        iterations = 100

        def iterate_index() -> None:
            list(index)

        elapsed = measure_time(iterate_index, iterations)

        result = PerfResult(
            f"materialized_index_iteration (n={scale})", scale, iterations, elapsed
        )
        result.print_report()

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_index_count_comparison(self, scale: int) -> None:
        """Compare count() performance between lazy and materialized indexes."""
        world = create_world_with_entities(scale, "complex")

        query_lazy = world.query().with_all([Position, Health])
        query_mat = world.query().with_all([Position, Health])

        lazy_index = world.create_index("lazy", query_lazy, materialized=False)
        mat_index = world.create_index(
            "mat", query_mat, watches=[Position, Health], materialized=True
        )

        # Force initialization of materialized index
        mat_index.count()

        iterations = 100

        elapsed_lazy = measure_time(lambda: lazy_index.count(), iterations)
        elapsed_mat = measure_time(lambda: mat_index.count(), iterations)

        result_lazy = PerfResult(
            f"lazy_index_count (n={scale})", scale, iterations, elapsed_lazy
        )
        result_mat = PerfResult(
            f"materialized_index_count (n={scale})", scale, iterations, elapsed_mat
        )

        result_lazy.print_report()
        result_mat.print_report()

        print(f"\nMaterialized speedup: {elapsed_lazy / elapsed_mat:.2f}x")


# =============================================================================
# Test: Observer Queue Performance
# =============================================================================


@pytest.mark.perf
class TestObserverQueuePerformance:
    """Performance tests for observer queue processing.

    NOTE: Observer queue uses list.pop(0) which is O(n).
    See src/relics/world.py:793 - should use collections.deque.
    """

    @pytest.mark.parametrize("scale", PERF_SCALES[:2], ids=PERF_SCALE_IDS[:2])
    def test_observer_queue_processing(self, scale: int) -> None:
        """Benchmark observer queue with many events."""
        from relics.observer import OnEntityCreated

        events_received = [0]

        class CountingObserver(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity):
                events_received[0] += 1

        world = World()
        register_standard_prefabs(world)
        world.observe(CountingObserver())

        # Spawn entities (queues events)
        for _ in range(scale):
            world.spawn("simple")

        events_received[0] = 0

        def process_queue() -> None:
            world._process_observer_queue()

        # Events already queued from spawning
        elapsed = measure_time(process_queue, 1)

        result = PerfResult(
            f"observer_queue_processing (n={scale})", scale, scale, elapsed
        )
        result.print_report()
        print("WARNING: Uses list.pop(0) which is O(n). Consider deque.popleft()")


# =============================================================================
# Test: Scaling Analysis
# =============================================================================


@pytest.mark.perf
class TestScalingAnalysis:
    """Summary tests comparing scaling behavior across operations."""

    def test_scaling_summary(self) -> None:
        """Print a summary comparing O(1) vs O(n) operations across scales."""
        scales = [100, 10_000]
        results: dict[str, dict[int, float]] = {
            "spawn": {},
            "query": {},
            "access": {},
        }

        for scale in scales:
            # Spawn timing
            world = World()
            register_standard_prefabs(world)
            elapsed = measure_time(lambda: world.spawn("complex"), scale)
            results["spawn"][scale] = (elapsed * 1000) / scale  # ms per entity

            # Query timing
            world = create_world_with_entities(scale, "complex")
            iterations = 100
            elapsed = measure_time(
                lambda: list(world.query().with_all([Position]).execute_ids()),
                iterations,
            )
            results["query"][scale] = (elapsed * 1000) / iterations  # ms per query

            # Access timing
            entity_id = next(iter(world._entities.keys()))
            entity = world.get_entity(entity_id)
            iterations = 10000
            elapsed = measure_time(lambda: entity.get_component(Position), iterations)
            results["access"][scale] = (elapsed * 1000) / iterations  # ms per access

        print("\n")
        print("=" * 70)
        print("SCALING ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"{'Scale':>12} | {'Spawn (ms/ent)':>14} | {'Query (ms/op)':>14} | {'Access (ms/op)':>14}")
        print("-" * 70)

        for scale in scales:
            print(
                f"{scale:>12,} | "
                f"{results['spawn'][scale]:>14.6f} | "
                f"{results['query'][scale]:>14.6f} | "
                f"{results['access'][scale]:>14.6f}"
            )

        print("-" * 70)
        print("EXPECTED BEHAVIOR:")
        print("  - Spawn: Should be ~constant per entity (O(1))")
        print("  - Query: Grows linearly with scale (O(n) full scan)")
        print("  - Access: Should be ~constant (O(1) dict lookup)")
        print("=" * 70)

        # Calculate scaling factors
        if len(scales) >= 2:
            scale_factor = scales[1] / scales[0]
            query_growth = results["query"][scales[1]] / results["query"][scales[0]]
            print(f"\nScale increased {scale_factor:.0f}x:")
            print(f"  - Query time growth: {query_growth:.1f}x (expected ~{scale_factor:.0f}x for O(n))")


# =============================================================================
# Test: Known Bottlenecks
# =============================================================================


@pytest.mark.perf
class TestKnownBottlenecks:
    """Tests specifically highlighting known performance bottlenecks."""

    def test_query_full_scan_bottleneck(self) -> None:
        """Demonstrate O(n) query bottleneck.

        Location: src/relics/query.py:204,219,240
        Issue: Every query iterates ALL entities.
        Recommendation: Consider archetype-based storage.
        """
        from pydantic.dataclasses import dataclass as pydantic_dataclass

        @pydantic_dataclass
        class Marker(Component):
            """Marker component for sparse query testing."""

            value: int = 0

        print("\n" + "=" * 70)
        print("BOTTLENECK: Query Full Scan")
        print("Location: src/relics/query.py:204,219,240")
        print("=" * 70)

        for scale in [1000, 10000]:
            world = create_world_with_entities(scale, "simple")

            # Add marker to only ~10% of entities
            for i, entity_id in enumerate(list(world._entities.keys())):
                if i % 10 == 0:
                    entity = world.get_entity(entity_id)
                    entity.add_component(Marker(value=i))

            iterations = 100
            elapsed = measure_time(
                lambda: list(world.query().with_all([Marker]).execute_ids()), iterations
            )

            print(f"Scale {scale:,}: {elapsed/iterations*1000:.4f}ms per query")

        print("\nRecommendation: Consider archetype-based storage for O(1) lookup")

    def test_observer_queue_pop_bottleneck(self) -> None:
        """Demonstrate O(n) observer queue dequeue bottleneck.

        Location: src/relics/world.py:793
        Issue: list.pop(0) is O(n)
        Recommendation: Use collections.deque.popleft() for O(1)
        """
        print("\n" + "=" * 70)
        print("BOTTLENECK: Observer Queue Dequeue")
        print("Location: src/relics/world.py:793")
        print("=" * 70)

        from relics.observer import OnEntityCreated

        class NoOpObserver(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity):
                pass

        for scale in [1000, 10000]:
            world = World()
            register_standard_prefabs(world)
            world.observe(NoOpObserver())

            # Queue up many events
            for _ in range(scale):
                world.spawn("simple")

            # Time the queue processing
            elapsed = measure_time(world._process_observer_queue, 1)
            print(f"Scale {scale:,}: {elapsed*1000:.4f}ms to process queue")

        print("\nRecommendation: Use collections.deque.popleft() for O(1) dequeue")
