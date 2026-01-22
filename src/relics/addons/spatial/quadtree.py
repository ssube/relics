"""QuadTree data structure for efficient 2D spatial queries.

A QuadTree recursively subdivides 2D space into four quadrants,
enabling O(log n) spatial queries for range and nearest-neighbor searches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Set, Tuple

from relics.types import EntityId

from .types import SpatialRegion


@dataclass
class QuadTreeBounds:
    """Axis-aligned bounding rectangle for QuadTree nodes.

    Defined by center point and half-extents.

    Attributes:
        center_x: X coordinate of center.
        center_y: Y coordinate of center.
        half_width: Half the width (extends left and right from center).
        half_height: Half the height (extends up and down from center).
    """

    center_x: float
    center_y: float
    half_width: float
    half_height: float

    @property
    def min_x(self) -> float:
        """Get minimum X coordinate."""
        return self.center_x - self.half_width

    @property
    def max_x(self) -> float:
        """Get maximum X coordinate."""
        return self.center_x + self.half_width

    @property
    def min_y(self) -> float:
        """Get minimum Y coordinate."""
        return self.center_y - self.half_height

    @property
    def max_y(self) -> float:
        """Get maximum Y coordinate."""
        return self.center_y + self.half_height

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within these bounds.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if the point is within bounds.
        """
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def intersects_region(self, region: SpatialRegion) -> bool:
        """Check if this bounds intersects a spatial region.

        Args:
            region: The spatial region to test.

        Returns:
            True if the bounds intersects the region.
        """
        return region.intersects_bounds(
            (self.min_x, self.min_y),
            (self.max_x, self.max_y),
        )

    def get_quadrant(self, x: float, y: float) -> int:
        """Determine which quadrant a point belongs to.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Quadrant index: 0=NW, 1=NE, 2=SW, 3=SE.
        """
        if x <= self.center_x:
            if y <= self.center_y:
                return 2  # SW
            else:
                return 0  # NW
        else:
            if y <= self.center_y:
                return 3  # SE
            else:
                return 1  # NE

    def subdivide(self) -> Tuple[
        "QuadTreeBounds",
        "QuadTreeBounds",
        "QuadTreeBounds",
        "QuadTreeBounds",
    ]:
        """Create four child bounds by subdividing this bounds.

        Returns:
            Tuple of (NW, NE, SW, SE) child bounds.
        """
        half_w = self.half_width / 2
        half_h = self.half_height / 2

        nw = QuadTreeBounds(
            self.center_x - half_w,
            self.center_y + half_h,
            half_w,
            half_h,
        )
        ne = QuadTreeBounds(
            self.center_x + half_w,
            self.center_y + half_h,
            half_w,
            half_h,
        )
        sw = QuadTreeBounds(
            self.center_x - half_w,
            self.center_y - half_h,
            half_w,
            half_h,
        )
        se = QuadTreeBounds(
            self.center_x + half_w,
            self.center_y - half_h,
            half_w,
            half_h,
        )

        return (nw, ne, sw, se)


@dataclass
class QuadTreeNode:
    """A node in the QuadTree.

    Attributes:
        bounds: The spatial bounds of this node.
        entities: Dictionary mapping entity IDs to their positions.
        children: Optional list of 4 child nodes (NW, NE, SW, SE).
        max_entities: Maximum entities before subdivision.
        max_depth: Maximum tree depth.
        depth: Current depth in the tree.
    """

    bounds: QuadTreeBounds
    max_entities: int = 8
    max_depth: int = 8
    depth: int = 0
    entities: Dict[EntityId, Tuple[float, float]] = field(default_factory=dict)
    children: Optional[List["QuadTreeNode"]] = None

    def _subdivide(self) -> None:
        """Create child nodes by splitting this node into quadrants."""
        if self.children is not None:
            return  # Already subdivided

        child_bounds = self.bounds.subdivide()
        self.children = [
            QuadTreeNode(
                bounds=b,
                max_entities=self.max_entities,
                max_depth=self.max_depth,
                depth=self.depth + 1,
            )
            for b in child_bounds
        ]

        # Redistribute entities to children
        entities_to_move = list(self.entities.items())
        self.entities.clear()

        for entity_id, (x, y) in entities_to_move:
            quadrant = self.bounds.get_quadrant(x, y)
            self.children[quadrant].insert(entity_id, x, y)

    def insert(self, entity_id: EntityId, x: float, y: float) -> bool:
        """Insert an entity at the given position.

        Args:
            entity_id: The entity to insert.
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if inserted successfully, False if out of bounds.
        """
        if not self.bounds.contains_point(x, y):
            return False

        # If we have children, delegate to appropriate child
        if self.children is not None:
            quadrant = self.bounds.get_quadrant(x, y)
            return self.children[quadrant].insert(entity_id, x, y)

        # Store in this node
        self.entities[entity_id] = (x, y)

        # Subdivide if we exceed capacity and haven't reached max depth
        if len(self.entities) > self.max_entities and self.depth < self.max_depth:
            self._subdivide()

        return True

    def remove(self, entity_id: EntityId) -> bool:
        """Remove an entity from the tree.

        Args:
            entity_id: The entity to remove.

        Returns:
            True if the entity was found and removed.
        """
        # Check this node
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True

        # Check children
        if self.children is not None:
            for child in self.children:
                if child.remove(entity_id):
                    return True

        return False

    def query(self, region: SpatialRegion) -> Iterator[EntityId]:
        """Query for entities within a region.

        Args:
            region: The spatial region to query.

        Yields:
            Entity IDs within the region.
        """
        # Check if this node intersects the query region
        if not self.bounds.intersects_region(region):
            return

        # Check entities in this node
        for entity_id, (x, y) in self.entities.items():
            if region.contains_point(x, y):
                yield entity_id

        # Recursively check children
        if self.children is not None:
            for child in self.children:
                yield from child.query(region)

    def get_all_entities(self) -> Iterator[Tuple[EntityId, float, float]]:
        """Get all entities in this node and its children.

        Yields:
            Tuples of (entity_id, x, y).
        """
        for entity_id, (x, y) in self.entities.items():
            yield (entity_id, x, y)

        if self.children is not None:
            for child in self.children:
                yield from child.get_all_entities()

    def count(self) -> int:
        """Count total entities in this node and children.

        Returns:
            Total entity count.
        """
        total = len(self.entities)
        if self.children is not None:
            for child in self.children:
                total += child.count()
        return total


