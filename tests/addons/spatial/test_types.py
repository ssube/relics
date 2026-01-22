"""Tests for spatial query region types."""

import math

import pytest

from relics.addons.spatial import (
    Box,
    Circle,
    Rectangle,
    Sphere,
    distance_2d,
    distance_3d,
    distance_squared_2d,
    distance_squared_3d,
)


class TestCircle:
    """Tests for Circle query region."""

    def test_contains_point_inside(self) -> None:
        """Test that points inside the circle are detected."""
        circle = Circle(center_x=0, center_y=0, radius=10)
        assert circle.contains_point(0, 0)
        assert circle.contains_point(5, 0)
        assert circle.contains_point(0, 5)
        assert circle.contains_point(7, 7)  # sqrt(98) < 10

    def test_contains_point_outside(self) -> None:
        """Test that points outside the circle are not detected."""
        circle = Circle(center_x=0, center_y=0, radius=10)
        assert not circle.contains_point(11, 0)
        assert not circle.contains_point(0, 11)
        assert not circle.contains_point(8, 8)  # sqrt(128) > 10

    def test_contains_point_on_boundary(self) -> None:
        """Test that points on the boundary are inside."""
        circle = Circle(center_x=0, center_y=0, radius=10)
        assert circle.contains_point(10, 0)
        assert circle.contains_point(0, 10)

    def test_intersects_bounds_fully_inside(self) -> None:
        """Test intersection when rectangle is fully inside circle."""
        circle = Circle(center_x=50, center_y=50, radius=100)
        assert circle.intersects_bounds((40, 40), (60, 60))

    def test_intersects_bounds_fully_outside(self) -> None:
        """Test no intersection when rectangle is far from circle."""
        circle = Circle(center_x=0, center_y=0, radius=10)
        assert not circle.intersects_bounds((100, 100), (200, 200))

    def test_intersects_bounds_partial_overlap(self) -> None:
        """Test intersection with partial overlap."""
        circle = Circle(center_x=0, center_y=0, radius=10)
        assert circle.intersects_bounds((5, -5), (20, 5))

    def test_intersects_bounds_corner_touch(self) -> None:
        """Test intersection when circle touches rectangle corner."""
        circle = Circle(center_x=0, center_y=0, radius=14.15)  # sqrt(200) approx
        assert circle.intersects_bounds((10, 10), (20, 20))


class TestRectangle:
    """Tests for Rectangle query region."""

    def test_contains_point_inside(self) -> None:
        """Test that points inside the rectangle are detected."""
        rect = Rectangle(min_x=0, min_y=0, max_x=100, max_y=100)
        assert rect.contains_point(50, 50)
        assert rect.contains_point(0, 0)
        assert rect.contains_point(100, 100)

    def test_contains_point_outside(self) -> None:
        """Test that points outside the rectangle are not detected."""
        rect = Rectangle(min_x=0, min_y=0, max_x=100, max_y=100)
        assert not rect.contains_point(-1, 50)
        assert not rect.contains_point(50, -1)
        assert not rect.contains_point(101, 50)
        assert not rect.contains_point(50, 101)

    def test_intersects_bounds_overlapping(self) -> None:
        """Test intersection with overlapping rectangles."""
        rect = Rectangle(min_x=0, min_y=0, max_x=100, max_y=100)
        assert rect.intersects_bounds((50, 50), (150, 150))

    def test_intersects_bounds_no_overlap(self) -> None:
        """Test no intersection with non-overlapping rectangles."""
        rect = Rectangle(min_x=0, min_y=0, max_x=100, max_y=100)
        assert not rect.intersects_bounds((200, 200), (300, 300))

    def test_intersects_bounds_touching_edge(self) -> None:
        """Test intersection when rectangles share an edge."""
        rect = Rectangle(min_x=0, min_y=0, max_x=100, max_y=100)
        assert rect.intersects_bounds((100, 0), (200, 100))

    def test_intersects_bounds_contained(self) -> None:
        """Test intersection when one rectangle contains the other."""
        rect = Rectangle(min_x=0, min_y=0, max_x=100, max_y=100)
        assert rect.intersects_bounds((25, 25), (75, 75))


