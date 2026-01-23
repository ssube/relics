"""Exception classes for the Tile Grid addon."""

from relics.errors import RelicError


class TileGridError(RelicError):
    """Base exception for all tile grid errors."""

    pass


class ChunkNotFoundError(TileGridError):
    """No chunk exists at the queried position."""

    pass


class LayerNotFoundError(TileGridError):
    """Chunk does not have the requested layer."""

    pass


class InvalidTileIndexError(TileGridError):
    """Tile coordinates are outside chunk bounds."""

    pass
