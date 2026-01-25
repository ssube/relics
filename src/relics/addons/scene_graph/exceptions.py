"""Exception classes for the scene graph addon."""

from relics.errors import RelicError


class SceneGraphError(RelicError):
    """Base exception for all scene graph errors."""

    pass


class DuplicatePathError(SceneGraphError):
    """A node with this path already exists.

    Raised when attempting to create a node path that is already
    in use by another node.
    """

    def __init__(self, path: str) -> None:
        """Initialize exception.

        Args:
            path: The duplicate path that was rejected.
        """
        self.path = path
        super().__init__(f"A node already exists at path: {path}")


class CycleDetectedError(SceneGraphError):
    """Reparenting would create a cycle in the hierarchy.

    Raised when attempting to set a node's parent to one of its
    descendants, which would create a cycle.
    """

    def __init__(self, child_path: str, parent_path: str) -> None:
        """Initialize exception.

        Args:
            child_path: Path of the child node.
            parent_path: Path of the target parent node.
        """
        self.child_path = child_path
        self.parent_path = parent_path
        super().__init__(
            f"Cannot make '{parent_path}' a parent of '{child_path}': "
            "would create a cycle"
        )


class InvalidNodeError(SceneGraphError):
    """Entity is not a scene node (missing NodeName component).

    Raised when an operation that requires a scene node is performed
    on an entity that doesn't have the NodeName component.
    """

    def __init__(self, entity_id: str) -> None:
        """Initialize exception.

        Args:
            entity_id: ID of the invalid entity.
        """
        self.entity_id = entity_id
        super().__init__(f"Entity '{entity_id}' is not a scene node (missing NodeName)")
