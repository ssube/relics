"""Performance tests for component change tracking.

These tests measure the performance of the component change tracking system.
Run baseline tests before making changes, then compare after optimization.

Usage:
    pytest tests/test_component_change_performance.py -v -s --tb=short
"""

import time
from typing import Any, List

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, OnComponentChanged, World, monitored


@monitored
@dataclass
class Health(Component):
    """Monitored health component for performance testing."""

    current: int
    maximum: int


class TestComponentChangePerformance:
    """Performance tests for component change tracking."""

    @pytest.mark.parametrize("scale", [100, 1000, 10000], ids=["100", "1k", "10k"])
    def test_single_field_change(self, scale: int) -> None:
        """Benchmark single field changes on monitored components."""
        world = World()
        world.register_prefab("unit", {Health: Health(current=100, maximum=100)})

        # Spawn entities
        entities = [world.spawn("unit") for _ in range(scale)]
        components = [e.get_component(Health) for e in entities]
        for c, e in zip(components, entities):
            c._bind_to_world(world, e.id)

        # Measure time to change all component fields
        start = time.perf_counter()
        for component in components:
            component.current = 80  # Single field change
        elapsed = time.perf_counter() - start

        print(f"\nScale {scale}: {elapsed*1000:.4f}ms for {scale} field changes")
        print(f"  Per-change: {elapsed/scale*1000000:.2f}us")

    @pytest.mark.parametrize("scale", [100, 1000, 10000], ids=["100", "1k", "10k"])
    def test_multiple_field_changes(self, scale: int) -> None:
        """Benchmark changing multiple fields on same component."""
        world = World()
        world.register_prefab("unit", {Health: Health(current=100, maximum=100)})

        entities = [world.spawn("unit") for _ in range(scale)]
        components = [e.get_component(Health) for e in entities]
        for c, e in zip(components, entities):
            c._bind_to_world(world, e.id)

        start = time.perf_counter()
        for component in components:
            component.current = 80  # Change 1
            component.maximum = 120  # Change 2
        elapsed = time.perf_counter() - start

        print(f"\nScale {scale}: {elapsed*1000:.4f}ms for {scale*2} field changes")
        print(f"  Per-change: {elapsed/(scale*2)*1000000:.2f}us")

    @pytest.mark.parametrize("scale", [100, 1000], ids=["100", "1k"])
    def test_observer_with_changes(self, scale: int) -> None:
        """Benchmark full cycle: change -> queue -> dispatch -> observer."""
        changes_received: List[Any] = []

        class ChangeCounter(OnComponentChanged):
            component_type = Health

            def on_component_changed(self, *args: Any) -> None:
                changes_received.append(args)

        world = World()
        world.register_prefab("unit", {Health: Health(current=100, maximum=100)})
        world.observe(ChangeCounter())

        entities = [world.spawn("unit") for _ in range(scale)]
        components = [e.get_component(Health) for e in entities]
        for c, e in zip(components, entities):
            c._bind_to_world(world, e.id)

        start = time.perf_counter()
        for component in components:
            component.current = 80
        world.tick(0)  # Process observer queue
        elapsed = time.perf_counter() - start

        assert len(changes_received) == scale
        print(f"\nScale {scale}: {elapsed*1000:.4f}ms for full change cycle")
        print(f"  Per-change (incl. observer): {elapsed/scale*1000000:.2f}us")

    def test_memory_allocation(self) -> None:
        """Measure memory allocations during component changes."""
        import tracemalloc

        world = World()
        world.register_prefab("unit", {Health: Health(current=100, maximum=100)})

        entity = world.spawn("unit")
        health = entity.get_component(Health)
        health._bind_to_world(world, entity.id)

        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        # Perform 1000 field changes
        for i in range(1000):
            health.current = 100 - (i % 50)

        snapshot2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        diff = snapshot2.compare_to(snapshot1, "lineno")
        total_allocated = sum(stat.size_diff for stat in diff if stat.size_diff > 0)

        print(f"\nMemory allocated for 1000 changes: {total_allocated / 1024:.2f} KB")
        print(f"  Per-change: {total_allocated / 1000:.0f} bytes")
