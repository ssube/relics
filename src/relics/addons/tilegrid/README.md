# Tile Grid Addon

A chunked tile system for building 2D and layered 3D worlds in the Relics ECS framework.

## Overview

The tile grid addon provides:

- **Chunked tile maps**: Organize tiles into chunks for efficient loading/unloading
- **Multiple layers**: Ground, decor, objects with z-ordering
- **Elevation support**: Per-tile elevation values for cliff/step effects
- **Collision data**: Per-tile movement speed multipliers for pathfinding
- **Observer-driven baking**: Automatic dirty tracking when tiles change
- **O(1) chunk lookup**: Materialized index for instant chunk queries

## Quick Start

```python
from relics import World
from relics.addons.tilegrid import (
    ChunkMetadata, TileVisualLayer,
    create_chunk_index, get_tile_at, local_to_index,
)

# Create world and chunk index
world = World()
index = create_chunk_index(world, chunk_size=32)

# Define a chunk prefab
tiles = [1] * (32 * 32)  # 32x32 tiles, all grass (tile index 1)
tiles[local_to_index(5, 5, 32)] = 42  # Special tile at position (5, 5)

world.register_prefab(
    "grass_chunk",
    {
        ChunkMetadata: ChunkMetadata(
            chunk_size=32,
            sprite_sheets=["overworld_tiles"],
            grid_index=(0, 0),
        ),
        TileVisualLayer: TileVisualLayer(
            name="ground",
            tiles=tiles,
            z_order=0,
        ),
    },
)

# Spawn chunks
world.spawn("grass_chunk")
world.tick(0)

# Query tiles by world position
tile = get_tile_at(world, 5.0, 5.0, "ground", index)
print(f"Tile at (5, 5): {tile}")  # Output: 42
```

## Components

### ChunkMetadata

Core metadata for a chunk entity.

```python
from relics.addons.tilegrid import ChunkMetadata

meta = ChunkMetadata(
    chunk_size=32,                    # Tiles per edge (16, 32, 64, 128)
    sprite_sheets=["overworld_tiles"], # Sprite sheet references
    grid_index=(0, 0),                 # Grid position (x, y) or (x, y, z)
)
```

### TileVisualLayer

Visual tile indices for rendering. Multiple visual layers can be added to a chunk.

```python
from relics.addons.tilegrid import TileVisualLayer, EMPTY_TILE

ground = TileVisualLayer(
    name="ground",
    tiles=[1] * 1024,  # 32x32 chunk
    z_order=0,
    affected_by_elevation=True,
)

# Use EMPTY_TILE (-1) for transparent tiles
decor = TileVisualLayer(
    name="decor",
    tiles=[EMPTY_TILE] * 1024,  # All empty
    z_order=1,  # Rendered above ground
)
```

### TileElevationLayer

Per-tile elevation values (0.0-1.0) for vertical offset rendering.

```python
from relics.addons.tilegrid import TileElevationLayer

elevation = [0.0] * 1024
elevation[0] = 1.0  # Corner tile is elevated (cliff)

layer = TileElevationLayer(values=elevation)
```

### TileCollisionLayer

Per-tile movement speed multipliers for collision and pathfinding.

```python
from relics.addons.tilegrid import TileCollisionLayer

collision = [1.0] * 1024  # All normal speed
collision[0] = 0.0   # Impassable wall
collision[10] = 0.5  # Half speed (mud, water)
collision[20] = 1.5  # Speed boost (road)

layer = TileCollisionLayer(values=collision)
```

### BakedChunk

Tracks baking state for rendered textures.

```python
from relics.addons.tilegrid import BakedChunk

baked = BakedChunk(
    visual_texture_id="",    # Set after baking
    elevation_texture_id="",
    collision_texture_id="",
    dirty=True,              # True = needs rebaking
)
```

## Coordinate System

Tiles use **row-major ordering** within chunks:

```
index = y * chunk_size + x
```

### Coordinate Utilities

