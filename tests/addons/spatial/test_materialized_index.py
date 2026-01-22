"""Tests for materialized spatial indexes."""

import pytest

from relics import World
from relics.addons.spatial import (
    Circle,
    MaterializedSpatialIndex2D,
    MaterializedSpatialIndex3D,
    OctreeBounds,
    Position2D,
    Position3D,
    QuadTreeBounds,
)


class TestMaterializedSpatialIndex2D:
    """Tests for MaterializedSpatialIndex2D."""

    def test_create_materialized_index(self) -> None:
        """Test creating a materialized spatial index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        assert index.count() == 0

    def test_index_initializes_on_first_access(self) -> None:
        """Test lazy initialization on first access."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        # Spawn before accessing index
        world.spawn("entity")
        world.spawn("entity")

        # First access triggers initialization
        assert index.count() == 2

    def test_add_entity(self) -> None:
        """Test manually adding an entity."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity")
        index.add_entity(e1.id)

        assert index.count() == 1

    def test_remove_entity(self) -> None:
        """Test removing an entity."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity")
        index.add_entity(e1.id)
        assert index.count() == 1

        index.remove_entity(e1.id)
        assert index.count() == 0

    def test_update_entity(self) -> None:
        """Test updating entity position."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity")
        index.add_entity(e1.id)

        # Query at original position
        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 1

        # Update position via component
        e1.remove_component(Position2D)
        e1.add_component(Position2D(x=500, y=500))
        index.update(e1.id)

        # Query at old position - should be empty
        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 0

        # Query at new position
        results = list(index.query_circle(500, 500, 10))
        assert len(results) == 1

    def test_invalidate(self) -> None:
        """Test invalidating the index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        world.spawn("entity")
        assert index.count() == 1

        # Spawn more entities without updating index
        world.spawn("entity")
        world.spawn("entity")

        # Count is stale
        assert index.count() == 1

        # Invalidate forces rebuild
        index.invalidate()
        assert index.count() == 3

    def test_query_circle(self) -> None:
        """Test circle query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity", {Position2D: Position2D(x=100, y=100)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=110, y=110)})
        e3 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        results = list(index.query_circle(100, 100, 20))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_rectangle(self) -> None:
        """Test rectangle query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity", {Position2D: Position2D(x=150, y=150)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=200, y=200)})
        e3 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        results = list(index.query_rectangle(100, 100, 300, 300))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_nearest(self) -> None:
        """Test nearest neighbor query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity", {Position2D: Position2D(x=110, y=110)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=120, y=120)})
        e3 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        results = index.query_nearest(100, 100, count=2)

        assert len(results) == 2
        assert results[0][0].id == e1.id
        assert results[1][0].id == e2.id
        assert results[0][1] < results[1][1]

    def test_get_entity_ids(self) -> None:
        """Test getting all entity IDs."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity")
        e2 = world.spawn("entity")

        entity_ids = index.get_entity_ids()
        assert len(entity_ids) == 2
        assert e1.id in entity_ids
        assert e2.id in entity_ids

    def test_iterate(self) -> None:
        """Test iterating over entities."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        world.spawn("entity")
        world.spawn("entity")

        entities = list(index)
        assert len(entities) == 2

    def test_query_region(self) -> None:
        """Test custom region query."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity", {Position2D: Position2D(x=100, y=100)})
        e2 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        circle = Circle(center_x=100, center_y=100, radius=10)
        results = list(index.query_region(circle))
        assert len(results) == 1
        assert results[0].id == e1.id

    def test_handles_entity_outside_bounds(self) -> None:
        """Test that entities outside bounds are not indexed."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        # Small bounds
        bounds = QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        # Entity inside bounds
        e1 = world.spawn("entity", {Position2D: Position2D(x=50, y=50)})
        # Entity outside bounds
        e2 = world.spawn("entity", {Position2D: Position2D(x=500, y=500)})

        # Only e1 should be in index
        assert index.count() == 1
        assert e1.id in index.get_entity_ids()
        assert e2.id not in index.get_entity_ids()

    def test_update_removes_entity_without_component(self) -> None:
        """Test that update removes entity if it no longer has the component."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity")
        assert index.count() == 1

        # Remove the position component
        e1.remove_component(Position2D)
        index.update(e1.id)

        assert index.count() == 0

    def test_update_removes_deleted_entity(self) -> None:
        """Test that update handles deleted entities."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(center_x=500, center_y=500, half_width=500, half_height=500)
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        e1 = world.spawn("entity")
        entity_id = e1.id
        assert index.count() == 1

        # Delete the entity
        world.remove(e1)
        index.update(entity_id)

        assert index.count() == 0


class TestMaterializedSpatialIndex3D:
    """Tests for MaterializedSpatialIndex3D."""

    def test_create_materialized_index_3d(self) -> None:
        """Test creating a 3D materialized spatial index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        assert index.count() == 0

    def test_query_sphere(self) -> None:
        """Test sphere query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=100, y=100, z=100)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=110, y=110, z=110)})
        e3 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        results = list(index.query_sphere(100, 100, 100, 30))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_query_box(self) -> None:
        """Test box query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=150, y=150, z=150)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=200, y=200, z=200)})
        e3 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        results = list(index.query_box(100, 100, 100, 300, 300, 300))
        assert len(results) == 2

        result_ids = {e.id for e in results}
        assert e1.id in result_ids
        assert e2.id in result_ids
        assert e3.id not in result_ids

    def test_add_update_remove(self) -> None:
        """Test add, update, and remove operations."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        # Add
        e1 = world.spawn("entity")
        index.add_entity(e1.id)
        assert index.count() == 1

        # Update
        e1.remove_component(Position3D)
        e1.add_component(Position3D(x=500, y=500, z=500))
        index.update(e1.id)
        results = list(index.query_sphere(500, 500, 500, 10))
        assert len(results) == 1

        # Remove
        index.remove_entity(e1.id)
        assert index.count() == 0

    def test_query_sphere_ids(self) -> None:
        """Test sphere query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=100, y=100, z=100)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        ids = list(index.query_sphere_ids(100, 100, 100, 20))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_box_ids(self) -> None:
        """Test box query returning IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=100, y=100, z=100)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        ids = list(index.query_box_ids(0, 0, 0, 200, 200, 200))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_region_3d(self) -> None:
        """Test custom 3D region query."""
        from relics.addons.spatial import Sphere

        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=100, y=100, z=100)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        sphere = Sphere(center_x=100, center_y=100, center_z=100, radius=10)
        results = list(index.query_region(sphere))
        assert len(results) == 1
        assert results[0].id == e1.id

    def test_query_region_ids_3d(self) -> None:
        """Test custom 3D region query returning IDs."""
        from relics.addons.spatial import Sphere

        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        sphere = Sphere(center_x=100, center_y=100, center_z=100, radius=10)
        ids = list(index.query_region_ids(sphere))
        assert len(ids) == 1
        assert e1.id in ids

    def test_query_nearest_3d(self) -> None:
        """Test nearest neighbor 3D query."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=0, y=0, z=0)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity", {Position3D: Position3D(x=110, y=110, z=110)})
        e2 = world.spawn("entity", {Position3D: Position3D(x=120, y=120, z=120)})
        e3 = world.spawn("entity", {Position3D: Position3D(x=500, y=500, z=500)})

        results = index.query_nearest(100, 100, 100, count=2)
        assert len(results) == 2
        assert results[0][0].id == e1.id
        assert results[1][0].id == e2.id
        assert results[0][1] < results[1][1]

    def test_get_entity_ids_3d(self) -> None:
        """Test getting all 3D entity IDs."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity")
        e2 = world.spawn("entity")

        entity_ids = index.get_entity_ids()
        assert len(entity_ids) == 2
        assert e1.id in entity_ids
        assert e2.id in entity_ids

    def test_iterate_3d(self) -> None:
        """Test iterating over 3D entities."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        world.spawn("entity")
        world.spawn("entity")

        entities = list(index)
        assert len(entities) == 2

    def test_invalidate_3d(self) -> None:
        """Test invalidating the 3D index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        world.spawn("entity")
        assert index.count() == 1

        # Spawn more without updating index
        world.spawn("entity")
        assert index.count() == 1

        # Invalidate forces rebuild
        index.invalidate()
        assert index.count() == 2

    def test_update_removes_entity_without_component_3d(self) -> None:
        """Test that update removes 3D entity if it no longer has the component."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity")
        assert index.count() == 1

        # Remove the position component
        e1.remove_component(Position3D)
        index.update(e1.id)

        assert index.count() == 0

    def test_update_removes_deleted_entity_3d(self) -> None:
        """Test that update handles deleted 3D entities."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        e1 = world.spawn("entity")
        entity_id = e1.id
        assert index.count() == 1

        # Delete the entity
        world.remove(e1)
        index.update(entity_id)

        assert index.count() == 0
