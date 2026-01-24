"""Tests for @shared_component decorator and component copying behavior."""

from dataclasses import dataclass

import pytest

from relics import (
    Component,
    World,
    copy_component,
    is_shared,
    monitored,
    monitored_component,
    shared_component,
)


@dataclass
class RegularComponent(Component):
    """A regular component for testing."""

    value: int
    items: list


@shared_component
@dataclass
class SharedData(Component):
    """A shared component for testing."""

    data: str
    values: list


@monitored_component
class MonitoredHealth(Component):
    """A monitored component for testing."""

    current: int
    maximum: int


class TestIsShared:
    """Tests for is_shared function."""

    def test_is_shared_true_on_decorated_class(self) -> None:
        """Test that is_shared returns True for @shared_component classes."""
        assert is_shared(SharedData) is True

    def test_is_shared_true_on_decorated_instance(self) -> None:
        """Test that is_shared returns True for @shared_component instances."""
        instance = SharedData(data="test", values=[1, 2, 3])
        assert is_shared(instance) is True

    def test_is_shared_false_on_regular_class(self) -> None:
        """Test that is_shared returns False for regular component classes."""
        assert is_shared(RegularComponent) is False

    def test_is_shared_false_on_regular_instance(self) -> None:
        """Test that is_shared returns False for regular component instances."""
        instance = RegularComponent(value=42, items=[1, 2, 3])
        assert is_shared(instance) is False

    def test_is_shared_false_on_monitored_class(self) -> None:
        """Test that is_shared returns False for @monitored classes."""
        assert is_shared(MonitoredHealth) is False


class TestMutualExclusion:
    """Tests for mutual exclusion of @shared_component and @monitored."""

    def test_shared_then_monitored_raises(self) -> None:
        """Test that applying @monitored to a @shared_component raises."""
        with pytest.raises(ValueError, match="mutually exclusive"):

            @monitored
            @shared_component
            @dataclass
            class InvalidComponent(Component):
                value: int

    def test_shared_then_monitored_component_raises(self) -> None:
        """Test that applying @monitored_component to a @shared_component raises."""
        with pytest.raises(ValueError, match="mutually exclusive"):

            @monitored_component
            @shared_component
            class InvalidComponent(Component):
                value: int

    def test_monitored_then_shared_raises(self) -> None:
        """Test that applying @shared_component to a @monitored class raises."""
        with pytest.raises(ValueError, match="mutually exclusive"):

            @shared_component
            @monitored
            @dataclass
            class InvalidComponent(Component):
                value: int


class TestCopyComponent:
    """Tests for copy_component function."""

    def test_regular_component_deep_copied(self) -> None:
        """Test that regular components are deep copied."""
        original = RegularComponent(value=42, items=[1, 2, 3])
        copied = copy_component(original)

        # Should be different instances
        assert copied is not original

        # Values should match
        assert copied.value == 42
        assert copied.items == [1, 2, 3]

        # Nested list should be a different instance (deep copy)
        assert copied.items is not original.items

    def test_shared_component_same_instance(self) -> None:
        """Test that @shared_component returns the same instance."""
        original = SharedData(data="test", values=[1, 2, 3])
        copied = copy_component(original)

        # Should be the exact same instance
        assert copied is original

    def test_monitored_component_deep_copied(self) -> None:
        """Test that @monitored components are deep copied."""
        original = MonitoredHealth(current=80, maximum=100)
        copied = copy_component(original)

        # Should be different instances
        assert copied is not original

        # Values should match
        assert copied.current == 80
        assert copied.maximum == 100


