"""@monitored decorator for change tracking on components."""

from __future__ import annotations

import copy
from dataclasses import fields
from typing import TYPE_CHECKING, Any, Type, TypeVar

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

    def _notify_change(
        self, field_name: str, old_value: Any, new_value: Any
    ) -> None:
        """Notify the world of a component field change.

        Args:
            field_name: The name of the field that changed.
            old_value: The previous field value.
            new_value: The new field value.
        """
        if self._monitored_world is not None and self._monitored_entity_id is not None:
            self._monitored_world._notify_component_changed(
                self._monitored_entity_id, self, field_name, old_value, new_value
            )


def monitored(cls: Type[T]) -> Type[T]:
    """Decorator to enable change tracking on a component class.

    Use this decorator on component classes that need to trigger
    OnComponentChanged observers when their values change.

    The decorated class must be a dataclass (use @dataclass from
    pydantic.dataclasses or standard dataclasses).

    Example:
        @monitored
        @dataclass
        class Health(Component):
            current: int
            maximum: int

    Args:
        cls: The component class to decorate.

    Returns:
        The decorated class with change tracking enabled.
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
    # Note: This must be done after the dataclass decorator is applied

    # Get field names if it's already a dataclass
    try:
        field_names = {f.name for f in fields(cls)}  # type: ignore
    except TypeError:
        field_names = set()

    def monitored_setattr(self: Any, name: str, value: Any) -> None:
        """Set attribute and notify world if this is a monitored field."""
        # Skip internal attributes
        if name.startswith("_monitored") or name.startswith("__"):
            object.__setattr__(self, name, value)
            return

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

    cls.__setattr__ = monitored_setattr  # type: ignore[method-assign]

    return cls


def is_monitored(obj: Any) -> bool:
    """Check if an object or class has the @monitored decorator.

    Args:
        obj: The object or class to check.

    Returns:
        True if the object/class is monitored.
    """
    return getattr(obj, "_is_monitored", False)
