"""Procedural Prefabs addon for the Relics ECS framework.

This addon provides graph-based entity generation with conditional components,
parameter inheritance, and automatic child entity spawning.

Example:
    >>> from relics import World
    >>> from relics.addons.procedural_prefabs import (
    ...     ProceduralPrefabRegistry,
    ...     HasEquipped,
    ...     create_cascade_observer,
    ...     get_children,
    ... )
    >>>
    >>> # Create world and registry
    >>> world = World()
    >>> registry = ProceduralPrefabRegistry(world, rng_seed=42)
    >>>
    >>> # Register component types
    >>> registry.register_component_type("Health", Health)
    >>> registry.register_component_type("Damage", Damage)
    >>>
    >>> # Load procedural prefabs
    >>> registry.load_directory("prefabs/procedural/")
    >>>
    >>> # Register prefab lists for attachment selection
    >>> registry.register_list("weapons_axe", ["battle_axe", "war_hammer"])
    >>> registry.register_list("weapons_sword", ["longsword", "shortsword"])
    >>>
    >>> # Optional: register cascade deletion
    >>> world.observe(create_cascade_observer())
    >>>
    >>> # Spawn procedural entity
    >>> character = registry.spawn("character", {
    ...     "race": "dwarf",
    ...     "class": "warrior",
    ... })
    >>> world.tick(0)
    >>>
    >>> # Query attachments
    >>> for equipped in get_children(character, HasEquipped):
    ...     print(f"Equipped: {equipped.id}")
"""

# Exceptions
from relics.addons.procedural_prefabs.exceptions import (
    AttachmentSelectionError,
    CyclicAttachmentError,
    ParamValidationError,
    PrefabListNotFoundError,
    ProcPrefabNotFoundError,
    ProceduralPrefabError,
)

# Core data classes
from relics.addons.procedural_prefabs.prefab import (
    AddOperation,
    AttachmentDefinition,
    ComponentRegistry,
    ComponentVariant,
    ConditionalBlock,
    DeriveOperation,
    GraphDefinition,
    ParamDefinition,
    ProceduralPrefab,
    WhenClause,
)

# Context
from relics.addons.procedural_prefabs.context import GenerationContext

# Matching
from relics.addons.procedural_prefabs.matcher import (
    find_all_matching_conditionals,
    find_matching_variant,
    group_variants_by_type,
    matches_when_clause,
)

# Resolution
from relics.addons.procedural_prefabs.resolver import (
    apply_add_operation,
    apply_conditionals,
    apply_derive_operation,
    create_component_instance,
    resolve_component_fields,
    resolve_components,
    resolve_graph,
)

# Edge types
from relics.addons.procedural_prefabs.edges import (
    EDGE_TYPE_MAP,
    HasAttached,
    HasEquipped,
    IsWearing,
    create_edge,
    get_edge_class,
    register_edge_type,
)

# Spawner
from relics.addons.procedural_prefabs.spawner import PrefabSpawner

# Registry
from relics.addons.procedural_prefabs.registry import ProceduralPrefabRegistry

# Utilities
from relics.addons.procedural_prefabs.utils import (
    DEFAULT_EDGE_TYPES,
    detach,
    destroy_with_children,
    get_all_children_ids,
    get_child_ids,
    get_children,
    get_children_recursive,
    get_holder,
    get_holder_id,
    get_root,
    get_slot,
)

# Observer
from relics.addons.procedural_prefabs.observer import (
    DestroyChildrenObserver,
    create_cascade_observer,
)

__all__ = [
    # Exceptions
    "ProceduralPrefabError",
    "ProcPrefabNotFoundError",
    "ParamValidationError",
    "PrefabListNotFoundError",
    "AttachmentSelectionError",
    "CyclicAttachmentError",
    # Core data classes
    "ParamDefinition",
    "WhenClause",
    "ComponentVariant",
    "DeriveOperation",
    "AddOperation",
    "ConditionalBlock",
    "AttachmentDefinition",
    "GraphDefinition",
    "ProceduralPrefab",
    "ComponentRegistry",
    # Context
    "GenerationContext",
    # Matching
    "matches_when_clause",
    "find_matching_variant",
    "find_all_matching_conditionals",
    "group_variants_by_type",
    # Resolution
    "resolve_component_fields",
    "create_component_instance",
    "resolve_components",
    "apply_derive_operation",
    "apply_add_operation",
    "apply_conditionals",
    "resolve_graph",
    # Edge types
    "HasEquipped",
    "IsWearing",
    "HasAttached",
    "EDGE_TYPE_MAP",
    "get_edge_class",
    "create_edge",
    "register_edge_type",
    # Spawner
    "PrefabSpawner",
    # Registry
    "ProceduralPrefabRegistry",
    # Utilities
    "DEFAULT_EDGE_TYPES",
    "get_children",
    "get_child_ids",
    "get_holder",
    "get_holder_id",
    "detach",
    "destroy_with_children",
    "get_children_recursive",
    "get_all_children_ids",
    "get_root",
    "get_slot",
    # Observer
    "DestroyChildrenObserver",
    "create_cascade_observer",
]