```python
from relics.addons.tilegrid import (
    world_to_chunk_index,
    world_to_local,
    local_to_index,
    index_to_local,
    chunk_center_from_grid_index,
    validate_tile_coords,
)

# World position -> chunk grid index
grid_x, grid_y = world_to_chunk_index(150.0, 200.0, chunk_size=32)
# (4, 6)

# World position -> local tile coordinates
local_x, local_y = world_to_local(150.0, 200.0, 144.0, 208.0, chunk_size=32)
# (22, 8)

# Local coordinates -> flat array index
index = local_to_index(22, 8, chunk_size=32)
# 8 * 32 + 22 = 278

# Flat index -> local coordinates
x, y = index_to_local(278, chunk_size=32)
# (22, 8)

# Grid index -> chunk center world position
cx, cy = chunk_center_from_grid_index(4, 6, chunk_size=32)
# (144.0, 208.0)

# Validate coordinates (raises InvalidTileIndexError if out of bounds)
validate_tile_coords(22, 8, chunk_size=32)  # OK
validate_tile_coords(50, 8, chunk_size=32)  # Raises!
```

## ChunkIndex

The `ChunkIndex` provides O(1) chunk lookup by grid position.

```python
from relics.addons.tilegrid import create_chunk_index, ChunkIndex

# Create with automatic observer registration
index = create_chunk_index(world, chunk_size=32)

# Or create manually without observer
index = create_chunk_index(world, chunk_size=32, auto_register_observer=False)

# Lookup by grid position
chunk = index.get_chunk_by_grid(0, 0)
if chunk:
    meta = chunk.get_component(ChunkMetadata)

# Lookup by world position
chunk = index.get_chunk_at_world_pos(150.0, 200.0)

# Iterate all chunks
for chunk in index:
    print(chunk.id)

# Count chunks
print(f"Total chunks: {index.count()}")
```

## Baking System

The baking system automatically tracks when chunks need re-rendering.

```python
from relics.addons.tilegrid import setup_baking_observers, BakedChunk

# Register baking observers
observers = setup_baking_observers(world)

# When tiles change, BakedChunk.dirty is set to True automatically

# Game loop: process dirty chunks
for chunk in index:
    if chunk.has_component(BakedChunk):
        baked = chunk.get_component(BakedChunk)
        if baked.dirty:
            # Rebake chunk
            texture_id = bake_chunk_to_texture(chunk)
            baked.visual_texture_id = texture_id
            baked.dirty = False
```

## 3D Support

For layered 3D worlds (e.g., dungeon floors):

```python
# 3D grid index
meta = ChunkMetadata(
    chunk_size=16,
    sprite_sheets=["dungeon_tiles"],
    grid_index=(0, 0, 2),  # Floor 2
)

# Lookup by 3D grid
chunk = index.get_chunk_by_grid_3d(0, 0, 2)

# 3D coordinate utilities
from relics.addons.tilegrid import (
    world_to_chunk_index_3d,
    world_to_local_3d,
    local_to_index_3d,
)

grid = world_to_chunk_index_3d(50.0, 50.0, 40.0, chunk_size=16)
# (3, 3, 2)

local = world_to_local_3d(50.0, 50.0, 40.0, 56.0, 56.0, 40.0, chunk_size=16)
# (2, 2, 8)

index = local_to_index_3d(2, 2, 8, chunk_size=16)
# 8 * 256 + 2 * 16 + 2 = 2082
```

## Exceptions

```python
from relics.addons.tilegrid import (
    TileGridError,
    ChunkNotFoundError,
    LayerNotFoundError,
    InvalidTileIndexError,
)

try:
    tile = get_tile_at(world, x, y, "nonexistent_layer", index)
except LayerNotFoundError:
    print("Layer not found on chunk")

try:
    validate_tile_coords(100, 100, chunk_size=32)
except InvalidTileIndexError:
    print("Coordinates out of bounds")
```

## Performance

- **Chunk lookup**: O(1) via dictionary hash
- **Tile access**: O(1) via flat array index
- **Observer updates**: O(1) per component change
- **Memory**: Tiles stored as flat `List[int]` for cache efficiency

### Recommended Chunk Sizes

| Use Case | Chunk Size | Tiles per Chunk |
|----------|------------|-----------------|
| Small maps | 16x16 | 256 |
| Standard | 32x32 | 1,024 |
| Large/streaming | 64x64 | 4,096 |
| Terrain | 128x128 | 16,384 |

## API Reference

See the module docstrings and `docs/AGENT_GUIDE.md` for complete API documentation.
