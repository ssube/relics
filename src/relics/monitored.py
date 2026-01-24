"""@monitored decorator for change tracking on components."""

from __future__ import annotations

import copy
from dataclasses import dataclass as std_dataclass
from dataclasses import fields, is_dataclass
from typing import TYPE_CHECKING, Any, Optional, Set, Type, TypeVar, cast

from relics.types import Component

if TYPE_CHECKING:
    from relics.types import EntityId
    from relics.world import World

T = TypeVar("T")


class MonitoredMixin:
    """Mixin that adds change tracking to a component.

    This mixin is added by the @monitored decorator and provides
    the infrastructure for notifying the World of component changes.
    """

    _monitored_world: "World" | None = None
    _monitored_entity_id: "EntityId" | None = None
    _is_monitored: bool = True

    def _bind_to_world(self, world: "World", entity_id: "EntityId") -> None:
        """Bind this component to a world and entity for change tracking.

        Args:
            world: The World to notify of changes.
            entity_id: The entity this component belongs to.
        """
        object.__setattr__(self, "_monitored_world", world)
        object.__setattr__(self, "_monitored_entity_id", entity_id)

    def _unbind_from_world(self) -> None:
        """Unbind this component from change tracking."""
        object.__setattr__(self, "_monitored_world", None)
        object.__setattr__(self, "_monitored_entity_id", None)

    def _notify_change(self, field_name: str, old_value: Any, new_value: Any) -> None:
        """Notify the world of a component field change.

        Args:
            field_name: The name of the field that changed.
            old_value: The previous field value.
            new_value: The new field value.
        """
        if self._monitored_world is not None and self._monitored_entity_id is not None:
            self._monitored_world._notify_component_changed(
                self._monitored_entity_id,
                cast(Component, self),
                field_name,
                old_value,
                new_value,
            )


def _create_monitored_setattr(
    field_names_cache: Optional[Set[str]] = None,
) -> Any:
    """Create a __setattr__ that tracks changes.

    Uses lazy field detection - field names are detected on first use
    if not provided upfront.
    """
    # Use a mutable container for lazy initialization
    cache: dict[str, Set[str]] = {"fields": field_names_cache or set()}
    initialized = [field_names_cache is not None]

    def monitored_setattr(self: Any, name: str, value: Any) -> None:
        """Set attribute and notify world if this is a monitored field."""
        # Skip internal attributes
        if name.startswith("_monitored") or name.startswith("__"):
            object.__setattr__(self, name, value)
            return

        # Lazy initialize field names from dataclass if needed
        if not initialized[0]:
            try:
                cache["fields"] = {f.name for f in fields(self.__class__)}
            except TypeError:
                cache["fields"] = set()
            initialized[0] = True

        field_names = cache["fields"]

        # Check if we should track this change
        should_notify = (
            hasattr(self, "_monitored_world")
            and self._monitored_world is not None
            and (not field_names or name in field_names)
        )

        if should_notify:
            # Capture old field value (not entire component)
            old_field_value = getattr(self, name, None)

            # Deep copy mutable types to preserve old state
            if isinstance(old_field_value, (list, dict, set)):
                old_field_value = copy.deepcopy(old_field_value)

            # Set the new value
            object.__setattr__(self, name, value)

            # Notify of change with field-level details
            self._notify_change(name, old_field_value, value)
        else:
            object.__setattr__(self, name, value)

    return monitored_setattr


def _apply_monitoring(cls: Type[T], field_names: Optional[Set[str]] = None) -> Type[T]:
    """Apply monitoring infrastructure to a class.

    Args:
        cls: The class to add monitoring to.
        field_names: Optional pre-computed field names (for dataclasses).

    Returns:
        The modified class with monitoring enabled.
    """
    # Add the mixin methods and attributes
    cls._monitored_world = None  # type: ignore[attr-defined]
    cls._monitored_entity_id = None  # type: ignore[attr-defined]
    cls._is_monitored = True  # type: ignore[attr-defined]

    # Add mixin methods
    cls._bind_to_world = MonitoredMixin._bind_to_world  # type: ignore
    cls._unbind_from_world = MonitoredMixin._unbind_from_world  # type: ignore
    cls._notify_change = MonitoredMixin._notify_change  # type: ignore

    # Override __setattr__ for change tracking
    cls.__setattr__ = _create_monitored_setattr(field_names)  # type: ignore[method-assign]

    return cls


def monitored(cls: Type[T]) -> Type[T]:
    """Decorator to enable change tracking on a component class.

    Use this decorator on component classes that need to trigger
    OnComponentChanged observers when their values change.

    This decorator can be used in two ways:

    1. With @dataclass (order-independent):

        @monitored
        @dataclass
        class Health(Component):
            current: int
            maximum: int

        # OR

        @dataclass
        @monitored
        class Health(Component):
            current: int
            maximum: int

    2. Using the combined decorator (recommended):

        @monitored_component
        class Health(Component):
            current: int
            maximum: int

    Args:
        cls: The component class to decorate.

    Returns:
        The decorated class with change tracking enabled.
    """
    # Get field names if it's already a dataclass
    field_names: Optional[Set[str]] = None
    if is_dataclass(cls):
        try:
            field_names = {f.name for f in fields(cls)}
        except TypeError:
            pass

    return _apply_monitoring(cls, field_names)


def monitored_component(cls: Type[T]) -> Type[T]:
    """Combined decorator that creates a monitored dataclass component.

    This is the recommended way to create monitored components as it
    handles the decorator ordering automatically.

    Example:
        @monitored_component
        class Health(Component):
            current: int
            maximum: int

        # Equivalent to:
        @monitored
        @dataclass
        class Health(Component):
            current: int
            maximum: int

    Args:
        cls: The component class to decorate.

    Returns:
        A dataclass with change tracking enabled.
    """
    # Apply @dataclass first
    cls = std_dataclass(cls)

    # Get field names from the dataclass
    field_names = {f.name for f in fields(cls)}

    # Apply monitoring
    return _apply_monitoring(cls, field_names)


def is_monitored(obj: Any) -> bool:
    """Check if an object or class has the @monitored decorator.

    Args:
        obj: The object or class to check.

    Returns:
        True if the object/class is monitored.
    """
    return getattr(obj, "_is_monitored", False)
