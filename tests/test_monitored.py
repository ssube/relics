"""Tests for relics.monitored module."""

from dataclasses import dataclass
from typing import Any, List, Tuple

from relics import Component, Entity, OnComponentChanged, World, is_monitored, monitored


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@monitored
@dataclass
class Health(Component):
    """Monitored component for health."""

    current: int
    maximum: int


class TestMonitoredDecorator:
    """Tests for @monitored decorator."""

    def test_is_monitored_true(self) -> None:
        """Test is_monitored returns True for decorated class."""
        assert is_monitored(Health) is True

    def test_is_monitored_false(self) -> None:
        """Test is_monitored returns False for non-decorated class."""
        assert is_monitored(Position) is False

    def test_is_monitored_instance(self) -> None:
        """Test is_monitored works on instances."""
        health = Health(current=100, maximum=100)
        assert is_monitored(health) is True

        pos = Position(x=0, y=0)
        assert is_monitored(pos) is False

    def test_monitored_class_still_works(self) -> None:
        """Test that monitored class can still be instantiated and used."""
        health = Health(current=100, maximum=100)
        assert health.current == 100
        assert health.maximum == 100

        # Can still modify values
        health.current = 80
        assert health.current == 80


class TestComponentChangeTracking:
    """Tests for change tracking with @monitored decorator."""

    def test_change_triggers_observer(self) -> None:
        """Test that changing a monitored component triggers observer."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )

        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = Health

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                changes.append((entity, component, field_name, old_value, new_value))

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(Health)

        # Bind the component to the world for tracking
        health._bind_to_world(world, entity.id)

        # Change the value
        health.current = 80
        world.tick(0.016)

        assert len(changes) == 1
        entity_changed, component, field_name, old_val, new_val = changes[0]
        assert entity_changed.id == entity.id
        assert field_name == "current"
        assert old_val == 100  # Old value
        assert new_val == 80  # New value
        assert component.current == 80  # Component has the new value

    def test_unbound_component_no_notification(self) -> None:
        """Test that unbound component doesn't trigger notifications."""
        # Create component without binding to world
        health = Health(current=100, maximum=100)
        health.current = 80  # Should not cause any issues
        assert health.current == 80

    def test_multiple_changes(self) -> None:
        """Test multiple sequential changes."""
        world = World()
        world.register_prefab(
            "player",
            {Health: Health(current=100, maximum=100)},
        )

        changes: List[int] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = Health

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                changes.append(new_value)

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(Health)
        health._bind_to_world(world, entity.id)

        health.current = 80
        health.current = 60
        health.current = 40
        world.tick(0.016)

        assert len(changes) == 3
        assert changes == [80, 60, 40]

    def test_bind_unbind(self) -> None:
        """Test binding and unbinding from world."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        changes: List[int] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = Health

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                changes.append(new_value)

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(Health)
        health._bind_to_world(world, entity.id)

        health.current = 80
        world.tick(0.016)

        # Unbind
        health._unbind_from_world()
        health.current = 60
        world.tick(0.016)

        # Should only have one change (the first one)
        assert len(changes) == 1


class TestMonitoredEdgeCases:
    """Tests for edge cases in @monitored decorator."""

    def test_monitored_non_dataclass(self) -> None:
        """Test @monitored on a non-dataclass class."""
        # This tests the TypeError exception path when fields() fails

        @monitored
        class PlainClass(Component):
            def __init__(self, value: int):
                self.value = value
                self._internal = "private"

        # Should still work
        obj = PlainClass(42)
        assert obj.value == 42

        # Setting internal attribute should use early return path
        obj._internal = "new_private"
        assert obj._internal == "new_private"

    def test_monitored_setattr_internal_attributes(self) -> None:
        """Test that internal attributes bypass change tracking."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        changes: List[int] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = Health

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                changes.append(new_value)

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(Health)
        health._bind_to_world(world, entity.id)

        # Setting _monitored_* attributes should not trigger notifications
        health._monitored_world = world
        health._monitored_entity_id = entity.id
        world.tick(0.016)

        # No changes should have been recorded from internal attr changes
        assert len(changes) == 0

        # Setting a regular field should trigger notification
        health.current = 80
        world.tick(0.016)
        assert len(changes) == 1

    def test_monitored_setattr_dunder_attributes(self) -> None:
        """Test that dunder attributes bypass change tracking."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        changes: List[int] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = Health

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                changes.append(new_value)

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(Health)
        health._bind_to_world(world, entity.id)

        # Setting __dict__ directly should not trigger notifications
        object.__setattr__(health, "__custom", "test")
        world.tick(0.016)

        # No changes should have been recorded
        assert len(changes) == 0

    def test_monitored_non_field_attribute(self) -> None:
        """Test setting a non-field attribute on a monitored dataclass."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        changes: List[int] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = Health

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                changes.append(new_value)

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(Health)
        health._bind_to_world(world, entity.id)

        # Setting a non-field attribute should not trigger notification
        # since field_names is populated and "extra" is not in it
        health.extra = "extra_value"  # type: ignore
        world.tick(0.016)

        # No change notification for non-field attribute
        assert len(changes) == 0
