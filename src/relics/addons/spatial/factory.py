"""Factory functions for creating spatial indexes.

Provides convenient functions to create and configure spatial indexes
with optional automatic observer registration.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Callable,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    overload,
)

from relics.types import Component

from .components import Position2D, Position3D
from .index import (
    LazySpatialIndex2D,
    MaterializedSpatialIndex2D,
    PositionExtractor2D,
    default_position_extractor_2d,
)
from .observer import create_spatial_observer_2d, create_spatial_observer_3d
from .quadtree import QuadTreeBounds

if TYPE_CHECKING:
    from relics.world import World

    from .index3d import LazySpatialIndex3D, MaterializedSpatialIndex3D
    from .octree import OctreeBounds


# Type alias for 3D position extractor
PositionExtractor3D = Callable[[Component], Tuple[float, float, float]]


def default_position_extractor_3d(component: Component) -> Tuple[float, float, float]:
    """Default position extractor for 3D components.

    Expects component to have x, y, and z attributes.

    Args:
        component: A component with x, y, and z attributes.

    Returns:
        Tuple of (x, y, z) coordinates.
    """
    return (
        getattr(component, "x"),
        getattr(component, "y"),
        getattr(component, "z"),
    )


@overload
def create_spatial_index_2d(
    world: "World",
    *,
    component_type: Type[Component] = Position2D,
    position_extractor: Optional[PositionExtractor2D] = None,
    materialized: Literal[True] = True,
    auto_register_observer: bool = True,
    bounds: QuadTreeBounds,
    max_entities_per_node: int = 8,
    max_depth: int = 8,
) -> MaterializedSpatialIndex2D: ...


@overload
def create_spatial_index_2d(
    world: "World",
    *,
    component_type: Type[Component] = Position2D,
    position_extractor: Optional[PositionExtractor2D] = None,
    materialized: Literal[False],
    auto_register_observer: bool = True,
    bounds: Optional[QuadTreeBounds] = None,
    max_entities_per_node: int = 8,
    max_depth: int = 8,
) -> LazySpatialIndex2D: ...


def create_spatial_index_2d(
    world: "World",
    *,
    component_type: Type[Component] = Position2D,
    position_extractor: Optional[PositionExtractor2D] = None,
    materialized: bool = True,
    auto_register_observer: bool = True,
    bounds: Optional[QuadTreeBounds] = None,
    max_entities_per_node: int = 8,
    max_depth: int = 8,
) -> Union[LazySpatialIndex2D, MaterializedSpatialIndex2D]:
    """Create a 2D spatial index for a World.

    Args:
        world: The World to index.
        component_type: The component type that holds position data.
                       Defaults to Position2D.
        position_extractor: Function to extract (x, y) from the component.
                           Defaults to accessing .x and .y attributes.
        materialized: If True, create a MaterializedSpatialIndex2D using
                     a QuadTree. If False, create a LazySpatialIndex2D.
        auto_register_observer: If True and materialized=True, automatically
                               register an observer to keep the index updated.
        bounds: The spatial bounds for the QuadTree.
               Required if materialized=True.
        max_entities_per_node: QuadTree subdivision threshold.
        max_depth: Maximum QuadTree depth.

    Returns:
        A LazySpatialIndex2D or MaterializedSpatialIndex2D instance.

    Raises:
        ValueError: If materialized=True but bounds is not provided.

    Example:
        >>> from relics.addons.spatial import (
        ...     Position2D, create_spatial_index_2d, QuadTreeBounds
        ... )
        >>> world = World()
        >>> world.register_prefab("enemy", {Position2D: Position2D(x=0, y=0)})
        >>> index = create_spatial_index_2d(
        ...     world,
        ...     bounds=QuadTreeBounds(0, 0, 1000, 1000),
        ... )
        >>> # Index is now ready to use
        >>> for entity in index.query_circle(500, 500, 100):
        ...     print(f"Nearby: {entity.id}")
    """
    extractor = position_extractor or default_position_extractor_2d

    if materialized:
        if bounds is None:
            raise ValueError("bounds is required for materialized spatial index")

        index = MaterializedSpatialIndex2D(
            world=world,
            component_type=component_type,
            bounds=bounds,
            position_extractor=extractor,
            max_entities_per_node=max_entities_per_node,
            max_depth=max_depth,
        )

        if auto_register_observer:
            observer = create_spatial_observer_2d(index, component_type)
            world.observe(observer)

        return index
    else:
        return LazySpatialIndex2D(
            world=world,
            component_type=component_type,
            position_extractor=extractor,
        )


def create_spatial_index_3d(
    world: "World",
    *,
    component_type: Type[Component] = Position3D,
    position_extractor: Optional[PositionExtractor3D] = None,
    materialized: bool = True,
    auto_register_observer: bool = True,
    bounds: Optional["OctreeBounds"] = None,
    max_entities_per_node: int = 8,
    max_depth: int = 8,
) -> Union["LazySpatialIndex3D", "MaterializedSpatialIndex3D"]:
    """Create a 3D spatial index for a World.

    Args:
        world: The World to index.
        component_type: The component type that holds position data.
                       Defaults to Position3D.
        position_extractor: Function to extract (x, y, z) from the component.
                           Defaults to accessing .x, .y, and .z attributes.
        materialized: If True, create a MaterializedSpatialIndex3D using
                     an Octree. If False, create a LazySpatialIndex3D.
        auto_register_observer: If True and materialized=True, automatically
                               register an observer to keep the index updated.
        bounds: The spatial bounds for the Octree.
               Required if materialized=True.
        max_entities_per_node: Octree subdivision threshold.
        max_depth: Maximum Octree depth.

    Returns:
        A LazySpatialIndex3D or MaterializedSpatialIndex3D instance.

    Raises:
        ValueError: If materialized=True but bounds is not provided.

    Example:
        >>> from relics.addons.spatial import (
        ...     Position3D, create_spatial_index_3d, OctreeBounds
        ... )
        >>> world = World()
        >>> world.register_prefab("enemy", {Position3D: Position3D(x=0, y=0, z=0)})
        >>> index = create_spatial_index_3d(
        ...     world,
        ...     bounds=OctreeBounds(0, 0, 0, 1000, 1000, 1000),
        ... )
        >>> # Index is now ready to use
        >>> for entity in index.query_sphere(500, 500, 500, 100):
        ...     print(f"Nearby: {entity.id}")
    """
    # Import here to avoid circular imports
    from .index3d import LazySpatialIndex3D, MaterializedSpatialIndex3D

    extractor = position_extractor or default_position_extractor_3d

    if materialized:
        if bounds is None:
            raise ValueError("bounds is required for materialized spatial index")

        index = MaterializedSpatialIndex3D(
            world=world,
            component_type=component_type,
            bounds=bounds,
            position_extractor=extractor,
            max_entities_per_node=max_entities_per_node,
            max_depth=max_depth,
        )

        if auto_register_observer:
            observer = create_spatial_observer_3d(index, component_type)
            world.observe(observer)

        return index
    else:
        return LazySpatialIndex3D(
            world=world,
            component_type=component_type,
            position_extractor=extractor,
        )
