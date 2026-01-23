"""Tests for WorldMetricsCollector."""

import pytest
from prometheus_client import REGISTRY
from pydantic.dataclasses import dataclass

from relics import Component, Edge, World
from relics.addons.prometheus import (
    COMPONENT_TYPES_COUNT,
    ENTITIES_BY_COMPONENT,
    ENTITIES_BY_PREFAB,
    ENTITY_COUNT,
    INDEX_COUNT,
    INDEX_ENTITY_COUNT,
    OBSERVER_COUNT,
    OBSERVER_QUEUE_LENGTH,
    PREFAB_COUNT,
    RELATIONSHIP_COUNT,
    RELATIONSHIPS_BY_TYPE,
    SYSTEM_COUNT,
    TICK_COUNT,
    TICK_DURATION,
    WORLD_EPOCH,
    WorldMetricsCollector,
)
from relics.index import MaterializedIndex
from relics.system import System


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@dataclass
class Health(Component):
    """Test component for health."""

    current: int
    maximum: int


@dataclass
class AllyTo(Edge):
    """Test edge type."""

    trust: float = 1.0


class TestWorldMetricsCollectorInit:
    """Tests for WorldMetricsCollector initialization."""

    def test_collector_creation(self) -> None:
        """Test basic collector creation."""
        world = World()
        collector = WorldMetricsCollector(world, world_id="test_world")

        assert collector.world_id == "test_world"
        assert collector._world == world

    def test_collector_with_default_id(self) -> None:
        """Test collector with default world ID."""
        world = World()
        collector = WorldMetricsCollector(world)

        assert collector.world_id == "default"

    def test_collector_auto_collect_enabled(self) -> None:
        """Test collector with auto-collection enabled."""
        world = World()
        collector = WorldMetricsCollector(
            world, world_id="test", collect_on_tick=True
        )

        # Original tick should be saved
        assert collector._original_tick is not None


class TestWorldMetricsCollectorEntityMetrics:
    """Tests for entity-related metrics collection."""

    def test_collect_entity_count(self) -> None:
        """Test that entity count is collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_entities")

        world.spawn("player")
        world.spawn("player")
        world.tick(0)

        collector.collect()

        # Check metric value
        value = ENTITY_COUNT.labels(world_id="test_entities")._value.get()
        assert value == 2

    def test_collect_entities_by_prefab(self) -> None:
        """Test that entities by prefab are collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=50, maximum=50)})
        collector = WorldMetricsCollector(world, world_id="test_prefab")

        world.spawn("player")
        world.spawn("player")
        world.spawn("enemy")
        world.tick(0)

        collector.collect()

        player_count = ENTITIES_BY_PREFAB.labels(
            world_id="test_prefab", prefab="player"
        )._value.get()
        enemy_count = ENTITIES_BY_PREFAB.labels(
            world_id="test_prefab", prefab="enemy"
        )._value.get()

        assert player_count == 2
        assert enemy_count == 1

    def test_collect_entities_by_component(self) -> None:
        """Test that entities by component are collected."""
        world = World()
        world.register_prefab("player", {
            Position: Position(x=0, y=0),
            Health: Health(current=100, maximum=100),
        })
        world.register_prefab("obstacle", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_component")

        world.spawn("player")
        world.spawn("obstacle")
        world.tick(0)

        collector.collect()

        position_count = ENTITIES_BY_COMPONENT.labels(
            world_id="test_component", component="Position"
        )._value.get()
        health_count = ENTITIES_BY_COMPONENT.labels(
            world_id="test_component", component="Health"
        )._value.get()

        assert position_count == 2  # Both player and obstacle have Position
        assert health_count == 1  # Only player has Health

    def test_collect_component_types_count(self) -> None:
        """Test that component types count is collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Health)
        collector = WorldMetricsCollector(world, world_id="test_comp_types")

        collector.collect()

        count = COMPONENT_TYPES_COUNT.labels(
            world_id="test_comp_types"
        )._value.get()
        assert count >= 2  # At least Position and Health

    def test_collect_prefab_count(self) -> None:
        """Test that prefab count is collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=50, maximum=50)})
        collector = WorldMetricsCollector(world, world_id="test_prefab_count")

        collector.collect()

        count = PREFAB_COUNT.labels(world_id="test_prefab_count")._value.get()
        assert count == 2


