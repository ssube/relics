"""Tests for relics.observer module."""

from typing import List, Tuple

from pydantic.dataclasses import dataclass

from relics import (
    Component,
    Entity,
    OnComponentAdded,
    OnComponentRemoved,
    OnEntityCreated,
    OnEntityDestroyed,
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
