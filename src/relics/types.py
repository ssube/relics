"""Core type definitions for the Relics ECS framework."""

from typing import TYPE_CHECKING

import pydantic.dataclasses

if TYPE_CHECKING:
    from relics.entity import Entity


@pydantic.dataclasses.dataclass(frozen=True)
class EntityId:
    """Structured entity identifier.

    Attributes:
        prefab: The prefab name this entity was instantiated from.
        sequence: Per-prefab timestamp + collision counter for uniqueness.
    """

    prefab: str
    sequence: int

    def __str__(self) -> str:
        """Return string representation as '{prefab}_{sequence}'."""
        return f"{self.prefab}_{self.sequence}"

    def __hash__(self) -> int:
        """Return hash based on prefab and sequence."""
        return hash((self.prefab, self.sequence))

    @classmethod
    def parse(cls, s: str) -> "EntityId":
        """Parse string representation back to EntityId.

        Args:
            s: String in format '{prefab}_{sequence}'

        Returns:
            Parsed EntityId instance.

        Raises:
            ValueError: If the string format is invalid.
        """
        parts = s.rsplit("_", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid EntityId format: {s}")
        prefab, seq_str = parts
        try:
            sequence = int(seq_str)
        except ValueError as e:
            raise ValueError(f"Invalid sequence in EntityId: {s}") from e
        return cls(prefab=prefab, sequence=sequence)


class Component:
    """Base class for all components.

    Components are pure data containers with no logic.
    Use Pydantic dataclasses to define component fields.
    """

    pass


class Edge:
    """Base class for relationship edges.

    Edges define typed relationships between entities.
    Subclasses can override validate() to enforce constraints.
    """

    def validate(self, source: "Entity", target: "Entity") -> bool:
        """Validate the relationship between source and target.

        Override this method to enforce relationship constraints.
        The default implementation accepts all relationships.

        Args:
            source: The source entity of the relationship.
            target: The target entity of the relationship.

        Returns:
            True if the relationship is valid.

        Raises:
            RelationshipValidationError: If validation fails.
        """
        return True


class CustomEvent:
    """Base class for custom events.

    Custom events allow user-defined event types that can be emitted
    via World.emit() and observed via OnCustomEvent observers.

    Use Pydantic dataclasses to define event fields.

    Example:
        @dataclass
        class DamageEvent(CustomEvent):
            source: EntityId
            target: EntityId
            amount: float
    """

    pass
