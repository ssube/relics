"""Spatial index implementations for efficient spatial queries.

Provides both lazy (brute-force) and materialized (QuadTree/Octree) implementations
for 2D and 3D spatial indexing.
"""

from __future__ import annotations

import heapq
from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Iterator, List, Optional, Set, Tuple, Type

from relics.entity import Entity
from relics.index import IndexView
from relics.types import Component, EntityId

from .quadtree import QuadTree, QuadTreeBounds
from .types import Circle, Rectangle, SpatialRegion, distance_2d

if TYPE_CHECKING:
    from relics.world import World


# Type alias for position extractor function
PositionExtractor2D = Callable[[Component], Tuple[float, float]]


def default_position_extractor_2d(component: Component) -> Tuple[float, float]:
    """Default position extractor for 2D components.

    Expects component to have x and y attributes.

    Args:
        component: A component with x and y attributes.

    Returns:
        Tuple of (x, y) coordinates.
    """
    return (getattr(component, "x"), getattr(component, "y"))


class SpatialIndexView2D(IndexView):
    """Abstract base class for 2D spatial indexes.

    Extends IndexView with spatial query methods for 2D space.
    """

    @abstractmethod
    def query_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> Iterator[Entity]:
        """Query for entities within a circular region.

        Args:
            center_x: X coordinate of circle center.
            center_y: Y coordinate of circle center.
            radius: Radius of the circle.

        Yields:
            Entity handles within the circle.
        """
        pass  # abstract

    @abstractmethod
    def query_rectangle(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> Iterator[Entity]:
        """Query for entities within a rectangular region.

        Args:
            min_x: Minimum X coordinate.
            min_y: Minimum Y coordinate.
            max_x: Maximum X coordinate.
            max_y: Maximum Y coordinate.

        Yields:
            Entity handles within the rectangle.
        """
        pass  # abstract

    @abstractmethod
    def query_region(self, region: SpatialRegion) -> Iterator[Entity]:
        """Query for entities within an arbitrary spatial region.

        Args:
            region: The spatial region to query.

        Yields:
            Entity handles within the region.
        """
        pass  # abstract

    @abstractmethod
    def query_nearest(
        self,
        x: float,
        y: float,
        count: int,
    ) -> List[Tuple[Entity, float]]:
        """Query for the nearest entities to a point.

        Args:
            x: X coordinate of the query point.
            y: Y coordinate of the query point.
            count: Maximum number of entities to return.

        Returns:
            List of (Entity, distance) tuples, sorted by distance.
        """
        pass  # abstract

    def query_circle_ids(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> Iterator[EntityId]:
        """Query for entity IDs within a circular region.

        Args:
            center_x: X coordinate of circle center.
            center_y: Y coordinate of circle center.
            radius: Radius of the circle.

        Yields:
            Entity IDs within the circle.
        """
        for entity in self.query_circle(center_x, center_y, radius):
            yield entity.id

    def query_rectangle_ids(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> Iterator[EntityId]:
        """Query for entity IDs within a rectangular region.

        Args:
            min_x: Minimum X coordinate.
            min_y: Minimum Y coordinate.
            max_x: Maximum X coordinate.
            max_y: Maximum Y coordinate.

        Yields:
            Entity IDs within the rectangle.
        """
        for entity in self.query_rectangle(min_x, min_y, max_x, max_y):
            yield entity.id

    def query_region_ids(self, region: SpatialRegion) -> Iterator[EntityId]:
        """Query for entity IDs within an arbitrary spatial region.

        Args:
            region: The spatial region to query.

        Yields:
            Entity IDs within the region.
        """
        for entity in self.query_region(region):
            yield entity.id


class LazySpatialIndex2D(SpatialIndexView2D):
    """Lazy 2D spatial index that performs brute-force O(n) queries.

    Simpler implementation that re-queries all entities on each access.
    Best for small entity counts or infrequent queries.
    """

    def __init__(
        self,
        world: "World",
        component_type: Type[Component],
        position_extractor: Optional[PositionExtractor2D] = None,
    ) -> None:
        """Create a lazy spatial index.

        Args:
            world: The World to query.
            component_type: The component type that holds position data.
            position_extractor: Function to extract (x, y) from component.
                               Defaults to accessing .x and .y attributes.
        """
        self._world = world
        self._component_type = component_type
        self._position_extractor = position_extractor or default_position_extractor_2d

    def _get_entities_with_positions(
        self,
    ) -> Iterator[Tuple[Entity, float, float]]:
        """Get all entities with their positions.

        Yields:
            Tuples of (Entity, x, y).
        """
        for entity_id, components in self._world._entities.items():
            if self._component_type in components:
                component = components[self._component_type]
                x, y = self._position_extractor(component)
                yield (Entity(self._world, entity_id), x, y)

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over all entities in the index."""
        for entity, _, _ in self._get_entities_with_positions():
            yield entity

    def count(self) -> int:
        """Count entities with the position component."""
        return sum(
            1 for _ in self._world._entities.values() if self._component_type in _
        )

    def get_entity_ids(self) -> Set[EntityId]:
        """Get entity IDs with the position component."""
        return {
            entity_id
            for entity_id, components in self._world._entities.items()
            if self._component_type in components
        }

    def query_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> Iterator[Entity]:
        """Query for entities within a circular region."""
        circle = Circle(center_x, center_y, radius)
        for entity, x, y in self._get_entities_with_positions():
            if circle.contains_point(x, y):
                yield entity

    def query_rectangle(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> Iterator[Entity]:
        """Query for entities within a rectangular region."""
        rect = Rectangle(min_x, min_y, max_x, max_y)
        for entity, x, y in self._get_entities_with_positions():
            if rect.contains_point(x, y):
                yield entity

    def query_region(self, region: SpatialRegion) -> Iterator[Entity]:
        """Query for entities within an arbitrary spatial region."""
        for entity, x, y in self._get_entities_with_positions():
            if region.contains_point(x, y):
                yield entity

    def query_nearest(
        self,
        x: float,
        y: float,
        count: int,
    ) -> List[Tuple[Entity, float]]:
        """Query for the nearest entities to a point."""
        # Use a heap for efficiency
        heap: List[Tuple[float, int, Entity]] = []
        idx = 0  # Tie-breaker for heap

        for entity, ex, ey in self._get_entities_with_positions():
            dist = distance_2d(x, y, ex, ey)
            if len(heap) < count:
                heapq.heappush(heap, (-dist, idx, entity))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, idx, entity))
            idx += 1

        # Sort by distance (ascending)
        result = [(entity, -neg_dist) for neg_dist, _, entity in heap]
        result.sort(key=lambda t: t[1])
        return result


class MaterializedSpatialIndex2D(SpatialIndexView2D):
    """Materialized 2D spatial index using a QuadTree.

    Provides O(log n) spatial queries by maintaining a QuadTree.
    Must be updated when entity positions change.
    """

    def __init__(
        self,
        world: "World",
        component_type: Type[Component],
        bounds: QuadTreeBounds,
        position_extractor: Optional[PositionExtractor2D] = None,
        max_entities_per_node: int = 8,
        max_depth: int = 8,
    ) -> None:
        """Create a materialized spatial index.

        Args:
            world: The World to query.
            component_type: The component type that holds position data.
            bounds: The spatial bounds for the QuadTree.
            position_extractor: Function to extract (x, y) from component.
            max_entities_per_node: QuadTree subdivision threshold.
            max_depth: Maximum QuadTree depth.
        """
        self._world = world
        self._component_type = component_type
        self._position_extractor = position_extractor or default_position_extractor_2d
        self._quadtree = QuadTree(
            bounds=bounds,
            max_entities_per_node=max_entities_per_node,
            max_depth=max_depth,
        )
        self._initialized = False

    @property
    def bounds(self) -> QuadTreeBounds:
        """Get the spatial bounds of this index."""
        return self._quadtree.bounds

    def _ensure_initialized(self) -> None:
        """Initialize the QuadTree if not already done."""
        if not self._initialized:
            self._rebuild()
            self._initialized = True

    def _rebuild(self) -> None:
        """Rebuild the QuadTree from scratch.

        Also binds monitored components to the world for change tracking.
        """
        self._quadtree.clear()
        for entity_id, components in self._world._entities.items():
            if self._component_type in components:
                component = components[self._component_type]
                # Bind monitored components to world for change tracking
                if hasattr(component, "_bind_to_world"):
                    component._bind_to_world(self._world, entity_id)
                x, y = self._position_extractor(component)
                self._quadtree.insert(entity_id, x, y)

    def invalidate(self) -> None:
        """Invalidate the index, forcing a full rebuild on next access."""
        self._initialized = False
        self._quadtree.clear()

    def update(self, entity_id: EntityId) -> None:
        """Update the index for a specific entity.

        Re-checks the entity's position and updates the QuadTree.

        Args:
            entity_id: The entity to update.
        """
        self._ensure_initialized()

        # Check if entity exists and has the component
        if entity_id in self._world._entities:
            components = self._world._entities[entity_id]
            if self._component_type in components:
                component = components[self._component_type]
                x, y = self._position_extractor(component)
                self._quadtree.update(entity_id, x, y)
            else:
                # Entity lost the component
                self._quadtree.remove(entity_id)
        else:
            # Entity was removed
            self._quadtree.remove(entity_id)

    def add_entity(self, entity_id: EntityId) -> None:
        """Add a new entity to the index.

        Args:
            entity_id: The entity to add.
        """
        self._ensure_initialized()

        if entity_id in self._world._entities:
            components = self._world._entities[entity_id]
            if self._component_type in components:
                component = components[self._component_type]
                x, y = self._position_extractor(component)
                self._quadtree.insert(entity_id, x, y)

    def remove_entity(self, entity_id: EntityId) -> None:
        """Remove an entity from the index.

        Args:
            entity_id: The entity to remove.
        """
        self._ensure_initialized()
        self._quadtree.remove(entity_id)

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over all entities in the index."""
        self._ensure_initialized()
        for entity_id, _, _ in self._quadtree.query_all():
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def count(self) -> int:
        """Count entities in the index."""
        self._ensure_initialized()
        return self._quadtree.count()

    def get_entity_ids(self) -> Set[EntityId]:
        """Get all entity IDs in the index."""
        self._ensure_initialized()
        return self._quadtree.get_entity_ids()

    def query_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> Iterator[Entity]:
        """Query for entities within a circular region."""
        self._ensure_initialized()
        circle = Circle(center_x, center_y, radius)
        for entity_id in self._quadtree.query(circle):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def query_rectangle(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> Iterator[Entity]:
        """Query for entities within a rectangular region."""
        self._ensure_initialized()
        rect = Rectangle(min_x, min_y, max_x, max_y)
        for entity_id in self._quadtree.query(rect):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def query_region(self, region: SpatialRegion) -> Iterator[Entity]:
        """Query for entities within an arbitrary spatial region."""
        self._ensure_initialized()
        for entity_id in self._quadtree.query(region):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def query_nearest(
        self,
        x: float,
        y: float,
        count: int,
    ) -> List[Tuple[Entity, float]]:
        """Query for the nearest entities to a point.

        Note: This implementation does a full scan for simplicity.
        A more optimized version would use iterative range expansion.
        """
        self._ensure_initialized()

        # Use a heap for efficiency
        heap: List[Tuple[float, int, Entity]] = []
        idx = 0

        for entity_id, ex, ey in self._quadtree.query_all():
            if entity_id not in self._world._entities:
                continue
            entity = Entity(self._world, entity_id)
            dist = distance_2d(x, y, ex, ey)
            if len(heap) < count:
                heapq.heappush(heap, (-dist, idx, entity))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, idx, entity))
            idx += 1

        # Sort by distance (ascending)
        result = [(entity, -neg_dist) for neg_dist, _, entity in heap]
        result.sort(key=lambda t: t[1])
        return result
