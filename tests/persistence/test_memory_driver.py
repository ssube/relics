"""Tests for in-memory persistence driver."""

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, Edge, World
from relics.persistence import InMemoryPersistenceDriver


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
    """Test edge type for ally relationships."""

    trust_level: float = 1.0


class TestInMemoryPersistenceDriver:
    """Tests for InMemoryPersistenceDriver class."""

    def test_driver_save_and_load(self) -> None:
        """Test basic save/load functionality."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        driver.save(world, "test_snapshot")

        world2 = World()
        driver.load(world2, "test_snapshot", {"Position": Position})

        assert len(world2._entities) == 1
        loaded = world2.get_entity(entity.id)
        assert loaded.get_component(Position).x == 10
        assert loaded.get_component(Position).y == 20

    def test_driver_multiple_snapshots(self) -> None:
        """Test storing and restoring multiple snapshots."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        # Create first snapshot
        world.spawn("player", {Position: Position(x=1, y=1)})
        driver.save(world, "snapshot_1")

        # Modify and create second snapshot
        world.spawn("player", {Position: Position(x=2, y=2)})
        driver.save(world, "snapshot_2")

        # Restore first snapshot
        world2 = World()
        driver.load(world2, "snapshot_1", {"Position": Position})
        assert len(world2._entities) == 1

        # Restore second snapshot
        world3 = World()
        driver.load(world3, "snapshot_2", {"Position": Position})
        assert len(world3._entities) == 2

    def test_driver_overwrite_snapshot(self) -> None:
        """Test that saving to same key overwrites."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player", {Position: Position(x=1, y=1)})
        driver.save(world, "checkpoint")

        world.spawn("player", {Position: Position(x=2, y=2)})
        driver.save(world, "checkpoint")

        world2 = World()
        driver.load(world2, "checkpoint", {"Position": Position})
        assert len(world2._entities) == 2

    def test_driver_load_nonexistent_raises(self) -> None:
        """Test that loading non-existent snapshot raises error."""
        driver = InMemoryPersistenceDriver()
        world = World()

        with pytest.raises(FileNotFoundError):
            driver.load(world, "nonexistent")

    def test_driver_round_trip_with_relationships(self) -> None:
        """Test save/load round-trip with relationships."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player", {Position: Position(x=10, y=20)})
        p2 = world.spawn("player", {Position: Position(x=30, y=40)})
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)

        driver.save(world, "with_relationships")

        world2 = World()
        driver.load(
            world2, "with_relationships", {"Position": Position}, {"AllyTo": AllyTo}
        )

        loaded_p1 = world2.get_entity(p1.id)
        assert loaded_p1.has_relationship(AllyTo, p2.id)

        relationships = loaded_p1.get_relationships(AllyTo)
        assert len(relationships) == 1
        edge, target_id = relationships[0]
        assert edge.trust_level == 0.9

    def test_driver_epoch_preserved(self) -> None:
        """Test that epoch is preserved on load."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        for _ in range(10):
            world.tick(0.016)

        driver.save(world, "with_epoch")

        world2 = World()
        driver.load(world2, "with_epoch", {"Position": Position})
        assert world2.epoch == 10

    def test_driver_no_reference_sharing(self) -> None:
        """Test that saved data is independent of original world."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        driver.save(world, "original")

        # Modify original world
        world.remove(entity)

        # Load should restore original state
        world2 = World()
        driver.load(world2, "original", {"Position": Position})
        assert world2.has_entity(entity.id)

    def test_driver_clear(self) -> None:
        """Test clearing all stored data."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save(world, "snapshot")
        driver.save_relic(world, "relic", "relics")

        driver.clear()

        assert driver.list_snapshots() == []
        assert driver.list_relics("relics") == []


class TestInMemoryRelics:
    """Tests for relic functionality in InMemoryPersistenceDriver."""

    def test_save_relic(self) -> None:
        """Test saving a named relic."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save_relic(world, "test_relic", "relics")

        relics = driver.list_relics("relics")
        assert len(relics) == 1
        assert relics[0].name == "test_relic"

    def test_load_relic(self) -> None:
        """Test loading a named relic."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})

        driver.save_relic(world, "test_load", "relics")

        world2 = World()
        driver.load_relic(world2, "test_load", "relics", {"Position": Position})

        assert world2.has_entity(entity.id)

    def test_list_relics(self) -> None:
        """Test listing relics."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save_relic(world, "relic1", "relics")
        driver.save_relic(world, "relic2", "relics")

        relics = driver.list_relics("relics")
        names = [r.name for r in relics]

        assert "relic1" in names
        assert "relic2" in names

    def test_list_relics_empty_dir(self) -> None:
        """Test listing relics in non-existent directory."""
        driver = InMemoryPersistenceDriver()
        relics = driver.list_relics("nonexistent")
        assert relics == []

    def test_overwrite_relic_fails(self) -> None:
        """Test that overwrite=False raises error on existing relic."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save_relic(world, "test_relic", "relics")

        with pytest.raises(FileExistsError):
            driver.save_relic(world, "test_relic", "relics")

    def test_overwrite_relic_succeeds(self) -> None:
        """Test that overwrite=True allows overwriting."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save_relic(world, "test_relic", "relics")
        driver.save_relic(world, "test_relic", "relics", overwrite=True)

        relics = driver.list_relics("relics")
        assert len(relics) == 1

    def test_load_nonexistent_relic(self) -> None:
        """Test loading non-existent relic raises error."""
        driver = InMemoryPersistenceDriver()
        world = World()

        with pytest.raises(FileNotFoundError):
            driver.load_relic(world, "nonexistent", "relics")

    def test_separate_relic_directories(self) -> None:
        """Test that different directories are independent."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save_relic(world, "relic", "dir1")
        driver.save_relic(world, "relic", "dir2")

        assert len(driver.list_relics("dir1")) == 1
        assert len(driver.list_relics("dir2")) == 1


class TestInMemoryHelperMethods:
    """Tests for helper methods in InMemoryPersistenceDriver."""

    def test_has_snapshot(self) -> None:
        """Test has_snapshot method."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        assert not driver.has_snapshot("test")
        driver.save(world, "test")
        assert driver.has_snapshot("test")

    def test_delete_snapshot(self) -> None:
        """Test delete_snapshot method."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        driver.save(world, "test")
        assert driver.has_snapshot("test")

        result = driver.delete_snapshot("test")
        assert result is True
        assert not driver.has_snapshot("test")

        # Delete non-existent returns False
        result = driver.delete_snapshot("nonexistent")
        assert result is False

    def test_list_snapshots(self) -> None:
        """Test list_snapshots method."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")

        assert driver.list_snapshots() == []

        driver.save(world, "snap1")
        driver.save(world, "snap2")

        snapshots = driver.list_snapshots()
        assert "snap1" in snapshots
        assert "snap2" in snapshots


