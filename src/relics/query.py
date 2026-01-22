"""Query builder for entity queries."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
)

from relics.entity import Entity
from relics.types import Component, Edge, EntityId

if TYPE_CHECKING:
    from relics.world import World


class QueryBuilder:
    """Builder pattern for constructing entity queries.

    Supports component selectors (with_all, with_any, with_none),
    predicate filters, and multiple execution modes.
    """

    def __init__(self, world: "World") -> None:
        """Create a new query builder.

        Args:
            world: The World to query.
        """
        self._world = world
        self._with_all: List[Type[Component]] = []
        self._with_any: List[Type[Component]] = []
        self._with_none: List[Type[Component]] = []
        self._filters: List[Callable[[Entity], bool]] = []
        self._iterate_types: Optional[List[Type[Component]]] = None
        # Relationship criteria
        self._with_relationships: List[Tuple[Type[Edge], Optional[EntityId]]] = []
        self._with_incoming: List[Tuple[Type[Edge], Optional[EntityId]]] = []

    def with_all(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Entities must have ALL of these components.

        Args:
            component_types: List of component types to require.

        Returns:
            Self for method chaining.
        """
        self._with_all.extend(component_types)
        return self

    def with_any(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Entities must have AT LEAST ONE of these components.

        Args:
            component_types: List of component types (at least one required).

        Returns:
            Self for method chaining.
        """
        self._with_any.extend(component_types)
        return self

    def with_none(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Entities must have NONE of these components.

        Args:
            component_types: List of component types to exclude.

        Returns:
            Self for method chaining.
        """
        self._with_none.extend(component_types)
        return self

    def with_filter(self, predicate: Callable[[Entity], bool]) -> "QueryBuilder":
        """Entities must pass this predicate function.

        Args:
            predicate: Function that returns True for matching entities.

        Returns:
            Self for method chaining.
        """
        self._filters.append(predicate)
        return self

    def iterate(self, component_types: List[Type[Component]]) -> "QueryBuilder":
        """Prepare component arrays for batch processing.

        Marks which components to return in execute_components().

        Args:
            component_types: List of component types to return.

        Returns:
            Self for method chaining.
        """
        self._iterate_types = component_types
        return self

    def with_relationship(
        self, edge_type: Type[Edge], target: Optional[EntityId] = None
    ) -> "QueryBuilder":
        """Entities must have an outgoing relationship of this type.

        Args:
            edge_type: The type of edge to require.
            target: Optional specific target entity to require.

        Returns:
            Self for method chaining.
        """
        self._with_relationships.append((edge_type, target))
        return self

    def with_incoming(
        self, edge_type: Type[Edge], source: Optional[EntityId] = None
    ) -> "QueryBuilder":
        """Entities must have an incoming relationship of this type.

        Args:
            edge_type: The type of edge to require.
            source: Optional specific source entity to require.

        Returns:
            Self for method chaining.
        """
        self._with_incoming.append((edge_type, source))
        return self

    def _matches(
        self,
        entity_id: EntityId,
        components: dict[Type[Component], Component],
    ) -> bool:
        """Check if an entity matches all query criteria.

        Args:
            entity_id: The entity's ID.
            components: The entity's component dictionary.

        Returns:
            True if the entity matches all criteria.
        """
        # Check with_all
        for comp_type in self._with_all:
            if comp_type not in components:
                return False

        # Check with_any (if specified)
        if self._with_any:
            has_any = False
            for comp_type in self._with_any:
                if comp_type in components:
                    has_any = True
                    break
            if not has_any:
                return False

        # Check with_none
        for comp_type in self._with_none:
            if comp_type in components:
                return False

        # Check outgoing relationships
        for edge_type, target in self._with_relationships:
            if not self._world._has_relationship(entity_id, edge_type, target):
                return False

        # Check incoming relationships
        for edge_type, source in self._with_incoming:
            if not self._world._has_incoming_relationship(entity_id, edge_type, source):
                return False

        return True

    def _apply_filters(self, entity: Entity) -> bool:
        """Apply predicate filters to an entity.

        Args:
            entity: The entity to check.

        Returns:
            True if the entity passes all filters.
        """
        for predicate in self._filters:
            if not predicate(entity):
                return False
        return True

    def execute_ids(self) -> Iterator[EntityId]:
        """Return matching entity IDs only.

        Yields:
            EntityIds of matching entities.
        """
        for entity_id, components in self._world._entities.items():
            if self._matches(entity_id, components):
                if self._filters:
                    entity = Entity(self._world, entity_id)
                    if self._apply_filters(entity):
                        yield entity_id
                else:
                    yield entity_id

    def execute_entities(self) -> Iterator[Entity]:
        """Return live Entity handles.

        Yields:
            Entity handles for matching entities.
        """
        for entity_id, components in self._world._entities.items():
            if self._matches(entity_id, components):
                entity = Entity(self._world, entity_id)
                if self._apply_filters(entity):
                    yield entity

    def execute_components(self) -> Iterator[Tuple[Any, ...]]:
        """Return entity ID with requested components (from iterate()).

        The returned tuple contains the EntityId followed by the
        component instances in the order specified by iterate().

        Yields:
            Tuple of (EntityId, component1, component2, ...).

        Raises:
            ValueError: If iterate() was not called.
        """
        if self._iterate_types is None:
            raise ValueError("iterate() must be called before execute_components()")

        for entity_id, components in self._world._entities.items():
            if self._matches(entity_id, components):
                if self._filters:
                    entity = Entity(self._world, entity_id)
                    if not self._apply_filters(entity):
                        continue

                # Extract requested components
                result: List[Any] = [entity_id]
                for comp_type in self._iterate_types:
                    if comp_type in components:
                        result.append(components[comp_type])
                    else:
                        # Component not present - skip this entity
                        break
                else:
                    yield tuple(result)
