"""Tests for NumPy compatibility in spatial position components."""

import pytest

from relics.addons.spatial import (
    NUMPY_AVAILABLE,
    Position2D,
    Position3D,
)


class TestPosition2DNoNumpy:
    """Tests for Position2D that don't require numpy."""

    def test_to_tuple(self) -> None:
        """Test to_tuple() conversion."""
        p = Position2D(x=1.0, y=2.0)
        result = p.to_tuple()
        assert result == (1.0, 2.0)
        assert isinstance(result, tuple)

    def test_to_tuple_negative(self) -> None:
        """Test to_tuple() with negative coordinates."""
        p = Position2D(x=-3.5, y=-4.5)
        result = p.to_tuple()
        assert result == (-3.5, -4.5)


class TestPosition3DNoNumpy:
    """Tests for Position3D that don't require numpy."""

    def test_to_tuple(self) -> None:
        """Test to_tuple() conversion."""
        p = Position3D(x=1.0, y=2.0, z=3.0)
        result = p.to_tuple()
        assert result == (1.0, 2.0, 3.0)
        assert isinstance(result, tuple)

    def test_to_tuple_negative(self) -> None:
        """Test to_tuple() with negative coordinates."""
        p = Position3D(x=-1.0, y=-2.0, z=-3.0)
        result = p.to_tuple()
        assert result == (-1.0, -2.0, -3.0)


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestPosition2DNumpy:
    """Tests for Position2D with numpy."""

    def test_to_numpy(self) -> None:
        """Test to_numpy() conversion."""
        import numpy as np

        p = Position2D(x=1.0, y=2.0)
        arr = p.to_numpy()
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float64
        assert arr.shape == (2,)
        assert list(arr) == [1.0, 2.0]

    def test_array_protocol(self) -> None:
        """Test __array__ protocol with np.array()."""
        import numpy as np

        p = Position2D(x=3.0, y=4.0)
        arr = np.array(p)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (2,)
        assert list(arr) == [3.0, 4.0]

    def test_array_protocol_with_dtype(self) -> None:
        """Test __array__ protocol with custom dtype."""
        import numpy as np

        p = Position2D(x=1.0, y=2.0)
        arr = np.array(p, dtype=np.float32)
        assert arr.dtype == np.float32

    def test_from_numpy(self) -> None:
        """Test from_numpy() factory method."""
        import numpy as np

        arr = np.array([5.0, 6.0])
        p = Position2D.from_numpy(arr)
        assert p.x == 5.0
        assert p.y == 6.0

    def test_from_numpy_int_array(self) -> None:
        """Test from_numpy() with integer array."""
        import numpy as np

        arr = np.array([5, 6], dtype=np.int32)
        p = Position2D.from_numpy(arr)
        assert p.x == 5.0
        assert p.y == 6.0

    def test_numpy_linalg_norm(self) -> None:
        """Test using np.linalg.norm on Position2D."""
        import numpy as np

        p = Position2D(x=3.0, y=4.0)
        arr = np.array(p)
        norm = np.linalg.norm(arr)
        assert abs(norm - 5.0) < 1e-10

    def test_numpy_distance(self) -> None:
        """Test computing distance between positions with numpy."""
        import numpy as np

        p1 = Position2D(x=0.0, y=0.0)
        p2 = Position2D(x=3.0, y=4.0)
        distance = np.linalg.norm(np.array(p2) - np.array(p1))
        assert abs(distance - 5.0) < 1e-10

    def test_roundtrip(self) -> None:
        """Test roundtrip conversion Position2D -> numpy -> Position2D."""
        import numpy as np

        original = Position2D(x=1.5, y=2.5)
        arr = np.array(original)
        restored = Position2D.from_numpy(arr)
        assert restored.x == original.x
        assert restored.y == original.y


