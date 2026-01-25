"""Spatial components for 2D and 3D positioning.

These components can be used with spatial indexes for efficient
spatial queries like range searches and nearest-neighbor queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from pydantic.dataclasses import dataclass

from relics.monitored import monitored
from relics.types import Component

# Optional numpy support
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    NUMPY_AVAILABLE = False

if TYPE_CHECKING:
    from numpy.typing import NDArray


@monitored
@dataclass
class Position2D(Component):
    """2D point position component.

    Attributes:
        x: X coordinate.
        y: Y coordinate.
    """

    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple (x, y).

        Returns:
            Tuple of (x, y) coordinates.
        """
        return (self.x, self.y)

    def to_numpy(self) -> "NDArray[np.float64]":
        """Convert to numpy array (like PyTorch's tensor.numpy()).

        Returns:
            1D numpy array with [x, y].

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for to_numpy()")
        return np.array([self.x, self.y], dtype=np.float64)

    def __array__(
        self, dtype: "type | None" = None, copy: "bool | None" = None
    ) -> "NDArray":
        """NumPy array protocol: allows np.array(position).

        Args:
            dtype: Optional dtype for the array.
            copy: Whether to copy. Ignored (always creates new array).

        Returns:
            NumPy array with [x, y].

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for array conversion")
        arr = np.array([self.x, self.y])
        return arr.astype(dtype) if dtype is not None else arr

    @staticmethod
    def from_numpy(arr: "NDArray") -> "Position2D":
        """Create Position2D from numpy array.

        Args:
            arr: Array with at least 2 elements.

        Returns:
            Position2D with coordinates from the array.
        """
        return Position2D(x=float(arr[0]), y=float(arr[1]))


@monitored
@dataclass
class Position3D(Component):
    """3D point position component.

    Attributes:
        x: X coordinate.
        y: Y coordinate.
        z: Z coordinate.
    """

    x: float
    y: float
    z: float

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple (x, y, z).

        Returns:
            Tuple of (x, y, z) coordinates.
        """
        return (self.x, self.y, self.z)

    def to_numpy(self) -> "NDArray[np.float64]":
        """Convert to numpy array (like PyTorch's tensor.numpy()).

        Returns:
            1D numpy array with [x, y, z].

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for to_numpy()")
        return np.array([self.x, self.y, self.z], dtype=np.float64)

    def __array__(
        self, dtype: "type | None" = None, copy: "bool | None" = None
    ) -> "NDArray":
        """NumPy array protocol: allows np.array(position).

        Args:
            dtype: Optional dtype for the array.
            copy: Whether to copy. Ignored (always creates new array).

        Returns:
            NumPy array with [x, y, z].

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for array conversion")
        arr = np.array([self.x, self.y, self.z])
        return arr.astype(dtype) if dtype is not None else arr

    @staticmethod
    def from_numpy(arr: "NDArray") -> "Position3D":
        """Create Position3D from numpy array.

        Args:
            arr: Array with at least 3 elements.

        Returns:
            Position3D with coordinates from the array.
        """
        return Position3D(x=float(arr[0]), y=float(arr[1]), z=float(arr[2]))


@monitored
@dataclass
class Bounds2D(Component):
    """2D bounding box component defined by center and half-extents.

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


@monitored
@dataclass
class AABB(Component):
    """3D axis-aligned bounding box component.

    Defined by center point and half-extents in each dimension.

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
