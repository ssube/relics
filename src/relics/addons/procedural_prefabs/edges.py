"""Edge types for procedural prefab attachments."""

from typing import Dict, Type

import pydantic.dataclasses

from relics.types import Edge


@pydantic.dataclasses.dataclass
class HasEquipped(Edge):
    """Edge representing an equipped item relationship.

    Used for items equipped in specific slots (weapons, armor, etc.).

    Attributes:
        slot: The equipment slot name.
    """

    slot: str = "default"


@pydantic.dataclasses.dataclass
class IsWearing(Edge):
    """Edge representing a worn item relationship.

    Used for clothing and accessories.

    Attributes:
        slot: The wearing slot name.
    """

    slot: str = "default"


@pydantic.dataclasses.dataclass
class HasAttached(Edge):
    """Generic attachment edge.

    Fallback for attachments that don't fit other categories.

    Attributes:
        slot: The attachment slot name.
    """

    slot: str = "default"


# Mapping of edge type names to classes
EDGE_TYPE_MAP: Dict[str, Type[Edge]] = {
    "HasEquipped": HasEquipped,
    "IsWearing": IsWearing,
    "HasAttached": HasAttached,
}


def get_edge_class(edge_type_name: str) -> Type[Edge]:
    """Get edge class by name.

    Args:
        edge_type_name: Name of the edge type.

    Returns:
        Edge class.

    Raises:
        KeyError: If edge type not found.
    """
    if edge_type_name not in EDGE_TYPE_MAP:
        raise KeyError(
            f"Unknown edge type: {edge_type_name}. "
            f"Available types: {list(EDGE_TYPE_MAP.keys())}"
        )
    return EDGE_TYPE_MAP[edge_type_name]


def create_edge(edge_type_name: str, slot: str) -> Edge:
    """Create an edge instance by name.

    Args:
        edge_type_name: Name of the edge type.
        slot: Slot name for the edge.

    Returns:
        Edge instance.

    Raises:
        KeyError: If edge type not found.
    """
    cls = get_edge_class(edge_type_name)
    # All our edge types have a slot parameter
    return cls(slot=slot)  # type: ignore[call-arg]


def register_edge_type(name: str, cls: Type[Edge]) -> None:
    """Register a custom edge type.

    Args:
        name: Name for the edge type.
        cls: Edge class to register.
    """
    EDGE_TYPE_MAP[name] = cls
