"""Observers for automatic chunk index updates and baking triggers.

These observers automatically update the ChunkIndex when ChunkMetadata
changes and mark chunks dirty when layer components are modified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Type, cast

from relics.observer import ComponentObserver
from relics.types import Component

from .components import (
    BakedChunk,
    ChunkMetadata,
    TileElevationLayer,
    TileCollisionLayer,
    TileVisualLayer,
)

if TYPE_CHECKING:
    from relics.entity import Entity

    from .index import ChunkIndex


class ChunkIndexObserver(ComponentObserver):
    """Observer that automatically updates a ChunkIndex.

    Watches for ChunkMetadata additions, changes, and removals to keep
    the ChunkIndex synchronized with chunk entities.

    Attributes:
        component_type: Set to ChunkMetadata.
        chunk_index: The ChunkIndex to update.
    """

    component_type: ClassVar[Type[Component]] = ChunkMetadata

    def __init__(self, chunk_index: "ChunkIndex") -> None:
        """Create a chunk index observer.

        Args:
            chunk_index: The chunk index to keep updated.
        """
        super().__init__()
        self._chunk_index = chunk_index

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition by adding entity to chunk index.

        Also binds monitored components for change tracking.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        # Bind monitored components to world for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)
        self._chunk_index.add_chunk(entity.id)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle component change by updating entity in chunk index.

        Args:
            entity: The entity whose component changed.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: The previous value of the field.
            new_value: The new value of the field.
        """
        if field_name == "grid_index":
            self._chunk_index.update_chunk(entity.id, old_value)

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal by removing entity from chunk index.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        self._chunk_index.remove_chunk(entity.id)


def create_chunk_index_observer(chunk_index: "ChunkIndex") -> ChunkIndexObserver:
    """Create a chunk index observer.

    Args:
        chunk_index: The chunk index to keep updated.

    Returns:
        A configured ChunkIndexObserver instance.
    """
    return ChunkIndexObserver(chunk_index)


class ChunkBakingObserver(ComponentObserver):
    """Observer that marks chunks dirty when layer components change.

    Watches for layer component changes and sets the dirty flag on the
    BakedChunk component to trigger rebaking.

    Attributes:
        component_type: Set dynamically to the layer component type.
    """

    component_type: ClassVar[Type[Component]]

    def __init__(self) -> None:
        """Create a chunk baking observer."""
        super().__init__()

    def _mark_dirty(self, entity: "Entity") -> None:
        """Mark a chunk as needing rebaking.

        Args:
            entity: The chunk entity to mark dirty.
        """
        if entity.has_component(BakedChunk):
            baked = entity.get_component(BakedChunk)
            baked.dirty = True
        else:
            # Add BakedChunk if it doesn't exist
            entity.add_component(BakedChunk(dirty=True))

    def on_component_added(self, entity: "Entity", component: Component) -> None:
        """Handle component addition by marking chunk dirty.

        Args:
            entity: The entity that received the component.
            component: The component that was added.
        """
        # Bind monitored components to world for change tracking
        if hasattr(component, "_bind_to_world"):
            component._bind_to_world(self.world, entity.id)
        self._mark_dirty(entity)

    def on_component_changed(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle component change by marking chunk dirty.

        Args:
            entity: The entity whose component changed.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: The previous value of the field.
            new_value: The new value of the field.
        """
        self._mark_dirty(entity)

    def on_component_removed(self, entity: "Entity", component: Component) -> None:
        """Handle component removal by marking chunk dirty.

        Args:
            entity: The entity that lost the component.
            component: The component that was removed.
        """
        self._mark_dirty(entity)


def create_baking_observer(component_type: Type[Component]) -> ChunkBakingObserver:
    """Create a baking observer for a specific layer component type.

    Creates a new observer class with the component_type set dynamically,
    then instantiates it.

    Args:
        component_type: The layer component type to watch.

    Returns:
        A configured ChunkBakingObserver instance.
    """
    # Create a dynamic subclass with the component_type set
    observer_class = type(
        f"ChunkBakingObserver_{component_type.__name__}",
        (ChunkBakingObserver,),
        {"component_type": component_type},
    )
    return cast(ChunkBakingObserver, observer_class())


# Layer component types that trigger baking
BAKING_LAYER_TYPES: tuple[Type[Component], ...] = (
    TileVisualLayer,
    TileElevationLayer,
    TileCollisionLayer,
)
