"""Tests for relics.system module."""

from typing import Dict, List, Type

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    Entity,
    Frequency,
    QueryBuilder,
    RunOrder,
    System,
    SystemDependencyCycleError,
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


class TestSystem:
    """Tests for System base class."""

    def test_system_registration(self) -> None:
        """Test registering a system with the world."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        class TestSystem(System):
            def query(self) -> QueryBuilder:
                return self.q.with_all([Position])

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

        system = TestSystem()
        world.register_system(system)
        assert system.world is world

    def test_system_q_property(self) -> None:
        """Test the q property returns a QueryBuilder."""
        world = World()

        class TestSystem(System):
            def query(self) -> QueryBuilder:
                return self.q.with_all([Position])

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

        system = TestSystem()
        world.register_system(system)
        builder = system.q
        assert isinstance(builder, QueryBuilder)

    def test_system_world_not_set(self) -> None:
        """Test accessing world before registration raises error."""

        class TestSystem(System):
            def query(self) -> QueryBuilder:
                return self.q.with_all([Position])

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

        system = TestSystem()
        with pytest.raises(RuntimeError):
            _ = system.world

    def test_system_execution(self) -> None:
        """Test that systems execute during tick."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(x=1, y=2)},
        )

        execution_count = [0]

        class MovementSystem(System):
            def query(self) -> QueryBuilder:
                return self.q.with_all([Position, Velocity])

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_count[0] += 1
                for entity in entities:
                    pos = entity.get_component(Position)
                    vel = entity.get_component(Velocity)
                    pos.x += vel.x * delta
                    pos.y += vel.y * delta

        world.spawn("player")
        world.register_system(MovementSystem())
        world.tick(1.0)

        assert execution_count[0] == 1


class TestFrequency:
    """Tests for Frequency class."""

    def test_every_tick(self) -> None:
        """Test EVERY_TICK frequency."""
        freq = Frequency.EVERY_TICK
        assert freq.should_run(1, 0.016) is True
        assert freq.should_run(2, 0.016) is True

    def test_every_n_ticks(self) -> None:
        """Test every_n_ticks frequency."""
        freq = Frequency.every_n_ticks(3)
        assert freq.should_run(1, 0.016) is False
        assert freq.should_run(2, 0.016) is False
        assert freq.should_run(3, 0.016) is True
        assert freq.should_run(4, 0.016) is False
        assert freq.should_run(6, 0.016) is True

    def test_fixed_interval(self) -> None:
        """Test fixed_interval frequency."""
        freq = Frequency.fixed_interval(1.0)
        # Not enough time
        assert freq.should_run(1, 0.5) is False
        # Accumulated enough time
        assert freq.should_run(2, 0.6) is True
        # Reset, need more time
        assert freq.should_run(3, 0.3) is False


