"""Tests for WebSocket synchronization observers."""

from typing import Any, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, World, monitored
from relics.addons.websocket import (
    SyncComponentObserver,
    SyncEntityObserver,
    create_entity_observer,
    create_sync_observer,
)
from relics.entity import Entity


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@monitored
@dataclass
class Health(Component):
    """Monitored test component for health."""

    current: int
    maximum: int


@dataclass
class Velocity(Component):
    """Test component for velocity."""

    vx: float
    vy: float


class TestSyncComponentObserver:
    """Tests for SyncComponentObserver class."""

    def test_observer_has_component_type(self) -> None:
        """Test that observer has component_type attribute."""
        observer = create_sync_observer(
            component_type=Position,
            on_change=lambda e, o, n: None,
        )
        assert observer.component_type == Position

    def test_observer_calls_on_change_for_added(self) -> None:
        """Test that on_change is called when component is added."""
        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        def track_change(
            entity: Entity,
            component: Component,
            field_name: str,
            old_value: Any,
            new_value: Any,
        ) -> None:
            changes.append((entity, component, field_name, old_value, new_value))

        observer = create_sync_observer(
            component_type=Position,
            on_change=track_change,
        )

        # Create mock entity
        entity = MagicMock(spec=Entity)
        component = Position(x=10, y=20)

        # Simulate component added
        observer.on_component_added(entity, component)

        assert len(changes) == 1
        assert changes[0][0] == entity
        assert changes[0][1] == component
        assert changes[0][2] == ""  # field_name is empty for additions
        assert changes[0][3] is None  # old value should be None for additions
        assert changes[0][4] == component  # new value is the component

    def test_observer_calls_on_change_for_changed(self) -> None:
        """Test that on_change is called when component changes."""
        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        def track_change(
            entity: Entity,
            component: Component,
            field_name: str,
            old_value: Any,
            new_value: Any,
        ) -> None:
            changes.append((entity, component, field_name, old_value, new_value))

        observer = create_sync_observer(
            component_type=Position,
            on_change=track_change,
        )

        entity = MagicMock(spec=Entity)
        component = Position(x=10, y=20)

        observer.on_component_changed(entity, component, "x", 0, 10)

        assert len(changes) == 1
        assert changes[0][1] == component
        assert changes[0][2] == "x"
        assert changes[0][3] == 0
        assert changes[0][4] == 10

    def test_observer_filter_blocks_changes(self) -> None:
        """Test that filter function can block changes."""
        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        def track_change(
            entity: Entity,
            component: Component,
            field_name: str,
            old_value: Any,
            new_value: Any,
        ) -> None:
            changes.append((entity, component, field_name, old_value, new_value))

        # Filter that blocks Position but allows Health
        def filter_fn(comp_type: type) -> bool:
            return comp_type != Position

        observer = create_sync_observer(
            component_type=Position,
            on_change=track_change,
            filter_fn=filter_fn,
        )

        entity = MagicMock(spec=Entity)
        component = Position(x=10, y=20)

        observer.on_component_added(entity, component)

        assert len(changes) == 0  # Should be blocked

    def test_observer_filter_allows_changes(self) -> None:
        """Test that filter function can allow changes."""
        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        def track_change(
            entity: Entity,
            component: Component,
            field_name: str,
            old_value: Any,
            new_value: Any,
        ) -> None:
            changes.append((entity, component, field_name, old_value, new_value))

        def filter_fn(comp_type: type) -> bool:
            return comp_type == Health

        observer = create_sync_observer(
            component_type=Health,
            on_change=track_change,
            filter_fn=filter_fn,
        )

        entity = MagicMock(spec=Entity)
        component = Health(current=100, maximum=100)

        observer.on_component_added(entity, component)

        assert len(changes) == 1

    def test_observer_on_component_removed_is_noop(self) -> None:
        """Test that on_component_removed doesn't trigger callback."""
        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        def track_change(
            entity: Entity,
            component: Component,
            field_name: str,
            old_value: Any,
            new_value: Any,
        ) -> None:
            changes.append((entity, component, field_name, old_value, new_value))

        observer = create_sync_observer(
            component_type=Position,
            on_change=track_change,
        )

        entity = MagicMock(spec=Entity)
        component = Position(x=10, y=20)

        observer.on_component_removed(entity, component)

        assert len(changes) == 0

    def test_create_sync_observer_creates_unique_class(self) -> None:
        """Test that create_sync_observer creates unique observer classes."""
        observer1 = create_sync_observer(
            component_type=Position,
            on_change=lambda e, o, n: None,
        )
        observer2 = create_sync_observer(
            component_type=Health,
            on_change=lambda e, o, n: None,
        )

        assert type(observer1).__name__ != type(observer2).__name__
        assert observer1.component_type != observer2.component_type


