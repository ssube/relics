"""Tests for when-clause matching."""

import pytest

from relics.addons.procedural_prefabs.context import GenerationContext
from relics.addons.procedural_prefabs.matcher import (
    find_all_matching_conditionals,
    find_matching_variant,
    group_variants_by_type,
    matches_when_clause,
)
from relics.addons.procedural_prefabs.prefab import (
    ComponentVariant,
    ConditionalBlock,
    DeriveOperation,
    WhenClause,
)


class TestMatchesWhenClause:
    """Tests for matches_when_clause."""

    def test_none_when_always_matches(self) -> None:
        """Test that None when clause always matches."""
        ctx = GenerationContext(params={"race": "elf"})
        assert matches_when_clause(None, ctx) is True

    def test_empty_conditions_matches(self) -> None:
        """Test that empty conditions match."""
        when = WhenClause(conditions={})
        ctx = GenerationContext(params={"race": "elf"})
        assert matches_when_clause(when, ctx) is True

    def test_single_condition_matches(self) -> None:
        """Test single condition matching."""
        when = WhenClause(conditions={"race": "elf"})
        ctx = GenerationContext(params={"race": "elf"})
        assert matches_when_clause(when, ctx) is True

    def test_single_condition_no_match(self) -> None:
        """Test single condition not matching."""
        when = WhenClause(conditions={"race": "elf"})
        ctx = GenerationContext(params={"race": "dwarf"})
        assert matches_when_clause(when, ctx) is False

    def test_multiple_conditions_all_match(self) -> None:
        """Test multiple conditions all matching."""
        when = WhenClause(conditions={"race": "elf", "class": "mage"})
        ctx = GenerationContext(params={"race": "elf", "class": "mage"})
        assert matches_when_clause(when, ctx) is True

    def test_multiple_conditions_partial_match(self) -> None:
        """Test multiple conditions with partial match."""
        when = WhenClause(conditions={"race": "elf", "class": "mage"})
        ctx = GenerationContext(params={"race": "elf", "class": "warrior"})
        assert matches_when_clause(when, ctx) is False

    def test_condition_against_derived(self) -> None:
        """Test matching against derived values."""
        when = WhenClause(conditions={"weapon_type": "sword"})
        ctx = GenerationContext(derived={"weapon_type": "sword"})
        assert matches_when_clause(when, ctx) is True

    def test_condition_missing_key(self) -> None:
        """Test condition with missing key doesn't match."""
        when = WhenClause(conditions={"race": "elf"})
        ctx = GenerationContext(params={})
        assert matches_when_clause(when, ctx) is False

    def test_condition_with_param_reference(self) -> None:
        """Test condition value with @param reference."""
        when = WhenClause(conditions={"selected": "@expected"})
        ctx = GenerationContext(params={"selected": "sword", "expected": "sword"})
        assert matches_when_clause(when, ctx) is True

    def test_condition_numeric_values(self) -> None:
        """Test condition with numeric values."""
        when = WhenClause(conditions={"level": 10})
        ctx = GenerationContext(params={"level": 10})
        assert matches_when_clause(when, ctx) is True

        ctx2 = GenerationContext(params={"level": 5})
        assert matches_when_clause(when, ctx2) is False

    def test_condition_boolean_values(self) -> None:
        """Test condition with boolean values."""
        when = WhenClause(conditions={"enabled": True})
        ctx = GenerationContext(params={"enabled": True})
        assert matches_when_clause(when, ctx) is True

        ctx2 = GenerationContext(params={"enabled": False})
        assert matches_when_clause(when, ctx2) is False


class TestFindMatchingVariant:
    """Tests for find_matching_variant (first-match semantics)."""

    def test_empty_variants(self) -> None:
        """Test with empty variant list."""
        ctx = GenerationContext()
        assert find_matching_variant([], ctx) is None

    def test_single_default_variant(self) -> None:
        """Test single variant with no condition."""
        variant = ComponentVariant(
            component_type="Health",
            fields={"value": 100},
        )
        ctx = GenerationContext()
        result = find_matching_variant([variant], ctx)
        assert result is variant

    def test_first_match_wins(self) -> None:
        """Test that first matching variant wins."""
        v1 = ComponentVariant(
            component_type="Health",
            fields={"value": 100},
            when=WhenClause(conditions={"race": "elf"}),
        )
        v2 = ComponentVariant(
            component_type="Health",
            fields={"value": 150},
            when=WhenClause(conditions={"race": "elf"}),
        )
        ctx = GenerationContext(params={"race": "elf"})
        result = find_matching_variant([v1, v2], ctx)
        assert result is v1

    def test_fallback_to_default(self) -> None:
        """Test fallback to default variant."""
        v_conditional = ComponentVariant(
            component_type="Health",
            fields={"value": 150},
            when=WhenClause(conditions={"race": "elf"}),
        )
        v_default = ComponentVariant(
            component_type="Health",
            fields={"value": 100},
        )
        ctx = GenerationContext(params={"race": "dwarf"})
        result = find_matching_variant([v_conditional, v_default], ctx)
        assert result is v_default

    def test_default_position_irrelevant(self) -> None:
        """Test that default position doesn't matter for fallback."""
        v_default = ComponentVariant(
            component_type="Health",
            fields={"value": 100},
        )
        v_conditional = ComponentVariant(
            component_type="Health",
            fields={"value": 150},
            when=WhenClause(conditions={"race": "elf"}),
        )
        # Default first
        ctx = GenerationContext(params={"race": "dwarf"})
        result = find_matching_variant([v_default, v_conditional], ctx)
        assert result is v_default

    def test_no_match_no_default(self) -> None:
        """Test no match and no default returns None."""
        v = ComponentVariant(
            component_type="Health",
            fields={"value": 150},
            when=WhenClause(conditions={"race": "elf"}),
        )
        ctx = GenerationContext(params={"race": "dwarf"})
        result = find_matching_variant([v], ctx)
        assert result is None

    def test_conditional_matches_over_later_default(self) -> None:
        """Test conditional match beats later default."""
        v_conditional = ComponentVariant(
            component_type="Health",
            fields={"value": 150},
            when=WhenClause(conditions={"race": "elf"}),
        )
        v_default = ComponentVariant(
            component_type="Health",
            fields={"value": 100},
        )
        ctx = GenerationContext(params={"race": "elf"})
        result = find_matching_variant([v_conditional, v_default], ctx)
        assert result is v_conditional


