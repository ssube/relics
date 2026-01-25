"""Tests for scene graph observers."""

import pytest

from relics import World
from relics.addons.scene_graph.components import (
    LocalOffset,
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
)
from relics.addons.scene_graph.edges import AttachedTo, ChildOf
from relics.addons.scene_graph.index import PathIndex
from relics.addons.scene_graph.observer import (
    AttachmentObserver,
    LocalOffsetObserver,
    LocalTransformObserver,
    NodeHierarchyObserver,
    NodeNameObserver,
    PathIndexObserver,
    WorldTransformObserver,
    create_all_observers,
)
from relics.addons.scene_graph.types import Vec3


class TestPathIndexObserver:
    """Tests for PathIndexObserver."""

    def test_tracks_node_path_added(self) -> None:
        """Test observer tracks NodePath additions."""
        world = World()
        index = PathIndex(world)
        observer = PathIndexObserver(index)
        world.observe(observer)

        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))

        world.tick(0)

        assert index.exists("/test")
        assert index.get("/test").id == entity.id

    def test_tracks_node_path_changed(self) -> None:
        """Test observer tracks NodePath changes."""
        world = World()
        index = PathIndex(world)
        observer = PathIndexObserver(index)
        world.observe(observer)

        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/old"))
        world.tick(0)

        # Change path
        entity.get_component(NodePath).path = "/new"
        world.tick(0)

        assert not index.exists("/old")
        assert index.exists("/new")

    def test_tracks_node_path_removed(self) -> None:
        """Test observer tracks NodePath removals."""
        world = World()
        index = PathIndex(world)
        observer = PathIndexObserver(index)
        world.observe(observer)

        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))
        world.tick(0)

        entity.remove_component(NodePath)
        world.tick(0)

        assert not index.exists("/test")


class TestNodeNameObserver:
    """Tests for NodeNameObserver."""

    def test_computes_path_on_name_added(self) -> None:
        """Test NodePath is computed when NodeName is added."""
        world = World()
        observer = NodeNameObserver()
        world.observe(observer)

        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodeName(name="test"))
        world.tick(0)

        assert entity.has_component(NodePath)
        assert entity.get_component(NodePath).path == "/test"

    def test_updates_path_on_name_changed(self) -> None:
        """Test NodePath updates when NodeName changes."""
        world = World()
        observer = NodeNameObserver()
        world.observe(observer)

        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodeName(name="old"))
        world.tick(0)

        entity.get_component(NodeName).name = "new"
        world.tick(0)

        assert entity.get_component(NodePath).path == "/new"


class TestNodeHierarchyObserver:
    """Tests for NodeHierarchyObserver."""

    def test_updates_path_on_reparent(self) -> None:
        """Test NodePath updates when node is reparented."""
        world = World()
        observer = NodeHierarchyObserver()
        world.observe(observer)

        world.register_prefab("node", {})
        root1 = world.spawn("node")
        root1.add_component(NodeName(name="root1"))
        root1.add_component(NodePath(path="/root1"))
        root2 = world.spawn("node")
        root2.add_component(NodeName(name="root2"))
        root2.add_component(NodePath(path="/root2"))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))
        child.add_component(NodePath(path="/child"))
        world.tick(0)

        # Add child to root1
        child.add_relationship(ChildOf(), root1.id)
        world.tick(0)

        assert child.get_component(NodePath).path == "/root1/child"

    def test_updates_descendants_on_reparent(self) -> None:
        """Test all descendant paths update on reparent."""
        world = World()
        observer = NodeHierarchyObserver()
        world.observe(observer)

        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))
        root.add_component(NodePath(path="/root"))

        branch = world.spawn("node")
        branch.add_component(NodeName(name="branch"))
        branch.add_component(NodePath(path="/branch"))

        leaf = world.spawn("node")
        leaf.add_component(NodeName(name="leaf"))
        leaf.add_component(NodePath(path="/branch/leaf"))
        leaf.add_relationship(ChildOf(), branch.id)
        world.tick(0)

        # Move branch under root
        branch.add_relationship(ChildOf(), root.id)
        world.tick(0)

        assert branch.get_component(NodePath).path == "/root/branch"
        assert leaf.get_component(NodePath).path == "/root/branch/leaf"


class TestLocalTransformObserver:
    """Tests for LocalTransformObserver."""

    def test_propagates_world_transform(self) -> None:
        """Test WorldTransform propagates when LocalTransform changes."""
        world = World()
        observer = LocalTransformObserver()
        world.observe(observer)

        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodeName(name="test"))
        entity.add_component(LocalTransform(position=Vec3(10.0, 0.0, 0.0)))
        world.tick(0)

        # Should have world transform
        assert entity.has_component(WorldTransform)
        wt = entity.get_component(WorldTransform)
        assert wt.position.x == pytest.approx(10.0)

    def test_propagates_to_children(self) -> None:
        """Test transform changes propagate to child nodes."""
        world = World()
        observer = LocalTransformObserver()
        hierarchy_observer = NodeHierarchyObserver()
        world.observe(observer)
        world.observe(hierarchy_observer)

        world.register_prefab("node", {})
        parent = world.spawn("node")
        parent.add_component(NodeName(name="parent"))
        parent.add_component(LocalTransform(position=Vec3(100.0, 0.0, 0.0)))
        parent.add_component(NodePath(path="/parent"))

        child = world.spawn("node")
        child.add_component(NodeName(name="child"))
        child.add_component(LocalTransform(position=Vec3(10.0, 0.0, 0.0)))
        child.add_component(NodePath(path="/parent/child"))
        child.add_relationship(ChildOf(), parent.id)
        world.tick(0)

        # Child should inherit parent position
        child_wt = child.get_component(WorldTransform)
        assert child_wt.position.x == pytest.approx(110.0)  # 100 + 10


