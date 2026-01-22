"""Tests for utility functions."""

import pytest
import pydantic.dataclasses

from relics import World
from relics.types import Component

from relics.addons.procedural_prefabs.edges import HasAttached, HasEquipped, IsWearing
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


# Test components
@pydantic.dataclasses.dataclass
class Name(Component):
    value: str


class TestDefaultEdgeTypes:
    """Tests for DEFAULT_EDGE_TYPES."""

    def test_contains_all_attachment_types(self) -> None:
        """Test that DEFAULT_EDGE_TYPES contains all attachment types."""
        assert HasEquipped in DEFAULT_EDGE_TYPES
        assert IsWearing in DEFAULT_EDGE_TYPES
        assert HasAttached in DEFAULT_EDGE_TYPES


class TestGetChildren:
    """Tests for get_children and get_child_ids."""

    def test_no_children(self) -> None:
        """Test entity with no children."""
        world = World()
        world.register_prefab("test", {Name: Name(value="parent")})
        parent = world.spawn("test")

        children = list(get_children(parent))
        assert children == []

    def test_single_child(self) -> None:
        """Test entity with single child."""
        world = World()
        world.register_prefab("parent", {Name: Name(value="parent")})
        world.register_prefab("child", {Name: Name(value="child")})

        parent = world.spawn("parent")
        child = world.spawn("child")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        children = list(get_children(parent))
        assert len(children) == 1
        assert children[0].id == child.id

    def test_multiple_children(self) -> None:
        """Test entity with multiple children."""
        world = World()
        world.register_prefab("parent", {Name: Name(value="parent")})
        world.register_prefab("child", {Name: Name(value="child")})

        parent = world.spawn("parent")
        child1 = world.spawn("child")
        child2 = world.spawn("child")

        parent.add_relationship(HasEquipped(slot="hand1"), child1.id)
        parent.add_relationship(HasEquipped(slot="hand2"), child2.id)

        children = list(get_children(parent))
        assert len(children) == 2

    def test_filter_by_edge_type(self) -> None:
        """Test filtering children by edge type."""
        world = World()
        world.register_prefab("parent", {Name: Name(value="parent")})
        world.register_prefab("child", {Name: Name(value="child")})

        parent = world.spawn("parent")
        equipped = world.spawn("child")
        wearing = world.spawn("child")

        parent.add_relationship(HasEquipped(slot="hand"), equipped.id)
        parent.add_relationship(IsWearing(slot="head"), wearing.id)

        # Filter by HasEquipped
        equipped_children = list(get_children(parent, HasEquipped))
        assert len(equipped_children) == 1
        assert equipped_children[0].id == equipped.id

        # Filter by IsWearing
        wearing_children = list(get_children(parent, IsWearing))
        assert len(wearing_children) == 1
        assert wearing_children[0].id == wearing.id

    def test_get_child_ids(self) -> None:
        """Test get_child_ids function."""
        world = World()
        world.register_prefab("parent", {Name: Name(value="parent")})
        world.register_prefab("child", {Name: Name(value="child")})

        parent = world.spawn("parent")
        child = world.spawn("child")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        child_ids = list(get_child_ids(parent))
        assert len(child_ids) == 1
        assert child_ids[0] == child.id


class TestGetHolder:
    """Tests for get_holder and get_holder_id."""

    def test_no_holder(self) -> None:
        """Test entity with no holder."""
        world = World()
        world.register_prefab("test", {Name: Name(value="test")})
        entity = world.spawn("test")

        assert get_holder(entity) is None
        assert get_holder_id(entity) is None

    def test_has_holder(self) -> None:
        """Test entity with a holder."""
        world = World()
        world.register_prefab("parent", {Name: Name(value="parent")})
        world.register_prefab("child", {Name: Name(value="child")})

        parent = world.spawn("parent")
        child = world.spawn("child")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        holder = get_holder(child)
        assert holder is not None
        assert holder.id == parent.id

    def test_get_holder_id(self) -> None:
        """Test get_holder_id function."""
        world = World()
        world.register_prefab("parent", {Name: Name(value="parent")})
        world.register_prefab("child", {Name: Name(value="child")})

        parent = world.spawn("parent")
        child = world.spawn("child")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        holder_id = get_holder_id(child)
        assert holder_id == parent.id

    def test_filter_by_edge_type(self) -> None:
        """Test filtering holder by edge type."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        holder1 = world.spawn("entity")
        holder2 = world.spawn("entity")
        child = world.spawn("entity")

        holder1.add_relationship(HasEquipped(slot="hand"), child.id)
        holder2.add_relationship(IsWearing(slot="head"), child.id)

        # Filter by HasEquipped
        h1 = get_holder(child, HasEquipped)
        assert h1 is not None
        assert h1.id == holder1.id

        # Filter by IsWearing
        h2 = get_holder(child, IsWearing)
        assert h2 is not None
        assert h2.id == holder2.id


class TestDetach:
    """Tests for detach function."""

    def test_detach_from_holder(self) -> None:
        """Test detaching an entity from its holder."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child = world.spawn("entity")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        # Verify attached
        assert get_holder(child) is not None

        # Detach
        result = detach(child)
        assert result is not None
        holder_id, edge = result
        assert holder_id == parent.id
        assert edge.slot == "hand"

        # Verify detached
        assert get_holder(child) is None

    def test_detach_not_attached(self) -> None:
        """Test detaching an entity that's not attached."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        entity = world.spawn("entity")
        result = detach(entity)
        assert result is None

    def test_detach_specific_edge_type(self) -> None:
        """Test detaching from specific edge type."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        holder1 = world.spawn("entity")
        holder2 = world.spawn("entity")
        child = world.spawn("entity")

        holder1.add_relationship(HasEquipped(slot="hand"), child.id)
        holder2.add_relationship(IsWearing(slot="head"), child.id)

        # Detach only from HasEquipped
        result = detach(child, HasEquipped)
        assert result is not None
        assert result[0] == holder1.id

        # Should still be attached via IsWearing
        assert get_holder(child, IsWearing) is not None


