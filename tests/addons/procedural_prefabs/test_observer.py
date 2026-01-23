"""Tests for DestroyChildrenObserver and cascade deletion utilities."""

import pydantic.dataclasses

from relics import World
from relics.addons.procedural_prefabs.edges import HasEquipped
from relics.addons.procedural_prefabs.observer import (
    DestroyChildrenObserver,
    create_cascade_observer,
)
from relics.addons.procedural_prefabs.utils import destroy_with_children
from relics.types import Component


# Test components
@pydantic.dataclasses.dataclass
class Name(Component):
    value: str


class TestDestroyWithChildren:
    """Tests for destroy_with_children utility function.

    The utility function is the recommended approach for cascade deletion
    as it works synchronously and doesn't depend on observer event timing.
    """

    def test_cascade_deletes_children(self) -> None:
        """Test that destroying parent cascades to children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child = world.spawn("entity")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        parent_id = parent.id
        child_id = child.id

        # Use destroy_with_children for reliable cascade deletion
        destroy_with_children(world, parent)

        # Both should be gone
        assert not world.has_entity(parent_id)
        assert not world.has_entity(child_id)

    def test_cascade_recursive(self) -> None:
        """Test recursive cascade deletion."""
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

        # Destroy grandparent with recursive=True (default)
        destroy_with_children(world, grandparent, recursive=True)

        # All should be gone
        assert not world.has_entity(grandparent_id)
        assert not world.has_entity(parent_id)
        assert not world.has_entity(child_id)

    def test_cascade_non_recursive(self) -> None:
        """Test non-recursive cascade deletion."""
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

        # Destroy grandparent with recursive=False
        destroy_with_children(world, grandparent, recursive=False)

        # Grandparent and immediate child should be gone
        assert not world.has_entity(grandparent_id)
        assert not world.has_entity(parent_id)
        # Grandchild should remain (non-recursive)
        assert world.has_entity(child_id)

    def test_no_children(self) -> None:
        """Test destroying entity without children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})
        entity = world.spawn("entity")
        entity_id = entity.id

        # Should not raise
        count = destroy_with_children(world, entity)

        assert count == 1
        assert not world.has_entity(entity_id)

    def test_multiple_children(self) -> None:
        """Test handling multiple children."""
        world = World()
        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child1 = world.spawn("entity")
        child2 = world.spawn("entity")
        child3 = world.spawn("entity")

        parent.add_relationship(HasEquipped(slot="slot1"), child1.id)
        parent.add_relationship(HasEquipped(slot="slot2"), child2.id)
        parent.add_relationship(HasEquipped(slot="slot3"), child3.id)

        parent_id = parent.id
        child1_id = child1.id
        child2_id = child2.id
        child3_id = child3.id

        count = destroy_with_children(world, parent)

        assert count == 4
        assert not world.has_entity(parent_id)
        assert not world.has_entity(child1_id)
        assert not world.has_entity(child2_id)
        assert not world.has_entity(child3_id)


class TestDestroyChildrenObserver:
    """Tests for DestroyChildrenObserver class.

    Note: The async observer has limitations due to event timing.
    The observer is notified after relationships are cleaned up,
    so it needs to maintain its own relationship cache.
    """

    def test_create_default_observer(self) -> None:
        """Test creating default cascade observer."""
        observer = create_cascade_observer()
        assert isinstance(observer, DestroyChildrenObserver)
        assert observer._recursive is True
        assert len(observer._edge_types) == 3  # All default types

    def test_create_with_edge_types(self) -> None:
        """Test creating observer with specific edge types."""
        observer = create_cascade_observer(edge_types=[HasEquipped])
        assert observer._edge_types == [HasEquipped]

    def test_create_non_recursive(self) -> None:
        """Test creating non-recursive observer."""
        observer = create_cascade_observer(recursive=False)
        assert observer._recursive is False

    def test_create_with_prefab_filter(self) -> None:
        """Test creating observer with prefab filter."""
        observer = create_cascade_observer(prefab="character")
        # Should create a subclass with prefab set
        assert observer.prefab == "character"

    def test_observer_cache_relationship(self) -> None:
        """Test that observer can cache relationships."""
        observer = DestroyChildrenObserver()

        from relics.types import EntityId

        parent_id = EntityId(prefab="parent", sequence=1)
        child_id = EntityId(prefab="child", sequence=2)

        observer._cache_relationship(parent_id, child_id)

        key = str(parent_id)
        assert key in observer._relationship_cache
        assert child_id in observer._relationship_cache[key]

    def test_observer_uncache_relationship(self) -> None:
        """Test that observer can uncache relationships."""
        observer = DestroyChildrenObserver()

        from relics.types import EntityId

        parent_id = EntityId(prefab="parent", sequence=1)
        child_id = EntityId(prefab="child", sequence=2)

        observer._cache_relationship(parent_id, child_id)
        observer._uncache_relationship(parent_id, child_id)

        key = str(parent_id)
        assert key in observer._relationship_cache
        assert child_id not in observer._relationship_cache[key]


class TestObserverWithManualCache:
    """Tests demonstrating observer with manually cached relationships.

    The async observer requires manual relationship caching to work correctly.
    This is the workaround for the event timing limitation.
    """

    def test_cascade_with_cached_relationships(self) -> None:
        """Test cascade deletion with manually cached relationships."""
        world = World()
        observer = DestroyChildrenObserver()
        world.observe(observer)

        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child = world.spawn("entity")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        # Manually cache the relationship for the observer
        observer._cache_relationship(parent.id, child.id)

        parent_id = parent.id
        child_id = child.id

        # Destroy parent
        world.remove(parent)
        world.tick(0)

        # Both should be gone because we cached the relationship
        assert not world.has_entity(parent_id)
        assert not world.has_entity(child_id)

    def test_cascade_recursive_with_cache(self) -> None:
        """Test recursive cascade with cached relationships.

        Note: The async observer has limitations with deep recursion.
        Child deletions are triggered within the same tick, but their
        own children may not be processed if events are batched.

        For deep hierarchies, use destroy_with_children() instead.
        """
        world = World()
        observer = DestroyChildrenObserver(recursive=True)
        world.observe(observer)

        world.register_prefab("entity", {Name: Name(value="entity")})

        grandparent = world.spawn("entity")
        parent = world.spawn("entity")

        grandparent.add_relationship(HasEquipped(slot="slot1"), parent.id)

        # Cache the relationship
        observer._cache_relationship(grandparent.id, parent.id)

        grandparent_id = grandparent.id
        parent_id = parent.id

        # Destroy grandparent
        world.remove(grandparent)
        world.tick(0)

        # Both should be gone (single level of recursion works)
        assert not world.has_entity(grandparent_id)
        assert not world.has_entity(parent_id)


class TestObserverLimitations:
    """Tests documenting observer limitations.

    These tests demonstrate why destroy_with_children() is preferred
    over the async observer for cascade deletion.
    """

    def test_observer_without_cache_does_nothing(self) -> None:
        """Observer without cached relationships won't cascade."""
        world = World()
        observer = DestroyChildrenObserver()
        world.observe(observer)

        world.register_prefab("entity", {Name: Name(value="entity")})

        parent = world.spawn("entity")
        child = world.spawn("entity")
        parent.add_relationship(HasEquipped(slot="hand"), child.id)

        parent_id = parent.id
        child_id = child.id

        # Don't cache relationships - observer won't know about children
        world.remove(parent)
        world.tick(0)

        # Parent is gone but child remains (observer had no cached relationships)
        assert not world.has_entity(parent_id)
        assert world.has_entity(child_id)  # Child survives!
