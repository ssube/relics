"""Tests for edge query functionality."""

from pydantic.dataclasses import dataclass

from relics import Component, Edge, World


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
    """Edge representing an alliance relationship."""

    trust_level: float = 1.0


@dataclass
class EnemyOf(Edge):
    """Edge representing an enemy relationship."""

    threat_level: int = 1


class TestWithRelationship:
    """Tests for with_relationship query method."""

    def test_query_entities_with_relationship(self) -> None:
        """Test querying entities that have outgoing relationships."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        world.spawn("player")  # p2 - no relationships
        p3 = world.spawn("player")

        # p1 has ally relationship, p2 doesn't
        p1.add_relationship(AllyTo(), p3.id)

        with_ally = list(world.query().with_relationship(AllyTo).execute_entities())
        assert len(with_ally) == 1
        assert with_ally[0] == p1

    def test_query_with_specific_target(self) -> None:
        """Test querying entities with relationship to specific target."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        p1.add_relationship(AllyTo(), p3.id)
        p2.add_relationship(AllyTo(), p3.id)

        # Query for entities with relationship to p3
        allied_to_p3 = list(
            world.query().with_relationship(AllyTo, p3.id).execute_entities()
        )
        assert len(allied_to_p3) == 2
        ids = {e.id for e in allied_to_p3}
        assert p1.id in ids
        assert p2.id in ids

    def test_query_with_relationship_and_components(self) -> None:
        """Test combining relationship and component queries."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab(
            "enemy",
            {Position: Position(x=10, y=10), Health: Health(current=100, maximum=100)},
        )

        player = world.spawn("player")
        enemy1 = world.spawn("enemy")
        world.spawn("enemy")  # enemy2 - unused

        player.add_relationship(AllyTo(), enemy1.id)

        # Query: has Health component AND has ally relationship
        result = list(
            world.query()
            .with_all([Health])
            .with_relationship(AllyTo)
            .execute_entities()
        )

        # Neither enemy has an ally relationship (player does, but no Health)
        assert len(result) == 0

        # Give enemy1 an ally relationship
        enemy1.add_relationship(AllyTo(), player.id)

        result = list(
            world.query()
            .with_all([Health])
            .with_relationship(AllyTo)
            .execute_entities()
        )
        assert len(result) == 1
        assert result[0] == enemy1


class TestWithIncoming:
    """Tests for with_incoming query method."""

    def test_query_entities_with_incoming(self) -> None:
        """Test querying entities that have incoming relationships."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        world.spawn("player")  # p3 - no relationships

        p1.add_relationship(AllyTo(), p2.id)

        # p2 has incoming, p1 and p3 don't
        with_incoming = list(
            world.query().with_incoming(AllyTo).execute_entities()
        )
        assert len(with_incoming) == 1
        assert with_incoming[0] == p2

    def test_query_with_specific_source(self) -> None:
        """Test querying entities with incoming relationship from source."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        p1.add_relationship(AllyTo(), p3.id)
        p2.add_relationship(AllyTo(), p3.id)

        # Query for entities with incoming from p1
        from_p1 = list(
            world.query().with_incoming(AllyTo, p1.id).execute_entities()
        )
        assert len(from_p1) == 1
        assert from_p1[0] == p3

    def test_query_with_incoming_and_components(self) -> None:
        """Test combining incoming relationship and component queries."""
        world = World()
        world.register_prefab("base", {Position: Position(x=0, y=0)})
        world.register_prefab(
            "defended",
            {Position: Position(x=5, y=5), Health: Health(current=100, maximum=100)},
        )

        base1 = world.spawn("base")
        defended1 = world.spawn("defended")
        world.spawn("defended")  # defended2 - no relationships

        base1.add_relationship(AllyTo(), defended1.id)

        # Query: has Health AND has incoming ally
        result = list(
            world.query()
            .with_all([Health])
            .with_incoming(AllyTo)
            .execute_entities()
        )
        assert len(result) == 1
        assert result[0] == defended1


class TestCombinedQueries:
    """Tests for combining multiple relationship queries."""

    def test_both_outgoing_and_incoming(self) -> None:
        """Test querying entities with both outgoing and incoming."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        # p2 is in the middle: p1 -> p2 -> p3
        p1.add_relationship(AllyTo(), p2.id)
        p2.add_relationship(AllyTo(), p3.id)

        # p2 has both outgoing and incoming
        result = list(
            world.query()
            .with_relationship(AllyTo)
            .with_incoming(AllyTo)
            .execute_entities()
        )
        assert len(result) == 1
        assert result[0] == p2

    def test_multiple_edge_types(self) -> None:
        """Test querying with multiple edge types."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        p1.add_relationship(EnemyOf(), p3.id)

        # p1 has both ally and enemy relationships
        result = list(
            world.query()
            .with_relationship(AllyTo)
            .with_relationship(EnemyOf)
            .execute_entities()
        )
        assert len(result) == 1
        assert result[0] == p1

        # p2 doesn't have enemy relationship
        p2.add_relationship(AllyTo(), p3.id)
        result = list(
            world.query()
            .with_relationship(AllyTo)
            .with_relationship(EnemyOf)
            .execute_entities()
        )
        assert len(result) == 1  # Still just p1

    def test_filter_with_relationships(self) -> None:
        """Test combining relationship queries with predicate filters."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        p3.add_relationship(AllyTo(trust_level=0.3), p2.id)

        def high_trust_ally(entity):
            rels = entity.get_relationships(AllyTo)
            return any(edge.trust_level > 0.5 for edge, _ in rels)

        result = list(
            world.query()
            .with_relationship(AllyTo)
            .with_filter(high_trust_ally)
            .execute_entities()
        )
        assert len(result) == 1
        assert result[0] == p1