class TestWorldMetricsCollectorSystemMetrics:
    """Tests for system-related metrics collection."""

    def test_collect_system_count(self) -> None:
        """Test that system count is collected."""
        world = World()

        class TestSystem(System):
            def query(self):
                return self.world.query()

            def process(self, entities, components, delta: float) -> None:
                pass

        world.register_system(TestSystem())
        collector = WorldMetricsCollector(world, world_id="test_systems")

        collector.collect()

        count = SYSTEM_COUNT.labels(world_id="test_systems")._value.get()
        assert count == 1

    def test_record_system_execution(self) -> None:
        """Test recording system execution time."""
        world = World()
        collector = WorldMetricsCollector(world, world_id="test_sys_exec")

        collector.record_system_execution("TestSystem", 0.005)

        # Histogram observation should be recorded
        # (We can't easily check histogram values, but we can verify no error)


class TestWorldMetricsCollectorObserverMetrics:
    """Tests for observer-related metrics collection."""

    def test_collect_observer_count(self) -> None:
        """Test that observer count is collected."""
        from relics import OnEntityCreated

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        class TestObserver(OnEntityCreated):
            prefab = "player"

            def on_entity_created(self, entity):
                pass

        world.observe(TestObserver())
        collector = WorldMetricsCollector(world, world_id="test_observers")

        collector.collect()

        count = OBSERVER_COUNT.labels(world_id="test_observers")._value.get()
        assert count >= 1

    def test_collect_observer_queue_length(self) -> None:
        """Test that observer queue length is collected."""
        world = World()
        collector = WorldMetricsCollector(world, world_id="test_obs_queue")

        collector.collect()

        # Queue should be empty initially
        length = OBSERVER_QUEUE_LENGTH.labels(
            world_id="test_obs_queue"
        )._value.get()
        assert length == 0


class TestWorldMetricsCollectorIndexMetrics:
    """Tests for index-related metrics collection."""

    def test_collect_index_count(self) -> None:
        """Test that index count is collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        # Create and register an index
        index = MaterializedIndex(world, world.query().with_all([Position]), [Position])
        world._indexes["position_index"] = index

        collector = WorldMetricsCollector(world, world_id="test_indexes")
        collector.collect()

        count = INDEX_COUNT.labels(world_id="test_indexes")._value.get()
        assert count >= 1

    def test_collect_index_entity_count(self) -> None:
        """Test that index entity counts are collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        # Spawn entities first
        world.spawn("player")
        world.spawn("player")
        world.tick(0)

        # Create and register an index
        index = MaterializedIndex(world, world.query().with_all([Position]), [Position])
        world._indexes["position_index"] = index

        collector = WorldMetricsCollector(world, world_id="test_idx_count")
        collector.collect()

        count = INDEX_ENTITY_COUNT.labels(
            world_id="test_idx_count", index_name="position_index"
        )._value.get()
        assert count == 2


class TestWorldMetricsCollectorRelationshipMetrics:
    """Tests for relationship-related metrics collection."""

    def test_collect_relationship_count(self) -> None:
        """Test that relationship count is collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        world.tick(0)

        p1.add_relationship(AllyTo(trust=0.9), p2.id)
        world.tick(0)

        collector = WorldMetricsCollector(world, world_id="test_rels")
        collector.collect()

        count = RELATIONSHIP_COUNT.labels(world_id="test_rels")._value.get()
        assert count == 1

    def test_collect_relationships_by_type(self) -> None:
        """Test that relationships by type are collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")
        world.tick(0)

        p1.add_relationship(AllyTo(trust=0.9), p2.id)
        p1.add_relationship(AllyTo(trust=0.8), p3.id)
        world.tick(0)

        collector = WorldMetricsCollector(world, world_id="test_rel_type")
        collector.collect()

        count = RELATIONSHIPS_BY_TYPE.labels(
            world_id="test_rel_type", edge_type="AllyTo"
        )._value.get()
        assert count == 2


