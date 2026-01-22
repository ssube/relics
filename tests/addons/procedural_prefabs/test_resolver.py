"""Tests for component resolution."""

import pydantic.dataclasses
import pytest

from relics.addons.procedural_prefabs.context import GenerationContext
from relics.addons.procedural_prefabs.prefab import (
    AddOperation,
    ComponentVariant,
    ConditionalBlock,
    DeriveOperation,
    GraphDefinition,
    WhenClause,
)
from relics.addons.procedural_prefabs.resolver import (
    apply_add_operation,
    apply_conditionals,
    apply_derive_operation,
    create_component_instance,
    resolve_component_fields,
    resolve_components,
    resolve_graph,
)
from relics.types import Component


# Test components
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int


@pydantic.dataclasses.dataclass
class Damage(Component):
    value: int
    damage_type: str = "physical"


@pydantic.dataclasses.dataclass
class Armor(Component):
    value: int


@pydantic.dataclasses.dataclass
class Buff(Component):
    name: str
    amount: int


# Component registry for tests
TEST_REGISTRY = {
    "Health": Health,
    "Damage": Damage,
    "Armor": Armor,
    "Buff": Buff,
}


class TestResolveComponentFields:
    """Tests for resolve_component_fields."""

    def test_no_params(self) -> None:
        """Test resolving fields with no @param references."""
        ctx = GenerationContext()
        fields = {"current": 100, "maximum": 100}
        result = resolve_component_fields(fields, ctx)
        assert result == {"current": 100, "maximum": 100}

    def test_single_param(self) -> None:
        """Test resolving a single @param reference."""
        ctx = GenerationContext(params={"hp": 100})
        fields = {"current": "@hp", "maximum": "@hp"}
        result = resolve_component_fields(fields, ctx)
        assert result == {"current": 100, "maximum": 100}

    def test_param_in_string(self) -> None:
        """Test resolving @param within a string."""
        ctx = GenerationContext(params={"type": "fire"})
        fields = {"damage_type": "@type"}
        result = resolve_component_fields(fields, ctx)
        assert result == {"damage_type": "fire"}

    def test_multiple_params(self) -> None:
        """Test resolving multiple @param references."""
        ctx = GenerationContext(params={"dmg": 10, "type": "ice"})
        fields = {"value": "@dmg", "damage_type": "@type"}
        result = resolve_component_fields(fields, ctx)
        assert result == {"value": 10, "damage_type": "ice"}

    def test_mixed_static_and_params(self) -> None:
        """Test mixing static values and @params."""
        ctx = GenerationContext(params={"hp": 100})
        fields = {"current": "@hp", "maximum": 150}
        result = resolve_component_fields(fields, ctx)
        assert result == {"current": 100, "maximum": 150}


class TestCreateComponentInstance:
    """Tests for create_component_instance."""

    def test_create_simple_component(self) -> None:
        """Test creating a simple component."""
        instance = create_component_instance(
            "Health",
            {"current": 100, "maximum": 100},
            TEST_REGISTRY,
        )
        assert isinstance(instance, Health)
        assert instance.current == 100
        assert instance.maximum == 100

    def test_create_with_defaults(self) -> None:
        """Test creating a component with default fields."""
        instance = create_component_instance(
            "Damage",
            {"value": 10},
            TEST_REGISTRY,
        )
        assert isinstance(instance, Damage)
        assert instance.value == 10
        assert instance.damage_type == "physical"

    def test_create_override_defaults(self) -> None:
        """Test overriding default fields."""
        instance = create_component_instance(
            "Damage",
            {"value": 10, "damage_type": "fire"},
            TEST_REGISTRY,
        )
        assert instance.damage_type == "fire"

    def test_unknown_component_type(self) -> None:
        """Test that unknown component type raises KeyError."""
        with pytest.raises(KeyError, match="not found in registry"):
            create_component_instance("Unknown", {}, TEST_REGISTRY)