class TestSpawnBehavior:
    """Tests for component copying during entity spawn."""

    def test_regular_components_are_deep_copied_on_spawn(self) -> None:
        """Test that regular prefab components are deep copied when spawning."""
        world = World()
        prefab_items = [1, 2, 3]
        world.register_prefab(
            "test",
            {RegularComponent: RegularComponent(value=42, items=prefab_items)},
        )

        entity1 = world.spawn("test")
        entity2 = world.spawn("test")

        comp1 = entity1.get_component(RegularComponent)
        comp2 = entity2.get_component(RegularComponent)

        # Components should be different instances
        assert comp1 is not comp2

        # Nested lists should be different instances
        assert comp1.items is not comp2.items
        assert comp1.items is not prefab_items
        assert comp2.items is not prefab_items

        # Mutating one should not affect the other
        comp1.items.append(4)
        assert comp1.items == [1, 2, 3, 4]
        assert comp2.items == [1, 2, 3]
        assert prefab_items == [1, 2, 3]

    def test_shared_components_are_same_instance_on_spawn(self) -> None:
        """Test that @shared_component prefab components share instances."""
        world = World()
        world.register_prefab(
            "test",
            {SharedData: SharedData(data="shared", values=[1, 2, 3])},
        )

        entity1 = world.spawn("test")
        entity2 = world.spawn("test")

        comp1 = entity1.get_component(SharedData)
        comp2 = entity2.get_component(SharedData)

        # Components should be the same instance
        assert comp1 is comp2

        # Mutating through one affects both
        comp1.values.append(4)
        assert comp2.values == [1, 2, 3, 4]

    def test_override_components_not_copied(self) -> None:
        """Test that override components are used as-is."""
        world = World()
        world.register_prefab(
            "test",
            {RegularComponent: RegularComponent(value=42, items=[1, 2, 3])},
        )

        override_comp = RegularComponent(value=100, items=[4, 5, 6])
        entity = world.spawn("test", {RegularComponent: override_comp})

        comp = entity.get_component(RegularComponent)

        # Override should be used directly
        assert comp is override_comp
        assert comp.value == 100
        assert comp.items == [4, 5, 6]

    def test_monitored_components_still_work(self) -> None:
        """Test backward compatibility with @monitored components."""
        from relics.observer import OnComponentChanged

        world = World()
        world.register_prefab(
            "test",
            {MonitoredHealth: MonitoredHealth(current=100, maximum=100)},
        )

        entity1 = world.spawn("test")
        entity2 = world.spawn("test")

        comp1 = entity1.get_component(MonitoredHealth)
        comp2 = entity2.get_component(MonitoredHealth)

        # Components should be different instances
        assert comp1 is not comp2

        # Change tracking should work
        changes: list = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = MonitoredHealth

            def on_component_changed(
                self, entity, component, field_name, old_value, new_value
            ):
                changes.append((field_name, old_value, new_value))

        observer = HealthChangeObserver()
        world.observe(observer)

        # Modify component
        comp1.current = 80
        world.tick(0)

        # Change should be tracked
        assert len(changes) == 1
        assert changes[0] == ("current", 100, 80)


class TestMixedPrefabs:
    """Tests for prefabs with mixed component types."""

    def test_prefab_with_shared_and_regular_components(self) -> None:
        """Test prefabs with both shared and regular components."""
        world = World()
        shared_data = SharedData(data="shared", values=[1, 2])
        regular_data = RegularComponent(value=42, items=[3, 4])

        world.register_prefab(
            "mixed",
            {
                SharedData: shared_data,
                RegularComponent: regular_data,
            },
        )

        entity1 = world.spawn("mixed")
        entity2 = world.spawn("mixed")

        # Shared components should be same instance
        shared1 = entity1.get_component(SharedData)
        shared2 = entity2.get_component(SharedData)
        assert shared1 is shared2
        assert shared1 is shared_data

        # Regular components should be different instances
        regular1 = entity1.get_component(RegularComponent)
        regular2 = entity2.get_component(RegularComponent)
        assert regular1 is not regular2
        assert regular1 is not regular_data

    def test_prefab_with_monitored_and_regular_components(self) -> None:
        """Test prefabs with both monitored and regular components."""
        world = World()
        monitored_data = MonitoredHealth(current=100, maximum=100)
        regular_data = RegularComponent(value=42, items=[1, 2])

        world.register_prefab(
            "mixed",
            {
                MonitoredHealth: monitored_data,
                RegularComponent: regular_data,
            },
        )

        entity1 = world.spawn("mixed")
        entity2 = world.spawn("mixed")

        # Both should be different instances (deep copied)
        mon1 = entity1.get_component(MonitoredHealth)
        mon2 = entity2.get_component(MonitoredHealth)
        assert mon1 is not mon2

        reg1 = entity1.get_component(RegularComponent)
        reg2 = entity2.get_component(RegularComponent)
        assert reg1 is not reg2