class TestAttachmentObserver:
    """Tests for AttachmentObserver."""

    def test_updates_attached_entity_transform(self) -> None:
        """Test WorldTransform updates when entity is attached."""
        world = World()
        observer = AttachmentObserver()
        transform_observer = LocalTransformObserver()
        world.observe(observer)
        world.observe(transform_observer)

        world.register_prefab("node", {})
        world.register_prefab("item", {})

        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        node.add_component(LocalTransform(position=Vec3(50.0, 0.0, 0.0)))
        world.tick(0)

        item = world.spawn("item")
        item.add_relationship(AttachedTo(), node.id)
        world.tick(0)

        # Item should have WorldTransform matching node
        assert item.has_component(WorldTransform)
        wt = item.get_component(WorldTransform)
        assert wt.position.x == pytest.approx(50.0)


class TestLocalOffsetObserver:
    """Tests for LocalOffsetObserver."""

    def test_applies_offset_to_attached_entity(self) -> None:
        """Test LocalOffset is applied to attached entity transform."""
        world = World()
        offset_observer = LocalOffsetObserver()
        transform_observer = LocalTransformObserver()
        attachment_observer = AttachmentObserver()
        world.observe(offset_observer)
        world.observe(transform_observer)
        world.observe(attachment_observer)

        world.register_prefab("node", {})
        world.register_prefab("item", {})

        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        node.add_component(LocalTransform(position=Vec3(100.0, 0.0, 0.0)))
        world.tick(0)

        item = world.spawn("item")
        item.add_component(LocalOffset(position=Vec3(5.0, 0.0, 0.0)))
        item.add_relationship(AttachedTo(), node.id)
        world.tick(0)

        # Item should have node position + offset
        wt = item.get_component(WorldTransform)
        assert wt.position.x == pytest.approx(105.0)  # 100 + 5

    def test_updates_on_offset_change(self) -> None:
        """Test WorldTransform updates when LocalOffset changes."""
        world = World()
        offset_observer = LocalOffsetObserver()
        transform_observer = LocalTransformObserver()
        attachment_observer = AttachmentObserver()
        world.observe(offset_observer)
        world.observe(transform_observer)
        world.observe(attachment_observer)

        world.register_prefab("node", {})
        world.register_prefab("item", {})

        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        node.add_component(LocalTransform(position=Vec3(100.0, 0.0, 0.0)))
        world.tick(0)

        item = world.spawn("item")
        item.add_component(LocalOffset(position=Vec3(5.0, 0.0, 0.0)))
        item.add_relationship(AttachedTo(), node.id)
        world.tick(0)

        # Change offset
        item.get_component(LocalOffset).position = Vec3(20.0, 0.0, 0.0)
        world.tick(0)

        wt = item.get_component(WorldTransform)
        assert wt.position.x == pytest.approx(120.0)  # 100 + 20


class TestWorldTransformObserver:
    """Tests for WorldTransformObserver."""

    def test_updates_attached_entities_on_change(self) -> None:
        """Test attached entities update when node WorldTransform changes."""
        world = World()
        wt_observer = WorldTransformObserver()
        transform_observer = LocalTransformObserver()
        attachment_observer = AttachmentObserver()
        world.observe(wt_observer)
        world.observe(transform_observer)
        world.observe(attachment_observer)

        world.register_prefab("node", {})
        world.register_prefab("item", {})

        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        node.add_component(LocalTransform(position=Vec3(50.0, 0.0, 0.0)))
        world.tick(0)

        item = world.spawn("item")
        item.add_relationship(AttachedTo(), node.id)
        world.tick(0)

        # Directly modify node's world transform
        node.get_component(LocalTransform).position = Vec3(100.0, 0.0, 0.0)
        world.tick(0)

        # Item should update
        wt = item.get_component(WorldTransform)
        assert wt.position.x == pytest.approx(100.0)


class TestCreateAllObservers:
    """Tests for create_all_observers helper."""

    def test_creates_all_observers(self) -> None:
        """Test that all observers are created."""
        world = World()
        index = PathIndex(world)
        observers = create_all_observers(index)

        assert (
            len(observers) == 7
        )  # PathIndex, NodeName, Hierarchy, Local, Attachment, Offset, World

        # Check types
        types = {type(o) for o in observers}
        assert PathIndexObserver in types
        assert NodeNameObserver in types
        assert NodeHierarchyObserver in types
        assert LocalTransformObserver in types
        assert AttachmentObserver in types
        assert LocalOffsetObserver in types
        assert WorldTransformObserver in types

    def test_observers_can_be_registered(self) -> None:
        """Test all observers can be registered to world."""
        world = World()
        index = PathIndex(world)
        observers = create_all_observers(index)

        for observer in observers:
            world.observe(observer)

        # Should not raise
        world.tick(0)
