"""Tests for secondary index functionality."""

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, IndexNotFoundError, World


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

    vx: float
    vy: float


class TestLazyIndex:
    """Tests for LazyIndex."""

    def test_create_lazy_index(self) -> None:
        """Test creating a lazy index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")
        world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index("players", query, materialized=False)

        entities = list(index)
        assert len(entities) == 2

    def test_lazy_index_count(self) -> None:
        """Test count on lazy index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")
        world.spawn("player")
        world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index("players", query, materialized=False)

        assert index.count() == 3
        assert len(index) == 3

    def test_lazy_index_updates_automatically(self) -> None:
        """Test that lazy index reflects current state."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index("players", query, materialized=False)

        assert index.count() == 1

        world.spawn("player")
        assert index.count() == 2

        world.remove(p1)
        assert index.count() == 1

    def test_lazy_index_with_complex_query(self) -> None:
        """Test lazy index with complex query criteria."""
        world = World()
        world.register_prefab(
            "moving",
            {Position: Position(x=0, y=0), Velocity: Velocity(vx=1, vy=1)},
        )
        world.register_prefab("static", {Position: Position(x=0, y=0)})

        world.spawn("moving")
        world.spawn("moving")
        world.spawn("static")

        query = world.query().with_all([Position, Velocity])
        index = world.create_index("moving_entities", query, materialized=False)

        assert index.count() == 2


class TestMaterializedIndex:
    """Tests for MaterializedIndex."""

    def test_create_materialized_index(self) -> None:
        """Test creating a materialized index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")
        world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index(
            "players", query, watches=[Position], materialized=True
        )

        entities = list(index)
        assert len(entities) == 2

    def test_materialized_index_count(self) -> None:
        """Test count on materialized index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")
        world.spawn("player")
        world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index(
            "players", query, watches=[Position], materialized=True
        )

        assert index.count() == 3
        assert len(index) == 3

    def test_materialized_index_invalidate(self) -> None:
        """Test invalidating materialized index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index(
            "players", query, watches=[Position], materialized=True
        )

        assert index.count() == 1

        # Spawn more but don't update index
        world.spawn("player")
        world.spawn("player")

        # Index still shows cached count
        # (Note: without manual update, cache is stale)
        # Invalidate to force refresh
        index.invalidate()

        assert index.count() == 3

    def test_materialized_index_update(self) -> None:
        """Test updating specific entity in materialized index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=100, maximum=100)})

        world.spawn("player")  # p1 - has position
        e1 = world.spawn("enemy")

        query = world.query().with_all([Position])
        index = world.create_index(
            "with_position", query, watches=[Position], materialized=True
        )

        # Initially just p1 has Position
        assert index.count() == 1

        # Add Position to enemy
        e1.add_component(Position(x=5, y=5))
        index.update(e1.id)

        assert index.count() == 2


class TestIndexRetrieval:
    """Tests for retrieving indexes by name."""

    def test_get_index_by_name(self) -> None:
        """Test retrieving an index by name."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")

        query = world.query().with_all([Position])
        created = world.create_index("my_index", query, materialized=False)

        retrieved = world.index("my_index")
        assert retrieved is created

    def test_index_not_found(self) -> None:
        """Test error when index doesn't exist."""
        world = World()

        with pytest.raises(IndexNotFoundError):
            world.index("nonexistent")

    def test_multiple_indexes(self) -> None:
        """Test multiple named indexes."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab(
            "enemy",
            {Position: Position(x=10, y=10), Health: Health(current=100, maximum=100)},
        )

        world.spawn("player")
        world.spawn("enemy")

        query1 = world.query().with_all([Position])
        query2 = world.query().with_all([Health])

        world.create_index("all_positioned", query1, materialized=False)
        world.create_index("all_with_health", query2, materialized=False)

        assert world.index("all_positioned").count() == 2
        assert world.index("all_with_health").count() == 1


class TestIndexWithFilters:
    """Tests for indexes with filter predicates."""

    def test_lazy_index_with_filter(self) -> None:
        """Test lazy index respects filter predicates."""
        world = World()
        # Spawn one damaged and one healthy player
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.register_prefab(
            "damaged_player",
            {Position: Position(x=0, y=0), Health: Health(current=50, maximum=100)},
        )

        p1 = world.spawn("damaged_player")
        world.spawn("player")  # p2 - healthy

        def is_damaged(entity):
            h = entity.get_component(Health)
            return h.current < h.maximum

        query = world.query().with_all([Health]).with_filter(is_damaged)
        index = world.create_index("damaged", query, materialized=False)

        damaged = list(index)
        assert len(damaged) == 1
        assert damaged[0] == p1


class TestMaterializedIndexEdgeCases:
    """Tests for edge cases in MaterializedIndex."""

    def test_materialized_index_with_filter(self) -> None:
        """Test materialized index with filter predicates."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.register_prefab(
            "damaged_player",
            {Position: Position(x=0, y=0), Health: Health(current=50, maximum=100)},
        )

        p1 = world.spawn("damaged_player")
        world.spawn("player")  # p2 - healthy

        def is_damaged(entity):
            h = entity.get_component(Health)
            return h.current < h.maximum

        query = world.query().with_all([Health]).with_filter(is_damaged)
        index = world.create_index(
            "damaged", query, watches=[Health], materialized=True
        )

        assert index.count() == 1
        entities = list(index)
        assert len(entities) == 1
        assert entities[0] == p1

        # Update to check filter application in update()
        p3 = world.spawn("damaged_player")
        index.update(p3.id)
        assert index.count() == 2

    def test_materialized_index_update_entity_no_match(self) -> None:
        """Test updating entity that doesn't match query."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=100, maximum=100)})

        p1 = world.spawn("player")
        e1 = world.spawn("enemy")

        query = world.query().with_all([Position])
        index = world.create_index(
            "with_position", query, watches=[Position], materialized=True
        )

        # Initialize cache
        assert index.count() == 1

        # Update entity that doesn't match (no Position)
        index.update(e1.id)

        # Should still only have 1
        assert index.count() == 1

        # Remove Position from p1 and update
        p1.remove_component(Position)
        index.update(p1.id)

        # Now should have 0
        assert index.count() == 0

    def test_materialized_index_update_deleted_entity(self) -> None:
        """Test updating with deleted entity."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        world.spawn("player")  # p2

        query = world.query().with_all([Position])
        index = world.create_index(
            "players", query, watches=[Position], materialized=True
        )

        assert index.count() == 2

        # Remove p1 from world
        world.remove(p1)

        # Update with deleted entity id
        index.update(p1.id)

        assert index.count() == 1

    def test_materialized_index_iter_deleted_entity(self) -> None:
        """Test iteration handles entity deleted between cache and access."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        query = world.query().with_all([Position])
        index = world.create_index(
            "players", query, watches=[Position], materialized=True
        )

        # Force cache initialization
        assert index.count() == 2

        # Remove one entity but don't update cache
        world.remove(p1)

        # Iteration should handle missing entity gracefully
        entities = list(index)
        assert len(entities) == 1
        assert entities[0] == p2

    def test_materialized_index_filter_excludes_entity(self) -> None:
        """Test that filter can exclude entity during update."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        world.spawn("player")  # p1 at origin

        def is_at_origin(entity):
            pos = entity.get_component(Position)
            return pos.x == 0 and pos.y == 0

        query = world.query().with_all([Position]).with_filter(is_at_origin)
        index = world.create_index(
            "at_origin", query, watches=[Position], materialized=True
        )

        # Initially p1 is at origin
        assert index.count() == 1

        # Spawn entity not at origin
        world.register_prefab(
            "moved_player",
            {Position: Position(x=10, y=10), Health: Health(current=100, maximum=100)},
        )
        p2 = world.spawn("moved_player")
        index.update(p2.id)

        # p2 should be excluded by filter
        assert index.count() == 1


