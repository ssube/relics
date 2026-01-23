"""Tests for spatial index observers."""

from relics import World
from relics.addons.spatial import (
    MaterializedSpatialIndex2D,
    MaterializedSpatialIndex3D,
    OctreeBounds,
    Position2D,
    Position3D,
    QuadTreeBounds,
    create_spatial_observer_2d,
    create_spatial_observer_3d,
)


class TestSpatialIndexObserver2D:
    """Tests for SpatialIndexObserver2D."""

    def test_observer_adds_new_entities(self) -> None:
        """Test that observer adds newly spawned entities to the index."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        # Create and register observer
        observer = create_spatial_observer_2d(index, Position2D)
        world.observe(observer)

        # Spawn entity - observer should add it (index initializes lazily)
        e1 = world.spawn("entity")
        world.tick(0)

        # Now check count - this will initialize index from world state
        # and include the entity that was just spawned
        assert index.count() == 1
        assert e1.id in index.get_entity_ids()

    def test_observer_removes_deleted_entities(self) -> None:
        """Test that observer removes entities when position component is removed."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        observer = create_spatial_observer_2d(index, Position2D)
        world.observe(observer)

        e1 = world.spawn("entity")
        world.tick(0)
        assert index.count() == 1

        # Remove the position component
        e1.remove_component(Position2D)
        world.tick(0)

        assert index.count() == 0

    def test_observer_updates_on_position_change(self) -> None:
        """Test that observer updates index when position changes."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        observer = create_spatial_observer_2d(index, Position2D)
        world.observe(observer)

        e1 = world.spawn("entity")
        world.tick(0)

        # Verify entity at original position
        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 1

        # Modify position using monitored component
        pos = e1.get_component(Position2D)
        pos.x = 500
        pos.y = 500
        world.tick(0)

        # Verify entity moved
        results = list(index.query_circle(100, 100, 10))
        assert len(results) == 0

        results = list(index.query_circle(500, 500, 10))
        assert len(results) == 1

    def test_observer_handles_multiple_entities(self) -> None:
        """Test observer with multiple entities."""
        world = World()
        world.register_prefab("entity", {Position2D: Position2D(x=100, y=100)})

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        observer = create_spatial_observer_2d(index, Position2D)
        world.observe(observer)

        # Spawn multiple entities
        entities = []
        for i in range(10):
            e = world.spawn(
                "entity", {Position2D: Position2D(x=100 + i * 10, y=100 + i * 10)}
            )
            entities.append(e)
        world.tick(0)

        assert index.count() == 10

        # Remove some
        for e in entities[:5]:
            e.remove_component(Position2D)
        world.tick(0)

        assert index.count() == 5

    def test_observer_component_type_is_set(self) -> None:
        """Test that observer's component_type is correctly set."""
        world = World()

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        observer = create_spatial_observer_2d(index, Position2D)

        assert observer.component_type == Position2D


class TestSpatialIndexObserver3D:
    """Tests for SpatialIndexObserver3D."""

    def test_observer_adds_new_entities_3d(self) -> None:
        """Test that 3D observer adds newly spawned entities to the index."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500,
            center_y=500,
            center_z=500,
            half_width=500,
            half_height=500,
            half_depth=500,
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        observer = create_spatial_observer_3d(index, Position3D)
        world.observe(observer)

        e1 = world.spawn("entity")
        world.tick(0)

        assert index.count() == 1
        assert e1.id in index.get_entity_ids()

    def test_observer_removes_deleted_entities_3d(self) -> None:
        """Test that 3D observer removes entities when position component is removed."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500,
            center_y=500,
            center_z=500,
            half_width=500,
            half_height=500,
            half_depth=500,
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        observer = create_spatial_observer_3d(index, Position3D)
        world.observe(observer)

        e1 = world.spawn("entity")
        world.tick(0)
        assert index.count() == 1

        e1.remove_component(Position3D)
        world.tick(0)

        assert index.count() == 0

    def test_observer_updates_on_position_change_3d(self) -> None:
        """Test that 3D observer updates index when position changes."""
        world = World()
        world.register_prefab("entity", {Position3D: Position3D(x=100, y=100, z=100)})

        bounds = OctreeBounds(
            center_x=500,
            center_y=500,
            center_z=500,
            half_width=500,
            half_height=500,
            half_depth=500,
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        observer = create_spatial_observer_3d(index, Position3D)
        world.observe(observer)

        e1 = world.spawn("entity")
        world.tick(0)

        # Verify entity at original position
        results = list(index.query_sphere(100, 100, 100, 10))
        assert len(results) == 1

        # Modify position using monitored component
        pos = e1.get_component(Position3D)
        pos.x = 500
        pos.y = 500
        pos.z = 500
        world.tick(0)

        # Verify entity moved
        results = list(index.query_sphere(100, 100, 100, 10))
        assert len(results) == 0

        results = list(index.query_sphere(500, 500, 500, 10))
        assert len(results) == 1

    def test_observer_component_type_is_set_3d(self) -> None:
        """Test that 3D observer's component_type is correctly set."""
        world = World()

        bounds = OctreeBounds(
            center_x=500,
            center_y=500,
            center_z=500,
            half_width=500,
            half_height=500,
            half_depth=500,
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        observer = create_spatial_observer_3d(index, Position3D)

        assert observer.component_type == Position3D


class TestSpatialIndexObserver2DComponentBinding:
    """Tests for component binding in 2D spatial observer."""

    def test_observer_binds_monitored_component_on_add(self) -> None:
        """Test that adding a monitored component via add_component triggers binding."""
        world = World()
        # Create prefab WITHOUT Position2D
        world.register_prefab("entity_no_pos", {})

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        index = MaterializedSpatialIndex2D(world, Position2D, bounds)

        observer = create_spatial_observer_2d(index, Position2D)
        world.observe(observer)

        # Spawn entity without position
        entity = world.spawn("entity_no_pos")
        world.tick(0)

        # Manually initialize index to set baseline
        assert index.count() == 0

        # Add position component via add_component (triggers on_component_added)
        pos = Position2D(x=100, y=100)
        entity.add_component(pos)
        world.tick(0)

        # Verify entity was added to index
        assert index.count() == 1
        assert entity.id in index.get_entity_ids()


class TestSpatialIndexObserver3DComponentBinding:
    """Tests for component binding in 3D spatial observer."""

    def test_observer_binds_monitored_component_on_add_3d(self) -> None:
        """Test that adding a monitored component via add_component triggers binding."""
        world = World()
        # Create prefab WITHOUT Position3D
        world.register_prefab("entity_no_pos", {})

        bounds = OctreeBounds(
            center_x=500,
            center_y=500,
            center_z=500,
            half_width=500,
            half_height=500,
            half_depth=500,
        )
        index = MaterializedSpatialIndex3D(world, Position3D, bounds)

        observer = create_spatial_observer_3d(index, Position3D)
        world.observe(observer)

        # Spawn entity without position
        entity = world.spawn("entity_no_pos")
        world.tick(0)

        # Manually initialize index to set baseline
        assert index.count() == 0

        # Add position component via add_component (triggers on_component_added)
        pos = Position3D(x=100, y=100, z=100)
        entity.add_component(pos)
        world.tick(0)

        # Verify entity was added to index
        assert index.count() == 1
        assert entity.id in index.get_entity_ids()