class TestWorldMetricsCollectorWorldStateMetrics:
    """Tests for world state metrics collection."""

    def test_collect_world_epoch(self) -> None:
        """Test that world epoch is collected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        for _ in range(5):
            world.tick(0.016)

        collector = WorldMetricsCollector(world, world_id="test_epoch")
        collector.collect()

        epoch = WORLD_EPOCH.labels(world_id="test_epoch")._value.get()
        assert epoch == 5


class TestWorldMetricsCollectorAutoCollect:
    """Tests for auto-collection functionality."""

    def test_enable_auto_collect(self) -> None:
        """Test enabling auto-collection."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_auto")

        collector.enable_auto_collect()

        # Tick should now be wrapped
        assert collector._original_tick is not None

        # Tick and check metrics are updated
        world.spawn("player")
        world.tick(0)

        count = ENTITY_COUNT.labels(world_id="test_auto")._value.get()
        assert count == 1

    def test_disable_auto_collect(self) -> None:
        """Test disabling auto-collection."""
        world = World()
        collector = WorldMetricsCollector(world, world_id="test_disable")

        collector.enable_auto_collect()
        collector.disable_auto_collect()

        assert collector._original_tick is None

    def test_auto_collect_records_tick_metrics(self) -> None:
        """Test that auto-collect records tick duration and count."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_tick_metrics")

        collector.enable_auto_collect()

        # Do some ticks
        for _ in range(3):
            world.tick(0.016)

        # Check tick count
        tick_count = TICK_COUNT.labels(world_id="test_tick_metrics")._value.get()
        assert tick_count == 3

    def test_detach_disables_auto_collect(self) -> None:
        """Test that detach disables auto-collection."""
        world = World()
        collector = WorldMetricsCollector(
            world, world_id="test_detach", collect_on_tick=True
        )

        collector.detach()

        assert collector._original_tick is None
        assert collector._world is None


class TestWorldMetricsCollectorEdgeCases:
    """Tests for edge cases in metrics collection."""

    def test_collect_empty_world(self) -> None:
        """Test collecting metrics from empty world."""
        world = World()
        collector = WorldMetricsCollector(world, world_id="test_empty")

        # Should not raise
        collector.collect()

        count = ENTITY_COUNT.labels(world_id="test_empty")._value.get()
        assert count == 0

    def test_collect_clears_removed_prefabs(self) -> None:
        """Test that removed prefabs are cleared from metrics."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        collector = WorldMetricsCollector(world, world_id="test_clear")

        entity = world.spawn("player")
        world.tick(0)
        collector.collect()

        # Remove entity
        world.remove(entity)
        world.tick(0)
        collector.collect()

        # Prefab should still exist in metrics (with 0 count)
        count = ENTITIES_BY_PREFAB.labels(
            world_id="test_clear", prefab="player"
        )._value.get()
        assert count == 0

    def test_multiple_collectors_different_worlds(self) -> None:
        """Test multiple collectors for different worlds."""
        world1 = World()
        world1.register_prefab("player", {Position: Position(x=0, y=0)})
        world2 = World()
        world2.register_prefab("enemy", {Health: Health(current=50, maximum=50)})

        collector1 = WorldMetricsCollector(world1, world_id="world_1")
        collector2 = WorldMetricsCollector(world2, world_id="world_2")

        world1.spawn("player")
        world1.spawn("player")
        world1.tick(0)

        world2.spawn("enemy")
        world2.tick(0)

        collector1.collect()
        collector2.collect()

        count1 = ENTITY_COUNT.labels(world_id="world_1")._value.get()
        count2 = ENTITY_COUNT.labels(world_id="world_2")._value.get()

        assert count1 == 2
        assert count2 == 1
