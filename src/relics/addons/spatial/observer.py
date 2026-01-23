"""Spatial index observers for automatic updates.

These observers automatically update materialized spatial indexes
when entity positions change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Type, cast

from relics.observer import ComponentObserver
from relics.types import Component

if TYPE_CHECKING:
    from relics.entity import Entity

    from .index import MaterializedSpatialIndex2D
    from .index3d import MaterializedSpatialIndex3D


class SpatialIndexObserver2D(ComponentObserver):
    """Observer that automatically updates a 2D spatial index.

    Watches for component additions, changes, and removals to keep
    a MaterializedSpatialIndex2D synchronized with entity positions.

    Note: For change detection to work, the position component must
    use the @monitored decorator.

    Attributes:
        component_type: Set dynamically to match the spatial index.
        spatial_index: The MaterializedSpatialIndex2D to update.
    """

    component_type: ClassVar[Type[Component]]

    def __init__(self, spatial_index: "MaterializedSpatialIndex2D") -> None:
        """Create a spatial index observer.

        Args:
            spatial_index: The spatial index to keep updated.
        """
        super().__init__()
        self._spatial_index = spatial_index

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition by adding entity to spatial index.

        Also binds monitored components to the world for change tracking.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        # Bind monitored components to world for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)
        self._spatial_index.add_entity(entity.id)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle component change by updating entity in spatial index.

        Args:
            entity: The entity whose component changed.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: The previous value of the field.
            new_value: The new value of the field.
        """
        self._spatial_index.update(entity.id)

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal by removing entity from spatial index.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        self._spatial_index.remove_entity(entity.id)


def create_spatial_observer_2d(
    spatial_index: "MaterializedSpatialIndex2D",
    component_type: Type[Component],
) -> SpatialIndexObserver2D:
    """Create a spatial index observer for a specific component type.

    Creates a new observer class with the component_type set dynamically,
    then instantiates it with the given spatial index.

    Args:
        spatial_index: The spatial index to keep updated.
        component_type: The component type to watch.

    Returns:
        A configured SpatialIndexObserver2D instance.
    """
    # Create a dynamic subclass with the component_type set
    observer_class = type(
        f"SpatialIndexObserver2D_{component_type.__name__}",
        (SpatialIndexObserver2D,),
        {"component_type": component_type},
    )
    return cast(SpatialIndexObserver2D, observer_class(spatial_index))


class SpatialIndexObserver3D(ComponentObserver):
    """Observer that automatically updates a 3D spatial index.

    Watches for component additions, changes, and removals to keep
    a MaterializedSpatialIndex3D synchronized with entity positions.

    Note: For change detection to work, the position component must
    use the @monitored decorator.

    Attributes:
        component_type: Set dynamically to match the spatial index.
        spatial_index: The MaterializedSpatialIndex3D to update.
    """

    component_type: ClassVar[Type[Component]]

    def __init__(self, spatial_index: "MaterializedSpatialIndex3D") -> None:
        """Create a spatial index observer.

        Args:
            spatial_index: The spatial index to keep updated.
        """
        super().__init__()
        self._spatial_index = spatial_index

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition by adding entity to spatial index.

        Also binds monitored components to the world for change tracking.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        # Bind monitored components to world for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)
        self._spatial_index.add_entity(entity.id)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle component change by updating entity in spatial index.

        Args:
            entity: The entity whose component changed.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: The previous value of the field.
            new_value: The new value of the field.
        """
        self._spatial_index.update(entity.id)

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal by removing entity from spatial index.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        self._spatial_index.remove_entity(entity.id)


def create_spatial_observer_3d(
    spatial_index: "MaterializedSpatialIndex3D",
    component_type: Type[Component],
) -> SpatialIndexObserver3D:
    """Create a spatial index observer for a specific 3D component type.

    Creates a new observer class with the component_type set dynamically,
    then instantiates it with the given spatial index.

    Args:
        spatial_index: The spatial index to keep updated.
        component_type: The component type to watch.

    Returns:
        A configured SpatialIndexObserver3D instance.
    """
    # Create a dynamic subclass with the component_type set
    observer_class = type(
        f"SpatialIndexObserver3D_{component_type.__name__}",
        (SpatialIndexObserver3D,),
        {"component_type": component_type},
    )
    return cast(SpatialIndexObserver3D, observer_class(spatial_index))