class TestSphere:
    """Tests for Sphere query region."""

    def test_contains_point_inside(self) -> None:
        """Test that points inside the sphere are detected."""
        sphere = Sphere(center_x=0, center_y=0, center_z=0, radius=10)
        assert sphere.contains_point(0, 0, 0)
        assert sphere.contains_point(5, 0, 0)
        assert sphere.contains_point(0, 5, 0)
        assert sphere.contains_point(0, 0, 5)
        assert sphere.contains_point(5, 5, 5)  # sqrt(75) < 10

    def test_contains_point_outside(self) -> None:
        """Test that points outside the sphere are not detected."""
        sphere = Sphere(center_x=0, center_y=0, center_z=0, radius=10)
        assert not sphere.contains_point(11, 0, 0)
        assert not sphere.contains_point(6, 6, 6)  # sqrt(108) > 10

    def test_intersects_bounds_overlapping(self) -> None:
        """Test intersection with overlapping box."""
        sphere = Sphere(center_x=50, center_y=50, center_z=50, radius=100)
        assert sphere.intersects_bounds((40, 40, 40), (60, 60, 60))

    def test_intersects_bounds_no_overlap(self) -> None:
        """Test no intersection with distant box."""
        sphere = Sphere(center_x=0, center_y=0, center_z=0, radius=10)
        assert not sphere.intersects_bounds((100, 100, 100), (200, 200, 200))


class TestBox:
    """Tests for Box query region."""

    def test_contains_point_inside(self) -> None:
        """Test that points inside the box are detected."""
        box = Box(min_x=0, min_y=0, min_z=0, max_x=100, max_y=100, max_z=100)
        assert box.contains_point(50, 50, 50)
        assert box.contains_point(0, 0, 0)
        assert box.contains_point(100, 100, 100)

    def test_contains_point_outside(self) -> None:
        """Test that points outside the box are not detected."""
        box = Box(min_x=0, min_y=0, min_z=0, max_x=100, max_y=100, max_z=100)
        assert not box.contains_point(-1, 50, 50)
        assert not box.contains_point(50, -1, 50)
        assert not box.contains_point(50, 50, -1)
        assert not box.contains_point(101, 50, 50)

    def test_intersects_bounds_overlapping(self) -> None:
        """Test intersection with overlapping boxes."""
        box = Box(min_x=0, min_y=0, min_z=0, max_x=100, max_y=100, max_z=100)
        assert box.intersects_bounds((50, 50, 50), (150, 150, 150))

    def test_intersects_bounds_no_overlap(self) -> None:
        """Test no intersection with non-overlapping boxes."""
        box = Box(min_x=0, min_y=0, min_z=0, max_x=100, max_y=100, max_z=100)
        assert not box.intersects_bounds((200, 200, 200), (300, 300, 300))

    def test_intersects_bounds_2d_fallback(self) -> None:
        """Test intersection with 2D bounds (no z coordinate)."""
        box = Box(min_x=0, min_y=0, min_z=0, max_x=100, max_y=100, max_z=100)
        # When z is not provided, defaults to 0
        assert box.intersects_bounds((50, 50), (75, 75))


class TestDistanceFunctions:
    """Tests for distance calculation functions."""

    def test_distance_2d_same_point(self) -> None:
        """Test distance between same point is zero."""
        assert distance_2d(0, 0, 0, 0) == 0
        assert distance_2d(100, 200, 100, 200) == 0

    def test_distance_2d_horizontal(self) -> None:
        """Test horizontal distance."""
        assert distance_2d(0, 0, 10, 0) == 10
        assert distance_2d(0, 0, -10, 0) == 10

    def test_distance_2d_vertical(self) -> None:
        """Test vertical distance."""
        assert distance_2d(0, 0, 0, 10) == 10
        assert distance_2d(0, 0, 0, -10) == 10

    def test_distance_2d_diagonal(self) -> None:
        """Test diagonal distance."""
        assert distance_2d(0, 0, 3, 4) == 5  # 3-4-5 triangle
        assert distance_2d(0, 0, 5, 12) == 13  # 5-12-13 triangle

    def test_distance_3d_same_point(self) -> None:
        """Test 3D distance between same point is zero."""
        assert distance_3d(0, 0, 0, 0, 0, 0) == 0

    def test_distance_3d_axis_aligned(self) -> None:
        """Test distance along single axis."""
        assert distance_3d(0, 0, 0, 10, 0, 0) == 10
        assert distance_3d(0, 0, 0, 0, 10, 0) == 10
        assert distance_3d(0, 0, 0, 0, 0, 10) == 10

    def test_distance_3d_diagonal(self) -> None:
        """Test 3D diagonal distance."""
        # sqrt(3^2 + 4^2 + 0^2) = 5
        assert distance_3d(0, 0, 0, 3, 4, 0) == 5
        # sqrt(1^2 + 2^2 + 2^2) = 3
        assert distance_3d(0, 0, 0, 1, 2, 2) == 3

    def test_distance_squared_2d(self) -> None:
        """Test squared distance calculation."""
        assert distance_squared_2d(0, 0, 3, 4) == 25  # 9 + 16
        assert distance_squared_2d(0, 0, 0, 0) == 0

    def test_distance_squared_3d(self) -> None:
        """Test 3D squared distance calculation."""
        assert distance_squared_3d(0, 0, 0, 1, 2, 2) == 9  # 1 + 4 + 4
        assert distance_squared_3d(0, 0, 0, 0, 0, 0) == 0