class TestResolveComponents:
    """Tests for resolve_components."""

    def test_single_component_no_condition(self) -> None:
        """Test resolving a single component with no condition."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 100, "maximum": 100},
                ),
            ],
        )
        ctx = GenerationContext()
        result = resolve_components(graph, ctx, TEST_REGISTRY)

        assert Health in result
        assert result[Health].current == 100

    def test_multiple_components(self) -> None:
        """Test resolving multiple components."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 100, "maximum": 100},
                ),
                ComponentVariant(
                    component_type="Damage",
                    fields={"value": 10},
                ),
            ],
        )
        ctx = GenerationContext()
        result = resolve_components(graph, ctx, TEST_REGISTRY)

        assert len(result) == 2
        assert Health in result
        assert Damage in result

    def test_first_match_semantics(self) -> None:
        """Test first-match semantics for component variants."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 150, "maximum": 150},
                    when=WhenClause(conditions={"race": "dwarf"}),
                ),
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 100, "maximum": 100},
                ),
            ],
        )

        # Dwarf context should get 150
        ctx_dwarf = GenerationContext(params={"race": "dwarf"})
        result_dwarf = resolve_components(graph, ctx_dwarf, TEST_REGISTRY)
        assert result_dwarf[Health].current == 150

        # Elf context should get default 100
        ctx_elf = GenerationContext(params={"race": "elf"})
        result_elf = resolve_components(graph, ctx_elf, TEST_REGISTRY)
        assert result_elf[Health].current == 100

    def test_param_resolution_in_components(self) -> None:
        """Test @param resolution in component fields."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": "@hp", "maximum": "@hp"},
                ),
            ],
        )
        ctx = GenerationContext(params={"hp": 200})
        result = resolve_components(graph, ctx, TEST_REGISTRY)
        assert result[Health].current == 200
        assert result[Health].maximum == 200

    def test_no_matching_variant(self) -> None:
        """Test that no match skips the component type."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 100, "maximum": 100},
                    when=WhenClause(conditions={"race": "elf"}),
                ),
            ],
        )
        ctx = GenerationContext(params={"race": "dwarf"})
        result = resolve_components(graph, ctx, TEST_REGISTRY)
        assert Health not in result


class TestApplyDeriveOperation:
    """Tests for apply_derive_operation."""

    def test_set_operation(self) -> None:
        """Test set derive operation."""
        ctx = GenerationContext()
        derive = DeriveOperation(target="damage", operation="set", value=10)
        apply_derive_operation(derive, ctx)
        assert ctx.get_derived("damage") == 10

    def test_add_operation(self) -> None:
        """Test add derive operation."""
        ctx = GenerationContext(derived={"damage": 10})
        derive = DeriveOperation(target="damage", operation="add", value=5)
        apply_derive_operation(derive, ctx)
        assert ctx.get_derived("damage") == 15

    def test_multiply_operation(self) -> None:
        """Test multiply derive operation."""
        ctx = GenerationContext(derived={"damage": 10})
        derive = DeriveOperation(target="damage", operation="multiply", value=2)
        apply_derive_operation(derive, ctx)
        assert ctx.get_derived("damage") == 20

    def test_append_operation(self) -> None:
        """Test append derive operation."""
        ctx = GenerationContext(derived={"tags": ["base"]})
        derive = DeriveOperation(target="tags", operation="append", value="bonus")
        apply_derive_operation(derive, ctx)
        assert ctx.get_derived("tags") == ["base", "bonus"]

    def test_param_reference_in_value(self) -> None:
        """Test @param reference in derive value."""
        ctx = GenerationContext(params={"bonus": 5})
        derive = DeriveOperation(target="damage", operation="set", value="@bonus")
        apply_derive_operation(derive, ctx)
        assert ctx.get_derived("damage") == 5


class TestApplyAddOperation:
    """Tests for apply_add_operation."""

    def test_add_new_component(self) -> None:
        """Test adding a new component."""
        ctx = GenerationContext()
        components = {}
        add = AddOperation(component_type="Armor", fields={"value": 10})
        apply_add_operation(add, ctx, TEST_REGISTRY, components)
        assert Armor in components
        assert components[Armor].value == 10

    def test_add_replaces_existing(self) -> None:
        """Test that add replaces existing component."""
        ctx = GenerationContext()
        components = {Armor: Armor(value=5)}
        add = AddOperation(component_type="Armor", fields={"value": 10})
        apply_add_operation(add, ctx, TEST_REGISTRY, components)
        assert components[Armor].value == 10

    def test_add_with_param_resolution(self) -> None:
        """Test add with @param resolution in fields."""
        ctx = GenerationContext(params={"armor_value": 15})
        components = {}
        add = AddOperation(component_type="Armor", fields={"value": "@armor_value"})
        apply_add_operation(add, ctx, TEST_REGISTRY, components)
        assert components[Armor].value == 15


class TestApplyConditionals:
    """Tests for apply_conditionals."""

    def test_no_conditionals(self) -> None:
        """Test with no conditionals defined."""
        graph = GraphDefinition(components=[])
        ctx = GenerationContext()
        components = {}
        apply_conditionals(graph, ctx, TEST_REGISTRY, components)
        assert components == {}

    def test_matching_conditional_adds_component(self) -> None:
        """Test matching conditional adds component."""
        graph = GraphDefinition(
            components=[],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={"class": "warrior"}),
                    add=[AddOperation(component_type="Armor", fields={"value": 10})],
                    derive=[],
                ),
            ],
        )
        ctx = GenerationContext(params={"class": "warrior"})
        components = {}
        apply_conditionals(graph, ctx, TEST_REGISTRY, components)
        assert Armor in components

    def test_non_matching_conditional_skipped(self) -> None:
        """Test non-matching conditional is skipped."""
        graph = GraphDefinition(
            components=[],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={"class": "warrior"}),
                    add=[AddOperation(component_type="Armor", fields={"value": 10})],
                    derive=[],
                ),
            ],
        )
        ctx = GenerationContext(params={"class": "mage"})
        components = {}
        apply_conditionals(graph, ctx, TEST_REGISTRY, components)
        assert Armor not in components

    def test_multiple_matching_conditionals(self) -> None:
        """Test all matching conditionals are applied."""
        graph = GraphDefinition(
            components=[],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={"class": "warrior"}),
                    add=[],
                    derive=[DeriveOperation(target="str", operation="set", value=10)],
                ),
                ConditionalBlock(
                    when=WhenClause(conditions={"class": "warrior"}),
                    add=[],
                    derive=[DeriveOperation(target="str", operation="add", value=5)],
                ),
            ],
        )
        ctx = GenerationContext(params={"class": "warrior"})
        components = {}
        apply_conditionals(graph, ctx, TEST_REGISTRY, components)
        # Both should apply: set 10, then add 5
        assert ctx.get_derived("str") == 15

    def test_derive_then_add_order(self) -> None:
        """Test derive operations run before add operations in a block."""
        graph = GraphDefinition(
            components=[],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={"class": "warrior"}),
                    add=[
                        AddOperation(component_type="Armor", fields={"value": "@str"})
                    ],
                    derive=[DeriveOperation(target="str", operation="set", value=10)],
                ),
            ],
        )
        ctx = GenerationContext(params={"class": "warrior"})
        components = {}
        apply_conditionals(graph, ctx, TEST_REGISTRY, components)
        # Derive should have set str=10 before add used it
        assert components[Armor].value == 10


class TestResolveGraph:
    """Tests for resolve_graph (full resolution)."""

    def test_basic_graph(self) -> None:
        """Test resolving a basic graph."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 100, "maximum": 100},
                ),
            ],
        )
        ctx = GenerationContext()
        result = resolve_graph(graph, ctx, TEST_REGISTRY)
        assert Health in result
        assert result[Health].current == 100

    def test_components_with_conditionals(self) -> None:
        """Test components combined with conditionals."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(
                    component_type="Health",
                    fields={"current": 100, "maximum": 100},
                ),
            ],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={"class": "warrior"}),
                    add=[AddOperation(component_type="Armor", fields={"value": 10})],
                    derive=[],
                ),
            ],
        )
        ctx = GenerationContext(params={"class": "warrior"})
        result = resolve_graph(graph, ctx, TEST_REGISTRY)
        assert Health in result
        assert Armor in result

    def test_conditional_adds_modify_context(self) -> None:
        """Test that conditional derive operations modify context for future use."""
        graph = GraphDefinition(
            components=[
                # Component uses a pre-existing param, not the derived value
                ComponentVariant(
                    component_type="Damage",
                    fields={"value": 5},
                ),
            ],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={}),  # Always matches
                    add=[],
                    derive=[
                        DeriveOperation(
                            target="bonus_damage", operation="set", value=10
                        )
                    ],
                ),
            ],
        )
        ctx = GenerationContext()
        result = resolve_graph(graph, ctx, TEST_REGISTRY)

        # The component should be created
        assert Damage in result
        assert result[Damage].value == 5

        # The derive operation should have modified the context
        assert ctx.get_derived("bonus_damage") == 10
