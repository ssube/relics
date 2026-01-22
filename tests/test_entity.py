"""Tests for relics.entity module."""

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    ComponentNotFoundError,
    DuplicateComponentError,
    EntityNotFoundError,
    World,
)


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@dataclass
class Velocity(Component):
    """Test component for velocity."""

    x: float
    y: float


@dataclass
class Health(Component):
    """Test component for health."""

    current: int
    maximum: int


class TestEntity:
    """Tests for Entity handle class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.world = World()
        self.world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

    def test_entity_id(self) -> None:
        """Test entity id property."""
        entity = self.world.spawn("player")
        assert entity.id.prefab == "player"
        assert entity.id.sequence > 0

    def test_entity_prefab(self) -> None:
        """Test entity prefab property."""
        entity = self.world.spawn("player")
        assert entity.prefab == "player"

    def test_get_component(self) -> None:
        """Test getting a component."""
        entity = self.world.spawn("player")
        pos = entity.get_component(Position)
        assert pos.x == 0
        assert pos.y == 0

    def test_get_component_not_found(self) -> None:
        """Test getting a component that doesn't exist."""
        entity = self.world.spawn("player")
        with pytest.raises(ComponentNotFoundError):
            entity.get_component(Velocity)

    def test_has_component_true(self) -> None:
        """Test has_component when component exists."""
        entity = self.world.spawn("player")
        assert entity.has_component(Position) is True

    def test_has_component_false(self) -> None:
        """Test has_component when component doesn't exist."""
        entity = self.world.spawn("player")
        assert entity.has_component(Velocity) is False

    def test_add_component(self) -> None:
        """Test adding a component."""
        entity = self.world.spawn("player")
        entity.add_component(Velocity(x=1, y=2))
        assert entity.has_component(Velocity)
        vel = entity.get_component(Velocity)
        assert vel.x == 1
        assert vel.y == 2

    def test_add_component_duplicate(self) -> None:
        """Test adding a duplicate component raises error."""
        entity = self.world.spawn("player")
        with pytest.raises(DuplicateComponentError):
            entity.add_component(Position(x=10, y=10))

    def test_remove_component(self) -> None:
        """Test removing a component."""
        entity = self.world.spawn("player")
        entity.remove_component(Position)
        assert entity.has_component(Position) is False

    def test_remove_component_not_found(self) -> None:
        """Test removing a component that doesn't exist."""
        entity = self.world.spawn("player")
        with pytest.raises(ComponentNotFoundError):
            entity.remove_component(Velocity)

    def test_entity_equality(self) -> None:
        """Test entity equality based on ID."""
        entity1 = self.world.spawn("player")
        entity2 = self.world.get_entity(entity1.id)
        assert entity1 == entity2

    def test_entity_inequality(self) -> None:
        """Test entity inequality for different IDs."""
        entity1 = self.world.spawn("player")
        entity2 = self.world.spawn("player")
        assert entity1 != entity2

    def test_entity_hash(self) -> None:
        """Test entity can be used in sets."""
        entity = self.world.spawn("player")
        entity_set = {entity}
        assert entity in entity_set

    def test_entity_repr(self) -> None:
        """Test entity string representation."""
        entity = self.world.spawn("player")
        repr_str = repr(entity)
        assert "Entity" in repr_str
        assert "player" in repr_str

    def test_lazy_validation_on_removed_entity(self) -> None:
        """Test that operations fail after entity is removed."""
        entity = self.world.spawn("player")
        self.world.remove(entity)

        with pytest.raises(EntityNotFoundError):
            entity.get_component(Position)

        with pytest.raises(EntityNotFoundError):
            entity.has_component(Position)

        with pytest.raises(EntityNotFoundError):
            entity.add_component(Velocity(x=1, y=1))

        with pytest.raises(EntityNotFoundError):
            entity.remove_component(Health)
