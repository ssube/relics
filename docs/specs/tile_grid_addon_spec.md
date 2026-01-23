# Relics: Tile Grid Addon Specification

**Version:** 0.1  
**Status:** Draft  
**Type:** Addon  
**Requires:** Relics ECS Framework, Spatial Index Addon

---

## Overview

The Tile Grid addon provides a chunked tile system for building 2D and layered 3D worlds. Chunks are ECS entities with layer components that store tile data, elevation, and collision information. An observer-driven baking system renders chunks into sprites for display.

This addon is designed for worlds like Dwarf Fortress where multiple z-levels create depth, or simpler 2D tilemaps with optional parallax layering.

---

## Critical Constraint: Addon Architecture

This module MUST be implemented as a standalone addon that does not modify the core Relics codebase.

- Uses the public Relics API for entity creation, components, and observers
- Uses the Spatial Index addon for chunk lookup by position
- Provides its own components, systems, and utilities

---

## Design Goals

1. **Chunked Architecture**: Tiles grouped into cube-shaped chunks for spatial optimization
2. **Layer Components**: Visual, elevation, and collision as separate components per chunk
3. **Extensible Layers**: Custom layer components for game-specific data (temperature, moisture, etc.)
4. **Baking System**: Observer converts tile data into renderable sprites
5. **Engine Agnostic**: Baking outputs data; rendering is the game's responsibility

---

## Core Concepts

### Chunks

Chunks are ECS entities representing a cube of tiles in the world.

- **Shape**: Always cubes (width = height = depth) for octree compatibility
- **Size**: Configurable per world via chunk prefab (e.g., 16³, 32³, 128³)
- **Positioning**: Centered using `Position2D` or `Position3D` components
- **Spatial Index**: Registered in quad/octree for efficient lookup

**Coordinate Example (128³ chunks):**
| Chunk Index | Center Position | World Bounds |
|-------------|-----------------|--------------|
| (0, 0, 0)   | (64, 64, 64)    | 0–128        |
| (1, 0, 0)   | (192, 64, 64)   | 128–256      |
| (0, 1, 0)   | (64, 192, 64)   | 128–256 (y)  |

For 2D worlds, the z-dimension (or y, depending on engine) has size 1, making chunks flat slabs that still use cube math.

### Tiles

Individual cells within a chunk, identified by local coordinates (0 to chunk_size - 1).

- **Tile Index**: Integer reference to a position on a sprite sheet
- **No Per-Tile Entities**: Tiles are data within layer components, not individual entities

### Sprite Sheets

Each chunk references a single sprite sheet (v0.1). Tiles are drawn by index from this sheet.

- Sprite sheet reference stored on the chunk entity
- All visual layers within a chunk share the same sheet
- Prepare for v0.2 by storing as single-item array: `sprite_sheets: [sheet_id]`

---

## Layer Components

Each layer is a separate component attached to a chunk entity. This allows selective querying and independent updates.

### VisualTileLayer

Stores tile indices for rendering. Multiple visual layers per chunk are supported (ground, decor, objects).

```python
@dataclass
class VisualTileLayer(Component):
    name: str                    # e.g., "ground", "decor", "objects"
    tiles: list[int]             # Flat array, row-major order
    z_order: int                 # Render priority within chunk
    affected_by_elevation: bool  # Whether elevation offsets this layer
```

**Tile Array Indexing (2D):**
```
index = y * chunk_width + x
```

**Tile Array Indexing (3D):**
```
index = z * (chunk_width * chunk_height) + y * chunk_width + x
```

A tile index of `-1` or a sentinel value indicates an empty/transparent tile.

### ElevationLayer

Stores per-tile elevation values that offset sprite rendering vertically.

```python
@dataclass
class ElevationLayer(Component):
    values: list[float]  # 0.0–1.0 per tile, same indexing as visual layers
```

**Rendering Effect:**
- Elevation offsets the baseline where sprites are drawn
- Creates cliff/step effects between tiles of different elevation
- v0.2 may render tiles at an angle for slopes

Visual layers with `affected_by_elevation: True` are offset; others (e.g., floating UI elements) can opt out.

### TileCollisionLayer

Stores per-tile movement speed multipliers.

```python
@dataclass
class TileCollisionLayer(Component):
    values: list[float]  # Per-tile speed multiplier
```

**Collision Value Semantics:**
| Value | Meaning |
|-------|---------|
| 0.0   | Impassable (wall) |
| 0.5   | Half speed (mud, water) |
| 1.0   | Full speed (normal ground) |
| > 1.0 | Speed boost (roads, ice) |

### ChunkMetadata

Core chunk information.

```python
@dataclass
class ChunkMetadata(Component):
    chunk_size: int              # Tiles per edge (e.g., 16, 32, 128)
    sprite_sheets: list[str]     # Single item in v0.1, prepared for v0.2
    grid_index: tuple[int, ...]  # (x, y) for 2D or (x, y, z) for 3D
```

