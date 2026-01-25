"""Tests for NumPy compatibility in scene graph math types."""

import pytest

from relics.addons.scene_graph import (
    NUMPY_AVAILABLE,
    Mat4,
    Quat,
    Vec3,
)


class TestVec3NoNumpy:
    """Tests for Vec3 that don't require numpy."""

    def test_to_tuple(self) -> None:
        """Test to_tuple() conversion."""
        v = Vec3(1.0, 2.0, 3.0)
        result = v.to_tuple()
        assert result == (1.0, 2.0, 3.0)
        assert isinstance(result, tuple)

    def test_from_sequence_list(self) -> None:
        """Test from_sequence() with a list."""
        v = Vec3.from_sequence([1.0, 2.0, 3.0])
        assert v == Vec3(1.0, 2.0, 3.0)

    def test_from_sequence_tuple(self) -> None:
        """Test from_sequence() with a tuple."""
        v = Vec3.from_sequence((4.0, 5.0, 6.0))
        assert v == Vec3(4.0, 5.0, 6.0)

    def test_add_with_list(self) -> None:
        """Test __add__ with a list."""
        v = Vec3(1.0, 2.0, 3.0)
        result = v + [4.0, 5.0, 6.0]
        assert result == Vec3(5.0, 7.0, 9.0)

    def test_add_with_tuple(self) -> None:
        """Test __add__ with a tuple."""
        v = Vec3(1.0, 2.0, 3.0)
        result = v + (4.0, 5.0, 6.0)
        assert result == Vec3(5.0, 7.0, 9.0)

    def test_radd_with_list(self) -> None:
        """Test __radd__ with a list."""
        v = Vec3(1.0, 2.0, 3.0)
        result = [4.0, 5.0, 6.0] + v
        assert result == Vec3(5.0, 7.0, 9.0)

    def test_sub_with_list(self) -> None:
        """Test __sub__ with a list."""
        v = Vec3(5.0, 7.0, 9.0)
        result = v - [1.0, 2.0, 3.0]
        assert result == Vec3(4.0, 5.0, 6.0)

    def test_rsub_with_list(self) -> None:
        """Test __rsub__ with a list."""
        v = Vec3(1.0, 2.0, 3.0)
        result = [5.0, 7.0, 9.0] - v
        assert result == Vec3(4.0, 5.0, 6.0)

    def test_dot_with_list(self) -> None:
        """Test dot() with a list."""
        v = Vec3(1.0, 2.0, 3.0)
        result = v.dot([4.0, 5.0, 6.0])
        assert result == 32.0  # 1*4 + 2*5 + 3*6

    def test_cross_with_list(self) -> None:
        """Test cross() with a list."""
        v = Vec3(1.0, 0.0, 0.0)
        result = v.cross([0.0, 1.0, 0.0])
        assert result == Vec3(0.0, 0.0, 1.0)

    def test_hadamard_with_list(self) -> None:
        """Test hadamard() with a list."""
        v = Vec3(2.0, 3.0, 4.0)
        result = v.hadamard([5.0, 6.0, 7.0])
        assert result == Vec3(10.0, 18.0, 28.0)


class TestQuatNoNumpy:
    """Tests for Quat that don't require numpy."""

    def test_to_tuple(self) -> None:
        """Test to_tuple() conversion."""
        q = Quat(0.1, 0.2, 0.3, 0.9)
        result = q.to_tuple()
        assert result == (0.1, 0.2, 0.3, 0.9)
        assert isinstance(result, tuple)

    def test_from_sequence_list(self) -> None:
        """Test from_sequence() with a list."""
        q = Quat.from_sequence([0.1, 0.2, 0.3, 0.9])
        assert q == Quat(0.1, 0.2, 0.3, 0.9)

    def test_from_sequence_tuple(self) -> None:
        """Test from_sequence() with a tuple."""
        q = Quat.from_sequence((0.0, 0.0, 0.0, 1.0))
        assert q == Quat.identity()

    def test_rotate_vector_with_list(self) -> None:
        """Test rotate_vector() with a list."""
        q = Quat.identity()
        result = q.rotate_vector([1.0, 2.0, 3.0])
        # Identity rotation should not change the vector
        assert abs(result.x - 1.0) < 1e-10
        assert abs(result.y - 2.0) < 1e-10
        assert abs(result.z - 3.0) < 1e-10


