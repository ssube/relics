"""Tests for relics.observer module."""

from typing import List, Tuple

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    ComponentObserver,
    Edge,
    Entity,
    EntityObserver,
    OnComponentAdded,
    OnComponentRemoved,
    OnEntityCreated,
    OnEntityDestroyed,
    RelationshipObserver,
    World,
)


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
class Dead(Component):
    """Marker component for dead entities."""

    pass


class TestOnEntityCreated:
    """Tests for OnEntityCreated observer."""

    def test_on_entity_created_all_prefabs(self) -> None:
        """Test observer triggers for all entity creations."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        created_entities: List[Entity] = []

        class CreationObserver(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                created_entities.append(entity)

        world.observe(CreationObserver())

        world.spawn("player")
        world.spawn("enemy")
        world.tick(0.016)  # Process observer queue

        assert len(created_entities) == 2

    def test_on_entity_created_specific_prefab(self) -> None:
        """Test observer triggers only for specific prefab."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        created_entities: List[Entity] = []

        class PlayerCreationObserver(OnEntityCreated):
            prefab = "player"

            def on_entity_created(self, entity: Entity) -> None:
                created_entities.append(entity)

        world.observe(PlayerCreationObserver())

        world.spawn("player")
        world.spawn("enemy")
        world.tick(0.016)

        assert len(created_entities) == 1
        assert created_entities[0].prefab == "player"


class TestOnEntityDestroyed:
    """Tests for OnEntityDestroyed observer."""

    def test_on_entity_destroyed(self) -> None:
        """Test observer triggers on entity destruction."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        destroyed_entities: List[Entity] = []

        class DestructionObserver(OnEntityDestroyed):
            prefab = None

            def on_entity_destroyed(self, entity: Entity) -> None:
                destroyed_entities.append(entity)

        world.observe(DestructionObserver())

        entity = world.spawn("player")
        world.tick(0.016)

        world.remove(entity)
        world.tick(0.016)

        assert len(destroyed_entities) == 1

    def test_on_entity_destroyed_specific_prefab(self) -> None:
        """Test observer triggers only for specific prefab destruction."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        destroyed_entities: List[Entity] = []

        class EnemyDestructionObserver(OnEntityDestroyed):
            prefab = "enemy"

            def on_entity_destroyed(self, entity: Entity) -> None:
                destroyed_entities.append(entity)

        world.observe(EnemyDestructionObserver())

        player = world.spawn("player")
        enemy = world.spawn("enemy")
        world.tick(0.016)

        world.remove(player)
        world.remove(enemy)
        world.tick(0.016)

        assert len(destroyed_entities) == 1
        assert destroyed_entities[0].prefab == "enemy"


class TestOnComponentAdded:
    """Tests for OnComponentAdded observer."""

    def test_on_component_added(self) -> None:
        """Test observer triggers when component is added."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        added_components: List[Tuple[Entity, Component]] = []

        class HealthAddedObserver(OnComponentAdded):
            component_type = Health

            def on_component_added(self, entity: Entity, component: Component) -> None:
                added_components.append((entity, component))

        world.observe(HealthAddedObserver())

        entity = world.spawn("player")
        entity.add_component(Health(current=100, maximum=100))
        world.tick(0.016)

        assert len(added_components) == 1
        assert added_components[0][0].id == entity.id
        assert isinstance(added_components[0][1], Health)

    def test_on_component_added_spawn(self) -> None:
        """Test observer triggers for components from prefab spawn."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        added_components: List[Tuple[Entity, Component]] = []

        class HealthAddedObserver(OnComponentAdded):
            component_type = Health

            def on_component_added(self, entity: Entity, component: Component) -> None:
                added_components.append((entity, component))

        world.observe(HealthAddedObserver())

        # spawn doesn't trigger add_component observers (components come from prefab)
        world.spawn("player")
        world.tick(0.016)

        # Prefab components don't trigger OnComponentAdded
        assert len(added_components) == 0


