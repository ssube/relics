"""3D spatial index implementations for efficient spatial queries.

Provides both lazy (brute-force) and materialized (Octree) implementations
for 3D spatial indexing.
"""

from __future__ import annotations

import heapq
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
)

from relics.entity import Entity
from relics.index import IndexView
from relics.types import Component, EntityId

from .octree import Octree, OctreeBounds
from .types import (
    Box,
    Sphere,
    SpatialRegion,
    distance_3d,
)

if TYPE_CHECKING:
    from relics.world import World


# Type alias for 3D position extractor function
PositionExtractor3D = Callable[[Component], Tuple[float, float, float]]


def default_position_extractor_3d(
    component: Component,
) -> Tuple[float, float, float]:
    """Default position extractor for 3D components.

    Expects component to have x, y, and z attributes.

    Args:
        component: A component with x, y, and z attributes.

    Returns:
        Tuple of (x, y, z) coordinates.
    """
    return (
        getattr(component, "x"),
        getattr(component, "y"),
        getattr(component, "z"),
    )


class SpatialIndexView3D(IndexView):
    """Abstract base class for 3D spatial indexes.

    Extends IndexView with spatial query methods for 3D space.
    """

    @abstractmethod
    def query_sphere(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float,
    ) -> Iterator[Entity]:
        """Query for entities within a spherical region.

        Args:
            center_x: X coordinate of sphere center.
            center_y: Y coordinate of sphere center.
            center_z: Z coordinate of sphere center.
            radius: Radius of the sphere.

        Yields:
            Entity handles within the sphere.
        """
        pass  # abstract

    @abstractmethod
    def query_box(
        self,
        min_x: float,
        min_y: float,
        min_z: float,
        max_x: float,
        max_y: float,
        max_z: float,
    ) -> Iterator[Entity]:
        """Query for entities within a box region.

        Args:
            min_x: Minimum X coordinate.
            min_y: Minimum Y coordinate.
            min_z: Minimum Z coordinate.
            max_x: Maximum X coordinate.
            max_y: Maximum Y coordinate.
            max_z: Maximum Z coordinate.

        Yields:
            Entity handles within the box.
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
        z: float,
        count: int,
    ) -> List[Tuple[Entity, float]]:
        """Query for the nearest entities to a point.

        Args:
            x: X coordinate of the query point.
            y: Y coordinate of the query point.
            z: Z coordinate of the query point.
            count: Maximum number of entities to return.

        Returns:
            List of (Entity, distance) tuples, sorted by distance.
        """
        pass  # abstract

    def query_sphere_ids(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float,
    ) -> Iterator[EntityId]:
        """Query for entity IDs within a spherical region.

        Args:
            center_x: X coordinate of sphere center.
            center_y: Y coordinate of sphere center.
            center_z: Z coordinate of sphere center.
            radius: Radius of the sphere.

        Yields:
            Entity IDs within the sphere.
        """
        for entity in self.query_sphere(center_x, center_y, center_z, radius):
            yield entity.id

    def query_box_ids(
        self,
        min_x: float,
        min_y: float,
        min_z: float,
        max_x: float,
        max_y: float,
        max_z: float,
    ) -> Iterator[EntityId]:
        """Query for entity IDs within a box region.

        Args:
            min_x: Minimum X coordinate.
            min_y: Minimum Y coordinate.
            min_z: Minimum Z coordinate.
            max_x: Maximum X coordinate.
            max_y: Maximum Y coordinate.
            max_z: Maximum Z coordinate.

        Yields:
            Entity IDs within the box.
        """
        for entity in self.query_box(min_x, min_y, min_z, max_x, max_y, max_z):
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


class LazySpatialIndex3D(SpatialIndexView3D):
    """Lazy 3D spatial index that performs brute-force O(n) queries.

    Simpler implementation that re-queries all entities on each access.
    Best for small entity counts or infrequent queries.
    """

    def __init__(
        self,
        world: "World",
        component_type: Type[Component],
        position_extractor: Optional[PositionExtractor3D] = None,
    ) -> None:
        """Create a lazy spatial index.

        Args:
            world: The World to query.
            component_type: The component type that holds position data.
            position_extractor: Function to extract (x, y, z) from component.
                               Defaults to accessing .x, .y, and .z attributes.
        """
        self._world = world
        self._component_type = component_type
        self._position_extractor = (
            position_extractor or default_position_extractor_3d
        )

    def _get_entities_with_positions(
        self,
    ) -> Iterator[Tuple[Entity, float, float, float]]:
        """Get all entities with their positions.

        Yields:
            Tuples of (Entity, x, y, z).
        """
        for entity_id, components in self._world._entities.items():
            if self._component_type in components:
                component = components[self._component_type]
                x, y, z = self._position_extractor(component)
                yield (Entity(self._world, entity_id), x, y, z)

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over all entities in the index."""
        for entity, _, _, _ in self._get_entities_with_positions():
            yield entity

    def count(self) -> int:
        """Count entities with the position component."""
        return sum(
            1
            for _ in self._world._entities.values()
            if self._component_type in _
        )

    def get_entity_ids(self) -> Set[EntityId]:
        """Get entity IDs with the position component."""
        return {
            entity_id
            for entity_id, components in self._world._entities.items()
            if self._component_type in components
        }

    def query_sphere(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float,
    ) -> Iterator[Entity]:
        """Query for entities within a spherical region."""
        sphere = Sphere(center_x, center_y, center_z, radius)
        for entity, x, y, z in self._get_entities_with_positions():
            if sphere.contains_point(x, y, z):
                yield entity

    def query_box(
        self,
        min_x: float,
        min_y: float,
        min_z: float,
        max_x: float,
        max_y: float,
        max_z: float,
    ) -> Iterator[Entity]:
        """Query for entities within a box region."""
        box = Box(min_x, min_y, min_z, max_x, max_y, max_z)
        for entity, x, y, z in self._get_entities_with_positions():
            if box.contains_point(x, y, z):
                yield entity

    def query_region(self, region: SpatialRegion) -> Iterator[Entity]:
        """Query for entities within an arbitrary spatial region."""
        for entity, x, y, z in self._get_entities_with_positions():
            if region.contains_point(x, y, z):
                yield entity

    def query_nearest(
        self,
        x: float,
        y: float,
        z: float,
        count: int,
    ) -> List[Tuple[Entity, float]]:
        """Query for the nearest entities to a point."""
        # Use a heap for efficiency
        heap: List[Tuple[float, int, Entity]] = []
        idx = 0  # Tie-breaker for heap

        for entity, ex, ey, ez in self._get_entities_with_positions():
            dist = distance_3d(x, y, z, ex, ey, ez)
            if len(heap) < count:
                heapq.heappush(heap, (-dist, idx, entity))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, idx, entity))
            idx += 1

        # Sort by distance (ascending)
        result = [(entity, -neg_dist) for neg_dist, _, entity in heap]
        result.sort(key=lambda t: t[1])
        return result


