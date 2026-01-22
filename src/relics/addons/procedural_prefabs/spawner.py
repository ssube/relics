"""Entity spawning for procedural prefabs."""

import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from relics.addons.procedural_prefabs.context import GenerationContext
from relics.addons.procedural_prefabs.edges import create_edge
from relics.addons.procedural_prefabs.exceptions import (
    AttachmentSelectionError,
    CyclicAttachmentError,
    ParamValidationError,
    PrefabListNotFoundError,
    ProcPrefabNotFoundError,
)
from relics.addons.procedural_prefabs.prefab import (
    AttachmentDefinition,
    ComponentRegistry,
    GraphDefinition,
    ProceduralPrefab,
)
from relics.addons.procedural_prefabs.resolver import resolve_graph

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World


class PrefabSpawner:
    """Spawns entities from procedural prefabs.

    Handles parameter validation, component resolution,
    and recursive attachment spawning.

    Attributes:
        registry: Registry of procedural prefabs.
        world: World to spawn entities in.
        component_registry: Registry of component types.
        rng: Random number generator for attachment selection.
    """

    def __init__(
        self,
        registry: Dict[str, ProceduralPrefab],
        prefab_lists: Dict[str, List[str]],
        world: "World",
        component_registry: ComponentRegistry,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Initialize spawner.

        Args:
            registry: Registry of procedural prefabs.
            prefab_lists: Registry of prefab lists.
            world: World to spawn entities in.
            component_registry: Registry of component types.
            rng: Optional RNG (default: new Random instance).
        """
        self._registry = registry
        self._prefab_lists = prefab_lists
        self._world = world
        self._component_registry = component_registry
        self._rng = rng or random.Random()

        # Stack for cycle detection
        self._spawn_stack: Set[str] = set()

    def spawn(
        self,
        prefab_name: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[GenerationContext] = None,
    ) -> "Entity":
        """Spawn an entity from a procedural prefab.

        Args:
            prefab_name: Name of the procedural prefab.
            params: Parameters to pass (merged with context params).
            context: Optional parent context for inheritance.

        Returns:
            Spawned entity with all attachments.

        Raises:
            ProcPrefabNotFoundError: If prefab not found.
            ParamValidationError: If parameter validation fails.
            CyclicAttachmentError: If cyclic attachment detected.
        """
        # Get prefab
        if prefab_name not in self._registry:
            raise ProcPrefabNotFoundError(prefab_name)

        prefab = self._registry[prefab_name]

        # Create context
        if context is None:
            context = GenerationContext(params=params or {})
        elif params:
            # Merge params into existing context
            merged_params = dict(context.params)
            merged_params.update(params)
            context = GenerationContext(params=merged_params, derived=context.derived)

        # Validate and apply defaults
        self._validate_params(prefab, context)

        # Check for cycles
        if prefab_name in self._spawn_stack:
            chain = list(self._spawn_stack) + [prefab_name]
            raise CyclicAttachmentError(chain)

        self._spawn_stack.add(prefab_name)

        try:
            # Resolve components
            components = resolve_graph(
                prefab.graph,
                context,
                self._component_registry,
            )

            # Create dynamic prefab name for this specific generation
            dynamic_name = f"_proc_{prefab.name}_{id(context)}"

            # Register dynamic prefab
            self._world.register_prefab(dynamic_name, components)

            # Spawn entity
            entity = self._world.spawn(dynamic_name)

            # Spawn attachments
            self._spawn_attachments(entity, prefab.graph, context)

            return entity

        finally:
            self._spawn_stack.discard(prefab_name)

    def _validate_params(
        self,
        prefab: ProceduralPrefab,
        context: GenerationContext,
    ) -> None:
        """Validate parameters and apply defaults.

        Args:
            prefab: Prefab to validate against.
            context: Context to validate/update.

        Raises:
            ParamValidationError: If validation fails.
        """
        for param_def in prefab.params:
            value = context.get_param(param_def.name)

            if value is None:
                # Check required
                if param_def.required:
                    raise ParamValidationError(
                        param_def.name,
                        "Required parameter not provided"
                    )

                # Apply default
                if param_def.default is not None:
                    # Mutate context params (need to access internal dict)
                    context._params[param_def.name] = param_def.default
            else:
                # Validate value
                try:
                    param_def.validate_value(value)
                except ValueError as e:
                    raise ParamValidationError(param_def.name, str(e)) from e

    def _spawn_attachments(
        self,
        parent: "Entity",
        graph: GraphDefinition,
        context: GenerationContext,
    ) -> None:
        """Spawn and attach child entities.

        Args:
            parent: Parent entity to attach to.
            graph: Graph definition with attachments.
            context: Current generation context.
        """
        if not graph.attachments:
            return

        for attachment in graph.attachments:
            self._spawn_attachment(parent, attachment, graph, context)

    def _spawn_attachment(
        self,
        parent: "Entity",
        attachment: AttachmentDefinition,
        graph: GraphDefinition,
        context: GenerationContext,
    ) -> Optional["Entity"]:
        """Spawn a single attachment.

        Args:
            parent: Parent entity to attach to.
            attachment: Attachment definition.
            graph: Graph definition (for local lists).
            context: Current generation context.

        Returns:
            Spawned child entity or None if skipped.
        """
        # Check skip flag
        if attachment.skip:
            return None

        # Resolve prefab name
        prefab_name = self._resolve_attachment_prefab(attachment, graph, context)

        if prefab_name is None:
            if attachment.optional:
                return None
            raise AttachmentSelectionError(
                attachment.slot,
                "No prefab resolved and attachment is not optional"
            )

        # Create child context
        child_context = context.child_context(
            inherit_params=attachment.inherit_params,
            override_params=attachment.override_params,
        )

        # Spawn child entity
        child = self.spawn(prefab_name, context=child_context)

        # Create edge and attach
        edge = create_edge(attachment.edge_type, attachment.slot)
        parent.add_relationship(edge, child.id)

        return child

    def _resolve_attachment_prefab(
        self,
        attachment: AttachmentDefinition,
        graph: GraphDefinition,
        context: GenerationContext,
    ) -> Optional[str]:
        """Resolve the prefab name for an attachment.

        Args:
            attachment: Attachment definition.
            graph: Graph definition (for local lists).
            context: Current generation context.

        Returns:
            Prefab name or None if cannot resolve.

        Raises:
            PrefabListNotFoundError: If list not found.
        """
        if attachment.prefab:
            # Static prefab with potential @param substitution
            resolved = context.resolve_value(attachment.prefab)
            return str(resolved) if resolved is not None else None

        if attachment.from_list:
            # Select from list
            list_name_resolved = context.resolve_value(attachment.from_list)
            if list_name_resolved is None:
                return None
            return self._select_from_list(str(list_name_resolved), graph)

        return None

    def _select_from_list(
        self,
        list_name: str,
        graph: GraphDefinition,
    ) -> Optional[str]:
        """Select a random prefab from a list.

        Checks local graph lists first, then global registry lists.

        Args:
            list_name: Name of the list to select from.
            graph: Graph definition with local lists.

        Returns:
            Selected prefab name or None if list empty.

        Raises:
            PrefabListNotFoundError: If list not found.
        """
        # Check local lists first
        options = None
        if graph.lists and list_name in graph.lists:
            options = graph.lists[list_name]
        elif list_name in self._prefab_lists:
            options = self._prefab_lists[list_name]
        else:
            raise PrefabListNotFoundError(list_name)

        if not options:
            return None

        return self._rng.choice(options)
