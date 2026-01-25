"""Math types for 3D transforms: Vec3, Quat, Mat4."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence, Tuple, Union

# Optional numpy support
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    NUMPY_AVAILABLE = False

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Type aliases for numpy interop
Vec3Like = Union["Vec3", Sequence[float]]
QuatLike = Union["Quat", Sequence[float]]


@dataclass(frozen=True)
class Vec3:
    """3D vector with x, y, z components.

    This is an immutable value type used for positions and scales.

    Attributes:
        x: X component.
        y: Y component.
        z: Z component.
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3Like) -> "Vec3":
        """Add two vectors component-wise."""
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        return Vec3(self.x + other[0], self.y + other[1], self.z + other[2])

    def __radd__(self, other: Sequence[float]) -> "Vec3":
        """Add sequence to vector (reverse)."""
        return Vec3(other[0] + self.x, other[1] + self.y, other[2] + self.z)

    def __sub__(self, other: Vec3Like) -> "Vec3":
        """Subtract two vectors component-wise."""
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        return Vec3(self.x - other[0], self.y - other[1], self.z - other[2])

    def __rsub__(self, other: Sequence[float]) -> "Vec3":
        """Subtract vector from sequence (reverse)."""
        return Vec3(other[0] - self.x, other[1] - self.y, other[2] - self.z)

    def __mul__(self, scalar: float) -> "Vec3":
        """Multiply vector by scalar."""
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vec3":
        """Multiply scalar by vector."""
        return self.__mul__(scalar)

    def __neg__(self) -> "Vec3":
        """Negate vector."""
        return Vec3(-self.x, -self.y, -self.z)

    def dot(self, other: Vec3Like) -> float:
        """Compute dot product with another vector."""
        if isinstance(other, Vec3):
            return self.x * other.x + self.y * other.y + self.z * other.z
        return self.x * other[0] + self.y * other[1] + self.z * other[2]

    def cross(self, other: Vec3Like) -> "Vec3":
        """Compute cross product with another vector."""
        if isinstance(other, Vec3):
            return Vec3(
                self.y * other.z - self.z * other.y,
                self.z * other.x - self.x * other.z,
                self.x * other.y - self.y * other.x,
            )
        return Vec3(
            self.y * other[2] - self.z * other[1],
            self.z * other[0] - self.x * other[2],
            self.x * other[1] - self.y * other[0],
        )

    def length(self) -> float:
        """Compute vector length (magnitude)."""
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def length_squared(self) -> float:
        """Compute squared vector length."""
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> "Vec3":
        """Return normalized (unit length) vector."""
        length = self.length()
        if length < 1e-10:
            return Vec3.zero()
        return Vec3(self.x / length, self.y / length, self.z / length)

    def hadamard(self, other: Vec3Like) -> "Vec3":
        """Compute Hadamard (component-wise) product."""
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        return Vec3(self.x * other[0], self.y * other[1], self.z * other[2])

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple (x, y, z).

        Returns:
            Tuple of (x, y, z) components.
        """
        return (self.x, self.y, self.z)

    def to_numpy(self) -> "NDArray[np.float64]":
        """Convert to numpy array.

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
        """NumPy array protocol: allows np.array(vec).

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
    def from_sequence(seq: Sequence[float]) -> "Vec3":
        """Create Vec3 from a sequence (list, tuple, or numpy array).

        Args:
            seq: Sequence with at least 3 elements.

        Returns:
            Vec3 with components from the sequence.
        """
        return Vec3(float(seq[0]), float(seq[1]), float(seq[2]))

    @staticmethod
    def zero() -> "Vec3":
        """Return zero vector (0, 0, 0)."""
        return Vec3(0.0, 0.0, 0.0)

    @staticmethod
    def one() -> "Vec3":
        """Return unit vector (1, 1, 1)."""
        return Vec3(1.0, 1.0, 1.0)

    @staticmethod
    def unit_x() -> "Vec3":
        """Return X axis unit vector (1, 0, 0)."""
        return Vec3(1.0, 0.0, 0.0)

    @staticmethod
    def unit_y() -> "Vec3":
        """Return Y axis unit vector (0, 1, 0)."""
        return Vec3(0.0, 1.0, 0.0)

    @staticmethod
    def unit_z() -> "Vec3":
        """Return Z axis unit vector (0, 0, 1)."""
        return Vec3(0.0, 0.0, 1.0)


@dataclass(frozen=True)
class Quat:
    """Quaternion for 3D rotations.

    Stored as (x, y, z, w) where w is the scalar component.
    Uses Hamilton product convention.

    Attributes:
        x: X component (imaginary i).
        y: Y component (imaginary j).
        z: Z component (imaginary k).
        w: W component (scalar/real).
    """

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

    def __mul__(self, other: "Quat") -> "Quat":
        """Hamilton product of two quaternions."""
        return Quat(
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
        )

    def conjugate(self) -> "Quat":
        """Return conjugate quaternion (inverse rotation)."""
        return Quat(-self.x, -self.y, -self.z, self.w)

    def inverse(self) -> "Quat":
        """Return inverse quaternion."""
        norm_sq = self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w
        if norm_sq < 1e-10:
            return Quat.identity()
        inv_norm = 1.0 / norm_sq
        return Quat(
            -self.x * inv_norm,
            -self.y * inv_norm,
            -self.z * inv_norm,
            self.w * inv_norm,
        )

    def normalized(self) -> "Quat":
        """Return normalized quaternion."""
        norm = math.sqrt(
            self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w
        )
        if norm < 1e-10:
            return Quat.identity()
        inv_norm = 1.0 / norm
        return Quat(
            self.x * inv_norm,
            self.y * inv_norm,
            self.z * inv_norm,
            self.w * inv_norm,
        )

    def rotate_vector(self, v: Vec3Like) -> Vec3:
        """Rotate a vector by this quaternion.

        Uses the formula: q * v * q^-1 (optimized).

        Args:
            v: Vector to rotate (Vec3 or sequence).

        Returns:
            Rotated vector.
        """
        # Convert to Vec3 if needed
        if not isinstance(v, Vec3):
            v = Vec3.from_sequence(v)
        # Optimized quaternion-vector rotation
        # t = 2 * cross(q.xyz, v)
        # v' = v + q.w * t + cross(q.xyz, t)
        qv = Vec3(self.x, self.y, self.z)
        t = qv.cross(v) * 2.0
        return v + t * self.w + qv.cross(t)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Convert to tuple (x, y, z, w).

        Returns:
            Tuple of (x, y, z, w) components.
        """
        return (self.x, self.y, self.z, self.w)

    def to_numpy(self) -> "NDArray[np.float64]":
        """Convert to numpy array.

        Returns:
            1D numpy array with [x, y, z, w].

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for to_numpy()")
        return np.array([self.x, self.y, self.z, self.w], dtype=np.float64)

    def __array__(
        self, dtype: "type | None" = None, copy: "bool | None" = None
    ) -> "NDArray":
        """NumPy array protocol: allows np.array(quat).

        Args:
            dtype: Optional dtype for the array.
            copy: Whether to copy. Ignored (always creates new array).

        Returns:
            NumPy array with [x, y, z, w].

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for array conversion")
        arr = np.array([self.x, self.y, self.z, self.w])
        return arr.astype(dtype) if dtype is not None else arr

    @staticmethod
    def from_sequence(seq: Sequence[float]) -> "Quat":
        """Create Quat from a sequence (list, tuple, or numpy array).

        Args:
            seq: Sequence with at least 4 elements [x, y, z, w].

        Returns:
            Quat with components from the sequence.
        """
        return Quat(float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))

    @staticmethod
    def identity() -> "Quat":
        """Return identity quaternion (no rotation)."""
        return Quat(0.0, 0.0, 0.0, 1.0)

    @staticmethod
    def from_axis_angle(axis: Vec3, angle: float) -> "Quat":
        """Create quaternion from axis-angle representation.

        Args:
            axis: Rotation axis (should be normalized).
            angle: Rotation angle in radians.

        Returns:
            Quaternion representing the rotation.
        """
        half_angle = angle * 0.5
        s = math.sin(half_angle)
        return Quat(
            axis.x * s,
            axis.y * s,
            axis.z * s,
            math.cos(half_angle),
        )

    @staticmethod
    def from_euler(x: float, y: float, z: float) -> "Quat":
        """Create quaternion from Euler angles (XYZ order).

        Args:
            x: Rotation around X axis in radians.
            y: Rotation around Y axis in radians.
            z: Rotation around Z axis in radians.

        Returns:
            Quaternion representing the combined rotation.
        """
        cx = math.cos(x * 0.5)
        sx = math.sin(x * 0.5)
        cy = math.cos(y * 0.5)
        sy = math.sin(y * 0.5)
        cz = math.cos(z * 0.5)
        sz = math.sin(z * 0.5)

        return Quat(
            sx * cy * cz - cx * sy * sz,
            cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz,
            cx * cy * cz + sx * sy * sz,
        )