class MaterializedSpatialIndex3D(SpatialIndexView3D):
    """Materialized 3D spatial index using an Octree.

    Provides O(log n) spatial queries by maintaining an Octree.
    Must be updated when entity positions change.
    """

    def __init__(
        self,
        world: "World",
        component_type: Type[Component],
        bounds: OctreeBounds,
        position_extractor: Optional[PositionExtractor3D] = None,
        max_entities_per_node: int = 8,
        max_depth: int = 8,
    ) -> None:
        """Create a materialized spatial index.

        Args:
            world: The World to query.
            component_type: The component type that holds position data.
            bounds: The spatial bounds for the Octree.
            position_extractor: Function to extract (x, y, z) from component.
            max_entities_per_node: Octree subdivision threshold.
            max_depth: Maximum Octree depth.
        """
        self._world = world
        self._component_type = component_type
        self._position_extractor = (
            position_extractor or default_position_extractor_3d
        )
        self._octree = Octree(
            bounds=bounds,
            max_entities_per_node=max_entities_per_node,
            max_depth=max_depth,
        )
        self._initialized = False

    @property
    def bounds(self) -> OctreeBounds:
        """Get the spatial bounds of this index."""
        return self._octree.bounds

    def _ensure_initialized(self) -> None:
        """Initialize the Octree if not already done."""
        if not self._initialized:
            self._rebuild()
            self._initialized = True

    def _rebuild(self) -> None:
        """Rebuild the Octree from scratch.

        Also binds monitored components to the world for change tracking.
        """
        self._octree.clear()
        for entity_id, components in self._world._entities.items():
            if self._component_type in components:
                component = components[self._component_type]
                # Bind monitored components to world for change tracking
                if hasattr(component, "_bind_to_world"):
                    component._bind_to_world(self._world, entity_id)
                x, y, z = self._position_extractor(component)
                self._octree.insert(entity_id, x, y, z)

    def invalidate(self) -> None:
        """Invalidate the index, forcing a full rebuild on next access."""
        self._initialized = False
        self._octree.clear()

    def update(self, entity_id: EntityId) -> None:
        """Update the index for a specific entity.

        Re-checks the entity's position and updates the Octree.

        Args:
            entity_id: The entity to update.
        """
        self._ensure_initialized()

        # Check if entity exists and has the component
        if entity_id in self._world._entities:
            components = self._world._entities[entity_id]
            if self._component_type in components:
                component = components[self._component_type]
                x, y, z = self._position_extractor(component)
                self._octree.update(entity_id, x, y, z)
            else:
                # Entity lost the component
                self._octree.remove(entity_id)
        else:
            # Entity was removed
            self._octree.remove(entity_id)

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
                x, y, z = self._position_extractor(component)
                self._octree.insert(entity_id, x, y, z)

    def remove_entity(self, entity_id: EntityId) -> None:
        """Remove an entity from the index.

        Args:
            entity_id: The entity to remove.
        """
        self._ensure_initialized()
        self._octree.remove(entity_id)

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over all entities in the index."""
        self._ensure_initialized()
        for entity_id, _, _, _ in self._octree.query_all():
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def count(self) -> int:
        """Count entities in the index."""
        self._ensure_initialized()
        return self._octree.count()

    def get_entity_ids(self) -> Set[EntityId]:
        """Get all entity IDs in the index."""
        self._ensure_initialized()
        return self._octree.get_entity_ids()

    def query_sphere(
        self,
        center_x: float,
        center_y: float,
        center_z: float,
        radius: float,
    ) -> Iterator[Entity]:
        """Query for entities within a spherical region."""
        self._ensure_initialized()
        sphere = Sphere(center_x, center_y, center_z, radius)
        for entity_id in self._octree.query(sphere):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def query_box(
        self,
        min_x: float,
        min_y: float,
        min_z: float,
        max_x: float,
        max_y: float,
        max_z: float,
    ) -> Iterator[Entity]:
        """Query for entities within a box region."""
        self._ensure_initialized()
        box = Box(min_x, min_y, min_z, max_x, max_y, max_z)
        for entity_id in self._octree.query(box):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def query_region(self, region: SpatialRegion) -> Iterator[Entity]:
        """Query for entities within an arbitrary spatial region."""
        self._ensure_initialized()
        for entity_id in self._octree.query(region):
            if entity_id in self._world._entities:
                yield Entity(self._world, entity_id)

    def query_nearest(
        self,
        x: float,
        y: float,
        z: float,
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

        for entity_id, ex, ey, ez in self._octree.query_all():
            if entity_id not in self._world._entities:
                continue
            entity = Entity(self._world, entity_id)
            dist = distance_3d(x, y, z, ex, ey, ez)
            if len(heap) < count:
                heapq.heappush(heap, (-dist, idx, entity))
            elif dist < -heap[0][0]:
                heapq.heapreplace(heap, (-dist, idx, entity))
            idx += 1

        # Sort by distance (ascending)
        result = [(entity, -neg_dist) for neg_dist, _, entity in heap]
        result.sort(key=lambda t: t[1])
        return result
