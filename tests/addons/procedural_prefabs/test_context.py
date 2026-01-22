"""Tests for GenerationContext."""

import pytest

from relics.addons.procedural_prefabs.context import GenerationContext


class TestGenerationContextBasics:
    """Tests for basic GenerationContext operations."""

    def test_create_empty_context(self) -> None:
        """Test creating an empty context."""
        ctx = GenerationContext()
        assert ctx.params == {}
        assert ctx.derived == {}

    def test_create_context_with_params(self) -> None:
        """Test creating a context with parameters."""
        ctx = GenerationContext(params={"race": "elf", "class": "mage"})
        assert ctx.params == {"race": "elf", "class": "mage"}

    def test_create_context_with_derived(self) -> None:
        """Test creating a context with derived values."""
        ctx = GenerationContext(derived={"base_damage": 10})
        assert ctx.derived == {"base_damage": 10}

    def test_params_are_copied(self) -> None:
        """Test that params are copied, not referenced."""
        original = {"race": "elf"}
        ctx = GenerationContext(params=original)
        original["race"] = "dwarf"
        assert ctx.params["race"] == "elf"

    def test_get_param(self) -> None:
        """Test getting a parameter value."""
        ctx = GenerationContext(params={"race": "elf"})
        assert ctx.get_param("race") == "elf"
        assert ctx.get_param("missing") is None
        assert ctx.get_param("missing", "default") == "default"

    def test_get_derived(self) -> None:
        """Test getting a derived value."""
        ctx = GenerationContext(derived={"damage": 10})
        assert ctx.get_derived("damage") == 10
        assert ctx.get_derived("missing") is None
        assert ctx.get_derived("missing", 0) == 0


class TestGenerationContextDerivedOperations:
    """Tests for derived value operations."""

    def test_set_derived(self) -> None:
        """Test setting a derived value."""
        ctx = GenerationContext()
        ctx.set_derived("damage", 10)
        assert ctx.get_derived("damage") == 10

    def test_set_derived_overwrites(self) -> None:
        """Test that set_derived overwrites existing values."""
        ctx = GenerationContext(derived={"damage": 10})
        ctx.set_derived("damage", 20)
        assert ctx.get_derived("damage") == 20

    def test_add_derived(self) -> None:
        """Test adding to a derived value."""
        ctx = GenerationContext(derived={"damage": 10})
        ctx.add_derived("damage", 5)
        assert ctx.get_derived("damage") == 15

    def test_add_derived_creates_if_missing(self) -> None:
        """Test that add_derived creates value if missing."""
        ctx = GenerationContext()
        ctx.add_derived("damage", 5)
        assert ctx.get_derived("damage") == 5

    def test_add_derived_type_error(self) -> None:
        """Test that add_derived raises on non-numeric."""
        ctx = GenerationContext(derived={"name": "test"})
        with pytest.raises(TypeError, match="non-numeric"):
            ctx.add_derived("name", 5)

    def test_multiply_derived(self) -> None:
        """Test multiplying a derived value."""
        ctx = GenerationContext(derived={"damage": 10})
        ctx.multiply_derived("damage", 2)
        assert ctx.get_derived("damage") == 20

    def test_multiply_derived_creates_if_missing(self) -> None:
        """Test that multiply_derived uses 1 as default."""
        ctx = GenerationContext()
        ctx.multiply_derived("multiplier", 5)
        assert ctx.get_derived("multiplier") == 5

    def test_multiply_derived_type_error(self) -> None:
        """Test that multiply_derived raises on non-numeric."""
        ctx = GenerationContext(derived={"name": "test"})
        with pytest.raises(TypeError, match="non-numeric"):
            ctx.multiply_derived("name", 2)

    def test_append_derived(self) -> None:
        """Test appending to a derived list."""
        ctx = GenerationContext(derived={"tags": ["warrior"]})
        ctx.append_derived("tags", "strong")
        assert ctx.get_derived("tags") == ["warrior", "strong"]

    def test_append_derived_creates_list(self) -> None:
        """Test that append_derived creates list if missing."""
        ctx = GenerationContext()
        ctx.append_derived("tags", "warrior")
        assert ctx.get_derived("tags") == ["warrior"]

    def test_append_derived_type_error(self) -> None:
        """Test that append_derived raises on non-list."""
        ctx = GenerationContext(derived={"name": "test"})
        with pytest.raises(TypeError, match="non-list"):
            ctx.append_derived("name", "suffix")