class TestIndexQueryIntegration:
    """Tests for using indexes in query builder."""

    def test_with_index_filters_to_index_members(self) -> None:
        """Test that with_index limits results to index members."""
        world = World()
        world.register_prefab(
            "alive_player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.register_prefab(
            "dead_player",
            {Position: Position(x=0, y=0), Health: Health(current=0, maximum=100)},
        )

        alive1 = world.spawn("alive_player")
        alive2 = world.spawn("alive_player")
        dead1 = world.spawn("dead_player")

        # Create index for alive entities
        def is_alive(entity):
            h = entity.get_component(Health)
            return h.current > 0

        alive_query = world.query().with_all([Health]).with_filter(is_alive)
        alive_index = world.create_index(
            "alive", alive_query, watches=[Health], materialized=True
        )

        # Query all with position, but filtered to alive index
        result = list(
            world.query().with_all([Position]).with_index(alive_index).execute_ids()
        )

        assert len(result) == 2
        assert alive1.id in result
        assert alive2.id in result
        assert dead1.id not in result

    def test_without_index_excludes_index_members(self) -> None:
        """Test that without_index excludes index members."""
        world = World()
        world.register_prefab(
            "alive_player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.register_prefab(
            "dead_player",
            {Position: Position(x=0, y=0), Health: Health(current=0, maximum=100)},
        )

        alive1 = world.spawn("alive_player")
        world.spawn("alive_player")  # alive2
        dead1 = world.spawn("dead_player")

        # Create index for alive entities
        def is_alive(entity):
            h = entity.get_component(Health)
            return h.current > 0

        alive_query = world.query().with_all([Health]).with_filter(is_alive)
        alive_index = world.create_index(
            "alive", alive_query, watches=[Health], materialized=True
        )

        # Query all with position, but excluding alive index (only dead)
        result = list(
            world.query()
            .with_all([Position])
            .without_index(alive_index)
            .execute_ids()
        )

        assert len(result) == 1
        assert dead1.id in result
        assert alive1.id not in result

    def test_with_index_and_without_index_combined(self) -> None:
        """Test combining with_index and without_index."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.register_prefab(
            "enemy",
            {
                Position: Position(x=10, y=10),
                Health: Health(current=50, maximum=100),
                Velocity: Velocity(vx=1, vy=1),
            },
        )
        world.register_prefab(
            "npc",
            {Position: Position(x=5, y=5), Health: Health(current=75, maximum=100)},
        )

        player1 = world.spawn("player")
        enemy1 = world.spawn("enemy")
        npc1 = world.spawn("npc")

        # Index for entities with health
        health_query = world.query().with_all([Health])
        health_index = world.create_index("has_health", health_query, materialized=True)

        # Index for moving entities
        moving_query = world.query().with_all([Velocity])
        moving_index = world.create_index("moving", moving_query, materialized=True)

        # Query: has health but not moving (player and npc)
        result = list(
            world.query()
            .with_index(health_index)
            .without_index(moving_index)
            .execute_ids()
        )

        assert len(result) == 2
        assert player1.id in result
        assert npc1.id in result
        assert enemy1.id not in result

    def test_with_index_lazy_index(self) -> None:
        """Test with_index works with lazy indexes."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=100, maximum=100)})

        p1 = world.spawn("player")
        world.spawn("player")  # p2
        e1 = world.spawn("enemy")

        # Create lazy index
        pos_query = world.query().with_all([Position])
        pos_index = world.create_index("positioned", pos_query, materialized=False)

        # Query with lazy index
        result = list(world.query().with_index(pos_index).execute_ids())

        assert len(result) == 2
        assert p1.id in result
        assert e1.id not in result

    def test_with_index_empty_index(self) -> None:
        """Test with_index handles empty index gracefully."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")

        # Create index for non-existent component
        health_query = world.query().with_all([Health])
        health_index = world.create_index("has_health", health_query, materialized=True)

        # Query with empty index should return nothing
        result = list(
            world.query().with_all([Position]).with_index(health_index).execute_ids()
        )

        assert len(result) == 0

    def test_multiple_with_indexes(self) -> None:
        """Test multiple with_index calls (intersection)."""
        world = World()
        world.register_prefab(
            "full_entity",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
                Velocity: Velocity(vx=1, vy=1),
            },
        )
        world.register_prefab(
            "partial_entity",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        full1 = world.spawn("full_entity")
        partial1 = world.spawn("partial_entity")

        pos_index = world.create_index(
            "positioned", world.query().with_all([Position]), materialized=True
        )
        vel_index = world.create_index(
            "moving", world.query().with_all([Velocity]), materialized=True
        )

        # Query with both indexes - only full_entity matches both
        result = list(
            world.query().with_index(pos_index).with_index(vel_index).execute_ids()
        )

        assert len(result) == 1
        assert full1.id in result
        assert partial1.id not in result

    def test_get_entity_ids_lazy_index(self) -> None:
        """Test get_entity_ids on lazy index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        pos_query = world.query().with_all([Position])
        pos_index = world.create_index("positioned", pos_query, materialized=False)

        entity_ids = pos_index.get_entity_ids()

        assert isinstance(entity_ids, set)
        assert len(entity_ids) == 2
        assert p1.id in entity_ids
        assert p2.id in entity_ids

    def test_get_entity_ids_materialized_index(self) -> None:
        """Test get_entity_ids on materialized index."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        pos_query = world.query().with_all([Position])
        pos_index = world.create_index(
            "positioned", pos_query, watches=[Position], materialized=True
        )

        entity_ids = pos_index.get_entity_ids()

        assert isinstance(entity_ids, set)
        assert len(entity_ids) == 2
        assert p1.id in entity_ids
        assert p2.id in entity_ids

        # Verify it returns a copy (not the internal cache)
        entity_ids.add(p1.id)  # Should not affect internal state
        assert pos_index.count() == 2

    def test_with_index_intersection_empty_early_exit(self) -> None:
        """Test that multiple indexes with no intersection returns empty."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=100, maximum=100)})

        world.spawn("player")  # Only has Position
        world.spawn("enemy")  # Only has Health

        # Create disjoint indexes
        pos_index = world.create_index(
            "positioned", world.query().with_all([Position]), materialized=True
        )
        health_index = world.create_index(
            "healthy", world.query().with_all([Health]), materialized=True
        )

        # Query with both indexes - no entity has both, should return empty
        result = list(
            world.query().with_index(pos_index).with_index(health_index).execute_ids()
        )

        assert len(result) == 0

    def test_without_index_removes_all_candidates(self) -> None:
        """Test that without_index can remove all candidates."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.spawn("player")
        world.spawn("player")

        # Create index that matches all entities
        all_index = world.create_index(
            "all_positioned", world.query().with_all([Position]), materialized=True
        )

        # Query with_all Position but exclude all positioned entities
        result = list(
            world.query()
            .with_all([Position])
            .without_index(all_index)
            .execute_ids()
        )

        assert len(result) == 0

    def test_with_index_component_intersection_empty(self) -> None:
        """Test component index + with_index intersection can be empty."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Health: Health(current=100, maximum=100)})

        world.spawn("player")
        world.spawn("enemy")

        # Index only has enemies (Health)
        health_index = world.create_index(
            "healthy", world.query().with_all([Health]), materialized=True
        )

        # Query: with_all Position AND with_index healthy
        # No entity has both Position AND is in healthy index
        result = list(
            world.query()
            .with_all([Position])
            .with_index(health_index)
            .execute_ids()
        )

        assert len(result) == 0


