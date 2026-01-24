"""Tests for @shared_component and @temporary_component decorators."""

from dataclasses import dataclass

import pytest

from relics import (
    Component,
    World,
    copy_component,
    is_shared,
    is_temporary,
    monitored,
    monitored_component,
    shared_component,
    temporary_component,
)
from relics.persistence import InMemoryPersistenceDriver


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


@temporary_component
@dataclass
class TemporaryState(Component):
    """A temporary component for testing."""

    session_id: str
    last_input: str


@temporary_component
@shared_component
@dataclass
class TemporarySharedCache(Component):
    """A temporary and shared component for testing."""

    cache_key: str
    cache_data: list


@temporary_component
@monitored_component
class TemporaryMonitoredInput(Component):
    """A temporary and monitored component for testing."""

    keys_pressed: list
    mouse_x: int
    mouse_y: int


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


class TestIsTemporary:
    """Tests for is_temporary function."""

    def test_is_temporary_true_on_decorated_class(self) -> None:
        """Test that is_temporary returns True for @temporary_component classes."""
        assert is_temporary(TemporaryState) is True

    def test_is_temporary_true_on_decorated_instance(self) -> None:
        """Test that is_temporary returns True for @temporary_component instances."""
        instance = TemporaryState(session_id="abc", last_input="enter")
        assert is_temporary(instance) is True

    def test_is_temporary_false_on_regular_class(self) -> None:
        """Test that is_temporary returns False for regular component classes."""
        assert is_temporary(RegularComponent) is False

    def test_is_temporary_false_on_shared_class(self) -> None:
        """Test that is_temporary returns False for @shared_component classes."""
        assert is_temporary(SharedData) is False

    def test_is_temporary_false_on_monitored_class(self) -> None:
        """Test that is_temporary returns False for @monitored classes."""
        assert is_temporary(MonitoredHealth) is False


class TestTemporaryWithOtherDecorators:
    """Tests for combining @temporary_component with other decorators."""

    def test_temporary_with_shared(self) -> None:
        """Test that @temporary_component can be combined with @shared_component."""
        assert is_temporary(TemporarySharedCache) is True
        assert is_shared(TemporarySharedCache) is True

    def test_temporary_with_monitored(self) -> None:
        """Test that @temporary_component can be combined with @monitored."""
        assert is_temporary(TemporaryMonitoredInput) is True
        # Monitored components still work
        instance = TemporaryMonitoredInput(keys_pressed=[], mouse_x=0, mouse_y=0)
        assert hasattr(instance, "_is_monitored")

    def test_temporary_shared_spawn_behavior(self) -> None:
        """Test that temporary+shared components share instances on spawn."""
        world = World()
        world.register_prefab(
            "test",
            {TemporarySharedCache: TemporarySharedCache(cache_key="k", cache_data=[])},
        )

        entity1 = world.spawn("test")
        entity2 = world.spawn("test")

        comp1 = entity1.get_component(TemporarySharedCache)
        comp2 = entity2.get_component(TemporarySharedCache)

        # Should be same instance (shared behavior)
        assert comp1 is comp2


class TestTemporaryPersistence:
    """Tests for @temporary_component persistence behavior."""

    def test_temporary_components_not_saved(self) -> None:
        """Test that temporary components are not persisted."""
        world = World()
        world.register_prefab(
            "test",
            {
                RegularComponent: RegularComponent(value=42, items=[1, 2]),
                TemporaryState: TemporaryState(session_id="abc", last_input="x"),
            },
        )

        entity = world.spawn("test")
        world.tick(0)

        # Verify entity has both components
        assert entity.has_component(RegularComponent)
        assert entity.has_component(TemporaryState)

        # Save and load
        driver = InMemoryPersistenceDriver()
        driver.save(world, "test_save")

        # Create new world and load
        world2 = World()
        world2.register_component_type(RegularComponent)
        world2.register_component_type(TemporaryState)
        driver.load(
            world2,
            "test_save",
            component_registry={
                "RegularComponent": RegularComponent,
                "TemporaryState": TemporaryState,
            },
        )

        # Get the loaded entity
        loaded_entity = world2.get_entity(entity.id)

        # Regular component should be restored
        assert loaded_entity.has_component(RegularComponent)
        regular = loaded_entity.get_component(RegularComponent)
        assert regular.value == 42
        assert regular.items == [1, 2]

        # Temporary component should NOT be restored
        assert not loaded_entity.has_component(TemporaryState)

    def test_temporary_prefab_components_not_saved(self) -> None:
        """Test that temporary components in prefabs are not persisted."""
        from relics.prefab import prefab_to_dict

        components = {
            RegularComponent: RegularComponent(value=1, items=[]),
            TemporaryState: TemporaryState(session_id="s", last_input=""),
        }

        result = prefab_to_dict("test", components)

        # Only regular component should be in the output
        assert "RegularComponent" in result["components"]
        assert "TemporaryState" not in result["components"]

    def test_save_load_with_mixed_components(self) -> None:
        """Test save/load with regular, shared, monitored, and temporary components."""
        world = World()
        world.register_prefab(
            "mixed",
            {
                RegularComponent: RegularComponent(value=1, items=["a"]),
                SharedData: SharedData(data="shared", values=[1]),
                MonitoredHealth: MonitoredHealth(current=50, maximum=100),
                TemporaryState: TemporaryState(session_id="sess", last_input="key"),
            },
        )

        entity = world.spawn("mixed")
        world.tick(0)

        # Save
        driver = InMemoryPersistenceDriver()
        driver.save(world, "mixed_save")

        # Load into new world
        world2 = World()
        driver.load(
            world2,
            "mixed_save",
            component_registry={
                "RegularComponent": RegularComponent,
                "SharedData": SharedData,
                "MonitoredHealth": MonitoredHealth,
                "TemporaryState": TemporaryState,
            },
        )

        loaded = world2.get_entity(entity.id)

        # Regular, shared, and monitored should be restored
        assert loaded.has_component(RegularComponent)
        assert loaded.has_component(SharedData)
        assert loaded.has_component(MonitoredHealth)

        # Temporary should NOT be restored
        assert not loaded.has_component(TemporaryState)

        # Verify values
        assert loaded.get_component(RegularComponent).value == 1
        assert loaded.get_component(SharedData).data == "shared"
        assert loaded.get_component(MonitoredHealth).current == 50
