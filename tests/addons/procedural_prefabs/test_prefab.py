"""Tests for procedural prefab data classes."""

import pytest
import pydantic

from relics.addons.procedural_prefabs.prefab import (
    AddOperation,
    AttachmentDefinition,
    ComponentVariant,
    ConditionalBlock,
    DeriveOperation,
    GraphDefinition,
    ParamDefinition,
    ProceduralPrefab,
    WhenClause,
)


class TestParamDefinition:
    """Tests for ParamDefinition."""

    def test_create_basic_param(self) -> None:
        """Test creating a basic parameter."""
        param = ParamDefinition(name="race")
        assert param.name == "race"
        assert param.param_type == "any"  # Default is "any" to accept all types
        assert param.required is False
        assert param.default is None
        assert param.allowed_values is None

    def test_create_required_param(self) -> None:
        """Test creating a required parameter."""
        param = ParamDefinition(name="class", required=True)
        assert param.required is True

    def test_create_param_with_default(self) -> None:
        """Test creating a parameter with default value."""
        param = ParamDefinition(name="level", param_type="int", default=1)
        assert param.default == 1

    def test_create_param_with_allowed_values(self) -> None:
        """Test creating a parameter with allowed values."""
        param = ParamDefinition(
            name="race",
            allowed_values=["human", "elf", "dwarf"],
        )
        assert param.allowed_values == ["human", "elf", "dwarf"]

    def test_validate_value_with_allowed_values(self) -> None:
        """Test value validation with allowed values."""
        param = ParamDefinition(
            name="race",
            allowed_values=["human", "elf", "dwarf"],
        )

        # Valid value
        assert param.validate_value("elf") is True

        # Invalid value
        with pytest.raises(ValueError, match="not in allowed values"):
            param.validate_value("orc")

    def test_validate_value_type_str(self) -> None:
        """Test string type validation."""
        param = ParamDefinition(name="name", param_type="str")

        assert param.validate_value("test") is True

        with pytest.raises(ValueError, match="Expected type 'str'"):
            param.validate_value(123)

    def test_validate_value_type_int(self) -> None:
        """Test integer type validation."""
        param = ParamDefinition(name="count", param_type="int")

        assert param.validate_value(42) is True

        with pytest.raises(ValueError, match="Expected type 'int'"):
            param.validate_value("forty-two")

    def test_validate_value_type_float(self) -> None:
        """Test float type validation."""
        param = ParamDefinition(name="rate", param_type="float")

        assert param.validate_value(3.14) is True
        assert param.validate_value(3) is True  # int is valid for float

        with pytest.raises(ValueError, match="Expected type 'float'"):
            param.validate_value("pi")

    def test_validate_value_type_bool(self) -> None:
        """Test boolean type validation."""
        param = ParamDefinition(name="enabled", param_type="bool")

        assert param.validate_value(True) is True
        assert param.validate_value(False) is True

        with pytest.raises(ValueError, match="Expected type 'bool'"):
            param.validate_value("true")

    def test_validate_value_type_list(self) -> None:
        """Test list type validation."""
        param = ParamDefinition(name="items", param_type="list")

        assert param.validate_value([1, 2, 3]) is True
        assert param.validate_value([]) is True

        with pytest.raises(ValueError, match="Expected type 'list'"):
            param.validate_value("not a list")


class TestWhenClause:
    """Tests for WhenClause."""

    def test_create_when_clause(self) -> None:
        """Test creating a when clause."""
        when = WhenClause(conditions={"race": "elf"})
        assert when.conditions == {"race": "elf"}

    def test_create_multi_condition(self) -> None:
        """Test creating a when clause with multiple conditions."""
        when = WhenClause(conditions={"race": "elf", "class": "mage"})
        assert when.conditions == {"race": "elf", "class": "mage"}