class TestMat4NoNumpy:
    """Tests for Mat4 that don't require numpy."""

    def test_to_tuple(self) -> None:
        """Test to_tuple() conversion."""
        m = Mat4.identity()
        result = m.to_tuple()
        assert result == m.data
        assert isinstance(result, tuple)
        assert len(result) == 16

    def test_from_sequence_flat_list(self) -> None:
        """Test from_sequence() with a flat list."""
        data = [
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
        ]
        m = Mat4.from_sequence(data)
        assert m == Mat4.identity()

    def test_from_sequence_nested_list(self) -> None:
        """Test from_sequence() with a nested 4x4 list."""
        data = [
            [1.0, 0.0, 0.0, 5.0],
            [0.0, 1.0, 0.0, 6.0],
            [0.0, 0.0, 1.0, 7.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        m = Mat4.from_sequence(data)
        expected = Mat4.from_translation(Vec3(5.0, 6.0, 7.0))
        assert m == expected

    def test_from_sequence_invalid_length(self) -> None:
        """Test from_sequence() with wrong number of elements."""
        with pytest.raises(ValueError, match="requires 16 elements"):
            Mat4.from_sequence([1.0, 2.0, 3.0])

    def test_transform_point_with_list(self) -> None:
        """Test transform_point() with a list."""
        m = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        result = m.transform_point([1.0, 2.0, 3.0])
        assert result == Vec3(11.0, 22.0, 33.0)

    def test_transform_vector_with_list(self) -> None:
        """Test transform_vector() with a list."""
        m = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        # Vectors are not affected by translation
        result = m.transform_vector([1.0, 2.0, 3.0])
        assert result == Vec3(1.0, 2.0, 3.0)


# Tests requiring numpy
@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestVec3Numpy:
    """Tests for Vec3 with numpy."""

    def test_to_numpy(self) -> None:
        """Test to_numpy() conversion."""
        import numpy as np

        v = Vec3(1.0, 2.0, 3.0)
        arr = v.to_numpy()
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float64
        assert arr.shape == (3,)
        assert list(arr) == [1.0, 2.0, 3.0]

    def test_array_protocol(self) -> None:
        """Test __array__ protocol with np.array()."""
        import numpy as np

        v = Vec3(1.0, 2.0, 3.0)
        arr = np.array(v)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (3,)
        assert list(arr) == [1.0, 2.0, 3.0]

    def test_array_protocol_with_dtype(self) -> None:
        """Test __array__ protocol with custom dtype."""
        import numpy as np

        v = Vec3(1.0, 2.0, 3.0)
        arr = np.array(v, dtype=np.float32)
        assert arr.dtype == np.float32

    def test_from_sequence_numpy_array(self) -> None:
        """Test from_sequence() with a numpy array."""
        import numpy as np

        arr = np.array([1.0, 2.0, 3.0])
        v = Vec3.from_sequence(arr)
        assert v == Vec3(1.0, 2.0, 3.0)

    def test_add_with_numpy_array(self) -> None:
        """Test __add__ with a numpy array."""
        import numpy as np

        v = Vec3(1.0, 2.0, 3.0)
        arr = np.array([4.0, 5.0, 6.0])
        result = v + arr
        assert result == Vec3(5.0, 7.0, 9.0)

    def test_sub_with_numpy_array(self) -> None:
        """Test __sub__ with a numpy array."""
        import numpy as np

        v = Vec3(5.0, 7.0, 9.0)
        arr = np.array([1.0, 2.0, 3.0])
        result = v - arr
        assert result == Vec3(4.0, 5.0, 6.0)

    def test_dot_with_numpy_array(self) -> None:
        """Test dot() with a numpy array."""
        import numpy as np

        v = Vec3(1.0, 2.0, 3.0)
        arr = np.array([4.0, 5.0, 6.0])
        result = v.dot(arr)
        assert result == 32.0

    def test_cross_with_numpy_array(self) -> None:
        """Test cross() with a numpy array."""
        import numpy as np

        v = Vec3(1.0, 0.0, 0.0)
        arr = np.array([0.0, 1.0, 0.0])
        result = v.cross(arr)
        assert result == Vec3(0.0, 0.0, 1.0)

    def test_hadamard_with_numpy_array(self) -> None:
        """Test hadamard() with a numpy array."""
        import numpy as np

        v = Vec3(2.0, 3.0, 4.0)
        arr = np.array([5.0, 6.0, 7.0])
        result = v.hadamard(arr)
        assert result == Vec3(10.0, 18.0, 28.0)

    def test_numpy_linalg_norm(self) -> None:
        """Test using np.linalg.norm on Vec3."""
        import numpy as np

        v = Vec3(3.0, 4.0, 0.0)
        # Via the array protocol
        arr = np.array(v)
        norm = np.linalg.norm(arr)
        assert abs(norm - 5.0) < 1e-10

    def test_numpy_dot(self) -> None:
        """Test using np.dot with Vec3."""
        import numpy as np

        v1 = Vec3(1.0, 2.0, 3.0)
        v2 = Vec3(4.0, 5.0, 6.0)
        result = np.dot(np.array(v1), np.array(v2))
        assert result == 32.0


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestQuatNumpy:
    """Tests for Quat with numpy."""

    def test_to_numpy(self) -> None:
        """Test to_numpy() conversion."""
        import numpy as np

        q = Quat(0.1, 0.2, 0.3, 0.9)
        arr = q.to_numpy()
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float64
        assert arr.shape == (4,)
        assert list(arr) == [0.1, 0.2, 0.3, 0.9]

    def test_array_protocol(self) -> None:
        """Test __array__ protocol with np.array()."""
        import numpy as np

        q = Quat(0.0, 0.0, 0.0, 1.0)
        arr = np.array(q)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (4,)
        assert list(arr) == [0.0, 0.0, 0.0, 1.0]

    def test_array_protocol_with_dtype(self) -> None:
        """Test __array__ protocol with custom dtype."""
        import numpy as np

        q = Quat(0.0, 0.0, 0.0, 1.0)
        arr = np.array(q, dtype=np.float32)
        assert arr.dtype == np.float32

    def test_from_sequence_numpy_array(self) -> None:
        """Test from_sequence() with a numpy array."""
        import numpy as np

        arr = np.array([0.0, 0.0, 0.0, 1.0])
        q = Quat.from_sequence(arr)
        assert q == Quat.identity()

    def test_rotate_vector_with_numpy_array(self) -> None:
        """Test rotate_vector() with a numpy array."""
        import numpy as np

        q = Quat.identity()
        arr = np.array([1.0, 2.0, 3.0])
        result = q.rotate_vector(arr)
        assert abs(result.x - 1.0) < 1e-10
        assert abs(result.y - 2.0) < 1e-10
        assert abs(result.z - 3.0) < 1e-10


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestMat4Numpy:
    """Tests for Mat4 with numpy."""

    def test_to_numpy_flat(self) -> None:
        """Test to_numpy() with flat shape."""
        import numpy as np

        m = Mat4.identity()
        arr = m.to_numpy(shape="flat")
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float64
        assert arr.shape == (16,)

    def test_to_numpy_matrix(self) -> None:
        """Test to_numpy() with matrix shape."""
        import numpy as np

        m = Mat4.identity()
        arr = m.to_numpy(shape="matrix")
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float64
        assert arr.shape == (4, 4)
        # Check diagonal is 1s
        for i in range(4):
            assert arr[i, i] == 1.0

    def test_to_numpy_invalid_shape(self) -> None:
        """Test to_numpy() with invalid shape."""
        m = Mat4.identity()
        with pytest.raises(ValueError, match="must be 'flat' or 'matrix'"):
            m.to_numpy(shape="invalid")  # type: ignore

    def test_array_protocol(self) -> None:
        """Test __array__ protocol with np.array()."""
        import numpy as np

        m = Mat4.identity()
        arr = np.array(m)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (4, 4)

    def test_array_protocol_with_dtype(self) -> None:
        """Test __array__ protocol with custom dtype."""
        import numpy as np

        m = Mat4.identity()
        arr = np.array(m, dtype=np.float32)
        assert arr.dtype == np.float32

    def test_from_sequence_numpy_flat(self) -> None:
        """Test from_sequence() with a flat numpy array."""
        import numpy as np

        arr = np.eye(4).flatten()
        m = Mat4.from_sequence(arr)
        assert m == Mat4.identity()

    def test_from_sequence_numpy_2d(self) -> None:
        """Test from_sequence() with a 2D numpy array."""
        import numpy as np

        arr = np.eye(4)
        arr[0, 3] = 10.0  # Translation X
        arr[1, 3] = 20.0  # Translation Y
        arr[2, 3] = 30.0  # Translation Z
        m = Mat4.from_sequence(arr)
        expected = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        assert m == expected

    def test_transform_point_with_numpy_array(self) -> None:
        """Test transform_point() with a numpy array."""
        import numpy as np

        m = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        arr = np.array([1.0, 2.0, 3.0])
        result = m.transform_point(arr)
        assert result == Vec3(11.0, 22.0, 33.0)

    def test_transform_vector_with_numpy_array(self) -> None:
        """Test transform_vector() with a numpy array."""
        import numpy as np

        m = Mat4.from_translation(Vec3(10.0, 20.0, 30.0))
        arr = np.array([1.0, 2.0, 3.0])
        result = m.transform_vector(arr)
        assert result == Vec3(1.0, 2.0, 3.0)

    def test_numpy_matrix_multiply(self) -> None:
        """Test matrix multiplication compatibility with numpy."""
        import numpy as np

        m = Mat4.from_translation(Vec3(1.0, 2.0, 3.0))
        arr = np.array(m)
        # Multiply with numpy
        result = arr @ arr
        # Should be double translation
        assert result[0, 3] == 2.0
        assert result[1, 3] == 4.0
        assert result[2, 3] == 6.0


@pytest.mark.skipif(NUMPY_AVAILABLE, reason="numpy is installed")
class TestNoNumpyErrors:
    """Tests that proper errors are raised when numpy is not available."""

    def test_vec3_to_numpy_raises(self) -> None:
        """Test Vec3.to_numpy() raises ImportError."""
        v = Vec3(1.0, 2.0, 3.0)
        with pytest.raises(ImportError, match="numpy is required"):
            v.to_numpy()

    def test_vec3_array_raises(self) -> None:
        """Test Vec3.__array__() raises ImportError."""
        v = Vec3(1.0, 2.0, 3.0)
        with pytest.raises(ImportError, match="numpy is required"):
            v.__array__()

    def test_quat_to_numpy_raises(self) -> None:
        """Test Quat.to_numpy() raises ImportError."""
        q = Quat.identity()
        with pytest.raises(ImportError, match="numpy is required"):
            q.to_numpy()

    def test_quat_array_raises(self) -> None:
        """Test Quat.__array__() raises ImportError."""
        q = Quat.identity()
        with pytest.raises(ImportError, match="numpy is required"):
            q.__array__()

    def test_mat4_to_numpy_raises(self) -> None:
        """Test Mat4.to_numpy() raises ImportError."""
        m = Mat4.identity()
        with pytest.raises(ImportError, match="numpy is required"):
            m.to_numpy()

    def test_mat4_array_raises(self) -> None:
        """Test Mat4.__array__() raises ImportError."""
        m = Mat4.identity()
        with pytest.raises(ImportError, match="numpy is required"):
            m.__array__()
