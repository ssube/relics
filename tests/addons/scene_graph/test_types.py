"""Tests for scene graph math types."""

import math

import pytest

from relics.addons.scene_graph.types import Mat4, Quat, Vec3


class TestVec3:
    """Tests for Vec3 type."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        v = Vec3()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_explicit_values(self) -> None:
        """Test explicit value construction."""
        v = Vec3(1.0, 2.0, 3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_immutable(self) -> None:
        """Test that Vec3 is immutable (frozen)."""
        v = Vec3(1.0, 2.0, 3.0)
        with pytest.raises(Exception):  # FrozenInstanceError
            v.x = 5.0  # type: ignore

    def test_addition(self) -> None:
        """Test vector addition."""
        a = Vec3(1.0, 2.0, 3.0)
        b = Vec3(4.0, 5.0, 6.0)
        result = a + b
        assert result.x == 5.0
        assert result.y == 7.0
        assert result.z == 9.0

    def test_subtraction(self) -> None:
        """Test vector subtraction."""
        a = Vec3(4.0, 5.0, 6.0)
        b = Vec3(1.0, 2.0, 3.0)
        result = a - b
        assert result.x == 3.0
        assert result.y == 3.0
        assert result.z == 3.0

    def test_scalar_multiplication(self) -> None:
        """Test scalar multiplication."""
        v = Vec3(1.0, 2.0, 3.0)
        result = v * 2.0
        assert result.x == 2.0
        assert result.y == 4.0
        assert result.z == 6.0

    def test_scalar_rmul(self) -> None:
        """Test reversed scalar multiplication."""
        v = Vec3(1.0, 2.0, 3.0)
        result = 2.0 * v
        assert result.x == 2.0
        assert result.y == 4.0
        assert result.z == 6.0

    def test_negation(self) -> None:
        """Test vector negation."""
        v = Vec3(1.0, -2.0, 3.0)
        result = -v
        assert result.x == -1.0
        assert result.y == 2.0
        assert result.z == -3.0

    def test_dot_product(self) -> None:
        """Test dot product."""
        a = Vec3(1.0, 2.0, 3.0)
        b = Vec3(4.0, 5.0, 6.0)
        result = a.dot(b)
        assert result == 32.0  # 1*4 + 2*5 + 3*6

    def test_cross_product(self) -> None:
        """Test cross product."""
        x = Vec3.unit_x()
        y = Vec3.unit_y()
        z = x.cross(y)
        assert z.x == pytest.approx(0.0)
        assert z.y == pytest.approx(0.0)
        assert z.z == pytest.approx(1.0)

    def test_length(self) -> None:
        """Test vector length."""
        v = Vec3(3.0, 4.0, 0.0)
        assert v.length() == pytest.approx(5.0)

    def test_length_squared(self) -> None:
        """Test squared vector length."""
        v = Vec3(3.0, 4.0, 0.0)
        assert v.length_squared() == pytest.approx(25.0)

    def test_normalized(self) -> None:
        """Test normalization."""
        v = Vec3(3.0, 4.0, 0.0)
        n = v.normalized()
        assert n.length() == pytest.approx(1.0)
        assert n.x == pytest.approx(0.6)
        assert n.y == pytest.approx(0.8)

    def test_normalized_zero_vector(self) -> None:
        """Test normalizing zero vector returns zero."""
        v = Vec3.zero()
        n = v.normalized()
        assert n.x == 0.0
        assert n.y == 0.0
        assert n.z == 0.0

    def test_hadamard_product(self) -> None:
        """Test component-wise multiplication."""
        a = Vec3(2.0, 3.0, 4.0)
        b = Vec3(5.0, 6.0, 7.0)
        result = a.hadamard(b)
        assert result.x == 10.0
        assert result.y == 18.0
        assert result.z == 28.0

    def test_zero_factory(self) -> None:
        """Test zero vector factory."""
        v = Vec3.zero()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_one_factory(self) -> None:
        """Test unit vector factory."""
        v = Vec3.one()
        assert v.x == 1.0
        assert v.y == 1.0
        assert v.z == 1.0

    def test_unit_vectors(self) -> None:
        """Test unit axis vectors."""
        x = Vec3.unit_x()
        y = Vec3.unit_y()
        z = Vec3.unit_z()
        assert x == Vec3(1.0, 0.0, 0.0)
        assert y == Vec3(0.0, 1.0, 0.0)
        assert z == Vec3(0.0, 0.0, 1.0)


class TestQuat:
    """Tests for Quat type."""

    def test_default_identity(self) -> None:
        """Test default values form identity quaternion."""
        q = Quat()
        assert q.x == 0.0
        assert q.y == 0.0
        assert q.z == 0.0
        assert q.w == 1.0

    def test_explicit_values(self) -> None:
        """Test explicit value construction."""
        q = Quat(0.1, 0.2, 0.3, 0.9)
        assert q.x == 0.1
        assert q.y == 0.2
        assert q.z == 0.3
        assert q.w == 0.9

    def test_immutable(self) -> None:
        """Test that Quat is immutable (frozen)."""
        q = Quat(0.0, 0.0, 0.0, 1.0)
        with pytest.raises(Exception):
            q.w = 0.5  # type: ignore

    def test_identity_factory(self) -> None:
        """Test identity quaternion factory."""
        q = Quat.identity()
        assert q.x == 0.0
        assert q.y == 0.0
        assert q.z == 0.0
        assert q.w == 1.0

    def test_hamilton_product_identity(self) -> None:
        """Test that identity * q = q."""
        identity = Quat.identity()
        q = Quat(0.1, 0.2, 0.3, 0.9).normalized()
        result = identity * q
        assert result.x == pytest.approx(q.x)
        assert result.y == pytest.approx(q.y)
        assert result.z == pytest.approx(q.z)
        assert result.w == pytest.approx(q.w)

    def test_hamilton_product(self) -> None:
        """Test Hamilton product."""
        # 90 degree rotation around X axis
        q1 = Quat.from_axis_angle(Vec3.unit_x(), math.pi / 2)
        # 90 degree rotation around Y axis
        q2 = Quat.from_axis_angle(Vec3.unit_y(), math.pi / 2)
        # Combined rotation
        result = q1 * q2
        assert result.normalized().w == pytest.approx(0.5, abs=0.01)

    def test_conjugate(self) -> None:
        """Test quaternion conjugate."""
        q = Quat(0.1, 0.2, 0.3, 0.9)
        c = q.conjugate()
        assert c.x == -0.1
        assert c.y == -0.2
        assert c.z == -0.3
        assert c.w == 0.9

    def test_inverse(self) -> None:
        """Test quaternion inverse."""
        q = Quat(0.1, 0.2, 0.3, 0.9).normalized()
        inv = q.inverse()
        # q * q^-1 should be identity
        result = q * inv
        assert result.x == pytest.approx(0.0, abs=1e-6)
        assert result.y == pytest.approx(0.0, abs=1e-6)
        assert result.z == pytest.approx(0.0, abs=1e-6)
        assert result.w == pytest.approx(1.0, abs=1e-6)

    def test_inverse_zero_quaternion(self) -> None:
        """Test inverse of zero quaternion returns identity."""
        q = Quat(0.0, 0.0, 0.0, 0.0)
        inv = q.inverse()
        assert inv == Quat.identity()

    def test_normalized(self) -> None:
        """Test quaternion normalization."""
        q = Quat(1.0, 2.0, 3.0, 4.0)
        n = q.normalized()
        length = math.sqrt(n.x**2 + n.y**2 + n.z**2 + n.w**2)
        assert length == pytest.approx(1.0)

    def test_normalized_zero(self) -> None:
        """Test normalizing zero quaternion returns identity."""
        q = Quat(0.0, 0.0, 0.0, 0.0)
        n = q.normalized()
        assert n == Quat.identity()

    def test_rotate_vector_identity(self) -> None:
        """Test identity rotation doesn't change vector."""
        q = Quat.identity()
        v = Vec3(1.0, 2.0, 3.0)
        result = q.rotate_vector(v)
        assert result.x == pytest.approx(v.x)
        assert result.y == pytest.approx(v.y)
        assert result.z == pytest.approx(v.z)

    def test_rotate_vector_90_degrees(self) -> None:
        """Test 90 degree rotation around Z axis."""
        q = Quat.from_axis_angle(Vec3.unit_z(), math.pi / 2)
        v = Vec3.unit_x()  # (1, 0, 0)
        result = q.rotate_vector(v)
        # Should become (0, 1, 0)
        assert result.x == pytest.approx(0.0, abs=1e-6)
        assert result.y == pytest.approx(1.0, abs=1e-6)
        assert result.z == pytest.approx(0.0, abs=1e-6)

    def test_from_axis_angle(self) -> None:
        """Test axis-angle to quaternion conversion."""
        # 180 degree rotation around Y
        q = Quat.from_axis_angle(Vec3.unit_y(), math.pi)
        assert q.x == pytest.approx(0.0, abs=1e-6)
        assert q.y == pytest.approx(1.0, abs=1e-6)
        assert q.z == pytest.approx(0.0, abs=1e-6)
        assert q.w == pytest.approx(0.0, abs=1e-6)

    def test_from_euler(self) -> None:
        """Test Euler angles to quaternion conversion."""
        # 90 degrees around X only
        q = Quat.from_euler(math.pi / 2, 0, 0)
        # Rotate unit Y, should become unit Z
        v = Vec3.unit_y()
        result = q.rotate_vector(v)
        assert result.x == pytest.approx(0.0, abs=1e-6)
        assert result.y == pytest.approx(0.0, abs=1e-6)
        assert result.z == pytest.approx(1.0, abs=1e-6)


