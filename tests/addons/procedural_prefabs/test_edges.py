"""Tests for edge types."""

import pytest

from relics.types import Edge

from relics.addons.procedural_prefabs.edges import (
    EDGE_TYPE_MAP,
    HasAttached,
    HasEquipped,
    IsWearing,
    create_edge,
    get_edge_class,
    register_edge_type,
)


class TestHasEquipped:
    """Tests for HasEquipped edge."""

    def test_create_default_slot(self) -> None:
        """Test creating HasEquipped with default slot."""
        edge = HasEquipped()
        assert edge.slot == "default"

    def test_create_with_slot(self) -> None:
        """Test creating HasEquipped with specific slot."""
        edge = HasEquipped(slot="main_hand")
        assert edge.slot == "main_hand"

    def test_is_edge(self) -> None:
        """Test that HasEquipped is an Edge."""
        edge = HasEquipped()
        assert isinstance(edge, Edge)


class TestIsWearing:
    """Tests for IsWearing edge."""

    def test_create_default_slot(self) -> None:
        """Test creating IsWearing with default slot."""
        edge = IsWearing()
        assert edge.slot == "default"

    def test_create_with_slot(self) -> None:
        """Test creating IsWearing with specific slot."""
        edge = IsWearing(slot="chest")
        assert edge.slot == "chest"

    def test_is_edge(self) -> None:
        """Test that IsWearing is an Edge."""
        edge = IsWearing()
        assert isinstance(edge, Edge)


class TestHasAttached:
    """Tests for HasAttached edge."""

    def test_create_default_slot(self) -> None:
        """Test creating HasAttached with default slot."""
        edge = HasAttached()
        assert edge.slot == "default"

    def test_create_with_slot(self) -> None:
        """Test creating HasAttached with specific slot."""
        edge = HasAttached(slot="accessory")
        assert edge.slot == "accessory"

    def test_is_edge(self) -> None:
        """Test that HasAttached is an Edge."""
        edge = HasAttached()
        assert isinstance(edge, Edge)


class TestEdgeTypeMap:
    """Tests for EDGE_TYPE_MAP."""

    def test_contains_all_builtin_types(self) -> None:
        """Test that map contains all built-in edge types."""
        assert "HasEquipped" in EDGE_TYPE_MAP
        assert "IsWearing" in EDGE_TYPE_MAP
        assert "HasAttached" in EDGE_TYPE_MAP

    def test_maps_to_correct_classes(self) -> None:
        """Test that map maps to correct classes."""
        assert EDGE_TYPE_MAP["HasEquipped"] is HasEquipped
        assert EDGE_TYPE_MAP["IsWearing"] is IsWearing
        assert EDGE_TYPE_MAP["HasAttached"] is HasAttached


class TestGetEdgeClass:
    """Tests for get_edge_class."""

    def test_get_existing_type(self) -> None:
        """Test getting an existing edge type."""
        assert get_edge_class("HasEquipped") is HasEquipped
        assert get_edge_class("IsWearing") is IsWearing
        assert get_edge_class("HasAttached") is HasAttached

    def test_get_unknown_type(self) -> None:
        """Test getting an unknown edge type raises KeyError."""
        with pytest.raises(KeyError, match="Unknown edge type"):
            get_edge_class("Unknown")


class TestCreateEdge:
    """Tests for create_edge."""

    def test_create_equipped(self) -> None:
        """Test creating HasEquipped edge."""
        edge = create_edge("HasEquipped", "main_hand")
        assert isinstance(edge, HasEquipped)
        assert edge.slot == "main_hand"

    def test_create_wearing(self) -> None:
        """Test creating IsWearing edge."""
        edge = create_edge("IsWearing", "head")
        assert isinstance(edge, IsWearing)
        assert edge.slot == "head"

    def test_create_attached(self) -> None:
        """Test creating HasAttached edge."""
        edge = create_edge("HasAttached", "custom")
        assert isinstance(edge, HasAttached)
        assert edge.slot == "custom"

    def test_create_unknown_type(self) -> None:
        """Test creating unknown edge type raises KeyError."""
        with pytest.raises(KeyError, match="Unknown edge type"):
            create_edge("Unknown", "slot")


class TestRegisterEdgeType:
    """Tests for register_edge_type."""

    def test_register_custom_type(self) -> None:
        """Test registering a custom edge type."""
        import pydantic.dataclasses

        @pydantic.dataclasses.dataclass
        class CustomEdge(Edge):
            slot: str = "default"
            custom_field: str = "value"

        register_edge_type("CustomEdge", CustomEdge)

        assert "CustomEdge" in EDGE_TYPE_MAP
        assert get_edge_class("CustomEdge") is CustomEdge

        edge = create_edge("CustomEdge", "test_slot")
        assert isinstance(edge, CustomEdge)
        assert edge.slot == "test_slot"

        # Clean up
        del EDGE_TYPE_MAP["CustomEdge"]

    def test_register_overwrites_existing(self) -> None:
        """Test that registering overwrites existing type."""
        import pydantic.dataclasses

        @pydantic.dataclasses.dataclass
        class NewHasEquipped(Edge):
            slot: str = "default"
            new_field: bool = True

        original = EDGE_TYPE_MAP["HasEquipped"]
        register_edge_type("HasEquipped", NewHasEquipped)

        assert EDGE_TYPE_MAP["HasEquipped"] is NewHasEquipped

        # Restore original
        EDGE_TYPE_MAP["HasEquipped"] = original
