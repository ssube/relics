"""Observers for WebSocket synchronization.

These observers detect changes in the world and trigger sync callbacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional, Type

from relics.observer import ComponentObserver, EntityObserver
from relics.types import Component

if TYPE_CHECKING:
    from relics.entity import Entity


# Type alias for change handlers
# Callback receives: entity, component, field_name, old_value, new_value
OnChangeCallback = Callable[["Entity", Component, str, Any, Any], None]
OnEntityCallback = Callable[["Entity"], None]


class SyncComponentObserver(ComponentObserver):
    """Observer that triggers callbacks on component changes.

    Used by both client and server to detect and synchronize component changes.

    Attributes:
        component_type: Set dynamically to match the observed component.
    """

    component_type: ClassVar[Type[Component]]

    def __init__(
        self,
        on_change: OnChangeCallback,
        filter_fn: Optional[Callable[[Type[Component]], bool]] = None,
    ) -> None:
        """Create a sync component observer.

        Args:
            on_change: Callback for component changes.
                Signature: (entity, component, field_name, old_value, new_value) -> None
            filter_fn: Optional filter function to skip certain changes.
                If returns False, the change is not synchronized.
        """
        super().__init__()
        self._on_change = on_change
        self._filter_fn = filter_fn

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        if self._filter_fn and not self._filter_fn(type(component)):
            return
        # For additions, pass empty field_name and None for old_value
        self._on_change(entity, component, "", None, component)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle component change.

        Args:
            entity: The entity whose component changed.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: The previous value of the field.
            new_value: The new value of the field.
        """
        if self._filter_fn and not self._filter_fn(type(component)):
            return
        self._on_change(entity, component, field_name, old_value, new_value)

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal.

        Component removals are not synchronized via this observer as they
        imply entity state changes that should be handled differently.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        # Component removals are typically handled at the entity level
        pass


def create_sync_observer(
    component_type: Type[Component],
    on_change: OnChangeCallback,
    filter_fn: Optional[Callable[[Type[Component]], bool]] = None,
) -> SyncComponentObserver:
    """Create a sync observer for a specific component type.

    Creates a new observer class with the component_type set dynamically,
    then instantiates it with the given callback.

    Args:
        component_type: The component type to watch.
        on_change: Callback for component changes.
        filter_fn: Optional filter function.

    Returns:
        A configured SyncComponentObserver instance.
    """
    observer_class = type(
        f"SyncObserver_{component_type.__name__}",
        (SyncComponentObserver,),
        {"component_type": component_type},
    )
    return observer_class(on_change=on_change, filter_fn=filter_fn)


class SyncEntityObserver(EntityObserver):
    """Observer that triggers callbacks on entity lifecycle events.

    Used by server to broadcast entity creation/destruction to clients.

    Attributes:
        prefab: Set to None to observe all prefabs.
    """

    prefab: ClassVar[Optional[str]] = None

    def __init__(
        self,
        on_created: Optional[OnEntityCallback] = None,
        on_destroyed: Optional[OnEntityCallback] = None,
    ) -> None:
        """Create a sync entity observer.

        Args:
            on_created: Callback for entity creation.
            on_destroyed: Callback for entity destruction.
        """
        super().__init__()
        self._on_created = on_created
        self._on_destroyed = on_destroyed

    def on_entity_created(self, entity: "Entity") -> None:
        """Handle entity creation.

        Args:
            entity: The entity that was created.
        """
        if self._on_created:
            self._on_created(entity)

    def on_entity_destroyed(self, entity: "Entity") -> None:
        """Handle entity destruction.

        Args:
            entity: The entity that was destroyed.
        """
        if self._on_destroyed:
            self._on_destroyed(entity)


def create_entity_observer(
    on_created: Optional[OnEntityCallback] = None,
    on_destroyed: Optional[OnEntityCallback] = None,
    prefab: Optional[str] = None,
) -> SyncEntityObserver:
    """Create an entity observer with optional prefab filtering.

    Args:
        on_created: Callback for entity creation.
        on_destroyed: Callback for entity destruction.
        prefab: Optional prefab name to filter. None means all prefabs.

    Returns:
        A configured SyncEntityObserver instance.
    """
    observer_class = type(
        f"SyncEntityObserver_{prefab or 'all'}",
        (SyncEntityObserver,),
        {"prefab": prefab},
    )
    return observer_class(on_created=on_created, on_destroyed=on_destroyed)
