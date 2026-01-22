"""When-clause matching for procedural prefabs."""

from typing import Dict, List, Optional

from relics.addons.procedural_prefabs.context import GenerationContext
from relics.addons.procedural_prefabs.prefab import (
    ComponentVariant,
    ConditionalBlock,
    WhenClause,
)


def matches_when_clause(
    when: Optional[WhenClause],
    context: GenerationContext,
) -> bool:
    """Check if a when clause matches the current context.

    Uses exact-match semantics: all conditions in the clause
    must match their corresponding context values.

    Args:
        when: When clause to match (None always matches).
        context: Current generation context.

    Returns:
        True if the clause matches.
    """
    if when is None:
        return True

    all_values = context.get_all_values()

    for key, expected in when.conditions.items():
        # Resolve @param references in expected value
        resolved_expected = context.resolve_value(expected)
        actual = all_values.get(key)

        if actual != resolved_expected:
            return False

    return True


def find_matching_variant(
    variants: List[ComponentVariant],
    context: GenerationContext,
) -> Optional[ComponentVariant]:
    """Find the first matching component variant.

    Uses first-match semantics with fallback to default:
    1. Iterate through variants in order
    2. Return first variant where when clause matches
    3. If no when clause matches, return the default variant (when=None)
    4. Return None if no match and no default

    Args:
        variants: List of component variants to search.
        context: Current generation context.

    Returns:
        Matching variant or None.
    """
    default: Optional[ComponentVariant] = None

    for variant in variants:
        if variant.when is None:
            # Remember default (no condition)
            default = variant
        elif matches_when_clause(variant.when, context):
            # First conditional match wins
            return variant

    # Fall back to default
    return default


def find_all_matching_conditionals(
    conditionals: List[ConditionalBlock],
    context: GenerationContext,
) -> List[ConditionalBlock]:
    """Find all conditional blocks that match the context.

    Uses all-match semantics: returns every block whose
    when clause matches, in order.

    Args:
        conditionals: List of conditional blocks.
        context: Current generation context.

    Returns:
        List of all matching conditional blocks.
    """
    return [
        block
        for block in conditionals
        if matches_when_clause(block.when, context)
    ]


def group_variants_by_type(
    variants: List[ComponentVariant],
) -> Dict[str, List[ComponentVariant]]:
    """Group component variants by their component type.

    Args:
        variants: List of component variants.

    Returns:
        Dictionary mapping component_type to list of variants.
    """
    groups: Dict[str, List[ComponentVariant]] = {}

    for variant in variants:
        if variant.component_type not in groups:
            groups[variant.component_type] = []
        groups[variant.component_type].append(variant)

    return groups
