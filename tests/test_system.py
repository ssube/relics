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