class TestSyncEntityObserver:
    """Tests for SyncEntityObserver class."""

    def test_observer_calls_on_created(self) -> None:
        """Test that on_created callback is called."""
        created: List[Entity] = []

        def track_created(entity: Entity) -> None:
            created.append(entity)

        observer = create_entity_observer(on_created=track_created)

        entity = MagicMock(spec=Entity)
        observer.on_entity_created(entity)

        assert len(created) == 1
        assert created[0] == entity

    def test_observer_calls_on_destroyed(self) -> None:
        """Test that on_destroyed callback is called."""
        destroyed: List[Entity] = []

        def track_destroyed(entity: Entity) -> None:
            destroyed.append(entity)

        observer = create_entity_observer(on_destroyed=track_destroyed)

        entity = MagicMock(spec=Entity)
        observer.on_entity_destroyed(entity)

        assert len(destroyed) == 1
        assert destroyed[0] == entity

    def test_observer_with_no_callbacks(self) -> None:
        """Test observer with no callbacks doesn't raise."""
        observer = create_entity_observer()

        entity = MagicMock(spec=Entity)
        # Should not raise
        observer.on_entity_created(entity)
        observer.on_entity_destroyed(entity)

    def test_observer_with_prefab_filter(self) -> None:
        """Test that observer respects prefab attribute."""
        observer = create_entity_observer(
            on_created=lambda e: None,
            prefab="player",
        )
        assert observer.prefab == "player"

    def test_observer_with_no_prefab(self) -> None:
        """Test observer with no prefab filter."""
        observer = create_entity_observer(on_created=lambda e: None)
        assert observer.prefab is None

    def test_create_entity_observer_creates_unique_class(self) -> None:
        """Test that create_entity_observer creates unique classes."""
        observer1 = create_entity_observer(prefab="player")
        observer2 = create_entity_observer(prefab="enemy")

        assert type(observer1).__name__ != type(observer2).__name__


class TestObserversWithWorld:
    """Integration tests for observers with World."""

    def test_component_observer_with_monitored_component(self) -> None:
        """Test that component observer works with monitored components."""
        changes: List[Tuple[Entity, Component, str, Any, Any]] = []

        def track_change(
            entity: Entity,
            component: Component,
            field_name: str,
            old_value: Any,
            new_value: Any,
        ) -> None:
            changes.append((entity, component, field_name, old_value, new_value))

        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        observer = create_sync_observer(
            component_type=Health,
            on_change=track_change,
        )
        world.observe(observer)

        entity = world.spawn("player")
        world.tick(0)

        # Get the health component and modify it
        health = entity.get_component(Health)
        health.current = 50
        world.tick(0)

        # Should have captured the change
        assert len(changes) >= 1
        # The last change should be the health modification
        last_change = changes[-1]
        assert last_change[2] == "current"  # field_name
        assert last_change[4] == 50  # new_value

    def test_entity_observer_on_spawn(self) -> None:
        """Test that entity observer fires on spawn."""
        created: List[Entity] = []

        def track_created(entity: Entity) -> None:
            created.append(entity)

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        observer = create_entity_observer(on_created=track_created)
        world.observe(observer)

        entity = world.spawn("player")
        world.tick(0)

        assert len(created) == 1
        assert created[0].id == entity.id

    def test_entity_observer_on_remove(self) -> None:
        """Test that entity observer fires on entity removal."""
        destroyed: List[Entity] = []

        def track_destroyed(entity: Entity) -> None:
            destroyed.append(entity)

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        observer = create_entity_observer(on_destroyed=track_destroyed)
        world.observe(observer)

        entity = world.spawn("player")
        world.tick(0)

        world.remove(entity)
        world.tick(0)

        assert len(destroyed) == 1

    def test_multiple_observers_same_component(self) -> None:
        """Test multiple observers for the same component type."""
        changes1: List[Any] = []
        changes2: List[Any] = []

        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        observer1 = create_sync_observer(
            component_type=Health,
            on_change=lambda e, c, f, o, n: changes1.append(n),
        )
        observer2 = create_sync_observer(
            component_type=Health,
            on_change=lambda e, c, f, o, n: changes2.append(n),
        )
        world.observe(observer1)
        world.observe(observer2)

        entity = world.spawn("player")
        world.tick(0)

        health = entity.get_component(Health)
        health.current = 50
        world.tick(0)

        # Both observers should have received changes
        assert len(changes1) >= 1
        assert len(changes2) >= 1