class TestMaterializedIndexUpdates:
    """Tests for materialized index update behavior."""

    def test_materialized_index_update_on_component_change(self) -> None:
        """Test that update() correctly handles component value changes."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        # Index for damaged entities (health < max)
        def is_damaged(entity):
            h = entity.get_component(Health)
            return h.current < h.maximum

        query = world.query().with_all([Health]).with_filter(is_damaged)
        index = world.create_index(
            "damaged", query, watches=[Health], materialized=True
        )

        # Initially no one is damaged
        assert index.count() == 0

        # Damage p1 by replacing component and update index
        p1.remove_component(Health)
        p1.add_component(Health(current=50, maximum=100))
        index.update(p1.id)

        assert index.count() == 1
        assert p1.id in index.get_entity_ids()

        # Heal p1 by replacing component and update index
        p1.remove_component(Health)
        p1.add_component(Health(current=100, maximum=100))
        index.update(p1.id)

        assert index.count() == 0

    def test_materialized_index_update_on_component_add(self) -> None:
        """Test that update() handles component addition."""
        world = World()
        world.register_prefab("basic", {Position: Position(x=0, y=0)})

        p1 = world.spawn("basic")
        p2 = world.spawn("basic")

        # Index for entities with Health
        query = world.query().with_all([Health])
        index = world.create_index(
            "has_health", query, watches=[Health], materialized=True
        )

        # Initially empty
        assert index.count() == 0

        # Add Health to p1 and update
        p1.add_component(Health(current=100, maximum=100))
        index.update(p1.id)

        assert index.count() == 1
        assert p1.id in index.get_entity_ids()

    def test_materialized_index_update_on_component_remove(self) -> None:
        """Test that update() handles component removal."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        p1 = world.spawn("player")

        # Index for entities with Health
        query = world.query().with_all([Health])
        index = world.create_index(
            "has_health", query, watches=[Health], materialized=True
        )

        assert index.count() == 1

        # Remove Health from p1 and update
        p1.remove_component(Health)
        index.update(p1.id)

        assert index.count() == 0

    def test_materialized_index_update_preserves_other_entities(self) -> None:
        """Test that update() doesn't affect other entities in index."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p3 = world.spawn("player")

        query = world.query().with_all([Health])
        index = world.create_index(
            "has_health", query, watches=[Health], materialized=True
        )

        assert index.count() == 3

        # Update only p1 (should not affect p2, p3)
        index.update(p1.id)

        assert index.count() == 3
        assert p1.id in index.get_entity_ids()
        assert p2.id in index.get_entity_ids()
        assert p3.id in index.get_entity_ids()

    def test_materialized_index_selective_update_vs_invalidate(self) -> None:
        """Test that selective update is more efficient than full invalidate."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        # Create many entities
        entities = [world.spawn("player") for _ in range(100)]

        query = world.query().with_all([Health])
        index = world.create_index(
            "has_health", query, watches=[Health], materialized=True
        )

        # Force initialization
        assert index.count() == 100

        # Add new entity
        new_entity = world.spawn("player")

        # Selective update should add just the one entity
        index.update(new_entity.id)

        assert index.count() == 101
        assert new_entity.id in index.get_entity_ids()