class TestGenerationContextValueResolution:
    """Tests for value resolution with @param syntax."""

    def test_resolve_simple_string(self) -> None:
        """Test resolving a simple string (no params)."""
        ctx = GenerationContext()
        assert ctx.resolve_value("hello") == "hello"

    def test_resolve_single_param(self) -> None:
        """Test resolving a single @param reference."""
        ctx = GenerationContext(params={"race": "elf"})
        assert ctx.resolve_value("@race") == "elf"

    def test_resolve_param_preserves_type(self) -> None:
        """Test that single @param preserves value type."""
        ctx = GenerationContext(params={"level": 10, "enabled": True})
        assert ctx.resolve_value("@level") == 10
        assert ctx.resolve_value("@enabled") is True

    def test_resolve_param_in_string(self) -> None:
        """Test resolving @param within a larger string."""
        ctx = GenerationContext(params={"race": "elf"})
        assert ctx.resolve_value("weapons_@race") == "weapons_elf"

    def test_resolve_multiple_params(self) -> None:
        """Test resolving multiple @params in string."""
        ctx = GenerationContext(params={"race": "elf", "cls": "mage"})
        # Note: @class won't work because "class" is followed by underscore
        # The pattern matches word characters only
        assert ctx.resolve_value("@race-@cls") == "elf-mage"

    def test_resolve_derived_value(self) -> None:
        """Test resolving @derived reference."""
        ctx = GenerationContext(derived={"bonus": 5})
        assert ctx.resolve_value("@bonus") == 5

    def test_derived_takes_precedence(self) -> None:
        """Test that derived values take precedence over params."""
        ctx = GenerationContext(
            params={"value": "from_param"},
            derived={"value": "from_derived"},
        )
        assert ctx.resolve_value("@value") == "from_derived"

    def test_resolve_missing_param_unchanged(self) -> None:
        """Test that missing @param is left unchanged in string."""
        ctx = GenerationContext()
        assert ctx.resolve_value("prefix_@missing_suffix") == "prefix_@missing_suffix"

    def test_resolve_missing_single_param(self) -> None:
        """Test that missing single @param returns None."""
        ctx = GenerationContext()
        assert ctx.resolve_value("@missing") is None

    def test_resolve_dict(self) -> None:
        """Test resolving @params in a dictionary."""
        ctx = GenerationContext(params={"damage": 10})
        result = ctx.resolve_value({"value": "@damage", "type": "fire"})
        assert result == {"value": 10, "type": "fire"}

    def test_resolve_list(self) -> None:
        """Test resolving @params in a list."""
        ctx = GenerationContext(params={"a": 1, "b": 2})
        result = ctx.resolve_value(["@a", "@b", "static"])
        assert result == [1, 2, "static"]

    def test_resolve_nested(self) -> None:
        """Test resolving @params in nested structures."""
        ctx = GenerationContext(params={"x": 10})
        result = ctx.resolve_value(
            {
                "outer": {
                    "inner": "@x",
                },
                "list": ["@x", "@x"],
            }
        )
        assert result == {
            "outer": {"inner": 10},
            "list": [10, 10],
        }


class TestGenerationContextAllValues:
    """Tests for get_all_values."""

    def test_get_all_values_empty(self) -> None:
        """Test get_all_values with empty context."""
        ctx = GenerationContext()
        assert ctx.get_all_values() == {}

    def test_get_all_values_params_only(self) -> None:
        """Test get_all_values with params only."""
        ctx = GenerationContext(params={"race": "elf"})
        assert ctx.get_all_values() == {"race": "elf"}

    def test_get_all_values_derived_only(self) -> None:
        """Test get_all_values with derived only."""
        ctx = GenerationContext(derived={"bonus": 5})
        assert ctx.get_all_values() == {"bonus": 5}

    def test_get_all_values_merged(self) -> None:
        """Test get_all_values merges params and derived."""
        ctx = GenerationContext(
            params={"race": "elf"},
            derived={"bonus": 5},
        )
        assert ctx.get_all_values() == {"race": "elf", "bonus": 5}

    def test_get_all_values_derived_precedence(self) -> None:
        """Test that derived takes precedence in get_all_values."""
        ctx = GenerationContext(
            params={"value": "param"},
            derived={"value": "derived"},
        )
        assert ctx.get_all_values() == {"value": "derived"}


class TestGenerationContextChildContext:
    """Tests for child_context creation."""

    def test_child_context_inherits_all(self) -> None:
        """Test that child context inherits all by default."""
        ctx = GenerationContext(
            params={"race": "elf", "class": "mage"},
            derived={"bonus": 5},
        )
        child = ctx.child_context()
        # Params and derived are merged into child params
        assert child.get_param("race") == "elf"
        assert child.get_param("class") == "mage"
        assert child.get_param("bonus") == 5

    def test_child_context_selective_inherit(self) -> None:
        """Test selective parameter inheritance."""
        ctx = GenerationContext(
            params={"race": "elf", "class": "mage", "level": 10},
        )
        child = ctx.child_context(inherit_params=["race", "level"])
        assert child.get_param("race") == "elf"
        assert child.get_param("level") == 10
        assert child.get_param("class") is None

    def test_child_context_override_params(self) -> None:
        """Test overriding parameters in child."""
        ctx = GenerationContext(params={"race": "elf", "level": 10})
        child = ctx.child_context(override_params={"level": 20, "bonus": 5})
        assert child.get_param("race") == "elf"
        assert child.get_param("level") == 20
        assert child.get_param("bonus") == 5

    def test_child_context_override_with_param_ref(self) -> None:
        """Test overriding with @param references."""
        ctx = GenerationContext(params={"race": "elf", "quality": "high"})
        child = ctx.child_context(override_params={"material": "@quality"})
        assert child.get_param("material") == "high"

    def test_child_context_fresh_derived(self) -> None:
        """Test that child context has fresh derived dict."""
        ctx = GenerationContext(derived={"bonus": 5})
        child = ctx.child_context()
        child.set_derived("new_value", 10)
        # Parent derived should not be affected
        assert ctx.get_derived("new_value") is None


class TestGenerationContextCopy:
    """Tests for context copying."""

    def test_copy_creates_independent(self) -> None:
        """Test that copy creates independent context."""
        ctx = GenerationContext(
            params={"race": "elf"},
            derived={"bonus": 5},
        )
        copy = ctx.copy()

        # Modify original
        ctx.set_derived("bonus", 10)

        # Copy should be unchanged
        assert copy.get_derived("bonus") == 5

    def test_copy_deep_copies_nested(self) -> None:
        """Test that copy deep copies nested structures."""
        ctx = GenerationContext(
            params={"items": ["sword", "shield"]},
        )
        copy = ctx.copy()

        # This should not affect copy
        ctx._params["items"].append("bow")

        assert copy.get_param("items") == ["sword", "shield"]