class TestInMemoryEdgeCases:
    """Tests for edge cases in loading - unknown types and orphaned data."""

    def test_load_skips_unknown_component_types(self) -> None:
        """Test loading world with components not in registry."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        entity = world.spawn("player")
        driver.save(world, "snapshot")

        # Load with only Position in registry - Health should be skipped
        world2 = World()
        driver.load(world2, "snapshot", {"Position": Position})  # No Health

        loaded = world2.get_entity(entity.id)
        assert loaded.has_component(Position)
        assert not loaded.has_component(Health)

    def test_load_skips_unknown_edge_types(self) -> None:
        """Test loading world with edge types not in registry."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        driver.save(world, "with_unknown_edge")

        # Load without AllyTo in edge registry
        world2 = World()
        driver.load(world2, "with_unknown_edge", {"Position": Position}, {})

        loaded_p1 = world2.get_entity(p1.id)
        # Should not have relationship since edge type wasn't in registry
        assert not loaded_p1.has_relationship(AllyTo)

    def test_load_skips_orphaned_source_relationships(self) -> None:
        """Test loading relationships where source entity is missing."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        driver.save(world, "snapshot")

        # Manually corrupt the data by removing source entity
        data = driver._storage["snapshot"]
        # Remove p1 from entities but keep relationship
        del data["entities"][str(p1.id)]
        del data["components"]["Position"][str(p1.id)]

        world2 = World()
        driver.load(world2, "snapshot", {"Position": Position}, {"AllyTo": AllyTo})

        # Only p2 should exist, p1 relationships should be skipped
        assert not world2.has_entity(p1.id)
        assert world2.has_entity(p2.id)

    def test_load_skips_orphaned_target_relationships(self) -> None:
        """Test loading relationships where target entity is missing."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        driver.save(world, "snapshot")

        # Manually corrupt the data by removing target entity
        data = driver._storage["snapshot"]
        del data["entities"][str(p2.id)]
        del data["components"]["Position"][str(p2.id)]

        world2 = World()
        driver.load(world2, "snapshot", {"Position": Position}, {"AllyTo": AllyTo})

        # p1 should exist but have no relationships (target is missing)
        assert world2.has_entity(p1.id)
        assert not world2.has_entity(p2.id)
        loaded_p1 = world2.get_entity(p1.id)
        assert not loaded_p1.has_relationship(AllyTo)


class TestInMemoryUseCases:
    """Tests for common use cases."""

    def test_undo_redo_pattern(self) -> None:
        """Test undo/redo pattern with snapshots."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        # Initial state
        entity = world.spawn("player", {Position: Position(x=0, y=0)})
        driver.save(world, "state_0")

        # Move player
        world._entities[entity.id][Position] = Position(x=10, y=10)
        driver.save(world, "state_1")

        # Move again
        world._entities[entity.id][Position] = Position(x=20, y=20)
        driver.save(world, "state_2")

        # Undo to state_1
        driver.load(world, "state_1", {"Position": Position})
        pos = world.get_entity(entity.id).get_component(Position)
        assert pos.x == 10

        # Undo to state_0
        driver.load(world, "state_0", {"Position": Position})
        pos = world.get_entity(entity.id).get_component(Position)
        assert pos.x == 0

        # Redo to state_2
        driver.load(world, "state_2", {"Position": Position})
        pos = world.get_entity(entity.id).get_component(Position)
        assert pos.x == 20

    def test_checkpoint_and_rollback(self) -> None:
        """Test checkpoint and rollback pattern."""
        driver = InMemoryPersistenceDriver()
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        # Create checkpoint
        entity = world.spawn("player", {Position: Position(x=5, y=5)})
        driver.save(world, "checkpoint")

        # Make changes that might fail
        world.spawn("player", {Position: Position(x=100, y=100)})
        world.spawn("player", {Position: Position(x=200, y=200)})

        # "Transaction failed" - rollback
        driver.load(world, "checkpoint", {"Position": Position})

        assert len(world._entities) == 1
        assert world.get_entity(entity.id).get_component(Position).x == 5

    def test_testing_isolation(self) -> None:
        """Test that driver provides isolation between tests."""
        driver = InMemoryPersistenceDriver()

        # Simulate test 1
        world1 = World()
        world1.register_prefab("player", {Position: Position(x=0, y=0)})
        world1.spawn("player")
        driver.save(world1, "test_data")

        # Clear between tests
        driver.clear()

        # Simulate test 2 - should not see test 1's data
        assert not driver.has_snapshot("test_data")
        assert driver.list_snapshots() == []
