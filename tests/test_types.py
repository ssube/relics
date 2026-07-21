"""Tests for relics.types module."""

import pytest
from pydantic.dataclasses import dataclass

from relics.types import Component, Edge, EntityId


class TestEntityId:
    """Tests for EntityId class."""

    def test_create_entity_id(self) -> None:
        """Test creating an EntityId."""
        entity_id = EntityId(prefab="player", sequence=12345)
        assert entity_id.prefab == "player"
        assert entity_id.sequence == 12345

    def test_str_representation(self) -> None:
        """Test string representation."""
        entity_id = EntityId(prefab="door", sequence=1705847293001000)
        assert str(entity_id) == "door_1705847293001000"

    def test_parse_valid_string(self) -> None:
        """Test parsing a valid string."""
        entity_id = EntityId.parse("player_12345")
        assert entity_id.prefab == "player"
        assert entity_id.sequence == 12345

    def test_parse_prefab_with_underscore(self) -> None:
        """Test parsing prefab name containing underscore."""
        entity_id = EntityId.parse("wooden_door_12345")
        assert entity_id.prefab == "wooden_door"
        assert entity_id.sequence == 12345

    def test_parse_invalid_format_no_underscore(self) -> None:
        """Test parsing invalid string without underscore."""
        with pytest.raises(ValueError, match="Invalid EntityId format"):
            EntityId.parse("player12345")

    def test_parse_invalid_sequence(self) -> None:
        """Test parsing string with non-numeric sequence."""
        with pytest.raises(ValueError, match="Invalid sequence"):
            EntityId.parse("player_abc")

    def test_hash_equality(self) -> None:
        """Test that equal EntityIds have same hash."""
        id1 = EntityId(prefab="test", sequence=100)
        id2 = EntityId(prefab="test", sequence=100)
        assert hash(id1) == hash(id2)
        assert id1 == id2
        assert {id1: "entity"}[id2] == "entity"

    def test_hash_inequality(self) -> None:
        """Test that different EntityIds have different hashes."""
        id1 = EntityId(prefab="test", sequence=100)
        id2 = EntityId(prefab="test", sequence=200)
        assert id1 != id2

    def test_ordering_uses_prefab_then_sequence(self) -> None:
        """Entity IDs sort deterministically by prefab and numeric sequence."""
        player_later = EntityId(prefab="player", sequence=20)
        apple = EntityId(prefab="apple", sequence=100)
        player_earlier = EntityId(prefab="player", sequence=3)

        assert sorted([player_later, apple, player_earlier]) == [
            apple,
            player_earlier,
            player_later,
        ]
        assert player_earlier < player_later
        assert player_later > player_earlier

    def test_frozen(self) -> None:
        """Test that EntityId is immutable."""
        entity_id = EntityId(prefab="test", sequence=100)
        with pytest.raises(Exception):  # Pydantic raises FrozenInstanceError
            entity_id.prefab = "other"  # type: ignore[misc]


class TestComponent:
    """Tests for Component base class."""

    def test_component_subclass(self) -> None:
        """Test creating a component subclass."""

        @dataclass
        class Position(Component):
            x: float
            y: float
            z: float = 0.0

        pos = Position(x=10.0, y=20.0)
        assert pos.x == 10.0
        assert pos.y == 20.0
        assert pos.z == 0.0

    def test_component_isinstance(self) -> None:
        """Test isinstance check for components."""

        @dataclass
        class Health(Component):
            current: int
            maximum: int

        health = Health(current=80, maximum=100)
        assert isinstance(health, Component)


class TestEdge:
    """Tests for Edge base class."""

    def test_edge_subclass(self) -> None:
        """Test creating an edge subclass."""

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        edge = AllyTo(trust_level=0.8)
        assert edge.trust_level == 0.8

    def test_edge_default_validate(self) -> None:
        """Test that default validate returns True."""
        edge = Edge()
        # validate requires Entity objects, but we can test the base behavior
        assert edge.validate(None, None)  # type: ignore[arg-type]

    def test_edge_isinstance(self) -> None:
        """Test isinstance check for edges."""

        @dataclass
        class ParentOf(Edge):
            pass

        edge = ParentOf()
        assert isinstance(edge, Edge)
