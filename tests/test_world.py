"""Tests for relics.world module."""

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    EntityNotFoundError,
    PrefabNotFoundError,
    World,
)
from relics.types import EntityId


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
class Velocity(Component):
    """Test component for velocity."""

    x: float
    y: float


class TestWorld:
    """Tests for World class."""

    def test_world_creation(self) -> None:
        """Test creating a world."""
        world = World()
        assert world.id is not None
        assert world.epoch == 0

    def test_world_custom_id(self) -> None:
        """Test creating a world with custom ID."""
        world = World(world_id="test-world")
        assert world.id == "test-world"

    def test_register_prefab(self) -> None:
        """Test registering a prefab."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0)},
        )
        assert "player" in world._prefabs

    def test_spawn_entity(self) -> None:
        """Test spawning an entity from prefab."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player")
        assert entity.id.prefab == "player"
        assert entity.has_component(Position)

    def test_spawn_with_overrides(self) -> None:
        """Test spawning with component overrides."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})
        pos = entity.get_component(Position)
        assert pos.x == 10
        assert pos.y == 20

    def test_spawn_with_additional_components(self) -> None:
        """Test spawning with additional components not in prefab."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Velocity: Velocity(x=1, y=1)})
        assert entity.has_component(Position)
        assert entity.has_component(Velocity)

    def test_spawn_unknown_prefab(self) -> None:
        """Test spawning from unknown prefab raises error."""
        world = World()
        with pytest.raises(PrefabNotFoundError):
            world.spawn("unknown")

    def test_get_entity(self) -> None:
        """Test getting an entity by ID."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player")
        retrieved = world.get_entity(entity.id)
        assert retrieved.id == entity.id

    def test_get_entity_not_found(self) -> None:
        """Test getting non-existent entity raises error."""
        world = World()
        entity_id = EntityId(prefab="test", sequence=12345)
        with pytest.raises(EntityNotFoundError):
            world.get_entity(entity_id)

    def test_has_entity_true(self) -> None:
        """Test has_entity returns True for existing entity."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player")
        assert world.has_entity(entity.id) is True

    def test_has_entity_false(self) -> None:
        """Test has_entity returns False for non-existent entity."""
        world = World()
        entity_id = EntityId(prefab="test", sequence=12345)
        assert world.has_entity(entity_id) is False

    def test_remove_entity(self) -> None:
        """Test removing an entity."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player")
        world.remove(entity)
        assert world.has_entity(entity.id) is False

    def test_remove_entity_by_id(self) -> None:
        """Test removing an entity by ID."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player")
        world.remove(entity.id)
        assert world.has_entity(entity.id) is False

    def test_remove_entity_not_found(self) -> None:
        """Test removing non-existent entity raises error."""
        world = World()
        entity_id = EntityId(prefab="test", sequence=12345)
        with pytest.raises(EntityNotFoundError):
            world.remove(entity_id)

    def test_tick_increments_epoch(self) -> None:
        """Test that tick increments epoch."""
        world = World()
        assert world.epoch == 0
        world.tick(0.016)
        assert world.epoch == 1
        world.tick(0.016)
        assert world.epoch == 2

    def test_sequence_uniqueness(self) -> None:
        """Test that spawned entities get unique sequences."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity1 = world.spawn("player")
        entity2 = world.spawn("player")
        assert entity1.id.sequence != entity2.id.sequence

    def test_prefab_index(self) -> None:
        """Test prefab index is updated correctly."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        player1 = world.spawn("player")
        player2 = world.spawn("player")
        enemy1 = world.spawn("enemy")

        assert len(world._prefab_index["player"]) == 2
        assert len(world._prefab_index["enemy"]) == 1
        assert player1.id in world._prefab_index["player"]
        assert player2.id in world._prefab_index["player"]
        assert enemy1.id in world._prefab_index["enemy"]

    def test_remove_updates_prefab_index(self) -> None:
        """Test that remove updates prefab index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        entity = world.spawn("player")
        assert entity.id in world._prefab_index["player"]

        world.remove(entity)
        assert entity.id not in world._prefab_index["player"]

    def test_query_returns_builder(self) -> None:
        """Test that query() returns a QueryBuilder."""
        from relics.query import QueryBuilder

        world = World()
        builder = world.query()
        assert isinstance(builder, QueryBuilder)
