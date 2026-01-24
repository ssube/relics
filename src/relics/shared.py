"""Component decorators for controlling spawn and persistence behavior.

This module provides:
- @shared_component: Opt out of deep copy during spawn
- @temporary_component: Opt out of persistence (not saved/loaded)
"""

import copy
from typing import Any, Type, TypeVar

from relics.types import Component

T = TypeVar("T")


def temporary_component(cls: Type[T]) -> Type[T]:
    """Mark a component as temporary (not persisted).

    Use this decorator on components that should not be saved to disk.
    Temporary components are skipped during world serialization and will
    not be present when the world is loaded back.

    This decorator can be combined with @shared_component or @monitored.

    Example:
        @temporary_component
        @dataclass
        class InputState(Component):
            keys_pressed: List[str]  # Runtime state, not saved

        @temporary_component
        @shared_component
        @dataclass
        class CachedTexture(Component):
            texture_id: int  # Shared, not saved

    Args:
        cls: The component class to decorate.

    Returns:
        The decorated class marked as temporary.
    """
    cls._is_temporary = True  # type: ignore[attr-defined]
    return cls


def is_temporary(obj: Any) -> bool:
    """Check if an object or class is marked as @temporary_component.

    Args:
        obj: The object or class to check.

    Returns:
        True if the object/class is marked as temporary.
    """
    return getattr(obj, "_is_temporary", False)


def shared_component(cls: Type[T]) -> Type[T]:
    """Mark a component as shared (not copied during spawn).

    Use this decorator on components that should share the same instance
    across all entities spawned from the same prefab. This is useful for:
    - Large immutable data (e.g., mesh references, texture atlases)
    - Singleton-like components that should be shared intentionally

    Note: This decorator is mutually exclusive with @monitored. A component
    cannot be both shared and monitored because monitored components need
    unique instances for change tracking.

    Example:
        @shared_component
        @dataclass
        class SharedMesh(Component):
            vertices: List[float]
            indices: List[int]

    Args:
        cls: The component class to decorate.

    Returns:
        The decorated class marked as shared.

    Raises:
        ValueError: If the class is already marked as @monitored.
    """
    if getattr(cls, "_is_monitored", False):
        raise ValueError(
            f"Cannot mark {cls.__name__} as @shared_component: "
            "it is already @monitored. These decorators are mutually exclusive."
        )
    cls._is_shared = True  # type: ignore[attr-defined]
    return cls


def is_shared(obj: Any) -> bool:
    """Check if an object or class is marked as @shared_component.

    Args:
        obj: The object or class to check.

    Returns:
        True if the object/class is marked as shared.
    """
    return getattr(obj, "_is_shared", False)


def copy_component(component: Component) -> Component:
    """Copy a component for entity spawning.

    This function determines how to copy a component when spawning an entity
    from a prefab:
    - @shared_component: returns the same instance (no copy)
    - All other components: deep copy to ensure independence

    Args:
        component: The component instance to copy.

    Returns:
        Either the same instance (if shared) or a deep copy.
    """
    if is_shared(component):
        return component
    return copy.deepcopy(component)
