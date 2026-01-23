"""Tests for tile grid types and constants."""

from relics.addons.tilegrid import EMPTY_TILE, LayerName, TileIndex


class TestEmptyTile:
    """Tests for EMPTY_TILE constant."""

    def test_empty_tile_value(self) -> None:
        """Test that EMPTY_TILE is -1."""
        assert EMPTY_TILE == -1

    def test_empty_tile_is_int(self) -> None:
        """Test that EMPTY_TILE is an integer."""
        assert isinstance(EMPTY_TILE, int)


class TestTypeAliases:
    """Tests for type alias existence."""

    def test_tile_index_is_int(self) -> None:
        """Test that TileIndex is an alias for int."""
        # TileIndex should accept integers
        tile: TileIndex = 5
        assert tile == 5

    def test_layer_name_is_str(self) -> None:
        """Test that LayerName is an alias for str."""
        # LayerName should accept strings
        name: LayerName = "ground"
        assert name == "ground"