@pytest.mark.skipif(not NUMPY_AVAILABLE, reason="numpy not installed")
class TestPosition3DNumpy:
    """Tests for Position3D with numpy."""

    def test_to_numpy(self) -> None:
        """Test to_numpy() conversion."""
        import numpy as np

        p = Position3D(x=1.0, y=2.0, z=3.0)
        arr = p.to_numpy()
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float64
        assert arr.shape == (3,)
        assert list(arr) == [1.0, 2.0, 3.0]

    def test_array_protocol(self) -> None:
        """Test __array__ protocol with np.array()."""
        import numpy as np

        p = Position3D(x=4.0, y=5.0, z=6.0)
        arr = np.array(p)
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (3,)
        assert list(arr) == [4.0, 5.0, 6.0]

    def test_array_protocol_with_dtype(self) -> None:
        """Test __array__ protocol with custom dtype."""
        import numpy as np

        p = Position3D(x=1.0, y=2.0, z=3.0)
        arr = np.array(p, dtype=np.float32)
        assert arr.dtype == np.float32

    def test_from_numpy(self) -> None:
        """Test from_numpy() factory method."""
        import numpy as np

        arr = np.array([7.0, 8.0, 9.0])
        p = Position3D.from_numpy(arr)
        assert p.x == 7.0
        assert p.y == 8.0
        assert p.z == 9.0

    def test_from_numpy_int_array(self) -> None:
        """Test from_numpy() with integer array."""
        import numpy as np

        arr = np.array([7, 8, 9], dtype=np.int32)
        p = Position3D.from_numpy(arr)
        assert p.x == 7.0
        assert p.y == 8.0
        assert p.z == 9.0

    def test_numpy_linalg_norm(self) -> None:
        """Test using np.linalg.norm on Position3D."""
        import numpy as np

        p = Position3D(x=1.0, y=2.0, z=2.0)
        arr = np.array(p)
        norm = np.linalg.norm(arr)
        assert abs(norm - 3.0) < 1e-10  # sqrt(1 + 4 + 4) = 3

    def test_numpy_distance(self) -> None:
        """Test computing distance between positions with numpy."""
        import numpy as np

        p1 = Position3D(x=0.0, y=0.0, z=0.0)
        p2 = Position3D(x=1.0, y=2.0, z=2.0)
        distance = np.linalg.norm(np.array(p2) - np.array(p1))
        assert abs(distance - 3.0) < 1e-10

    def test_numpy_dot_product(self) -> None:
        """Test computing dot product with numpy."""
        import numpy as np

        p1 = Position3D(x=1.0, y=2.0, z=3.0)
        p2 = Position3D(x=4.0, y=5.0, z=6.0)
        dot = np.dot(np.array(p1), np.array(p2))
        assert dot == 32.0  # 1*4 + 2*5 + 3*6

    def test_numpy_cross_product(self) -> None:
        """Test computing cross product with numpy."""
        import numpy as np

        p1 = Position3D(x=1.0, y=0.0, z=0.0)
        p2 = Position3D(x=0.0, y=1.0, z=0.0)
        cross = np.cross(np.array(p1), np.array(p2))
        assert cross[0] == 0.0
        assert cross[1] == 0.0
        assert cross[2] == 1.0

    def test_roundtrip(self) -> None:
        """Test roundtrip conversion Position3D -> numpy -> Position3D."""
        import numpy as np

        original = Position3D(x=1.5, y=2.5, z=3.5)
        arr = np.array(original)
        restored = Position3D.from_numpy(arr)
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.z == original.z


@pytest.mark.skipif(NUMPY_AVAILABLE, reason="numpy is installed")
class TestNoNumpyErrors:
    """Tests that proper errors are raised when numpy is not available."""

    def test_position2d_to_numpy_raises(self) -> None:
        """Test Position2D.to_numpy() raises ImportError."""
        p = Position2D(x=1.0, y=2.0)
        with pytest.raises(ImportError, match="numpy is required"):
            p.to_numpy()

    def test_position2d_array_raises(self) -> None:
        """Test Position2D.__array__() raises ImportError."""
        p = Position2D(x=1.0, y=2.0)
        with pytest.raises(ImportError, match="numpy is required"):
            p.__array__()

    def test_position3d_to_numpy_raises(self) -> None:
        """Test Position3D.to_numpy() raises ImportError."""
        p = Position3D(x=1.0, y=2.0, z=3.0)
        with pytest.raises(ImportError, match="numpy is required"):
            p.to_numpy()

    def test_position3d_array_raises(self) -> None:
        """Test Position3D.__array__() raises ImportError."""
        p = Position3D(x=1.0, y=2.0, z=3.0)
        with pytest.raises(ImportError, match="numpy is required"):
            p.__array__()
