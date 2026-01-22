"""Entity handle for live access to entity state."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple, Type, TypeVar

from relics.errors import (
    ComponentNotFoundError,
    DuplicateComponentError,
    EntityNotFoundError,
)
from relics.types import Component, Edge, EntityId

if TYPE_CHECKING:
    from relics.world import World

T = TypeVar("T", bound=Component)
E = TypeVar("E", bound=Edge)


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

    def add_relationship(self, edge: Edge, target: "EntityId") -> None:
        """Add a relationship from this entity to another.

        Args:
            edge: The edge instance defining the relationship.
            target: The target entity ID.

        Raises:
            EntityNotFoundError: If this entity or target doesn't exist.
            RelationshipValidationError: If edge validation fails.
        """
        self._validate_exists()
        self._world._add_relationship(self._id, edge, target)

    def remove_relationship(
        self, edge_type: Type[Edge], target: "EntityId"
    ) -> None:
        """Remove a relationship from this entity to another.

        Args:
            edge_type: The type of edge to remove.
            target: The target entity ID.

        Raises:
            EntityNotFoundError: If this entity doesn't exist.
        """
        self._validate_exists()
        self._world._remove_relationship(self._id, edge_type, target)

    def get_relationships(
        self, edge_type: Type[E]
    ) -> List[Tuple[E, "EntityId"]]:
        """Get all outgoing relationships of the specified type.

        Args:
            edge_type: The type of edge to get.

        Returns:
            List of (edge, target_id) tuples.

        Raises:
            EntityNotFoundError: If this entity doesn't exist.
        """
        self._validate_exists()
        return self._world._get_relationships(self._id, edge_type)  # type: ignore

    def get_incoming_relationships(
        self, edge_type: Type[E]
    ) -> List[Tuple["EntityId", E]]:
        """Get all incoming relationships of the specified type.

        Args:
            edge_type: The type of edge to get.

        Returns:
            List of (source_id, edge) tuples.

        Raises:
            EntityNotFoundError: If this entity doesn't exist.
        """
        self._validate_exists()
        return self._world._get_incoming_relationships(  # type: ignore
            self._id, edge_type
        )

    def has_relationship(
        self, edge_type: Type[Edge], target: "EntityId | None" = None
    ) -> bool:
        """Check if this entity has an outgoing relationship.

        Args:
            edge_type: The type of edge to check.
            target: Optional specific target to check for.

        Returns:
            True if the relationship exists.

        Raises:
            EntityNotFoundError: If this entity doesn't exist.
        """
        self._validate_exists()
        return self._world._has_relationship(self._id, edge_type, target)

    def has_incoming_relationship(
        self, edge_type: Type[Edge], source: "EntityId | None" = None
    ) -> bool:
        """Check if this entity has an incoming relationship.

        Args:
            edge_type: The type of edge to check.
            source: Optional specific source to check for.

        Returns:
            True if the relationship exists.

        Raises:
            EntityNotFoundError: If this entity doesn't exist.
        """
        self._validate_exists()
        return self._world._has_incoming_relationship(self._id, edge_type, source)

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
