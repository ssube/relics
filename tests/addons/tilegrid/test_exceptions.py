"""Tests for tile grid exceptions."""

import pytest

from relics.addons.tilegrid import (
    ChunkNotFoundError,
    InvalidTileIndexError,
    LayerNotFoundError,
    TileGridError,
)
from relics.errors import RelicError


class TestTileGridError:
    """Tests for TileGridError base exception."""

    def test_inherits_from_relic_error(self) -> None:
        """Test that TileGridError inherits from RelicError."""
        assert issubclass(TileGridError, RelicError)

    def test_raise_tile_grid_error(self) -> None:
        """Test raising TileGridError with a message."""
        with pytest.raises(TileGridError) as exc_info:
            raise TileGridError("Test error message")
        assert str(exc_info.value) == "Test error message"


class TestChunkNotFoundError:
    """Tests for ChunkNotFoundError."""

    def test_inherits_from_tile_grid_error(self) -> None:
        """Test that ChunkNotFoundError inherits from TileGridError."""
        assert issubclass(ChunkNotFoundError, TileGridError)

    def test_raise_chunk_not_found_error(self) -> None:
        """Test raising ChunkNotFoundError with a message."""
        with pytest.raises(ChunkNotFoundError) as exc_info:
            raise ChunkNotFoundError("No chunk at position (5, 10)")
        assert "No chunk at position (5, 10)" in str(exc_info.value)


class TestLayerNotFoundError:
    """Tests for LayerNotFoundError."""

    def test_inherits_from_tile_grid_error(self) -> None:
        """Test that LayerNotFoundError inherits from TileGridError."""
        assert issubclass(LayerNotFoundError, TileGridError)

    def test_raise_layer_not_found_error(self) -> None:
        """Test raising LayerNotFoundError with a message."""
        with pytest.raises(LayerNotFoundError) as exc_info:
            raise LayerNotFoundError("Layer 'ground' not found")
        assert "Layer 'ground' not found" in str(exc_info.value)


class TestInvalidTileIndexError:
    """Tests for InvalidTileIndexError."""

    def test_inherits_from_tile_grid_error(self) -> None:
        """Test that InvalidTileIndexError inherits from TileGridError."""
        assert issubclass(InvalidTileIndexError, TileGridError)

    def test_raise_invalid_tile_index_error(self) -> None:
        """Test raising InvalidTileIndexError with a message."""
        with pytest.raises(InvalidTileIndexError) as exc_info:
            raise InvalidTileIndexError("Tile (50, 50) outside bounds (0-31)")
        assert "Tile (50, 50) outside bounds (0-31)" in str(exc_info.value)
