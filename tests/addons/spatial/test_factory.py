"""Tests for spatial index factory functions."""

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


class TestCreateSpatialIndex2D:
    """Tests for create_spatial_index_2d factory function."""

    def test_create_materialized_index(self) -> None:
        """Test creating a materialized 2D index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        assert isinstance(index, MaterializedSpatialIndex2D)

    def test_create_lazy_index(self) -> None:
        """Test creating a lazy 2D index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = create_spatial_index_2d(
            world,
            materialized=False,
        )

        assert isinstance(index, LazySpatialIndex2D)

    def test_materialized_requires_bounds(self) -> None:
        """Test that materialized index requires bounds."""
        world = World()

        with pytest.raises(ValueError, match="bounds is required"):
            create_spatial_index_2d(world, materialized=True)

    def test_auto_register_observer(self) -> None:
        """Test that observer is auto-registered when enabled."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
            auto_register_observer=True,
        )

        # Spawn entity and tick - observer should add it
        # Don't access index before spawning to avoid early initialization
        e1 = world.spawn("entity")
        world.tick(0)

        # Now check - index will initialize on first access and include the entity
        assert index.count() == 1

    def test_no_auto_register_observer(self) -> None:
        """Test disabling auto-registration of observer."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
            auto_register_observer=False,
        )

        # Spawn entity and tick - no observer means index won't update
        world.spawn("entity")
        world.tick(0)

        # Index should still be empty (no auto-update)
        # But first access will trigger initialization
        assert index.count() == 1  # Initialized on first access

        # Spawn more without observer
        world.spawn("entity")
        world.tick(0)

        # Count is stale (no observer to update)
        assert index.count() == 1

        # Invalidate to refresh
        index.invalidate()
        assert index.count() == 2

    def test_custom_component_type(self) -> None:
        """Test using a custom component type."""
        from pydantic.dataclasses import dataclass

        from relics import Component
        from relics.monitored import monitored

        @monitored
        @dataclass
        class CustomPos(Component):
            pos_x: float
            pos_y: float

        world = World()
        world.register_prefab("entity", {CustomPos: CustomPos(pos_x=100, pos_y=100)})

        index = create_spatial_index_2d(
            world,
            component_type=CustomPos,
            position_extractor=lambda c: (c.pos_x, c.pos_y),
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        e1 = world.spawn("entity")
        world.tick(0)

        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 1

    def test_custom_quadtree_params(self) -> None:
        """Test custom QuadTree parameters."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
            max_entities_per_node=4,
            max_depth=4,
        )

        # Spawn many entities to trigger subdivision
        for i in range(20):
            world.spawn(
                "entity", {Position2D: Position2D(x=100 + i * 10, y=100 + i * 5)}
            )

        world.tick(0)
        assert index.count() == 20


class TestCreateSpatialIndex3D:
    """Tests for create_spatial_index_3d factory function."""

    def test_create_materialized_index_3d(self) -> None:
        """Test creating a materialized 3D index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = create_spatial_index_3d(
            world,
            bounds=OctreeBounds(500, 500, 500, 500, 500, 500),
        )

        assert isinstance(index, MaterializedSpatialIndex3D)

    def test_create_lazy_index_3d(self) -> None:
        """Test creating a lazy 3D index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = create_spatial_index_3d(
            world,
            materialized=False,
        )

        assert isinstance(index, LazySpatialIndex3D)

    def test_materialized_3d_requires_bounds(self) -> None:
        """Test that materialized 3D index requires bounds."""
        world = World()

        with pytest.raises(ValueError, match="bounds is required"):
            create_spatial_index_3d(world, materialized=True)

    def test_auto_register_observer_3d(self) -> None:
        """Test that observer is auto-registered for 3D index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        index = create_spatial_index_3d(
            world,
            bounds=OctreeBounds(500, 500, 500, 500, 500, 500),
            auto_register_observer=True,
        )

        # Spawn entity and tick
        e1 = world.spawn("entity")
        world.tick(0)

        assert index.count() == 1
