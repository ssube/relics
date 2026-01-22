"""Relics: An ECS Graph Database Framework.

A relic is a snapshot of a world at a particular epoch.
"""

__version__ = "0.1.0"

# Core types
from relics.types import Component, Edge, EntityId

# Entity handle
from relics.entity import Entity

# World
from relics.world import World

# Query system
from relics.query import QueryBuilder

# Systems
from relics.system import Frequency, RunOrder, System

# Observers
from relics.observer import (
    Observer,
    OnComponentAdded,
    OnComponentChanged,
    OnComponentRemoved,
    OnEntityCreated,
    OnEntityDestroyed,
)

# Monitored decorator
from relics.monitored import is_monitored, monitored

# Persistence
from relics.persistence import (
    RelicInfo,
    list_relics,
    load,
    load_relic,
    save,
    save_relic,
)

# Prefabs
from relics.prefab import (
    get_prefab,
    list_prefabs,
    load_prefabs_from_json,
    save_prefabs_to_json,
)

# Errors
from relics.errors import (
    ComponentNotFoundError,
    DuplicateComponentError,
    EntityNotFoundError,
    PrefabNotFoundError,
    RelicError,
    SystemDependencyCycleError,
)

__all__ = [
    # Version
    "__version__",
    # Core types
    "Component",
    "Edge",
    "EntityId",
    # Entity
    "Entity",
    # World
    "World",
    # Query
    "QueryBuilder",
    # Systems
    "Frequency",
    "RunOrder",
    "System",
    # Observers
    "Observer",
    "OnComponentAdded",
    "OnComponentChanged",
    "OnComponentRemoved",
    "OnEntityCreated",
    "OnEntityDestroyed",
    # Monitored
    "is_monitored",
    "monitored",
    # Persistence
    "RelicInfo",
    "list_relics",
    "load",
    "load_relic",
    "save",
    "save_relic",
    # Prefabs
    "get_prefab",
    "list_prefabs",
    "load_prefabs_from_json",
    "save_prefabs_to_json",
    # Errors
    "ComponentNotFoundError",
    "DuplicateComponentError",
    "EntityNotFoundError",
    "PrefabNotFoundError",
    "RelicError",
    "SystemDependencyCycleError",
]
