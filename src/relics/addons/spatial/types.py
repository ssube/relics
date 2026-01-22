"""Spatial query region types for 2D and 3D spatial queries.

These types define regions that can be used to query spatial indexes
for entities within a specific area.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple


class SpatialRegion(ABC):
    """Abstract base class for spatial query regions.

    Spatial regions define areas that can be tested for point containment
    and bounds intersection, used by spatial indexes for range queries.
    """

    @abstractmethod
    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a point is contained within this region.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.
            z: Z coordinate of the point (default 0 for 2D).

        Returns:
            True if the point is inside the region.
        """
        pass  # abstract

    @abstractmethod
    def intersects_bounds(
        self,
        min_corner: Tuple[float, ...],
        max_corner: Tuple[float, ...],
    ) -> bool:
        """Check if this region intersects with an axis-aligned bounding box.

        Args:
            min_corner: Minimum corner coordinates (x, y) or (x, y, z).
            max_corner: Maximum corner coordinates (x, y) or (x, y, z).

        Returns:
            True if the region intersects the bounding box.
        """
        pass  # abstract


@dataclass
class Circle(SpatialRegion):
    """2D circular query region.

    Attributes:
        center_x: X coordinate of the circle center.
        center_y: Y coordinate of the circle center.
        radius: Radius of the circle.
    """

    center_x: float
    center_y: float
    radius: float

    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a point is within the circle.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.
            z: Z coordinate (ignored for 2D circle).

        Returns:
            True if the point is inside the circle.
        """
        dx = x - self.center_x
        dy = y - self.center_y
        return (dx * dx + dy * dy) <= (self.radius * self.radius)

    def intersects_bounds(
        self,
        min_corner: Tuple[float, ...],
        max_corner: Tuple[float, ...],
    ) -> bool:
        """Check if the circle intersects an axis-aligned rectangle.

        Uses the closest point on rectangle to circle center algorithm.

        Args:
            min_corner: Minimum corner (min_x, min_y).
            max_corner: Maximum corner (max_x, max_y).

        Returns:
            True if the circle intersects the rectangle.
        """
        # Find the closest point on the rectangle to the circle center
        closest_x = max(min_corner[0], min(self.center_x, max_corner[0]))
        closest_y = max(min_corner[1], min(self.center_y, max_corner[1]))

        # Check if the closest point is within the circle
        dx = self.center_x - closest_x
        dy = self.center_y - closest_y
        return (dx * dx + dy * dy) <= (self.radius * self.radius)


@dataclass
class Rectangle(SpatialRegion):
    """2D rectangular query region (axis-aligned).

    Attributes:
        min_x: Minimum X coordinate.
        min_y: Minimum Y coordinate.
        max_x: Maximum X coordinate.
        max_y: Maximum Y coordinate.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a point is within the rectangle.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.
            z: Z coordinate (ignored for 2D rectangle).

        Returns:
            True if the point is inside the rectangle.
        """
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def intersects_bounds(
        self,
        min_corner: Tuple[float, ...],
        max_corner: Tuple[float, ...],
    ) -> bool:
        """Check if this rectangle intersects another axis-aligned rectangle.

        Args:
            min_corner: Minimum corner (min_x, min_y).
            max_corner: Maximum corner (max_x, max_y).

        Returns:
            True if the rectangles intersect.
        """
        return not (
            self.max_x < min_corner[0]
            or self.min_x > max_corner[0]
            or self.max_y < min_corner[1]
            or self.min_y > max_corner[1]
        )


@dataclass
class Sphere(SpatialRegion):
    """3D spherical query region.

    Attributes:
        center_x: X coordinate of the sphere center.
        center_y: Y coordinate of the sphere center.
        center_z: Z coordinate of the sphere center.
        radius: Radius of the sphere.
    """

    center_x: float
    center_y: float
    center_z: float
    radius: float

    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a point is within the sphere.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.
            z: Z coordinate of the point.

        Returns:
            True if the point is inside the sphere.
        """
        dx = x - self.center_x
        dy = y - self.center_y
        dz = z - self.center_z
        return (dx * dx + dy * dy + dz * dz) <= (self.radius * self.radius)

    def intersects_bounds(
        self,
        min_corner: Tuple[float, ...],
        max_corner: Tuple[float, ...],
    ) -> bool:
        """Check if the sphere intersects an axis-aligned box.

        Uses the closest point on box to sphere center algorithm.

        Args:
            min_corner: Minimum corner (min_x, min_y, min_z).
            max_corner: Maximum corner (max_x, max_y, max_z).

        Returns:
            True if the sphere intersects the box.
        """
        # Handle both 2D and 3D bounds
        min_z = min_corner[2] if len(min_corner) > 2 else 0.0
        max_z = max_corner[2] if len(max_corner) > 2 else 0.0

        # Find the closest point on the box to the sphere center
        closest_x = max(min_corner[0], min(self.center_x, max_corner[0]))
        closest_y = max(min_corner[1], min(self.center_y, max_corner[1]))
        closest_z = max(min_z, min(self.center_z, max_z))

        # Check if the closest point is within the sphere
        dx = self.center_x - closest_x
        dy = self.center_y - closest_y
        dz = self.center_z - closest_z
        return (dx * dx + dy * dy + dz * dz) <= (self.radius * self.radius)