class TestFindAllMatchingConditionals:
    """Tests for find_all_matching_conditionals (all-match semantics)."""

    def test_empty_conditionals(self) -> None:
        """Test with empty conditional list."""
        ctx = GenerationContext()
        assert find_all_matching_conditionals([], ctx) == []

    def test_all_match(self) -> None:
        """Test that all matching conditionals are returned."""
        c1 = ConditionalBlock(
            when=WhenClause(conditions={"race": "elf"}),
            add=[],
            derive=[],
        )
        c2 = ConditionalBlock(
            when=WhenClause(conditions={"race": "elf"}),
            add=[],
            derive=[],
        )
        ctx = GenerationContext(params={"race": "elf"})
        result = find_all_matching_conditionals([c1, c2], ctx)
        assert result == [c1, c2]

    def test_partial_match(self) -> None:
        """Test that only matching conditionals are returned."""
        c1 = ConditionalBlock(
            when=WhenClause(conditions={"race": "elf"}),
            add=[],
            derive=[],
        )
        c2 = ConditionalBlock(
            when=WhenClause(conditions={"race": "dwarf"}),
            add=[],
            derive=[],
        )
        ctx = GenerationContext(params={"race": "elf"})
        result = find_all_matching_conditionals([c1, c2], ctx)
        assert result == [c1]

    def test_no_match(self) -> None:
        """Test with no matching conditionals."""
        c1 = ConditionalBlock(
            when=WhenClause(conditions={"race": "elf"}),
            add=[],
            derive=[],
        )
        ctx = GenerationContext(params={"race": "dwarf"})
        result = find_all_matching_conditionals([c1], ctx)
        assert result == []

    def test_order_preserved(self) -> None:
        """Test that order of matching conditionals is preserved."""
        c1 = ConditionalBlock(
            when=WhenClause(conditions={"class": "warrior"}),
            add=[],
            derive=[DeriveOperation(target="str", operation="add", value=5)],
        )
        c2 = ConditionalBlock(
            when=WhenClause(conditions={"class": "warrior"}),
            add=[],
            derive=[DeriveOperation(target="str", operation="add", value=3)],
        )
        c3 = ConditionalBlock(
            when=WhenClause(conditions={"race": "dwarf"}),
            add=[],
            derive=[DeriveOperation(target="con", operation="add", value=2)],
        )
        ctx = GenerationContext(params={"class": "warrior", "race": "dwarf"})
        result = find_all_matching_conditionals([c1, c2, c3], ctx)
        assert result == [c1, c2, c3]


class TestGroupVariantsByType:
    """Tests for group_variants_by_type."""

    def test_empty_variants(self) -> None:
        """Test with empty variant list."""
        assert group_variants_by_type([]) == {}

    def test_single_type(self) -> None:
        """Test grouping variants of single type."""
        v1 = ComponentVariant(component_type="Health", fields={"value": 100})
        v2 = ComponentVariant(component_type="Health", fields={"value": 150})
        result = group_variants_by_type([v1, v2])
        assert result == {"Health": [v1, v2]}

    def test_multiple_types(self) -> None:
        """Test grouping variants of multiple types."""
        v1 = ComponentVariant(component_type="Health", fields={"value": 100})
        v2 = ComponentVariant(component_type="Damage", fields={"value": 10})
        v3 = ComponentVariant(component_type="Health", fields={"value": 150})
        result = group_variants_by_type([v1, v2, v3])
        assert result == {
            "Health": [v1, v3],
            "Damage": [v2],
        }

    def test_preserves_order(self) -> None:
        """Test that order within groups is preserved."""
        v1 = ComponentVariant(component_type="Health", fields={"value": 100})
        v2 = ComponentVariant(component_type="Health", fields={"value": 150})
        v3 = ComponentVariant(component_type="Health", fields={"value": 200})
        result = group_variants_by_type([v1, v2, v3])
        assert result["Health"] == [v1, v2, v3]