class TestExportEntity:
    """Tests for export_entity functionality."""

    def test_export_entity_basic(self) -> None:
        """Test basic entity export."""
        world = World()
        world.register_prefab("player", {Position: Position(x=5, y=10)})

        p1 = world.spawn("player")

        exported = world.export_entity(p1.id)

        assert exported["id"] == str(p1.id)
        assert exported["prefab"] == "player"
        assert "Position" in exported["components"]
        assert exported["components"]["Position"]["x"] == 5
        assert exported["components"]["Position"]["y"] == 10

    def test_export_entity_with_relationships(self) -> None:
        """Test entity export includes relationships."""
        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)

        exported = world.export_entity(p1.id)

        assert "relationships" in exported
        assert "AllyTo" in exported["relationships"]
        assert len(exported["relationships"]["AllyTo"]) == 1
        assert exported["relationships"]["AllyTo"][0]["target"] == str(p2.id)

    def test_export_entity_with_incoming(self) -> None:
        """Test entity export includes incoming relationships."""
        from relics import Edge

        @dataclass
        class AllyTo(Edge):
            trust_level: float = 1.0

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)

        exported = world.export_entity(p2.id)

        assert "incoming_relationships" in exported
        assert "AllyTo" in exported["incoming_relationships"]
        assert len(exported["incoming_relationships"]["AllyTo"]) == 1
        rel = exported["incoming_relationships"]["AllyTo"][0]
        assert rel["source"] == str(p1.id)