class TestComponentVariant:
    """Tests for ComponentVariant."""

    def test_create_basic_variant(self) -> None:
        """Test creating a basic component variant."""
        variant = ComponentVariant(
            component_type="Health",
            fields={"current": 100, "maximum": 100},
        )
        assert variant.component_type == "Health"
        assert variant.fields == {"current": 100, "maximum": 100}
        assert variant.when is None

    def test_create_conditional_variant(self) -> None:
        """Test creating a conditional component variant."""
        variant = ComponentVariant(
            component_type="Health",
            fields={"current": 150, "maximum": 150},
            when=WhenClause(conditions={"race": "dwarf"}),
        )
        assert variant.when is not None
        assert variant.when.conditions == {"race": "dwarf"}


class TestDeriveOperation:
    """Tests for DeriveOperation."""

    def test_create_set_operation(self) -> None:
        """Test creating a set derive operation."""
        derive = DeriveOperation(target="base_damage", operation="set", value=10)
        assert derive.target == "base_damage"
        assert derive.operation == "set"
        assert derive.value == 10

    def test_create_add_operation(self) -> None:
        """Test creating an add derive operation."""
        derive = DeriveOperation(target="bonus", operation="add", value=5)
        assert derive.operation == "add"

    def test_create_multiply_operation(self) -> None:
        """Test creating a multiply derive operation."""
        derive = DeriveOperation(target="damage", operation="multiply", value=1.5)
        assert derive.operation == "multiply"

    def test_create_append_operation(self) -> None:
        """Test creating an append derive operation."""
        derive = DeriveOperation(target="tags", operation="append", value="warrior")
        assert derive.operation == "append"

    def test_invalid_operation_raises_error(self) -> None:
        """Test that invalid operation raises error."""
        with pytest.raises(ValueError, match="Invalid operation"):
            DeriveOperation(target="x", operation="invalid", value=1)


class TestAddOperation:
    """Tests for AddOperation."""

    def test_create_add_operation(self) -> None:
        """Test creating an add operation."""
        add = AddOperation(
            component_type="Buff",
            fields={"name": "strength", "amount": 5},
        )
        assert add.component_type == "Buff"
        assert add.fields == {"name": "strength", "amount": 5}


class TestConditionalBlock:
    """Tests for ConditionalBlock."""

    def test_create_conditional_block(self) -> None:
        """Test creating a conditional block."""
        block = ConditionalBlock(
            when=WhenClause(conditions={"class": "warrior"}),
            add=[AddOperation(component_type="Armor", fields={"value": 10})],
            derive=[DeriveOperation(target="strength", operation="add", value=5)],
        )
        assert block.when.conditions == {"class": "warrior"}
        assert len(block.add) == 1
        assert len(block.derive) == 1

    def test_create_conditional_block_empty_lists(self) -> None:
        """Test creating a conditional block with empty lists."""
        block = ConditionalBlock(
            when=WhenClause(conditions={"x": "y"}),
            add=[],
            derive=[],
        )
        assert len(block.add) == 0
        assert len(block.derive) == 0


class TestAttachmentDefinition:
    """Tests for AttachmentDefinition."""

    def test_create_static_attachment(self) -> None:
        """Test creating a static prefab attachment."""
        att = AttachmentDefinition(
            prefab="sword",
            edge_type="HasEquipped",
            slot="main_hand",
        )
        assert att.prefab == "sword"
        assert att.edge_type == "HasEquipped"
        assert att.slot == "main_hand"
        assert att.from_list is None

    def test_create_list_attachment(self) -> None:
        """Test creating a list-based attachment."""
        att = AttachmentDefinition(
            from_list="weapons_sword",
            edge_type="HasEquipped",
            slot="main_hand",
        )
        assert att.from_list == "weapons_sword"
        assert att.prefab is None

    def test_create_skip_attachment(self) -> None:
        """Test creating a skip attachment."""
        att = AttachmentDefinition(skip=True)
        assert att.skip is True

    def test_attachment_defaults(self) -> None:
        """Test attachment default values."""
        att = AttachmentDefinition(prefab="test")
        assert att.edge_type == "HasAttached"
        assert att.slot == "default"
        assert att.inherit_params is None
        assert att.override_params is None
        assert att.optional is False
        assert att.skip is False

    def test_attachment_with_inherit_params(self) -> None:
        """Test attachment with param inheritance."""
        att = AttachmentDefinition(
            prefab="armor",
            inherit_params=["quality", "material"],
        )
        assert att.inherit_params == ["quality", "material"]

    def test_attachment_with_override_params(self) -> None:
        """Test attachment with param overrides."""
        att = AttachmentDefinition(
            prefab="weapon",
            override_params={"damage_type": "fire"},
        )
        assert att.override_params == {"damage_type": "fire"}

    def test_attachment_requires_prefab_or_list_or_skip(self) -> None:
        """Test that attachment requires prefab, from_list, or skip."""
        with pytest.raises(ValueError, match="must have"):
            AttachmentDefinition()

    def test_attachment_cannot_have_both_prefab_and_list(self) -> None:
        """Test that attachment cannot have both prefab and from_list."""
        with pytest.raises(ValueError, match="cannot have both"):
            AttachmentDefinition(prefab="sword", from_list="weapons")


