"""Tests for relics.world module."""

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    ComponentObserver,
    Edge,
    EntityNotFoundError,
    PrefabNotFoundError,
    RelationshipValidationError,
    World,
    monitored,
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


@dataclass
class AllyTo(Edge):
    """Test edge for relationships."""

    trust_level: float = 1.0


@dataclass
class FailingEdge(Edge):
    """Edge that raises an exception during validation."""

    def validate(self, source, target):
        raise ValueError("Validation error")


class TestRelationshipEdgeCases:
    """Tests for relationship edge cases in World."""

    def test_add_relationship_nonexistent_source(self) -> None:
        """Test add_relationship with non-existent source raises error."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        target = world.spawn("player")
        fake_source_id = EntityId(prefab="player", sequence=999999)

        with pytest.raises(EntityNotFoundError) as exc_info:
            world._add_relationship(fake_source_id, AllyTo(), target.id)
        assert "Source entity" in str(exc_info.value)

    def test_add_relationship_nonexistent_target(self) -> None:
        """Test add_relationship with non-existent target raises error."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        source = world.spawn("player")
        fake_target_id = EntityId(prefab="player", sequence=999999)

        with pytest.raises(EntityNotFoundError) as exc_info:
            world._add_relationship(source.id, AllyTo(), fake_target_id)
        assert "Target entity" in str(exc_info.value)

    def test_add_relationship_validation_exception(self) -> None:
        """Test add_relationship when edge validation raises exception."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        source = world.spawn("player")
        target = world.spawn("player")

        with pytest.raises(RelationshipValidationError) as exc_info:
            world._add_relationship(source.id, FailingEdge(), target.id)
        assert "Edge validation raised exception" in str(exc_info.value)

    def test_get_relationships_no_relationships(self) -> None:
        """Test _get_relationships for entity with no relationships."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        entity = world.spawn("player")

        # Entity has no relationships at all
        relationships = world._get_relationships(entity.id, AllyTo)
        assert relationships == []

    def test_get_relationships_no_relationships_of_type(self) -> None:
        """Test _get_relationships for entity with no relationships of that type."""

        @dataclass
        class EnemyOf(Edge):
            """Another edge type."""

            pass

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        # Add EnemyOf relationship, then query for AllyTo
        p1.add_relationship(EnemyOf(), p2.id)

        # Query for AllyTo should return empty
        relationships = world._get_relationships(p1.id, AllyTo)
        assert relationships == []

    def test_get_incoming_relationships_no_relationships(self) -> None:
        """Test _get_incoming_relationships for entity with no incoming."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        entity = world.spawn("player")

        # Entity has no incoming relationships at all
        relationships = world._get_incoming_relationships(entity.id, AllyTo)
        assert relationships == []

    def test_get_incoming_relationships_no_relationships_of_type(self) -> None:
        """Test _get_incoming_relationships for entity with no incoming of that type."""

        @dataclass
        class EnemyOf(Edge):
            """Another edge type."""

            pass

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        # p1 -> p2 with EnemyOf, then query p2 for AllyTo incoming
        p1.add_relationship(EnemyOf(), p2.id)

        # Query for AllyTo incoming should return empty
        relationships = world._get_incoming_relationships(p2.id, AllyTo)
        assert relationships == []


class TestExportEntity:
    """Tests for export_entity in World."""

    def test_export_entity_not_found(self) -> None:
        """Test export_entity with non-existent entity raises error."""
        world = World()

        fake_id = EntityId(prefab="player", sequence=999999)
        with pytest.raises(EntityNotFoundError):
            world.export_entity(fake_id)


@monitored
@dataclass
class MonitoredHealth(Component):
    """Monitored health component for testing."""

    current: int
    maximum: int


class TestComponentObserverOnChanged:
    """Tests for ComponentObserver handling on_component_changed."""

    def test_component_observer_receives_changed_events(self) -> None:
        """Test that ComponentObserver receives on_component_changed events."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                MonitoredHealth: MonitoredHealth(current=100, maximum=100),
            },
        )

        changes = []

        class HealthTracker(ComponentObserver):
            component_type = MonitoredHealth

            def on_component_changed(self, entity, old_value, new_value):
                changes.append((old_value.current, new_value.current))

        world.observe(HealthTracker())

        entity = world.spawn("player")
        health = entity.get_component(MonitoredHealth)
        health._bind_to_world(world, entity.id)

        # Change health
        health.current = 80
        world.tick(0.016)

        assert len(changes) == 1
        assert changes[0] == (100, 80)
