"""Integration tests for spatial indexing addon."""

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, World
from relics.addons.spatial import (
    OctreeBounds,
    Position2D,
    Position3D,
    QuadTreeBounds,
    create_spatial_index_2d,
    create_spatial_index_3d,
)


@dataclass
class Enemy(Component):
    """Enemy marker component."""
    damage: float = 10.0


@dataclass
class Player(Component):
    """Player marker component."""
    health: float = 100.0


class TestBasicUsage:
    """Tests for basic spatial index usage."""

    def test_basic_2d_workflow(self) -> None:
        """Test basic 2D spatial index workflow."""
        world = World()
        world.register_prefab("enemy", {Position2D: Position2D(x=0, y=0), Enemy: Enemy()})

        # Create index
        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        # Spawn enemies
        for i in range(10):
            world.spawn("enemy", {Position2D: Position2D(x=i * 100, y=i * 100)})
        world.tick(0)

        # Query nearby enemies
        nearby = list(index.query_circle(250, 250, 200))
        assert len(nearby) > 0
        assert len(nearby) < 10  # Not all enemies should be nearby

    def test_basic_3d_workflow(self) -> None:
        """Test basic 3D spatial index workflow."""
        world = World()
        world.register_prefab("enemy", {Position3D: Position3D(x=0, y=0, z=0), Enemy: Enemy()})

        # Create index
        index = create_spatial_index_3d(
            world,
            bounds=OctreeBounds(500, 500, 500, 500, 500, 500),
        )

        # Spawn enemies
        for i in range(10):
            world.spawn("enemy", {Position3D: Position3D(x=i * 100, y=i * 100, z=i * 50)})
        world.tick(0)

        # Query nearby enemies
        nearby = list(index.query_sphere(250, 250, 125, 200))
        assert len(nearby) > 0


class TestQueryBuilderIntegration:
    """Tests for integration with QueryBuilder."""

    def test_with_index_2d(self) -> None:
        """Test using spatial index with QueryBuilder.with_index()."""
        world = World()
        world.register_prefab("enemy", {Position2D: Position2D(x=0, y=0), Enemy: Enemy()})
        world.register_prefab("player", {Position2D: Position2D(x=0, y=0), Player: Player()})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        # Spawn entities
        e1 = world.spawn("enemy", {Position2D: Position2D(x=100, y=100)})
        e2 = world.spawn("enemy", {Position2D: Position2D(x=500, y=500)})
        p1 = world.spawn("player", {Position2D: Position2D(x=110, y=110)})
        world.tick(0)

        # Query for enemies near the player using spatial index
        # First get nearby entities
        nearby_ids = set(index.query_circle_ids(100, 100, 50))
        assert e1.id in nearby_ids
        assert e2.id not in nearby_ids
        assert p1.id in nearby_ids

        # Combine with component query - get only nearby enemies
        nearby_enemies = list(
            world.query()
            .with_all([Enemy])
            .with_index(index)
            .execute_entities()
        )

        # Should include all enemies that are in the index
        assert len(nearby_enemies) == 2

    def test_spatial_filter_in_query(self) -> None:
        """Test using spatial query as a filter."""
        world = World()
        world.register_prefab("enemy", {Position2D: Position2D(x=0, y=0), Enemy: Enemy()})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        # Spawn enemies
        e1 = world.spawn("enemy", {Position2D: Position2D(x=100, y=100)})
        e2 = world.spawn("enemy", {Position2D: Position2D(x=500, y=500)})
        e3 = world.spawn("enemy", {Position2D: Position2D(x=120, y=120)})
        world.tick(0)

        # Use spatial query result to filter
        nearby_ids = set(index.query_circle_ids(100, 100, 50))

        nearby_enemies = [
            e for e in world.query().with_all([Enemy]).execute_entities()
            if e.id in nearby_ids
        ]

        assert len(nearby_enemies) == 2
        assert e1 in nearby_enemies
        assert e3 in nearby_enemies
        assert e2 not in nearby_enemies