class TestMat4:
    """Tests for Mat4 type."""

    def test_identity(self) -> None:
        """Test identity matrix factory."""
        m = Mat4.identity()
        # Diagonal should be 1
        assert m.get(0, 0) == 1.0
        assert m.get(1, 1) == 1.0
        assert m.get(2, 2) == 1.0
        assert m.get(3, 3) == 1.0
        # Off-diagonal should be 0
        assert m.get(0, 1) == 0.0
        assert m.get(1, 0) == 0.0

    def test_wrong_size_raises(self) -> None:
        """Test that wrong size data raises ValueError."""
        with pytest.raises(ValueError):
            Mat4((1.0, 2.0, 3.0))  # Only 3 elements

    def test_getitem(self) -> None:
        """Test flat index access."""
        m = Mat4.identity()
        assert m[0] == 1.0  # m00
        assert m[5] == 1.0  # m11
        assert m[15] == 1.0  # m33

    def test_get_row_col(self) -> None:
        """Test row/column access."""
        m = Mat4.identity()
        assert m.get(0, 0) == 1.0
        assert m.get(1, 1) == 1.0
        assert m.get(0, 1) == 0.0

    def test_matrix_multiplication_identity(self) -> None:
        """Test identity * M = M."""
        identity = Mat4.identity()
        translation = Mat4.from_translation(Vec3(1.0, 2.0, 3.0))
        result = identity * translation
        for i in range(16):
            assert result[i] == pytest.approx(translation[i])

    def test_matrix_multiplication(self) -> None:
        """Test matrix multiplication."""
        t1 = Mat4.from_translation(Vec3(1.0, 0.0, 0.0))
        t2 = Mat4.from_translation(Vec3(0.0, 2.0, 0.0))
        result = t1 * t2
        # Translation should combine
        assert result.get(0, 3) == pytest.approx(1.0)
        assert result.get(1, 3) == pytest.approx(2.0)

    def test_transform_point(self) -> None:
        """Test point transformation."""
        m = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        p = Vec3(1.0, 2.0, 3.0)
        result = m.transform_point(p)
        assert result.x == pytest.approx(11.0)
        assert result.y == pytest.approx(22.0)
        assert result.z == pytest.approx(33.0)

    def test_transform_vector(self) -> None:
        """Test vector transformation (ignores translation)."""
        m = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        v = Vec3(1.0, 2.0, 3.0)
        result = m.transform_vector(v)
        # Should NOT be affected by translation
        assert result.x == pytest.approx(1.0)
        assert result.y == pytest.approx(2.0)
        assert result.z == pytest.approx(3.0)

    def test_from_translation(self) -> None:
        """Test translation matrix creation."""
        t = Vec3(5.0, 10.0, 15.0)
        m = Mat4.from_translation(t)
        # Translation stored in last column
        assert m.get(0, 3) == 5.0
        assert m.get(1, 3) == 10.0
        assert m.get(2, 3) == 15.0

    def test_from_rotation(self) -> None:
        """Test rotation matrix creation."""
        q = Quat.from_axis_angle(Vec3.unit_z(), math.pi / 2)
        m = Mat4.from_rotation(q)
        # Rotating unit X should give unit Y
        v = Vec3.unit_x()
        result = m.transform_point(v)
        assert result.x == pytest.approx(0.0, abs=1e-6)
        assert result.y == pytest.approx(1.0, abs=1e-6)
        assert result.z == pytest.approx(0.0, abs=1e-6)

    def test_from_scale(self) -> None:
        """Test scale matrix creation."""
        s = Vec3(2.0, 3.0, 4.0)
        m = Mat4.from_scale(s)
        p = Vec3(1.0, 1.0, 1.0)
        result = m.transform_point(p)
        assert result.x == pytest.approx(2.0)
        assert result.y == pytest.approx(3.0)
        assert result.z == pytest.approx(4.0)

    def test_from_trs(self) -> None:
        """Test TRS matrix creation."""
        t = Vec3(10.0, 0.0, 0.0)
        r = Quat.identity()
        s = Vec3(2.0, 2.0, 2.0)
        m = Mat4.from_trs(t, r, s)

        # Transform origin
        p = Vec3.zero()
        result = m.transform_point(p)
        assert result.x == pytest.approx(10.0)
        assert result.y == pytest.approx(0.0)
        assert result.z == pytest.approx(0.0)

        # Transform unit point
        p2 = Vec3(1.0, 1.0, 1.0)
        result2 = m.transform_point(p2)
        assert result2.x == pytest.approx(12.0)  # 10 + 2*1
        assert result2.y == pytest.approx(2.0)  # 0 + 2*1
        assert result2.z == pytest.approx(2.0)  # 0 + 2*1

    def test_from_trs_with_rotation(self) -> None:
        """Test TRS matrix with rotation."""
        t = Vec3.zero()
        r = Quat.from_axis_angle(Vec3.unit_z(), math.pi / 2)  # 90 deg around Z
        s = Vec3.one()
        m = Mat4.from_trs(t, r, s)

        # Rotating unit X should give unit Y
        p = Vec3.unit_x()
        result = m.transform_point(p)
        assert result.x == pytest.approx(0.0, abs=1e-6)
        assert result.y == pytest.approx(1.0, abs=1e-6)
        assert result.z == pytest.approx(0.0, abs=1e-6)

    def test_immutable(self) -> None:
        """Test that Mat4 is immutable (frozen)."""
        m = Mat4.identity()
        with pytest.raises(Exception):
            m.data = (0.0,) * 16  # type: ignore
