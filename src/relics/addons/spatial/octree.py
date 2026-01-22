"""Octree data structure for efficient 3D spatial queries.

An Octree recursively subdivides 3D space into eight octants,
enabling O(log n) spatial queries for range and nearest-neighbor searches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Set, Tuple

from relics.types import EntityId

from .types import SpatialRegion


@dataclass
class OctreeBounds:
    """Axis-aligned bounding box for Octree nodes.

    Defined by center point and half-extents.

    Attributes:
        center_x: X coordinate of center.
        center_y: Y coordinate of center.
        center_z: Z coordinate of center.
        half_width: Half the width (X dimension).
        half_height: Half the height (Y dimension).
        half_depth: Half the depth (Z dimension).
    """

    center_x: float
    center_y: float
    center_z: float
    half_width: float
    half_height: float
    half_depth: float

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

    @property
    def min_z(self) -> float:
        """Get minimum Z coordinate."""
        return self.center_z - self.half_depth

    @property
    def max_z(self) -> float:
        """Get maximum Z coordinate."""
        return self.center_z + self.half_depth

    def contains_point(self, x: float, y: float, z: float) -> bool:
        """Check if a point is within these bounds.

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.

        Returns:
            True if the point is within bounds.
        """
        return (
            self.min_x <= x <= self.max_x
            and self.min_y <= y <= self.max_y
            and self.min_z <= z <= self.max_z
        )

    def intersects_region(self, region: SpatialRegion) -> bool:
        """Check if this bounds intersects a spatial region.

        Args:
            region: The spatial region to test.

        Returns:
            True if the bounds intersects the region.
        """
        return region.intersects_bounds(
            (self.min_x, self.min_y, self.min_z),
            (self.max_x, self.max_y, self.max_z),
        )

    def get_octant(self, x: float, y: float, z: float) -> int:
        """Determine which octant a point belongs to.

        Octants are numbered 0-7 based on position relative to center:
        - Bit 0 (1): X > center_x
        - Bit 1 (2): Y > center_y
        - Bit 2 (4): Z > center_z

        Args:
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.

        Returns:
            Octant index (0-7).
        """
        octant = 0
        if x > self.center_x:
            octant |= 1
        if y > self.center_y:
            octant |= 2
        if z > self.center_z:
            octant |= 4
        return octant

    def subdivide(self) -> Tuple[
        "OctreeBounds",
        "OctreeBounds",
        "OctreeBounds",
        "OctreeBounds",
        "OctreeBounds",
        "OctreeBounds",
        "OctreeBounds",
        "OctreeBounds",
    ]:
        """Create eight child bounds by subdividing this bounds.

        Returns:
            Tuple of 8 child bounds indexed by octant number.
        """
        half_w = self.half_width / 2
        half_h = self.half_height / 2
        half_d = self.half_depth / 2

        children = []
        for octant in range(8):
            # Determine offset based on octant bits
            dx = half_w if (octant & 1) else -half_w
            dy = half_h if (octant & 2) else -half_h
            dz = half_d if (octant & 4) else -half_d

            children.append(
                OctreeBounds(
                    self.center_x + dx,
                    self.center_y + dy,
                    self.center_z + dz,
                    half_w,
                    half_h,
                    half_d,
                )
            )

        return tuple(children)  # type: ignore


@dataclass
class OctreeNode:
    """A node in the Octree.

    Attributes:
        bounds: The spatial bounds of this node.
        entities: Dictionary mapping entity IDs to their positions.
        children: Optional list of 8 child nodes.
        max_entities: Maximum entities before subdivision.
        max_depth: Maximum tree depth.
        depth: Current depth in the tree.
    """

    bounds: OctreeBounds
    max_entities: int = 8
    max_depth: int = 8
    depth: int = 0
    entities: Dict[EntityId, Tuple[float, float, float]] = field(default_factory=dict)
    children: Optional[List["OctreeNode"]] = None

    def _subdivide(self) -> None:
        """Create child nodes by splitting this node into octants."""
        if self.children is not None:
            return  # Already subdivided

        child_bounds = self.bounds.subdivide()
        self.children = [
            OctreeNode(
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

        for entity_id, (x, y, z) in entities_to_move:
            octant = self.bounds.get_octant(x, y, z)
            self.children[octant].insert(entity_id, x, y, z)

    def insert(self, entity_id: EntityId, x: float, y: float, z: float) -> bool:
        """Insert an entity at the given position.

        Args:
            entity_id: The entity to insert.
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.

        Returns:
            True if inserted successfully, False if out of bounds.
        """
        if not self.bounds.contains_point(x, y, z):
            return False

        # If we have children, delegate to appropriate child
        if self.children is not None:
            octant = self.bounds.get_octant(x, y, z)
            return self.children[octant].insert(entity_id, x, y, z)

        # Store in this node
        self.entities[entity_id] = (x, y, z)

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
        for entity_id, (x, y, z) in self.entities.items():
            if region.contains_point(x, y, z):
                yield entity_id

        # Recursively check children
        if self.children is not None:
            for child in self.children:
                yield from child.query(region)

    def get_all_entities(self) -> Iterator[Tuple[EntityId, float, float, float]]:
        """Get all entities in this node and its children.

        Yields:
            Tuples of (entity_id, x, y, z).
        """
        for entity_id, (x, y, z) in self.entities.items():
            yield (entity_id, x, y, z)

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


class Octree:
    """Octree data structure for 3D spatial indexing.

    Provides efficient O(log n) spatial queries for point positions.

    Attributes:
        root: The root node of the tree.
        entity_positions: Mapping of entity IDs to their current positions.
    """

    def __init__(
        self,
        bounds: OctreeBounds,
        max_entities_per_node: int = 8,
        max_depth: int = 8,
    ) -> None:
        """Create a new Octree.

        Args:
            bounds: The spatial bounds of the entire tree.
            max_entities_per_node: Maximum entities per node before subdivision.
            max_depth: Maximum depth of the tree.
        """
        self._bounds = bounds
        self._max_entities = max_entities_per_node
        self._max_depth = max_depth
        self._root = OctreeNode(
            bounds=bounds,
            max_entities=max_entities_per_node,
            max_depth=max_depth,
            depth=0,
        )
        self._entity_positions: Dict[EntityId, Tuple[float, float, float]] = {}

    @property
    def bounds(self) -> OctreeBounds:
        """Get the bounds of this Octree."""
        return self._bounds

    def insert(self, entity_id: EntityId, x: float, y: float, z: float) -> bool:
        """Insert an entity at the given position.

        If the entity already exists, it will be updated.

        Args:
            entity_id: The entity to insert.
            x: X coordinate.
            y: Y coordinate.
            z: Z coordinate.

        Returns:
            True if inserted successfully, False if out of bounds.
        """
        # Remove old position if exists
        if entity_id in self._entity_positions:
            self.remove(entity_id)

        if self._root.insert(entity_id, x, y, z):
            self._entity_positions[entity_id] = (x, y, z)
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

    def update(self, entity_id: EntityId, x: float, y: float, z: float) -> bool:
        """Update an entity's position.

        Args:
            entity_id: The entity to update.
            x: New X coordinate.
            y: New Y coordinate.
            z: New Z coordinate.

        Returns:
            True if updated successfully.
        """
        return self.insert(entity_id, x, y, z)

    def query(self, region: SpatialRegion) -> Iterator[EntityId]:
        """Query for entities within a region.

        Args:
            region: The spatial region to query.

        Yields:
            Entity IDs within the region.
        """
        yield from self._root.query(region)

    def query_all(self) -> Iterator[Tuple[EntityId, float, float, float]]:
        """Get all entities in the tree.

        Yields:
            Tuples of (entity_id, x, y, z).
        """
        yield from self._root.get_all_entities()

    def get_position(self, entity_id: EntityId) -> Optional[Tuple[float, float, float]]:
        """Get an entity's current position.

        Args:
            entity_id: The entity to look up.

        Returns:
            Position tuple (x, y, z) or None if not found.
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
        self._root = OctreeNode(
            bounds=self._bounds,
            max_entities=self._max_entities,
            max_depth=self._max_depth,
            depth=0,
        )
        self._entity_positions.clear()
