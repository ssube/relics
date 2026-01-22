"""Tests for relics.query module."""

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, World


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


@dataclass
class Dead(Component):
    """Marker component for dead entities."""

    pass


class TestQueryBuilder:
    """Tests for QueryBuilder class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.world = World()
        self.world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Velocity: Velocity(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )
        self.world.register_prefab(
            "static",
            {Position: Position(x=0, y=0)},
        )

    def test_with_all_single(self) -> None:
        """Test with_all with single component."""
        self.world.spawn("player")
        self.world.spawn("static")

        results = list(self.world.query().with_all([Position]).execute_entities())
        assert len(results) == 2

    def test_with_all_multiple(self) -> None:
        """Test with_all with multiple components."""
        self.world.spawn("player")
        self.world.spawn("static")

        results = list(
            self.world.query().with_all([Position, Velocity]).execute_entities()
        )
        assert len(results) == 1  # Only player has both

    def test_with_any(self) -> None:
        """Test with_any selector."""
        self.world.spawn("player")
        self.world.spawn("static")

        results = list(
            self.world.query().with_any([Velocity, Health]).execute_entities()
        )
        assert len(results) == 1  # Only player has either

    def test_with_none(self) -> None:
        """Test with_none selector."""
        player = self.world.spawn("player")
        self.world.spawn("static")

        # Add Dead to player
        player.add_component(Dead())

        results = list(self.world.query().with_none([Dead]).execute_entities())
        assert len(results) == 1  # Only static doesn't have Dead

    def test_combined_selectors(self) -> None:
        """Test combining with_all, with_any, with_none."""
        player = self.world.spawn("player")
        self.world.spawn("static")

        # Mark player as dead
        player.add_component(Dead())

        # Query: must have Position, must have Velocity or Health, must not have Dead
        results = list(
            self.world.query()
            .with_all([Position])
            .with_any([Velocity, Health])
            .with_none([Dead])
            .execute_entities()
        )
        assert len(results) == 0  # Player is dead, static doesn't have Velocity/Health

    def test_with_filter(self) -> None:
        """Test with_filter predicate."""
        p1 = self.world.spawn("player", {Position: Position(x=10, y=0)})
        self.world.spawn("player", {Position: Position(x=50, y=0)})

        # Filter for entities with x < 30
        results = list(
            self.world.query()
            .with_all([Position])
            .with_filter(lambda e: e.get_component(Position).x < 30)
            .execute_entities()
        )
        assert len(results) == 1
        assert results[0].id == p1.id

    def test_multiple_filters(self) -> None:
        """Test multiple with_filter predicates."""
        self.world.spawn("player", {Health: Health(current=80, maximum=100)})
        self.world.spawn("player", {Health: Health(current=50, maximum=100)})
        self.world.spawn("player", {Health: Health(current=30, maximum=100)})

        # Filter for health between 40 and 90
        results = list(
            self.world.query()
            .with_all([Health])
            .with_filter(lambda e: e.get_component(Health).current > 40)
            .with_filter(lambda e: e.get_component(Health).current < 90)
            .execute_entities()
        )
        assert len(results) == 2  # 80 and 50

    def test_execute_ids(self) -> None:
        """Test execute_ids returns EntityIds."""
        entity = self.world.spawn("player")

        ids = list(self.world.query().with_all([Position]).execute_ids())
        assert len(ids) >= 1
        assert entity.id in ids

    def test_execute_entities(self) -> None:
        """Test execute_entities returns Entity handles."""
        self.world.spawn("player")

        entities = list(self.world.query().with_all([Position]).execute_entities())
        assert len(entities) >= 1
        # Check it's an Entity
        assert hasattr(entities[0], "get_component")

    def test_iterate_and_execute_components(self) -> None:
        """Test iterate() and execute_components()."""
        self.world.spawn("player", {Position: Position(x=10, y=20)})

        results = list(
            self.world.query()
            .with_all([Position, Velocity])
            .iterate([Position, Velocity])
            .execute_components()
        )

        assert len(results) == 1
        entity_id, pos, vel = results[0]
        assert pos.x == 10
        assert pos.y == 20

    def test_execute_components_without_iterate(self) -> None:
        """Test execute_components raises error without iterate()."""
        self.world.spawn("player")

        with pytest.raises(ValueError, match="iterate"):
            list(self.world.query().with_all([Position]).execute_components())

    def test_empty_query(self) -> None:
        """Test query with no selectors returns all entities."""
        self.world.spawn("player")
        self.world.spawn("static")

        results = list(self.world.query().execute_entities())
        assert len(results) == 2

    def test_query_no_matches(self) -> None:
        """Test query with no matches returns empty."""
        self.world.spawn("static")

        results = list(self.world.query().with_all([Velocity]).execute_entities())
        assert len(results) == 0

    def test_chaining_returns_self(self) -> None:
        """Test that all builder methods return self for chaining."""
        builder = self.world.query()

        result = builder.with_all([Position])
        assert result is builder

        result = builder.with_any([Velocity])
        assert result is builder

        result = builder.with_none([Dead])
        assert result is builder

        result = builder.with_filter(lambda e: True)
        assert result is builder

        result = builder.iterate([Position])
        assert result is builder

    def test_prefab_filter(self) -> None:
        """Test filtering by prefab using with_filter."""
        self.world.spawn("player")
        self.world.spawn("player")
        self.world.spawn("static")

        results = list(
            self.world.query()
            .with_filter(lambda e: e.prefab == "player")
            .execute_entities()
        )
        assert len(results) == 2


class TestExecuteComponentsEdgeCases:
    """Tests for edge cases in execute_components."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.world = World()
        self.world.register_prefab(
            "full",
            {
                Position: Position(x=0, y=0),
                Velocity: Velocity(x=1, y=1),
                Health: Health(current=100, maximum=100),
            },
        )
        self.world.register_prefab(
            "partial",
            {Position: Position(x=0, y=0), Health: Health(current=50, maximum=100)},
        )

    def test_execute_components_with_filter_passes(self) -> None:
        """Test execute_components when filter passes."""
        p1 = self.world.spawn("full", {Position: Position(x=10, y=20)})
        self.world.spawn("full", {Position: Position(x=50, y=50)})

        # Filter for position.x < 30
        results = list(
            self.world.query()
            .with_all([Position, Velocity])
            .with_filter(lambda e: e.get_component(Position).x < 30)
            .iterate([Position, Velocity])
            .execute_components()
        )

        assert len(results) == 1
        entity_id, pos, vel = results[0]
        assert entity_id == p1.id
        assert pos.x == 10
        assert pos.y == 20

    def test_execute_components_filter_rejects(self) -> None:
        """Test execute_components when filter rejects some entities."""
        self.world.spawn("full", {Position: Position(x=10, y=20)})
        self.world.spawn("full", {Position: Position(x=50, y=50)})

        # Filter that rejects all
        results = list(
            self.world.query()
            .with_all([Position, Velocity])
            .with_filter(lambda e: False)
            .iterate([Position, Velocity])
            .execute_components()
        )

        assert len(results) == 0

    def test_execute_components_missing_iterate_component(self) -> None:
        """Test execute_components skips entities missing iterate components."""
        self.world.spawn("full")  # Has Position, Velocity, Health
        self.world.spawn("partial")  # Has Position, Health but no Velocity

        # Query for Position but iterate includes Velocity
        results = list(
            self.world.query()
            .with_all([Position])
            .iterate([Position, Velocity])
            .execute_components()
        )

        # Only "full" entity should be returned (has both Position and Velocity)
        assert len(results) == 1

    def test_execute_components_filter_and_missing_component(self) -> None:
        """Test execute_components with filter and missing iterate component."""
        # Create entities that pass filter but don't have all iterate components
        self.world.spawn("partial", {Position: Position(x=5, y=5)})
        self.world.spawn("full", {Position: Position(x=10, y=10)})

        # Filter passes both, but partial is missing Velocity for iterate
        results = list(
            self.world.query()
            .with_all([Position])
            .with_filter(lambda e: e.get_component(Position).x < 20)
            .iterate([Position, Velocity])
            .execute_components()
        )

        # Only "full" entity should be returned
        assert len(results) == 1
        entity_id, pos, vel = results[0]
        assert pos.x == 10