@dataclass(frozen=True)
class Mat4:
    """4x4 transformation matrix stored in row-major order.

    The 16 elements are stored as a tuple for immutability.
    Matrix layout:
        [m00, m01, m02, m03]
        [m10, m11, m12, m13]
        [m20, m21, m22, m23]
        [m30, m31, m32, m33]

    Where m03, m13, m23 are translation components.

    Attributes:
        data: Tuple of 16 floats in row-major order.
    """

    data: Tuple[
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
        float,
    ]

    def __post_init__(self) -> None:
        """Validate data length."""
        if len(self.data) != 16:
            raise ValueError(f"Mat4 requires 16 elements, got {len(self.data)}")

    def __getitem__(self, index: int) -> float:
        """Get element by flat index."""
        return self.data[index]

    def get(self, row: int, col: int) -> float:
        """Get element by row and column."""
        return self.data[row * 4 + col]

    def __mul__(self, other: "Mat4") -> "Mat4":
        """Matrix multiplication."""
        result = []
        for row in range(4):
            for col in range(4):
                val = 0.0
                for k in range(4):
                    val += self.get(row, k) * other.get(k, col)
                result.append(val)
        return Mat4(tuple(result))  # type: ignore[arg-type]

    def transform_point(self, p: Vec3Like) -> Vec3:
        """Transform a point (w=1) by this matrix.

        Args:
            p: Point to transform (Vec3 or sequence).

        Returns:
            Transformed point.
        """
        if isinstance(p, Vec3):
            px, py, pz = p.x, p.y, p.z
        else:
            px, py, pz = p[0], p[1], p[2]
        x = self.data[0] * px + self.data[1] * py + self.data[2] * pz + self.data[3]
        y = self.data[4] * px + self.data[5] * py + self.data[6] * pz + self.data[7]
        z = self.data[8] * px + self.data[9] * py + self.data[10] * pz + self.data[11]
        return Vec3(x, y, z)

    def transform_vector(self, v: Vec3Like) -> Vec3:
        """Transform a direction vector (w=0) by this matrix.

        Args:
            v: Vector to transform (Vec3 or sequence).

        Returns:
            Transformed vector.
        """
        if isinstance(v, Vec3):
            vx, vy, vz = v.x, v.y, v.z
        else:
            vx, vy, vz = v[0], v[1], v[2]
        x = self.data[0] * vx + self.data[1] * vy + self.data[2] * vz
        y = self.data[4] * vx + self.data[5] * vy + self.data[6] * vz
        z = self.data[8] * vx + self.data[9] * vy + self.data[10] * vz
        return Vec3(x, y, z)

    def to_tuple(self) -> Tuple[float, ...]:
        """Convert to tuple (same as data attribute).

        Returns:
            Tuple of 16 floats in row-major order.
        """
        return self.data

    def to_numpy(self, shape: str = "flat") -> "NDArray[np.float64]":
        """Convert to numpy array.

        Args:
            shape: "flat" for 1D array of 16 elements, "matrix" for 4x4 2D array.

        Returns:
            NumPy array with matrix data.

        Raises:
            ImportError: If numpy is not installed.
            ValueError: If shape is not "flat" or "matrix".
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for to_numpy()")
        if shape == "flat":
            return np.array(self.data, dtype=np.float64)
        elif shape == "matrix":
            return np.array(self.data, dtype=np.float64).reshape(4, 4)
        else:
            raise ValueError(f"shape must be 'flat' or 'matrix', got '{shape}'")

    def __array__(
        self, dtype: "type | None" = None, copy: "bool | None" = None
    ) -> "NDArray":
        """NumPy array protocol: allows np.array(mat).

        Returns a 4x4 matrix (more useful for matrix operations).

        Args:
            dtype: Optional dtype for the array.
            copy: Whether to copy. Ignored (always creates new array).

        Returns:
            4x4 NumPy array.

        Raises:
            ImportError: If numpy is not installed.
        """
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required for array conversion")
        arr = np.array(self.data).reshape(4, 4)
        return arr.astype(dtype) if dtype is not None else arr

    @staticmethod
    def from_sequence(seq: Sequence[float]) -> "Mat4":
        """Create Mat4 from a flat sequence or nested 4x4 sequence.

        Args:
            seq: Flat sequence of 16 elements or nested 4x4 sequence.

        Returns:
            Mat4 with data from the sequence.

        Raises:
            ValueError: If sequence doesn't have correct dimensions.
        """
        # Check if it's a nested sequence (4x4)
        if hasattr(seq, "__len__") and len(seq) == 4:
            first = seq[0]
            if hasattr(first, "__len__") and len(first) == 4:
                # Nested 4x4 sequence - flatten it
                flat = []
                for row in seq:
                    for val in row:  # type: ignore[attr-defined]
                        flat.append(float(val))
                return Mat4(tuple(flat))  # type: ignore[arg-type]
        # Flat sequence
        if len(seq) != 16:
            raise ValueError(f"Mat4 requires 16 elements, got {len(seq)}")
        return Mat4(tuple(float(v) for v in seq))  # type: ignore[arg-type]

    @staticmethod
    def identity() -> "Mat4":
        """Return identity matrix."""
        return Mat4(
            (
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
            )
        )

    @staticmethod
    def from_translation(t: Vec3) -> "Mat4":
        """Create translation matrix.

        Args:
            t: Translation vector.

        Returns:
            Translation matrix.
        """
        return Mat4(
            (
                1.0,
                0.0,
                0.0,
                t.x,
                0.0,
                1.0,
                0.0,
                t.y,
                0.0,
                0.0,
                1.0,
                t.z,
                0.0,
                0.0,
                0.0,
                1.0,
            )
        )

    @staticmethod
    def from_rotation(q: Quat) -> "Mat4":
        """Create rotation matrix from quaternion.

        Args:
            q: Rotation quaternion.

        Returns:
            Rotation matrix.
        """
        xx = q.x * q.x
        xy = q.x * q.y
        xz = q.x * q.z
        xw = q.x * q.w
        yy = q.y * q.y
        yz = q.y * q.z
        yw = q.y * q.w
        zz = q.z * q.z
        zw = q.z * q.w

        return Mat4(
            (
                1.0 - 2.0 * (yy + zz),
                2.0 * (xy - zw),
                2.0 * (xz + yw),
                0.0,
                2.0 * (xy + zw),
                1.0 - 2.0 * (xx + zz),
                2.0 * (yz - xw),
                0.0,
                2.0 * (xz - yw),
                2.0 * (yz + xw),
                1.0 - 2.0 * (xx + yy),
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
            )
        )

    @staticmethod
    def from_scale(s: Vec3) -> "Mat4":
        """Create scale matrix.

        Args:
            s: Scale vector.

        Returns:
            Scale matrix.
        """
        return Mat4(
            (
                s.x,
                0.0,
                0.0,
                0.0,
                0.0,
                s.y,
                0.0,
                0.0,
                0.0,
                0.0,
                s.z,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
            )
        )

    @staticmethod
    def from_trs(translation: Vec3, rotation: Quat, scale: Vec3) -> "Mat4":
        """Create TRS (translation * rotation * scale) matrix.

        Args:
            translation: Translation vector.
            rotation: Rotation quaternion.
            scale: Scale vector.

        Returns:
            Combined transformation matrix.
        """
        # Compute rotation matrix elements
        xx = rotation.x * rotation.x
        xy = rotation.x * rotation.y
        xz = rotation.x * rotation.z
        xw = rotation.x * rotation.w
        yy = rotation.y * rotation.y
        yz = rotation.y * rotation.z
        yw = rotation.y * rotation.w
        zz = rotation.z * rotation.z
        zw = rotation.z * rotation.w

        # Rotation matrix (3x3)
        r00 = 1.0 - 2.0 * (yy + zz)
        r01 = 2.0 * (xy - zw)
        r02 = 2.0 * (xz + yw)
        r10 = 2.0 * (xy + zw)
        r11 = 1.0 - 2.0 * (xx + zz)
        r12 = 2.0 * (yz - xw)
        r20 = 2.0 * (xz - yw)
        r21 = 2.0 * (yz + xw)
        r22 = 1.0 - 2.0 * (xx + yy)

        # Apply scale to rotation
        return Mat4(
            (
                r00 * scale.x,
                r01 * scale.y,
                r02 * scale.z,
                translation.x,
                r10 * scale.x,
                r11 * scale.y,
                r12 * scale.z,
                translation.y,
                r20 * scale.x,
                r21 * scale.y,
                r22 * scale.z,
                translation.z,
                0.0,
                0.0,
                0.0,
                1.0,
            )
        )
