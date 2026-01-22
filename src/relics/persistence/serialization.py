"""Serialization helpers for components and edges."""

from __future__ import annotations

from typing import Any, Dict, Type, Union

from relics.types import Component, Edge

# Type alias for serializable types
Serializable = Union[Component, Edge]


def _component_to_dict(component: Serializable) -> Dict[str, Any]:
    """Convert a component or edge to a dictionary for serialization.

    Handles multiple component formats:
    - Standard dataclasses (with __dataclass_fields__)
    - Pydantic dataclasses (with __pydantic_fields__)
    - Pydantic BaseModel (with model_fields)
    - Plain classes (using __dict__)

    Private fields (starting with underscore) are excluded.

    Args:
        component: The component or edge to convert.

    Returns:
        Dictionary of field values.
    """
    if hasattr(component, "__dataclass_fields__"):
        return {
            name: getattr(component, name)
            for name in component.__dataclass_fields__
            if not name.startswith("_")
        }
    elif hasattr(component, "__pydantic_fields__"):
        return {
            name: getattr(component, name)
            for name in component.__pydantic_fields__
            if not name.startswith("_")
        }
    elif hasattr(component, "model_fields"):
        return {
            name: getattr(component, name)
            for name in component.model_fields
            if not name.startswith("_")
        }
    else:
        return {k: v for k, v in component.__dict__.items() if not k.startswith("_")}


def _dict_to_component(
    comp_type: Type[Serializable],
    data: Dict[str, Any],
) -> Serializable:
    """Convert a dictionary to a component or edge instance.

    Args:
        comp_type: The component or edge type.
        data: The field values.

    Returns:
        A component or edge instance.
    """
    return comp_type(**data)
