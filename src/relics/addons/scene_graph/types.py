"""Math types for 3D transforms: Vec3, Quat, Mat4."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


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

    def __add__(self, other: "Vec3") -> "Vec3":
        """Add two vectors component-wise."""
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        """Subtract two vectors component-wise."""
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        """Multiply vector by scalar."""
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vec3":
        """Multiply scalar by vector."""
        return self.__mul__(scalar)

    def __neg__(self) -> "Vec3":
        """Negate vector."""
        return Vec3(-self.x, -self.y, -self.z)

    def dot(self, other: "Vec3") -> float:
        """Compute dot product with another vector."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        """Compute cross product with another vector."""
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
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

    def hadamard(self, other: "Vec3") -> "Vec3":
        """Compute Hadamard (component-wise) product."""
        return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)

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

    def rotate_vector(self, v: Vec3) -> Vec3:
        """Rotate a vector by this quaternion.

        Uses the formula: q * v * q^-1 (optimized).

        Args:
            v: Vector to rotate.

        Returns:
            Rotated vector.
        """
        # Optimized quaternion-vector rotation
        # t = 2 * cross(q.xyz, v)
        # v' = v + q.w * t + cross(q.xyz, t)
        qv = Vec3(self.x, self.y, self.z)
        t = qv.cross(v) * 2.0
        return v + t * self.w + qv.cross(t)

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

    def transform_point(self, p: Vec3) -> Vec3:
        """Transform a point (w=1) by this matrix.

        Args:
            p: Point to transform.

        Returns:
            Transformed point.
        """
        x = self.data[0] * p.x + self.data[1] * p.y + self.data[2] * p.z + self.data[3]
        y = self.data[4] * p.x + self.data[5] * p.y + self.data[6] * p.z + self.data[7]
        z = (
            self.data[8] * p.x
            + self.data[9] * p.y
            + self.data[10] * p.z
            + self.data[11]
        )
        return Vec3(x, y, z)

    def transform_vector(self, v: Vec3) -> Vec3:
        """Transform a direction vector (w=0) by this matrix.

        Args:
            v: Vector to transform.

        Returns:
            Transformed vector.
        """
        x = self.data[0] * v.x + self.data[1] * v.y + self.data[2] * v.z
        y = self.data[4] * v.x + self.data[5] * v.y + self.data[6] * v.z
        z = self.data[8] * v.x + self.data[9] * v.y + self.data[10] * v.z
        return Vec3(x, y, z)

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
