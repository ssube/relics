"""Entity handle for live access to entity state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type, TypeVar

from relics.errors import (
    ComponentNotFoundError,
    DuplicateComponentError,
    EntityNotFoundError,
)
from relics.types import Component, EntityId

if TYPE_CHECKING:
    from relics.world import World

T = TypeVar("T", bound=Component)


class Entity:
    """Live handle to an entity. Always reflects current world state.

    Entity handles use lazy validation: they check that the entity exists
    in the world when accessing components or relationships, not at
    handle creation time.

    Attributes:
        _world: Reference to the World containing this entity.
        _id: The entity's unique identifier.
    """

    __slots__ = ("_world", "_id")

    def __init__(self, world: "World", entity_id: EntityId) -> None:
        """Create an entity handle.

        Args:
            world: The World containing this entity.
            entity_id: The entity's unique identifier.
        """
        self._world = world
        self._id = entity_id

    def _validate_exists(self) -> None:
        """Check that the entity still exists in the world.

        Raises:
            EntityNotFoundError: If the entity no longer exists.
        """
        if not self._world.has_entity(self._id):
            raise EntityNotFoundError(f"Entity {self._id} not found in world")

    @property
    def id(self) -> EntityId:
        """The entity's unique identifier."""
        return self._id

    @property
    def prefab(self) -> str:
        """The prefab this entity was instantiated from."""
        return self._id.prefab

    def get_component(self, component_type: Type[T]) -> T:
        """Get component of the specified type.

        Args:
            component_type: The type of component to retrieve.

        Returns:
            The component instance.

        Raises:
            EntityNotFoundError: If the entity no longer exists.
            ComponentNotFoundError: If the entity doesn't have this component.
        """
        self._validate_exists()
        components = self._world._entities[self._id]
        if component_type not in components:
            raise ComponentNotFoundError(
                f"Entity {self._id} does not have component {component_type.__name__}"
            )
        return components[component_type]  # type: ignore[return-value]

    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if entity has a component of the specified type.

        Args:
            component_type: The type of component to check for.

        Returns:
            True if the entity has the component, False otherwise.

        Raises:
            EntityNotFoundError: If the entity no longer exists.
        """
        self._validate_exists()
        return component_type in self._world._entities[self._id]

    def add_component(self, component: Component) -> None:
        """Add a component to the entity.

        Args:
            component: The component instance to add.

        Raises:
            EntityNotFoundError: If the entity no longer exists.
            DuplicateComponentError: If the entity already has this component type.
        """
        self._validate_exists()
        component_type = type(component)
        if component_type in self._world._entities[self._id]:
            raise DuplicateComponentError(
                f"Entity {self._id} already has component {component_type.__name__}"
            )
        self._world._add_component(self._id, component)

    def remove_component(self, component_type: Type[Component]) -> None:
        """Remove a component from the entity.

        Args:
            component_type: The type of component to remove.

        Raises:
            EntityNotFoundError: If the entity no longer exists.
            ComponentNotFoundError: If the entity doesn't have this component.
        """
        self._validate_exists()
        if component_type not in self._world._entities[self._id]:
            raise ComponentNotFoundError(
                f"Entity {self._id} does not have component {component_type.__name__}"
            )
        self._world._remove_component(self._id, component_type)

    def __eq__(self, other: object) -> bool:
        """Check equality based on entity ID."""
        if not isinstance(other, Entity):
            return NotImplemented
        return self._id == other._id and self._world is other._world

    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self._id)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Entity({self._id})"