@dataclass
class Box(SpatialRegion):
    """3D axis-aligned box query region.

    Attributes:
        min_x: Minimum X coordinate.
        min_y: Minimum Y coordinate.
        min_z: Minimum Z coordinate.
        max_x: Maximum X coordinate.
        max_y: Maximum Y coordinate.
        max_z: Maximum Z coordinate.
    """

    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a point is within the box.

        Args:
            x: X coordinate of the point.
            y: Y coordinate of the point.
            z: Z coordinate of the point.

        Returns:
            True if the point is inside the box.
        """
        return (
            self.min_x <= x <= self.max_x
            and self.min_y <= y <= self.max_y
            and self.min_z <= z <= self.max_z
        )

    def intersects_bounds(
        self,
        min_corner: Tuple[float, ...],
        max_corner: Tuple[float, ...],
    ) -> bool:
        """Check if this box intersects another axis-aligned box.

        Args:
            min_corner: Minimum corner (min_x, min_y, min_z).
            max_corner: Maximum corner (max_x, max_y, max_z).

        Returns:
            True if the boxes intersect.
        """
        # Handle both 2D and 3D bounds
        min_z = min_corner[2] if len(min_corner) > 2 else 0.0
        max_z = max_corner[2] if len(max_corner) > 2 else 0.0

        return not (
            self.max_x < min_corner[0]
            or self.min_x > max_corner[0]
            or self.max_y < min_corner[1]
            or self.min_y > max_corner[1]
            or self.max_z < min_z
            or self.min_z > max_z
        )


def distance_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two 2D points.

    Args:
        x1: X coordinate of first point.
        y1: Y coordinate of first point.
        x2: X coordinate of second point.
        y2: Y coordinate of second point.

    Returns:
        Euclidean distance between the points.
    """
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


def distance_3d(
    x1: float, y1: float, z1: float, x2: float, y2: float, z2: float
) -> float:
    """Calculate Euclidean distance between two 3D points.

    Args:
        x1: X coordinate of first point.
        y1: Y coordinate of first point.
        z1: Z coordinate of first point.
        x2: X coordinate of second point.
        y2: Y coordinate of second point.
        z2: Z coordinate of second point.

    Returns:
        Euclidean distance between the points.
    """
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def distance_squared_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate squared Euclidean distance between two 2D points.

    Faster than distance_2d() when only comparing distances.

    Args:
        x1: X coordinate of first point.
        y1: Y coordinate of first point.
        x2: X coordinate of second point.
        y2: Y coordinate of second point.

    Returns:
        Squared Euclidean distance between the points.
    """
    dx = x2 - x1
    dy = y2 - y1
    return dx * dx + dy * dy


def distance_squared_3d(
    x1: float, y1: float, z1: float, x2: float, y2: float, z2: float
) -> float:
    """Calculate squared Euclidean distance between two 3D points.

    Faster than distance_3d() when only comparing distances.

    Args:
        x1: X coordinate of first point.
        y1: Y coordinate of first point.
        z1: Z coordinate of first point.
        x2: X coordinate of second point.
        y2: Y coordinate of second point.
        z2: Z coordinate of second point.

    Returns:
        Squared Euclidean distance between the points.
    """
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    return dx * dx + dy * dy + dz * dz
