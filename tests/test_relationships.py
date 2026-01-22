"""Tests for relationship (edge) functionality."""

from typing import List

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    Edge,
    Entity,
    OnRelationshipAdded,
    OnRelationshipRemoved,
    RelationshipValidationError,
    World,
)


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@dataclass
class Team(Component):
    """Test component for team membership."""

    team_id: str


@dataclass
class AllyTo(Edge):
    """Edge representing an alliance relationship."""

    trust_level: float = 1.0


@dataclass
class EnemyOf(Edge):
    """Edge representing an enemy relationship."""

    threat_level: int = 1


@dataclass
class ParentOf(Edge):
    """Edge with validation - can't be your own parent."""

    def validate(self, source: Entity, target: Entity) -> bool:
        return source.id != target.id


@dataclass
class SameTeamOnly(Edge):
    """Edge that only allows same-team relationships."""

    def validate(self, source: Entity, target: Entity) -> bool:
        if not source.has_component(Team) or not target.has_component(Team):
            return False
        return source.get_component(Team).team_id == target.get_component(Team).team_id


class TestRelationshipBasics:
    """Tests for basic relationship CRUD operations."""

    def test_add_relationship(self) -> None:
        """Test adding a relationship between entities."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)

        assert p1.has_relationship(AllyTo)
        assert p1.has_relationship(AllyTo, p2.id)
        assert not p1.has_relationship(EnemyOf)

    def test_get_relationships(self) -> None:
        """Test getting outgoing relationships."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)
        p1.add_relationship(AllyTo(trust_level=0.5), p3.id)

        relationships = p1.get_relationships(AllyTo)
        assert len(relationships) == 2

        targets = {target_id for _, target_id in relationships}
        assert p2.id in targets
        assert p3.id in targets

    def test_get_incoming_relationships(self) -> None:
        """Test getting incoming relationships."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        p3.add_relationship(AllyTo(), p2.id)

        incoming = p2.get_incoming_relationships(AllyTo)
        assert len(incoming) == 2

        sources = {source_id for source_id, _ in incoming}
        assert p1.id in sources
        assert p3.id in sources

    def test_has_incoming_relationship(self) -> None:
        """Test checking for incoming relationships."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)

        assert p2.has_incoming_relationship(AllyTo)
        assert p2.has_incoming_relationship(AllyTo, p1.id)
        assert not p2.has_incoming_relationship(EnemyOf)
        assert not p1.has_incoming_relationship(AllyTo)

    def test_remove_relationship(self) -> None:
        """Test removing a relationship."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        assert p1.has_relationship(AllyTo, p2.id)

        p1.remove_relationship(AllyTo, p2.id)
        assert not p1.has_relationship(AllyTo, p2.id)
        assert not p2.has_incoming_relationship(AllyTo, p1.id)

    def test_multiple_edge_types(self) -> None:
        """Test having multiple edge types between same entities."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        p1.add_relationship(EnemyOf(threat_level=5), p2.id)

        assert p1.has_relationship(AllyTo, p2.id)
        assert p1.has_relationship(EnemyOf, p2.id)

        ally_rels = p1.get_relationships(AllyTo)
        enemy_rels = p1.get_relationships(EnemyOf)
        assert len(ally_rels) == 1
        assert len(enemy_rels) == 1


class TestRelationshipValidation:
    """Tests for relationship validation."""

    def test_validation_passes(self) -> None:
        """Test that valid relationships are accepted."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        # ParentOf should pass when source != target
        p1.add_relationship(ParentOf(), p2.id)
        assert p1.has_relationship(ParentOf, p2.id)

    def test_validation_fails(self) -> None:
        """Test that invalid relationships are rejected."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")

        # Can't be your own parent
        with pytest.raises(RelationshipValidationError):
            p1.add_relationship(ParentOf(), p1.id)

    def test_component_based_validation(self) -> None:
        """Test validation that depends on components."""
        world = World()
        world.register_prefab("player", {Team: Team(team_id="blue")})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player", {Team: Team(team_id="red")})

        # Same team - should pass
        p1.add_relationship(SameTeamOnly(), p2.id)
        assert p1.has_relationship(SameTeamOnly, p2.id)

        # Different teams - should fail
        with pytest.raises(RelationshipValidationError):
            p1.add_relationship(SameTeamOnly(), p3.id)


class TestRelationshipCleanup:
    """Tests for relationship cleanup when entities are removed."""

    def test_cleanup_on_source_removal(self) -> None:
        """Test that relationships are cleaned up when source is removed."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        assert p2.has_incoming_relationship(AllyTo, p1.id)

        world.remove(p1)
        world.tick(0)  # Process events

        # p2 should no longer have incoming relationship from p1
        assert not p2.has_incoming_relationship(AllyTo, p1.id)

    def test_cleanup_on_target_removal(self) -> None:
        """Test that relationships are cleaned up when target is removed."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        assert p1.has_relationship(AllyTo, p2.id)

        world.remove(p2)
        world.tick(0)

        # p1 should no longer have relationship to p2
        assert not p1.has_relationship(AllyTo, p2.id)


class TestRelationshipObservers:
    """Tests for relationship observers."""

    def test_on_relationship_added_observer(self) -> None:
        """Test OnRelationshipAdded observer is triggered."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        events: List[tuple] = []

        class AllyAddedObserver(OnRelationshipAdded):
            edge_type = AllyTo

            def on_relationship_added(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                events.append((source.id, edge, target.id))

        world.observe(AllyAddedObserver())

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        world.tick(0)

        assert len(events) == 1
        source_id, edge, target_id = events[0]
        assert source_id == p1.id
        assert target_id == p2.id
        assert isinstance(edge, AllyTo)
        assert edge.trust_level == 0.9

    def test_on_relationship_removed_observer(self) -> None:
        """Test OnRelationshipRemoved observer is triggered."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        events: List[tuple] = []

        class AllyRemovedObserver(OnRelationshipRemoved):
            edge_type = AllyTo

            def on_relationship_removed(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                events.append((source.id, edge, target.id))

        world.observe(AllyRemovedObserver())

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        world.tick(0)

        p1.remove_relationship(AllyTo, p2.id)
        world.tick(0)

        assert len(events) == 1
        source_id, edge, target_id = events[0]
        assert source_id == p1.id
        assert target_id == p2.id

    def test_observer_filters_by_edge_type(self) -> None:
        """Test that observers only receive events for their edge type."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        ally_events: List[tuple] = []
        enemy_events: List[tuple] = []

        class AllyObserver(OnRelationshipAdded):
            edge_type = AllyTo

            def on_relationship_added(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                ally_events.append((source.id, target.id))

        class EnemyObserver(OnRelationshipAdded):
            edge_type = EnemyOf

            def on_relationship_added(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                enemy_events.append((source.id, target.id))

        world.observe(AllyObserver())
        world.observe(EnemyObserver())

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        world.tick(0)

        assert len(ally_events) == 1
        assert len(enemy_events) == 0
