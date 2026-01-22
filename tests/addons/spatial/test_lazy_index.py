"""Tests for lazy spatial indexes."""

import pytest

from relics import World
from relics.addons.spatial import (
    Circle,
    LazySpatialIndex2D,
    LazySpatialIndex3D,
    Position2D,
    Position3D,
    Rectangle,
    Sphere,
)


class TestLazySpatialIndex2D:
    """Tests for LazySpatialIndex2D."""

    def test_create_lazy_index(self) -> None:
        """Test creating a lazy spatial index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)
        assert index.count() == 0

    def test_index_reflects_world_state(self) -> None:
        """Test that lazy index reflects current world state."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity")
        assert index.count() == 1

        e2 = world.spawn("entity")
        assert index.count() == 2

        world.remove(e1)
        assert index.count() == 1

    def test_query_circle(self) -> None:
        """Test circle query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        # Spawn entities at different positions
        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=60, y=60)})
        e3 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        results = list(index.query_circle(50, 50, 20))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_rectangle(self) -> None:
        """Test rectangle query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=75, y=75)})
        e3 = world.spawn("entity", {Position2D: Position2D(x=200, y=200)})

        results = list(index.query_rectangle(0, 0, 100, 100))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_region(self) -> None:
        """Test custom region query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=200, y=200)})

        circle = Circle(center_x=50, center_y=50, radius=10)
        results = list(index.query_region(circle))

        assert len(results) == 1
        assert results[0].id == e1.id

    def test_query_nearest(self) -> None:
        """Test nearest neighbor query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity", {Position2D: Position2D(x=10, y=10)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=20, y=20)})
        e3 = world.spawn("entity", {Position2D: Position2D(x=100, y=100)})

        results = index.query_nearest(0, 0, count=2)

        assert len(results) == 2
        # First should be closest
        assert results[0][0].id == e1.id
        assert results[1][0].id == e2.id
        # Distances should be increasing
        assert results[0][1] < results[1][1]

    def test_get_entity_ids(self) -> None:
        """Test getting all entity IDs."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity")
        e2 = world.spawn("entity")

        entity_ids = index.get_entity_ids()
        assert len(entity_ids) == 2
        assert e1.id in entity_ids
        assert e2.id in entity_ids

    def test_iterate(self) -> None:
        """Test iterating over entities."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity")
        e2 = world.spawn("entity")

        entities = list(index)
        assert len(entities) == 2

    def test_custom_position_extractor(self) -> None:
        """Test using a custom position extractor."""
        from pydantic.dataclasses import dataclass
        from relics import Component

        @dataclass
        class CustomPos(Component):
            pos_x: float
            pos_y: float

        world = World()
        world.register_prefab("entity", {CustomPos: CustomPos(pos_x=0, pos_y=0)})

        index = LazySpatialIndex2D(
            world,
            CustomPos,
            position_extractor=lambda c: (c.pos_x, c.pos_y),
        )

        e1 = world.spawn("entity", {CustomPos: CustomPos(pos_x=50, pos_y=50)})
        e2 = world.spawn("entity", {CustomPos: CustomPos(pos_x=500, pos_y=500)})

        results = list(index.query_circle(50, 50, 10))
        assert len(results) == 1
        assert results[0].id == e1.id

    def test_query_circle_ids(self) -> None:
        """Test circle query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        ids = list(index.query_circle_ids(50, 50, 10))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_rectangle_ids(self) -> None:
        """Test rectangle query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        ids = list(index.query_rectangle_ids(0, 0, 100, 100))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_region_ids(self) -> None:
        """Test region query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = LazySpatialIndex2D(world, Position2D)

        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        circle = Circle(center_x=50, center_y=50, radius=10)
        ids = list(index.query_region_ids(circle))
        assert len(ids) == 1
        assert e1.id in ids


class TestLazySpatialIndex3D:
    """Tests for LazySpatialIndex3D."""

    def test_create_lazy_index_3d(self) -> None:
        """Test creating a 3D lazy spatial index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)
        assert index.count() == 0

    def test_query_sphere(self) -> None:
        """Test sphere query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=50, y=50, z=50)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=55, y=55, z=55)})
        e3 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        results = list(index.query_sphere(50, 50, 50, 20))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_box(self) -> None:
        """Test box query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=50, y=50, z=50)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=75, y=75, z=75)})
        e3 = world.spawn("entity", {Position3D: Position3D(x=200, y=200, z=200)})

        results = list(index.query_box(0, 0, 0, 100, 100, 100))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_nearest_3d(self) -> None:
        """Test 3D nearest neighbor query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=10, y=10, z=10)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=20, y=20, z=20)})
        e3 = world.spawn("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        results = index.query_nearest(0, 0, 0, count=2)

        assert len(results) == 2
        assert results[0][0].id == e1.id
        assert results[1][0].id == e2.id
        assert results[0][1] < results[1][1]

    def test_query_sphere_ids(self) -> None:
        """Test sphere query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=50, y=50, z=50)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        ids = list(index.query_sphere_ids(50, 50, 50, 20))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_box_ids(self) -> None:
        """Test box query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=50, y=50, z=50)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        ids = list(index.query_box_ids(0, 0, 0, 100, 100, 100))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_region_3d(self) -> None:
        """Test custom 3D region query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=50, y=50, z=50)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=200, y=200, z=200)})

        sphere = Sphere(center_x=50, center_y=50, center_z=50, radius=10)
        results = list(index.query_region(sphere))

        assert len(results) == 1
        assert results[0].id == e1.id

    def test_query_region_ids_3d(self) -> None:
        """Test custom 3D region query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity", {Position3D: Position3D(x=50, y=50, z=50)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=200, y=200, z=200)})

        sphere = Sphere(center_x=50, center_y=50, center_z=50, radius=10)
        ids = list(index.query_region_ids(sphere))

        assert len(ids) == 1
        assert e1.id in ids

    def test_get_entity_ids_3d(self) -> None:
        """Test getting all 3D entity IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity")
        e2 = world.spawn("entity")

        entity_ids = index.get_entity_ids()
        assert len(entity_ids) == 2
        assert e1.id in entity_ids
        assert e2.id in entity_ids

    def test_iterate_3d(self) -> None:
        """Test iterating over 3D entities."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        index = LazySpatialIndex3D(world, Position3D)

        e1 = world.spawn("entity")
        e2 = world.spawn("entity")

        entities = list(index)
        assert len(entities) == 2