class TestSystemDependencies:
    """Tests for system dependency resolution."""

    def test_after_dependency(self) -> None:
        """Test AFTER dependency ordering."""
        world = World()
        execution_order: List[str] = []

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("A")

        class SystemB(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.AFTER: [SystemA]}

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("B")

        # Register in reverse order
        world.register_system(SystemB())
        world.register_system(SystemA())
        world.tick(0.016)

        assert execution_order == ["A", "B"]

    def test_before_dependency(self) -> None:
        """Test BEFORE dependency ordering."""
        world = World()
        execution_order: List[str] = []

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.BEFORE: [SystemB]}

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("A")

        class SystemB(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("B")

        world.register_system(SystemB())
        world.register_system(SystemA())
        world.tick(0.016)

        assert execution_order == ["A", "B"]

    def test_cycle_detection(self) -> None:
        """Test that circular dependencies raise error."""
        world = World()

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.AFTER: [SystemB]}

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

        class SystemB(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.AFTER: [SystemA]}

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

        world.register_system(SystemA())
        with pytest.raises(SystemDependencyCycleError):
            world.register_system(SystemB())

    def test_wildcard_after(self) -> None:
        """Test WILDCARD in AFTER makes system run last."""
        world = World()
        execution_order: List[str] = []

        class CleanupSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.AFTER: [System.WILDCARD]}

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("Cleanup")

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("A")

        class SystemB(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("B")

        world.register_system(CleanupSystem())
        world.register_system(SystemA())
        world.register_system(SystemB())
        world.tick(0.016)

        # Cleanup should be last
        assert execution_order[-1] == "Cleanup"

    def test_wildcard_before(self) -> None:
        """Test WILDCARD in BEFORE makes system run first."""
        world = World()
        execution_order: List[str] = []

        class InitSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.BEFORE: [System.WILDCARD]}

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("Init")

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("A")

        class SystemB(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("B")

        world.register_system(SystemA())
        world.register_system(InitSystem())
        world.register_system(SystemB())
        world.tick(0.016)

        # Init should be first
        assert execution_order[0] == "Init"


class TestSubSystems:
    """Tests for sub_systems feature."""

    def test_sub_systems_default_empty(self) -> None:
        """Test that sub_systems returns empty list by default."""

        class TestSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

        system = TestSystem()
        assert system.sub_systems() == []

    def test_sub_systems_execution(self) -> None:
        """Test that sub_systems are executed after main process."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab(
            "enemy",
            {Position: Position(x=10, y=10), Velocity: Velocity(x=-1, y=-1)},
        )

        execution_order: List[str] = []
        player_count = [0]
        enemy_count = [0]

        class CombatSystem(System):
            def query(self) -> QueryBuilder:
                # Main query: entities with Position only (players)
                return self.q.with_all([Position]).with_none([Velocity])

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("main")
                player_count[0] = len(entities)

            def sub_systems(self):
                def process_enemies(
                    entities: List[Entity],
                    components: List[List[Component]],
                    delta: float,
                ) -> None:
                    execution_order.append("sub")
                    enemy_count[0] = len(entities)

                # Sub-query: entities with Position AND Velocity (enemies)
                return [(self.q.with_all([Position, Velocity]), process_enemies)]

        world.spawn("player")
        world.spawn("enemy")
        world.register_system(CombatSystem())
        world.tick(0.016)

        assert execution_order == ["main", "sub"]
        assert player_count[0] == 1
        assert enemy_count[0] == 1

    def test_sub_systems_with_iterate(self) -> None:
        """Test that sub_systems receive components from iterate()."""
        world = World()
        world.register_prefab(
            "moving",
            {Position: Position(x=0, y=0), Velocity: Velocity(x=1, y=2)},
        )

        received_components: List[List[Component]] = []

        class MovementSystem(System):
            def query(self) -> QueryBuilder:
                return self.q.with_all([Position])

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                pass

            def sub_systems(self):
                def update_positions(
                    entities: List[Entity],
                    components: List[List[Component]],
                    delta: float,
                ) -> None:
                    received_components.clear()
                    received_components.extend(components)

                return [(
                    self.q.with_all([Position, Velocity]).iterate([Position, Velocity]),
                    update_positions
                )]

        world.spawn("moving")
        world.register_system(MovementSystem())
        world.tick(0.016)

        # Should have two component lists (Position and Velocity)
        assert len(received_components) == 2
        assert len(received_components[0]) == 1  # One Position
        assert len(received_components[1]) == 1  # One Velocity
        assert isinstance(received_components[0][0], Position)
        assert isinstance(received_components[1][0], Velocity)

    def test_multiple_sub_systems(self) -> None:
        """Test multiple sub_systems execute in order."""
        world = World()
        world.register_prefab("entity", {Position: Position(x=0, y=0)})

        execution_order: List[str] = []

        class MultiSubSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(
                self,
                entities: List[Entity],
                components: List[List[Component]],
                delta: float,
            ) -> None:
                execution_order.append("main")

            def sub_systems(self):
                def sub1(entities, components, delta):
                    execution_order.append("sub1")

                def sub2(entities, components, delta):
                    execution_order.append("sub2")

                def sub3(entities, components, delta):
                    execution_order.append("sub3")

                return [
                    (self.q, sub1),
                    (self.q, sub2),
                    (self.q, sub3),
                ]

        world.spawn("entity")
        world.register_system(MultiSubSystem())
        world.tick(0.016)

        assert execution_order == ["main", "sub1", "sub2", "sub3"]