---

## Chunk Prefab

Chunks are instantiated from a prefab that defines world-wide settings.

```json
{
  "name": "overworld_chunk",
  "components": {
    "ChunkMetadata": {
      "chunk_size": 32,
      "sprite_sheets": ["overworld_tiles"],
      "grid_index": [0, 0]
    },
    "Position2D": { "x": 0, "y": 0 }
  }
}
```

Different regions can use different prefabs (e.g., `dungeon_chunk` with different sprite sheets) but all chunks in a world MUST share the same `chunk_size`.

---

## Baking System

An observer watches for chunk changes and bakes layer data into renderable textures.

### Trigger Conditions

- Chunk entity created
- Any layer component added or modified
- Manual invalidation request

### Baking Outputs

| Layer | Output | Format |
|-------|--------|--------|
| VisualTileLayer | Sprite texture | RGBA, composited from sprite sheet |
| ElevationLayer | Heightmap texture | Single-channel float (debug only) |
| TileCollisionLayer | Collision texture | Single-channel float (debug only) |

For normal operation, elevation and collision remain as data arrays. Textures are generated only for debug visualization.

### BakedChunk Component

Added to chunk entities after baking.

```python
@dataclass
class BakedChunk(Component):
    visual_texture_id: str       # Reference to baked sprite
    elevation_texture_id: str    # Optional, debug only
    collision_texture_id: str    # Optional, debug only
    dirty: bool                  # True if rebake needed
```

---

## Spatial Queries

The addon uses the existing Spatial Index addon for chunk lookups.

### Find Chunk at Position

```python
def get_chunk_at(world: World, position: Position2D | Position3D) -> Entity | None:
    """Returns the chunk entity containing the given world position."""
    # Uses spatial index query internally
```

### Find Tile at Position

```python
def get_tile_at(
    world: World, 
    position: Position2D | Position3D,
    layer_name: str
) -> int | None:
    """Returns the tile index at the given world position for a specific layer."""
    chunk = get_chunk_at(world, position)
    if chunk is None:
        return None
    local = world_to_local(position, chunk)
    layer = chunk.get_component(VisualTileLayer, name=layer_name)
    return layer.tiles[local_to_index(local, chunk)]
```

### Coordinate Conversion

```python
def world_to_chunk_index(position: Position2D, chunk_size: int) -> tuple[int, int]:
    """Convert world position to chunk grid index."""
    return (int(position.x // chunk_size), int(position.y // chunk_size))

def world_to_local(position: Position2D, chunk: Entity) -> tuple[int, int]:
    """Convert world position to local tile coordinates within a chunk."""
    meta = chunk.get_component(ChunkMetadata)
    pos = chunk.get_component(Position2D)
    half = meta.chunk_size / 2
    local_x = int(position.x - (pos.x - half))
    local_y = int(position.y - (pos.y - half))
    return (local_x, local_y)
```

---

## Version Roadmap

### v0.1 (Current)
- 2D chunks (z-size = 1)
- Single sprite sheet per chunk
- Per-tile collision (TileCollisionLayer)
- Basic elevation with vertical offset
- Observer-based baking

### v0.2 (Planned)
- 3D chunks with full cube dimensions
- Multiple sprite sheets per chunk
- SpriteCollisionLayer (per-pixel collision data)
- PolygonCollisionLayer (converted from sprite collision)
- Angled tile rendering for slopes

---

## Usage Example

```python
from relics import World
from relics_tilegrid import (
    ChunkMetadata, VisualTileLayer, ElevationLayer, 
    TileCollisionLayer, TileGridSystem, get_tile_at
)

# Register the tile grid system
world = World()
world.register_system(TileGridSystem())

# Create a chunk
chunk = world.spawn("overworld_chunk", {
    ChunkMetadata: ChunkMetadata(
        chunk_size=32,
        sprite_sheets=["overworld_tiles"],
        grid_index=(0, 0)
    ),
    Position2D: Position2D(x=512, y=512)  # Centered for 32-tile chunk
})

# Add layers
ground_tiles = [1] * (32 * 32)  # All grass
ground_tiles[0] = 5  # Corner is water
chunk.add_component(VisualTileLayer(
    name="ground",
    tiles=ground_tiles,
    z_order=0,
    affected_by_elevation=True
))

collision = [1.0] * (32 * 32)  # All walkable
collision[0] = 0.5  # Water slows movement
chunk.add_component(TileCollisionLayer(values=collision))

# Query a tile
tile_index = get_tile_at(world, Position2D(x=10, y=10), "ground")
```

---

## Error Handling

```python
class TileGridError(RelicError):
    """Base exception for tile grid errors."""
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
```
