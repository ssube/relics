"""Observer base classes for reactive event handling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Optional, Type

from relics.types import Component, CustomEvent, Edge

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World


class Observer(ABC):
    """Base class for all observers.

    Observers react to events in the World. By default, events are
    queued and processed at the end of each tick.
    """

    def __init__(self) -> None:
        """Initialize the observer."""
        self._world: "World" | None = None

    @property
    def world(self) -> "World":
        """The World this observer is registered with.

        Raises:
            RuntimeError: If the observer is not registered with a world.
        """
        if self._world is None:
            raise RuntimeError("Observer is not registered with a world")
        return self._world

    @world.setter
    def world(self, value: "World") -> None:
        """Set the World this observer is registered with."""
        self._world = value


class OnComponentAdded(Observer):
    """Triggered when a component is added to an entity.

    Subclasses must set component_type and implement on_component_added().
    """

    component_type: ClassVar[Type[Component]]

    @abstractmethod
    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        pass


class OnComponentRemoved(Observer):
    """Triggered when a component is removed from an entity.

    Subclasses must set component_type and implement on_component_removed().
    """

    component_type: ClassVar[Type[Component]]

    @abstractmethod
    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        pass


class OnComponentChanged(Observer):
    """Triggered when a @monitored component changes.

    Requires the component class to have the @monitored decorator.
    Subclasses must set component_type and implement on_component_changed().
    """

    component_type: ClassVar[Type[Component]]

    @abstractmethod
    def on_component_changed(
        self,
        entity: "Entity",
        old_value: Component,
        new_value: Component,
    ) -> None:
        """Handle component value change.

        Args:
            entity: The entity whose component changed.
            old_value: The previous component value.
            new_value: The new component value.
        """
        pass


class OnEntityCreated(Observer):
    """Triggered when an entity is spawned.

    Set prefab to filter for specific prefabs, or None for all prefabs.
    Subclasses must implement on_entity_created().
    """

    prefab: ClassVar[Optional[str]] = None

    @abstractmethod
    def on_entity_created(self, entity: "Entity") -> None:
        """Handle entity creation.

        Args:
            entity: The entity that was created.
        """
        pass


class OnEntityDestroyed(Observer):
    """Triggered when an entity is removed.

    Set prefab to filter for specific prefabs, or None for all prefabs.
    Subclasses must implement on_entity_destroyed().
    """

    prefab: ClassVar[Optional[str]] = None

    @abstractmethod
    def on_entity_destroyed(self, entity: "Entity") -> None:
        """Handle entity destruction.

        Args:
            entity: The entity that was destroyed.
        """
        pass


class OnRelationshipAdded(Observer):
    """Triggered when a relationship is added between entities.

    Subclasses must set edge_type and implement on_relationship_added().
    """

    edge_type: ClassVar[Type[Edge]]

    @abstractmethod
    def on_relationship_added(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle relationship addition.

        Args:
            source: The source entity of the relationship.
            edge: The edge instance that was added.
            target: The target entity of the relationship.
        """
        pass


class OnRelationshipRemoved(Observer):
    """Triggered when a relationship is removed between entities.

    Subclasses must set edge_type and implement on_relationship_removed().
    """

    edge_type: ClassVar[Type[Edge]]

    @abstractmethod
    def on_relationship_removed(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle relationship removal.

        Args:
            source: The source entity of the relationship.
            edge: The edge instance that was removed.
            target: The target entity of the relationship.
        """
        pass


class OnCustomEvent(Observer):
    """Triggered when a custom event is emitted.

    Subclasses must set event_type and implement on_event().
    """

    event_type: ClassVar[Type[CustomEvent]]

    @abstractmethod
    def on_event(self, event: CustomEvent) -> None:
        """Handle custom event.

        Args:
            event: The custom event that was emitted.
        """
        pass


# Multi-event observers for lifecycle tracking


class ComponentObserver(Observer):
    """Observer for component lifecycle events (added, changed, removed).

    Subclasses must set component_type and can override any of the
    lifecycle methods they're interested in.
    """

    component_type: ClassVar[Type[Component]]

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition. Override to implement.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        pass

    def on_component_changed(
        self,
        entity: "Entity",
        old_value: Component,
        new_value: Component,
    ) -> None:
        """Handle component value change. Override to implement.

        Args:
            entity: The entity whose component changed.
            old_value: The previous component value.
            new_value: The new component value.
        """
        pass

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal. Override to implement.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        pass


class RelationshipObserver(Observer):
    """Observer for relationship lifecycle events (added, removed).

    Subclasses must set edge_type and can override any of the
    lifecycle methods they're interested in.
    """

    edge_type: ClassVar[Type[Edge]]

    def on_relationship_added(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle relationship addition. Override to implement.

        Args:
            source: The source entity of the relationship.
            edge: The edge instance that was added.
            target: The target entity of the relationship.
        """
        pass

    def on_relationship_removed(
        self, source: "Entity", edge: Edge, target: "Entity"
    ) -> None:
        """Handle relationship removal. Override to implement.

        Args:
            source: The source entity of the relationship.
            edge: The edge instance that was removed.
            target: The target entity of the relationship.
        """
        pass


class EntityObserver(Observer):
    """Observer for entity lifecycle events (created, destroyed).

    Set prefab to filter for specific prefabs, or None for all prefabs.
    Can override any of the lifecycle methods.
    """

    prefab: ClassVar[Optional[str]] = None

    def on_entity_created(self, entity: "Entity") -> None:
        """Handle entity creation. Override to implement.

        Args:
            entity: The entity that was created.
        """
        pass

    def on_entity_destroyed(self, entity: "Entity") -> None:
        """Handle entity destruction. Override to implement.

        Args:
            entity: The entity that was destroyed.
        """
        pass
