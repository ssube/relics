"""Tests for spatial components."""

import pytest

from relics.addons.spatial import AABB, Bounds2D, Position2D, Position3D
from relics.monitored import is_monitored


class TestPosition2D:
    """Tests for Position2D component."""

    def test_create_position2d(self) -> None:
        """Test creating a Position2D component."""
        pos = Position2D(x=10.5, y=20.3)
        assert pos.x == 10.5
        assert pos.y == 20.3

    def test_position2d_is_monitored(self) -> None:
        """Test that Position2D has the @monitored decorator."""
        assert is_monitored(Position2D)

    def test_position2d_default_values(self) -> None:
        """Test Position2D requires explicit values."""
        # Position2D doesn't have defaults, so this should fail with validation error
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            Position2D()  # type: ignore


class TestPosition3D:
    """Tests for Position3D component."""

    def test_create_position3d(self) -> None:
        """Test creating a Position3D component."""
        pos = Position3D(x=10.5, y=20.3, z=30.7)
        assert pos.x == 10.5
        assert pos.y == 20.3
        assert pos.z == 30.7

    def test_position3d_is_monitored(self) -> None:
        """Test that Position3D has the @monitored decorator."""
        assert is_monitored(Position3D)


class TestBounds2D:
    """Tests for Bounds2D component."""

    def test_create_bounds2d(self) -> None:
        """Test creating a Bounds2D component."""
        bounds = Bounds2D(center_x=50, center_y=50, half_width=25, half_height=15)
        assert bounds.center_x == 50
        assert bounds.center_y == 50
        assert bounds.half_width == 25
        assert bounds.half_height == 15

    def test_bounds2d_min_max_properties(self) -> None:
        """Test Bounds2D min/max coordinate properties."""
        bounds = Bounds2D(center_x=100, center_y=200, half_width=50, half_height=30)
        assert bounds.min_x == 50
        assert bounds.max_x == 150
        assert bounds.min_y == 170
        assert bounds.max_y == 230

    def test_bounds2d_is_monitored(self) -> None:
        """Test that Bounds2D has the @monitored decorator."""
        assert is_monitored(Bounds2D)


class TestAABB:
    """Tests for AABB (3D bounding box) component."""

    def test_create_aabb(self) -> None:
        """Test creating an AABB component."""
        aabb = AABB(
            center_x=50,
            center_y=50,
            center_z=50,
            half_width=25,
            half_height=15,
            half_depth=10,
        )
        assert aabb.center_x == 50
        assert aabb.center_y == 50
        assert aabb.center_z == 50
        assert aabb.half_width == 25
        assert aabb.half_height == 15
        assert aabb.half_depth == 10

    def test_aabb_min_max_properties(self) -> None:
        """Test AABB min/max coordinate properties."""
        aabb = AABB(
            center_x=100,
            center_y=200,
            center_z=300,
            half_width=50,
            half_height=30,
            half_depth=20,
        )
        assert aabb.min_x == 50
        assert aabb.max_x == 150
        assert aabb.min_y == 170
        assert aabb.max_y == 230
        assert aabb.min_z == 280
        assert aabb.max_z == 320

    def test_aabb_is_monitored(self) -> None:
        """Test that AABB has the @monitored decorator."""
        assert is_monitored(AABB)