class TestDestroyWithChildren:
    """Tests for destroy_with_children function."""

    def test_destroy_single_entity(self) -> None:
        """Test destroying a single entity."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        entity = world.spawn("entity")
        entity_id = entity.id

        count = destroy_with_children(world, entity)
        assert count == 1
        assert not world.has_entity(entity_id)

    def test_destroy_with_children_recursive(self) -> None:
        """Test recursive destruction of children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        grandparent = world.spawn("entity")
        parent = world.spawn("entity")
        child = world.spawn("entity")

        grandparent.add_relationship(HasEquipped(slot="slot1"), parent.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child.id)

        grandparent_id = grandparent.id
        parent_id = parent.id
        child_id = child.id

        count = destroy_with_children(world, grandparent, recursive=True)

        assert count == 3
        assert not world.has_entity(grandparent_id)
        assert not world.has_entity(parent_id)
        assert not world.has_entity(child_id)

    def test_destroy_non_recursive(self) -> None:
        """Test non-recursive destruction."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        grandparent = world.spawn("entity")
        parent = world.spawn("entity")
        child = world.spawn("entity")

        grandparent.add_relationship(HasEquipped(slot="slot1"), parent.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child.id)

        grandparent_id = grandparent.id
        parent_id = parent.id
        child_id = child.id

        count = destroy_with_children(world, grandparent, recursive=False)

        assert count == 2  # grandparent + parent
        assert not world.has_entity(grandparent_id)
        assert not world.has_entity(parent_id)
        # Child should still exist (was not recursively destroyed)
        # Note: Actually, since parent was destroyed, child's relationship
        # to parent is removed, but the child entity itself remains
        assert world.has_entity(child_id)


class TestGetChildrenRecursive:
    """Tests for get_children_recursive."""

    def test_no_children(self) -> None:
        """Test with no children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        entity = world.spawn("entity")
        children = list(get_children_recursive(entity))
        assert children == []

    def test_single_level(self) -> None:
        """Test with single level of children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child1 = world.spawn("entity")
        child2 = world.spawn("entity")

        parent.add_relationship(HasEquipped(slot="slot1"), child1.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child2.id)

        children = list(get_children_recursive(parent))
        assert len(children) == 2

    def test_multiple_levels(self) -> None:
        """Test with multiple levels of children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        grandparent = world.spawn("entity")
        parent = world.spawn("entity")
        child1 = world.spawn("entity")
        child2 = world.spawn("entity")

        grandparent.add_relationship(HasEquipped(slot="slot1"), parent.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child1.id)
        parent.add_relationship(HasEquipped(slot="slot3"), child2.id)

        descendants = list(get_children_recursive(grandparent))
        assert len(descendants) == 3  # parent + child1 + child2

    def test_get_all_children_ids(self) -> None:
        """Test get_all_children_ids function."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        grandparent = world.spawn("entity")
        parent = world.spawn("entity")
        child = world.spawn("entity")

        grandparent.add_relationship(HasEquipped(slot="slot1"), parent.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child.id)

        ids = get_all_children_ids(grandparent)
        assert len(ids) == 2
        assert parent.id in ids
        assert child.id in ids


class TestGetRoot:
    """Tests for get_root function."""

    def test_root_is_self(self) -> None:
        """Test when entity is its own root."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        entity = world.spawn("entity")
        root = get_root(entity)
        assert root.id == entity.id

    def test_find_root(self) -> None:
        """Test finding root in hierarchy."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        grandparent = world.spawn("entity")
        parent = world.spawn("entity")
        child = world.spawn("entity")

        grandparent.add_relationship(HasEquipped(slot="slot1"), parent.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child.id)

        # All should have grandparent as root
        assert get_root(child).id == grandparent.id
        assert get_root(parent).id == grandparent.id
        assert get_root(grandparent).id == grandparent.id


class TestGetSlot:
    """Tests for get_slot function."""

    def test_not_attached(self) -> None:
        """Test get_slot when not attached."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        entity = world.spawn("entity")
        assert get_slot(entity) is None

    def test_attached_with_slot(self) -> None:
        """Test get_slot when attached."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child = world.spawn("entity")
        parent.add_relationship(HasEquipped(slot="main_hand"), child.id)

        assert get_slot(child) == "main_hand"