class TestGraphDefinition:
    """Tests for GraphDefinition."""

    def test_create_basic_graph(self) -> None:
        """Test creating a basic graph definition."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(component_type="Health", fields={"current": 100}),
            ],
        )
        assert len(graph.components) == 1
        assert graph.conditionals is None
        assert graph.attachments is None
        assert graph.lists is None

    def test_create_full_graph(self) -> None:
        """Test creating a full graph definition."""
        graph = GraphDefinition(
            components=[
                ComponentVariant(component_type="Health", fields={"current": 100}),
            ],
            conditionals=[
                ConditionalBlock(
                    when=WhenClause(conditions={"x": "y"}),
                    add=[],
                    derive=[],
                ),
            ],
            attachments=[
                AttachmentDefinition(prefab="weapon", slot="hand"),
            ],
            lists={"weapons": ["sword", "axe"]},
        )
        assert len(graph.components) == 1
        assert len(graph.conditionals) == 1
        assert len(graph.attachments) == 1
        assert graph.lists == {"weapons": ["sword", "axe"]}


class TestProceduralPrefab:
    """Tests for ProceduralPrefab."""

    def test_create_basic_prefab(self) -> None:
        """Test creating a basic procedural prefab."""
        prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(components=[]),
        )
        assert prefab.name == "character"
        assert prefab.params == []
        assert prefab.base_prefab is None

    def test_create_prefab_with_params(self) -> None:
        """Test creating a prefab with parameters."""
        prefab = ProceduralPrefab(
            name="character",
            params=[
                ParamDefinition(name="race", required=True),
                ParamDefinition(name="level", default=1),
            ],
            graph=GraphDefinition(components=[]),
        )
        assert len(prefab.params) == 2

    def test_get_param(self) -> None:
        """Test getting a parameter by name."""
        prefab = ProceduralPrefab(
            name="character",
            params=[
                ParamDefinition(name="race"),
                ParamDefinition(name="class"),
            ],
            graph=GraphDefinition(components=[]),
        )
        param = prefab.get_param("race")
        assert param is not None
        assert param.name == "race"

        # Non-existent param
        assert prefab.get_param("missing") is None

    def test_get_required_params(self) -> None:
        """Test getting required parameters."""
        prefab = ProceduralPrefab(
            name="character",
            params=[
                ParamDefinition(name="race", required=True),
                ParamDefinition(name="class", required=True),
                ParamDefinition(name="level", required=False),
            ],
            graph=GraphDefinition(components=[]),
        )
        required = prefab.get_required_params()
        assert len(required) == 2
        assert all(p.required for p in required)

    def test_prefab_with_base(self) -> None:
        """Test creating a prefab with base prefab."""
        prefab = ProceduralPrefab(
            name="warrior",
            params=[],
            graph=GraphDefinition(components=[]),
            base_prefab="character",
        )
        assert prefab.base_prefab == "character"