class QuadTree:
    """QuadTree data structure for 2D spatial indexing.

    Provides efficient O(log n) spatial queries for point positions.

    Attributes:
        root: The root node of the tree.
        entity_positions: Mapping of entity IDs to their current positions.
    """

    def __init__(
        self,
        bounds: QuadTreeBounds,
        max_entities_per_node: int = 8,
        max_depth: int = 8,
    ) -> None:
        """Create a new QuadTree.

        Args:
            bounds: The spatial bounds of the entire tree.
            max_entities_per_node: Maximum entities per node before subdivision.
            max_depth: Maximum depth of the tree.
        """
        self._bounds = bounds
        self._max_entities = max_entities_per_node
        self._max_depth = max_depth
        self._root = QuadTreeNode(
            bounds=bounds,
            max_entities=max_entities_per_node,
            max_depth=max_depth,
            depth=0,
        )
        self._entity_positions: Dict[EntityId, Tuple[float, float]] = {}

    @property
    def bounds(self) -> QuadTreeBounds:
        """Get the bounds of this QuadTree."""
        return self._bounds

    def insert(self, entity_id: EntityId, x: float, y: float) -> bool:
        """Insert an entity at the given position.

        If the entity already exists, it will be updated.

        Args:
            entity_id: The entity to insert.
            x: X coordinate.
            y: Y coordinate.

        Returns:
            True if inserted successfully, False if out of bounds.
        """
        # Remove old position if exists
        if entity_id in self._entity_positions:
            self.remove(entity_id)

        if self._root.insert(entity_id, x, y):
            self._entity_positions[entity_id] = (x, y)
            return True
        return False

    def remove(self, entity_id: EntityId) -> bool:
        """Remove an entity from the tree.

        Args:
            entity_id: The entity to remove.

        Returns:
            True if the entity was found and removed.
        """
        if entity_id not in self._entity_positions:
            return False

        self._root.remove(entity_id)
        del self._entity_positions[entity_id]
        return True

    def update(self, entity_id: EntityId, x: float, y: float) -> bool:
        """Update an entity's position.

        Args:
            entity_id: The entity to update.
            x: New X coordinate.
            y: New Y coordinate.

        Returns:
            True if updated successfully.
        """
        return self.insert(entity_id, x, y)

    def query(self, region: SpatialRegion) -> Iterator[EntityId]:
        """Query for entities within a region.

        Args:
            region: The spatial region to query.

        Yields:
            Entity IDs within the region.
        """
        yield from self._root.query(region)

    def query_all(self) -> Iterator[Tuple[EntityId, float, float]]:
        """Get all entities in the tree.

        Yields:
            Tuples of (entity_id, x, y).
        """
        yield from self._root.get_all_entities()

    def get_position(self, entity_id: EntityId) -> Optional[Tuple[float, float]]:
        """Get an entity's current position.

        Args:
            entity_id: The entity to look up.

        Returns:
            Position tuple (x, y) or None if not found.
        """
        return self._entity_positions.get(entity_id)

    def contains(self, entity_id: EntityId) -> bool:
        """Check if an entity is in the tree.

        Args:
            entity_id: The entity to check.

        Returns:
            True if the entity is in the tree.
        """
        return entity_id in self._entity_positions

    def get_entity_ids(self) -> Set[EntityId]:
        """Get all entity IDs in the tree.

        Returns:
            Set of all entity IDs.
        """
        return set(self._entity_positions.keys())

    def count(self) -> int:
        """Count total entities in the tree.

        Returns:
            Total entity count.
        """
        return len(self._entity_positions)

    def clear(self) -> None:
        """Remove all entities from the tree."""
        self._root = QuadTreeNode(
            bounds=self._bounds,
            max_entities=self._max_entities,
            max_depth=self._max_depth,
            depth=0,
        )
        self._entity_positions.clear()