class TestOnComponentRemoved:
    """Tests for OnComponentRemoved observer."""

    def test_on_component_removed(self) -> None:
        """Test observer triggers when component is removed."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        removed_components: List[Tuple[Entity, Component]] = []

        class HealthRemovedObserver(OnComponentRemoved):
            component_type = Health

            def on_component_removed(
                self, entity: Entity, component: Component
            ) -> None:
                removed_components.append((entity, component))

        world.observe(HealthRemovedObserver())

        entity = world.spawn("player")
        entity.remove_component(Health)
        world.tick(0.016)

        assert len(removed_components) == 1
        assert removed_components[0][0].id == entity.id
        assert isinstance(removed_components[0][1], Health)


class TestObserverQueue:
    """Tests for observer queue processing."""

    def test_observers_processed_at_tick_end(self) -> None:
        """Test that observers are processed at end of tick."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        processed_at_epoch: List[int] = []

        class CreationObserver(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                processed_at_epoch.append(self.world.epoch)

        world.observe(CreationObserver())

        world.spawn("player")  # Queued
        # Not processed yet
        world.tick(0.016)  # Now processed

        assert len(processed_at_epoch) == 1
        assert processed_at_epoch[0] == 1  # Processed during tick 1

    def test_multiple_observers_same_event(self) -> None:
        """Test multiple observers for same event type."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        observer1_count = [0]
        observer2_count = [0]

        class Observer1(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                observer1_count[0] += 1

        class Observer2(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                observer2_count[0] += 1

        world.observe(Observer1())
        world.observe(Observer2())

        world.spawn("player")
        world.tick(0.016)

        assert observer1_count[0] == 1
        assert observer2_count[0] == 1

    def test_observer_can_modify_world(self) -> None:
        """Test that observers can spawn/remove entities."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("ghost", {Position: Position(x=0, y=0)})

        class SpawnGhostOnDeath(OnComponentAdded):
            component_type = Dead

            def on_component_added(self, entity: Entity, component: Component) -> None:
                # Spawn a ghost when entity dies
                pos = entity.get_component(Position)
                self.world.spawn("ghost", {Position: Position(x=pos.x, y=pos.y)})

        world.observe(SpawnGhostOnDeath())

        player = world.spawn("player", {Position: Position(x=10, y=20)})
        player.add_component(Dead())
        world.tick(0.016)

        # Should have player + ghost
        all_entities = list(world.query().execute_entities())
        assert len(all_entities) == 2

        ghost = [e for e in all_entities if e.prefab == "ghost"][0]
        ghost_pos = ghost.get_component(Position)
        assert ghost_pos.x == 10
        assert ghost_pos.y == 20


@dataclass
class AllyTo(Edge):
    """Test edge for relationships."""

    trust_level: float = 1.0


class TestMultiEventObservers:
    """Tests for multi-event observers (ComponentObserver, EntityObserver, etc.)."""

    def test_component_observer_add_and_remove(self) -> None:
        """Test ComponentObserver receives add and remove events."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        events = []

        class HealthTracker(ComponentObserver):
            component_type = Health

            def on_component_added(self, entity, component):
                events.append(("added", entity.id, component.current))

            def on_component_removed(self, entity, component):
                events.append(("removed", entity.id, component.current))

        world.observe(HealthTracker())

        player = world.spawn("player")
        player.add_component(Health(current=100, maximum=100))
        world.tick(0)

        assert len(events) == 1
        assert events[0] == ("added", player.id, 100)

        # Remove component
        player.remove_component(Health)
        world.tick(0)

        assert len(events) == 2
        assert events[1] == ("removed", player.id, 100)

    def test_entity_observer_all_events(self) -> None:
        """Test EntityObserver receives create and destroy events."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        events = []

        class PlayerTracker(EntityObserver):
            prefab = "player"

            def on_entity_created(self, entity):
                events.append(("created", entity.id))

            def on_entity_destroyed(self, entity):
                events.append(("destroyed", entity.id))

        world.observe(PlayerTracker())

        player = world.spawn("player")
        world.tick(0)

        assert len(events) == 1
        assert events[0] == ("created", player.id)

        world.remove(player)
        world.tick(0)

        assert len(events) == 2
        assert events[1] == ("destroyed", player.id)

    def test_entity_observer_filters_by_prefab(self) -> None:
        """Test EntityObserver only receives events for its prefab."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        events = []

        class PlayerTracker(EntityObserver):
            prefab = "player"

            def on_entity_created(self, entity):
                events.append(("created", entity.prefab))

            def on_entity_destroyed(self, entity):
                events.append(("destroyed", entity.prefab))

        world.observe(PlayerTracker())

        player = world.spawn("player")
        enemy = world.spawn("enemy")
        world.tick(0)

        # Only player creation should be recorded
        assert len(events) == 1
        assert events[0] == ("created", "player")

        world.remove(player)
        world.remove(enemy)
        world.tick(0)

        # Only player destruction should be recorded
        assert len(events) == 2
        assert events[1] == ("destroyed", "player")

    def test_entity_observer_all_prefabs(self) -> None:
        """Test EntityObserver with prefab=None receives all events."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        events = []

        class AllEntityTracker(EntityObserver):
            prefab = None

            def on_entity_created(self, entity):
                events.append(("created", entity.prefab))

        world.observe(AllEntityTracker())

        world.spawn("player")
        world.spawn("enemy")
        world.tick(0)

        assert len(events) == 2

    def test_relationship_observer_all_events(self) -> None:
        """Test RelationshipObserver receives add and remove events."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        events = []

        class AllyTracker(RelationshipObserver):
            edge_type = AllyTo

            def on_relationship_added(self, source, edge, target):
                events.append(("added", source.id, target.id, edge.trust_level))

            def on_relationship_removed(self, source, edge, target):
                events.append(("removed", source.id, target.id))

        world.observe(AllyTracker())

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        world.tick(0)

        assert len(events) == 1
        assert events[0] == ("added", p1.id, p2.id, 0.9)

        p1.remove_relationship(AllyTo, p2.id)
        world.tick(0)

        assert len(events) == 2
        assert events[1] == ("removed", p1.id, p2.id)

    def test_component_observer_default_methods(self) -> None:
        """Test that ComponentObserver default methods are no-ops."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        # Create observer that doesn't override any methods
        class EmptyObserver(ComponentObserver):
            component_type = Health

        observer = EmptyObserver()
        world.observe(observer)

        player = world.spawn("player")
        player.add_component(Health(current=100, maximum=100))
        player.remove_component(Health)
        world.tick(0)

        # Should not raise any errors

    def test_entity_observer_default_methods(self) -> None:
        """Test that EntityObserver default methods are no-ops."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        class EmptyObserver(EntityObserver):
            prefab = None

        observer = EmptyObserver()
        world.observe(observer)

        player = world.spawn("player")
        world.remove(player)
        world.tick(0)

        # Should not raise any errors

    def test_relationship_observer_default_methods(self) -> None:
        """Test that RelationshipObserver default methods are no-ops."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        class EmptyObserver(RelationshipObserver):
            edge_type = AllyTo

        observer = EmptyObserver()
        world.observe(observer)

        p1 = world.spawn("player")
        p2 = world.spawn("player")

        p1.add_relationship(AllyTo(), p2.id)
        p1.remove_relationship(AllyTo, p2.id)
        world.tick(0)

        # Should not raise any errors


class TestObserverWorldProperty:
    """Tests for Observer.world property."""

    def test_observer_world_not_registered(self) -> None:
        """Test accessing world before registration raises error."""

        class TestObserver(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                pass

        observer = TestObserver()

        with pytest.raises(RuntimeError) as exc_info:
            _ = observer.world
        assert "Observer is not registered with a world" in str(exc_info.value)

    def test_observer_world_after_registration(self) -> None:
        """Test accessing world after registration succeeds."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        class TestObserver(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                pass

        observer = TestObserver()
        world.observe(observer)

        # Should not raise
        assert observer.world is world
