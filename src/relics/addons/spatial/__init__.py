"""Spatial indexing addon for the Relics ECS framework.

This module provides efficient spatial queries for entities with position
components. It supports both 2D (QuadTree) and 3D (Octree) spatial indexing
with lazy and materialized implementations.

Basic Usage:
    >>> from relics import World
    >>> from relics.addons.spatial import (
    ...     Position2D, create_spatial_index_2d, QuadTreeBounds
    ... )
    >>>
    >>> world = World()
    >>> world.register_prefab("enemy", {Position2D: Position2D(x=0, y=0)})
    >>>
    >>> # Create index (observer auto-registered for materialized indexes)
    >>> index = create_spatial_index_2d(
    ...     world,
    ...     bounds=QuadTreeBounds(0, 0, 1000, 1000),
    ... )
    >>>
    >>> # Spawn some entities
    >>> for i in range(100):
    ...     world.spawn("enemy", {Position2D: Position2D(x=i*10, y=i*10)})
    >>>
    >>> # Spatial queries
    >>> for entity in index.query_circle(500, 500, 100):
    ...     print(f"Nearby: {entity.id}")

Custom Components:
    >>> from relics.monitored import monitored
    >>> from pydantic.dataclasses import dataclass
    >>>
    >>> @monitored  # Required for change detection
    >>> @dataclass
    >>> class MyPosition(Component):
    ...     pos_x: float
    ...     pos_y: float
    >>>
    >>> index = create_spatial_index_2d(
    ...     world,
    ...     component_type=MyPosition,
    ...     position_extractor=lambda c: (c.pos_x, c.pos_y),
    ...     bounds=QuadTreeBounds(0, 0, 500, 500),
    ... )

3D Spatial Indexing:
    >>> from relics.addons.spatial import (
    ...     Position3D, create_spatial_index_3d, OctreeBounds
    ... )
    >>>
    >>> index_3d = create_spatial_index_3d(
    ...     world,
    ...     bounds=OctreeBounds(0, 0, 0, 1000, 1000, 1000),
    ... )
    >>>
    >>> for entity in index_3d.query_sphere(500, 500, 500, 100):
    ...     print(f"Nearby 3D: {entity.id}")

Combining 2D and 3D Indexes:
    You can apply both 2D and 3D indexes to the same world to provide
    different views of your spatial data. For example, a top-down 2D
    view alongside a full 3D spatial index:

    >>> # 3D position component for full spatial data
    >>> world.register_prefab("ship", {Position3D: Position3D(x=0, y=0, z=0)})
    >>>
    >>> # Full 3D spatial index
    >>> index_3d = create_spatial_index_3d(
    ...     world,
    ...     bounds=OctreeBounds(0, 0, 0, 1000, 1000, 500),
    ... )
    >>>
    >>> # Top-down 2D view (ignoring Z coordinate)
    >>> index_2d = create_spatial_index_2d(
    ...     world,
    ...     component_type=Position3D,
    ...     position_extractor=lambda c: (c.x, c.y),  # Ignore Z
    ...     bounds=QuadTreeBounds(0, 0, 1000, 1000),
    ... )
    >>>
    >>> # Now you can query either index:
    >>> # 3D sphere query for nearby ships in 3D space
    >>> nearby_3d = list(index_3d.query_sphere(500, 500, 250, 100))
    >>> # 2D circle query for ships near a point on the XY plane
    >>> nearby_2d = list(index_2d.query_circle(500, 500, 100))

QueryBuilder Integration:
    >>> # Combine spatial queries with component queries
    >>> nearby_enemies = (
    ...     world.query()
    ...     .with_all([Enemy])
    ...     .with_index(index)  # Uses get_entity_ids() for set intersection
    ...     .execute_entities()
    ... )
"""

# Components
from .components import AABB, Bounds2D, Position2D, Position3D

# Factory functions
from .factory import create_spatial_index_2d, create_spatial_index_3d

# 2D index classes
from .index import (
    LazySpatialIndex2D,
    MaterializedSpatialIndex2D,
    PositionExtractor2D,
    SpatialIndexView2D,
)

# 3D index classes
from .index3d import (
    LazySpatialIndex3D,
    MaterializedSpatialIndex3D,
    PositionExtractor3D,
    SpatialIndexView3D,
)

# Observers
from .observer import (
    SpatialIndexObserver2D,
    SpatialIndexObserver3D,
    create_spatial_observer_2d,
    create_spatial_observer_3d,
)

# Octree
from .octree import Octree, OctreeBounds, OctreeNode

# QuadTree
from .quadtree import QuadTree, QuadTreeBounds, QuadTreeNode

# Query region types
from .types import (
    Box,
    Circle,
    Rectangle,
    Sphere,
    SpatialRegion,
    distance_2d,
    distance_3d,
    distance_squared_2d,
    distance_squared_3d,
)

__all__ = [
    # Components
    "Position2D",
    "Position3D",
    "Bounds2D",
    "AABB",
    # Query regions
    "SpatialRegion",
    "Circle",
    "Rectangle",
    "Sphere",
    "Box",
    # Distance functions
    "distance_2d",
    "distance_3d",
    "distance_squared_2d",
    "distance_squared_3d",
    # QuadTree
    "QuadTree",
    "QuadTreeBounds",
    "QuadTreeNode",
    # Octree
    "Octree",
    "OctreeBounds",
    "OctreeNode",
    # 2D Index
    "SpatialIndexView2D",
    "LazySpatialIndex2D",
    "MaterializedSpatialIndex2D",
    "PositionExtractor2D",
    # 3D Index
    "SpatialIndexView3D",
    "LazySpatialIndex3D",
    "MaterializedSpatialIndex3D",
    "PositionExtractor3D",
    # Observers
    "SpatialIndexObserver2D",
    "SpatialIndexObserver3D",
    "create_spatial_observer_2d",
    "create_spatial_observer_3d",
    # Factory functions
    "create_spatial_index_2d",
    "create_spatial_index_3d",
]
