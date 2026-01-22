"""Secondary index implementations for efficient entity queries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterator, List, Set, Type

from relics.entity import Entity
from relics.types import Component, EntityId

if TYPE_CHECKING:
    from relics.query import QueryBuilder
    from relics.world import World


class IndexView(ABC):
    """Abstract base class for secondary indexes.

    Indexes provide efficient access to entities matching certain criteria.
    """

    @abstractmethod
    def __iter__(self) -> Iterator[Entity]:
        """Iterate over entities in the index.

        Yields:
            Entity handles for matching entities.
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Get the number of entities in the index.

        Returns:
            Number of matching entities.
        """
        pass

    def __len__(self) -> int:
        """Get the number of entities in the index."""
        return self.count()


class LazyIndex(IndexView):
    """Index that re-executes query on each access.

    This is simpler but may be slower for frequently accessed indexes.
    """

    def __init__(self, world: "World", query: "QueryBuilder") -> None:
        """Create a lazy index.

        Args:
            world: The World to query.
            query: The query that defines index membership.
        """
        self._world = world
        self._query = query

    def __iter__(self) -> Iterator[Entity]:
        """Re-execute the query and yield matching entities."""
        yield from self._query.execute_entities()

    def count(self) -> int:
        """Count matching entities by executing the query."""
        return sum(1 for _ in self._query.execute_entities())


class MaterializedIndex(IndexView):
    """Index that maintains a cached set of entity IDs.

    Updates when watched components change. More efficient for
    frequently accessed indexes, but requires memory for the cache.
    """

    def __init__(
        self,
        world: "World",
        query: "QueryBuilder",
        watches: List[Type[Component]],
    ) -> None:
        """Create a materialized index.

        Args:
            world: The World to query.
            query: The query that defines index membership.
            watches: Component types that trigger index updates.
        """
        self._world = world
        self._query = query
        self._watches = set(watches)
        self._cache: Set[EntityId] = set()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize the cache if not already done."""
        if not self._initialized:
            self._cache = set(self._query.execute_ids())
            self._initialized = True

    def invalidate(self) -> None:
        """Invalidate the cache, forcing re-computation on next access."""
        self._initialized = False
        self._cache.clear()

    def update(self, entity_id: EntityId) -> None:
        """Update the index for a specific entity.

        Re-checks if the entity matches the query criteria.

        Args:
            entity_id: The entity to update.
        """
        self._ensure_initialized()

        # Check if entity still exists and matches
        if entity_id in self._world._entities:
            components = self._world._entities[entity_id]
            if self._query._matches(entity_id, components):
                # Check filters
                if self._query._filters:
                    entity = Entity(self._world, entity_id)
                    if self._query._apply_filters(entity):
                        self._cache.add(entity_id)
                    else:
                        self._cache.discard(entity_id)
                else:
                    self._cache.add(entity_id)
            else:
                self._cache.discard(entity_id)
        else:
            self._cache.discard(entity_id)

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over cached entities."""
        self._ensure_initialized()
        for entity_id in list(self._cache):
            # Verify entity still exists
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)
            else:
                self._cache.discard(entity_id)

    def count(self) -> int:
        """Get the count from cache."""
        self._ensure_initialized()
        return len(self._cache)
