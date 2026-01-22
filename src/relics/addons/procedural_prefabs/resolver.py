"""Component and conditional resolution for procedural prefabs."""

from typing import Any, Dict, Type

from relics.addons.procedural_prefabs.context import GenerationContext
from relics.addons.procedural_prefabs.matcher import (
    find_all_matching_conditionals,
    find_matching_variant,
    group_variants_by_type,
)
from relics.addons.procedural_prefabs.prefab import (
    AddOperation,
    ComponentRegistry,
    DeriveOperation,
    GraphDefinition,
)
from relics.types import Component


def resolve_component_fields(
    fields: Dict[str, Any],
    context: GenerationContext,
) -> Dict[str, Any]:
    """Resolve @param references in component fields.

    Args:
        fields: Field dictionary with potential @param references.
        context: Current generation context.

    Returns:
        Dictionary with all @param references resolved.
    """
    return {key: context.resolve_value(value) for key, value in fields.items()}


def create_component_instance(
    component_type: str,
    fields: Dict[str, Any],
    component_registry: ComponentRegistry,
) -> Component:
    """Create a component instance from type name and fields.

    Args:
        component_type: Name of the component type.
        fields: Field values for the component.
        component_registry: Registry mapping names to component classes.

    Returns:
        Component instance.

    Raises:
        KeyError: If component type not in registry.
    """
    if component_type not in component_registry:
        raise KeyError(f"Component type not found in registry: {component_type}")

    cls = component_registry[component_type]
    instance: Component = cls(**fields)
    return instance


def resolve_components(
    graph: GraphDefinition,
    context: GenerationContext,
    component_registry: ComponentRegistry,
) -> Dict[Type[Component], Component]:
    """Resolve base components from graph definition.

    Uses first-match semantics for component variants:
    - For each component type, find the first matching variant
    - Fall back to default (no when clause) if no match
    - Skip component type if no match and no default

    Args:
        graph: Graph definition with component variants.
        context: Current generation context.
        component_registry: Registry mapping names to component classes.

    Returns:
        Dictionary mapping component types to instances.
    """
    components: Dict[Type[Component], Component] = {}

    # Group variants by component type
    grouped = group_variants_by_type(graph.components)

    for type_name, variants in grouped.items():
        # Find matching variant for this type
        matching = find_matching_variant(variants, context)

        if matching is not None:
            # Resolve fields and create instance
            resolved_fields = resolve_component_fields(matching.fields, context)
            instance = create_component_instance(
                type_name, resolved_fields, component_registry
            )

            cls = component_registry[type_name]
            components[cls] = instance

    return components


def apply_derive_operation(
    derive: DeriveOperation,
    context: GenerationContext,
) -> None:
    """Apply a derive operation to the context.

    Args:
        derive: Derive operation to apply.
        context: Context to modify.
    """
    resolved_value = context.resolve_value(derive.value)

    if derive.operation == "set":
        context.set_derived(derive.target, resolved_value)
    elif derive.operation == "add":
        context.add_derived(derive.target, resolved_value)
    elif derive.operation == "multiply":
        context.multiply_derived(derive.target, resolved_value)
    elif derive.operation == "append":
        context.append_derived(derive.target, resolved_value)


def apply_add_operation(
    add: AddOperation,
    context: GenerationContext,
    component_registry: ComponentRegistry,
    components: Dict[Type[Component], Component],
) -> None:
    """Apply an add operation to create/update a component.

    Args:
        add: Add operation to apply.
        context: Current generation context.
        component_registry: Registry mapping names to component classes.
        components: Components dictionary to update.
    """
    resolved_fields = resolve_component_fields(add.fields, context)
    instance = create_component_instance(
        add.component_type, resolved_fields, component_registry
    )

    cls = component_registry[add.component_type]
    components[cls] = instance


def apply_conditionals(
    graph: GraphDefinition,
    context: GenerationContext,
    component_registry: ComponentRegistry,
    components: Dict[Type[Component], Component],
) -> None:
    """Apply all matching conditional blocks.

    Uses all-match semantics: every conditional block whose
    when clause matches will have its operations applied,
    in order.

    Note: Derive operations modify the context, which may
    affect subsequent conditional matching or component fields.

    Args:
        graph: Graph definition with conditionals.
        context: Context to modify.
        component_registry: Registry mapping names to component classes.
        components: Components dictionary to update.
    """
    if not graph.conditionals:
        return

    matching = find_all_matching_conditionals(graph.conditionals, context)

    for block in matching:
        # Apply derive operations first
        for derive in block.derive:
            apply_derive_operation(derive, context)

        # Then apply add operations
        for add in block.add:
            apply_add_operation(add, context, component_registry, components)


def resolve_graph(
    graph: GraphDefinition,
    context: GenerationContext,
    component_registry: ComponentRegistry,
) -> Dict[Type[Component], Component]:
    """Fully resolve a graph definition into components.

    This is the main resolution function that:
    1. Resolves base components (first-match)
    2. Applies all matching conditionals (all-match)

    Args:
        graph: Graph definition to resolve.
        context: Current generation context.
        component_registry: Registry mapping names to component classes.

    Returns:
        Dictionary mapping component types to instances.
    """
    # Step 1: Resolve base components
    components = resolve_components(graph, context, component_registry)

    # Step 2: Apply conditionals
    apply_conditionals(graph, context, component_registry, components)

    return components