class TestDualIndexes:
    """Tests for using both 2D and 3D indexes on the same world.

    This demonstrates providing a top-down 2D view alongside a full 3D
    spatial index for the same entities.
    """

    def test_2d_and_3d_index_on_same_world(self) -> None:
        """Test applying both 2D and 3D index to same Position3D entities."""
        world = World()
        world.register_prefab("ship", {Position3D: Position3D(x=0, y=0, z=0)})

        # Full 3D spatial index
        index_3d = create_spatial_index_3d(
            world,
            bounds=OctreeBounds(500, 500, 250, 500, 500, 250),
        )

        # Top-down 2D view (ignoring Z coordinate)
        index_2d = create_spatial_index_2d(
            world,
            component_type=Position3D,
            position_extractor=lambda c: (c.x, c.y),  # Ignore Z
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        # Spawn ships at various 3D positions
        # Two ships at same X,Y but different Z
        ship1 = world.spawn("ship", {Position3D: Position3D(x=100, y=100, z=50)})
        ship2 = world.spawn("ship", {Position3D: Position3D(x=100, y=100, z=200)})
        # One ship at different X,Y
        ship3 = world.spawn("ship", {Position3D: Position3D(x=500, y=500, z=100)})
        world.tick(0)

        # 2D query at (100, 100) - should find both ships 1 and 2
        nearby_2d = list(index_2d.query_circle(100, 100, 50))
        assert len(nearby_2d) == 2
        nearby_2d_ids = {e.id for e in nearby_2d}
        assert ship1.id in nearby_2d_ids
        assert ship2.id in nearby_2d_ids
        assert ship3.id not in nearby_2d_ids

        # 3D query at (100, 100, 50) with small radius - should only find ship1
        nearby_3d = list(index_3d.query_sphere(100, 100, 50, 30))
        assert len(nearby_3d) == 1
        assert nearby_3d[0].id == ship1.id

        # 3D query at (100, 100, 200) - should only find ship2
        nearby_3d = list(index_3d.query_sphere(100, 100, 200, 30))
        assert len(nearby_3d) == 1
        assert nearby_3d[0].id == ship2.id

    def test_height_layer_queries(self) -> None:
        """Test querying different height layers using 3D index."""
        world = World()
        world.register_prefab("ship", {Position3D: Position3D(x=0, y=0, z=0)})

        index = create_spatial_index_3d(
            world,
            bounds=OctreeBounds(500, 500, 500, 500, 500, 500),
        )

        # Spawn ships at different heights
        low_ships = []
        high_ships = []

        for i in range(5):
            # Low altitude ships (z = 0-100)
            ship = world.spawn("ship", {Position3D: Position3D(x=i * 100, y=i * 100, z=50)})
            low_ships.append(ship)

            # High altitude ships (z = 400-500)
            ship = world.spawn("ship", {Position3D: Position3D(x=i * 100, y=i * 100, z=450)})
            high_ships.append(ship)

        world.tick(0)

        # Query low layer (z centered at 50)
        from relics.addons.spatial import Box
        low_layer = Box(min_x=0, min_y=0, min_z=0, max_x=1000, max_y=1000, max_z=100)
        low_results = list(index.query_region(low_layer))
        assert len(low_results) == 5
        low_ids = {e.id for e in low_results}
        for ship in low_ships:
            assert ship.id in low_ids

        # Query high layer (z centered at 450)
        high_layer = Box(min_x=0, min_y=0, min_z=400, max_x=1000, max_y=1000, max_z=500)
        high_results = list(index.query_region(high_layer))
        assert len(high_results) == 5
        high_ids = {e.id for e in high_results}
        for ship in high_ships:
            assert ship.id in high_ids


class TestDynamicUpdates:
    """Tests for dynamic entity updates."""

    def test_position_changes_update_index(self) -> None:
        """Test that position changes are reflected in the index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        entity = world.spawn("entity", {Position2D: Position2D(x=100, y=100)})
        world.tick(0)

        # Entity should be at original position
        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 1

        # Move entity
        pos = entity.get_component(Position2D)
        pos.x = 500
        pos.y = 500
        world.tick(0)

        # Entity should be at new position
        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 0

        results = list(index.query_circle(500, 500, 10))
        assert len(results) == 1

    def test_entity_removal(self) -> None:
        """Test that removed entities are removed from index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        entity = world.spawn("entity")
        world.tick(0)
        assert index.count() == 1

        # Remove entity
        entity.remove_component(Position2D)
        world.tick(0)

        assert index.count() == 0


class TestNearestNeighbor:
    """Tests for nearest neighbor queries."""

    def test_find_k_nearest(self) -> None:
        """Test finding k nearest neighbors."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=0, y=0)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        # Spawn entities at known distances from origin
        for i in range(1, 6):
            world.spawn("entity", {Position2D: Position2D(x=i * 100, y=0)})
        world.tick(0)

        # Find 3 nearest to origin
        results = index.query_nearest(0, 0, count=3)

        assert len(results) == 3
        # Verify they're sorted by distance
        for i in range(len(results) - 1):
            assert results[i][1] <= results[i + 1][1]

        # First should be at (100, 0)
        assert results[0][1] == pytest.approx(100, rel=0.01)

    def test_nearest_with_fewer_entities(self) -> None:
        """Test nearest query when fewer entities than requested."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        index = create_spatial_index_2d(
            world,
            bounds=QuadTreeBounds(500, 500, 500, 500),
        )

        world.spawn("entity")
        world.spawn("entity")
        world.tick(0)

        # Ask for more than exist
        results = index.query_nearest(0, 0, count=10)
        assert len(results) == 2
