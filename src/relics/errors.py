"""Exception classes for the Relics ECS framework."""


class RelicError(Exception):
    """Base exception for all Relic errors."""

    pass


class EntityNotFoundError(RelicError):
    """Entity does not exist in world."""

    pass


class ComponentNotFoundError(RelicError):
    """Entity does not have the requested component."""

    pass


class DuplicateComponentError(RelicError):
    """Entity already has this component type."""

    pass


class PrefabNotFoundError(RelicError):
    """Prefab does not exist."""

    pass


class SystemDependencyCycleError(RelicError):
    """System dependencies form a cycle (fatal at registration)."""

    pass


class RelationshipValidationError(RelicError):
    """Relationship validation failed.

    Raised when an Edge.validate() method returns False or raises
    an exception during relationship creation.
    """

    pass


class IndexNotFoundError(RelicError):
    """Index does not exist in world."""

    pass
