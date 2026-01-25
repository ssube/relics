"""Tests for scene graph utility functions."""

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
from relics.addons.scene_graph.types import Mat4, Quat, Vec3
from relics.addons.scene_graph.utils import (
    compute_attached_transform,
    compute_path,
    compute_world_transform,
    get_ancestors,
    get_attached,
    get_children,
    get_descendants,
    get_node,
    get_node_of,
    get_parent,
    get_roots,
    is_scene_node,
    propagate_transforms,
    update_descendant_paths,
    update_node_path,
    would_create_cycle,
)


class TestIsSceneNode:
    """Tests for is_scene_node function."""

    def test_entity_with_node_name(self) -> None:
        """Test entity with NodeName is a scene node."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodeName(name="test"))

        assert is_scene_node(entity) is True

    def test_entity_without_node_name(self) -> None:
        """Test entity without NodeName is not a scene node."""
        world = World()
        world.register_prefab("entity", {})
        entity = world.spawn("entity")

        assert is_scene_node(entity) is False


class TestGetNode:
    """Tests for get_node function."""

    def test_get_existing_node(self) -> None:
        """Test getting an existing node by path."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))

        index = PathIndex(world)
        result = get_node(world, "/test", index)

        assert result is not None
        assert result.id == entity.id

    def test_get_nonexistent_node(self) -> None:
        """Test getting a nonexistent node returns None."""
        world = World()
        index = PathIndex(world)
        result = get_node(world, "/nonexistent", index)

        assert result is None


class TestGetChildren:
    """Tests for get_children function."""

    def test_get_children_of_parent(self) -> None:
        """Test getting children of a parent node."""
        world = World()
        world.register_prefab("node", {})
        parent = world.spawn("node")
        parent.add_component(NodeName(name="parent"))
        child1 = world.spawn("node")
        child1.add_component(NodeName(name="child1"))
        child2 = world.spawn("node")
        child2.add_component(NodeName(name="child2"))

        child1.add_relationship(ChildOf(), parent.id)
        child2.add_relationship(ChildOf(), parent.id)

        children = get_children(world, parent)

        assert len(children) == 2
        child_ids = {c.id for c in children}
        assert child1.id in child_ids
        assert child2.id in child_ids

    def test_get_children_of_leaf(self) -> None:
        """Test getting children of a leaf node returns empty list."""
        world = World()
        world.register_prefab("node", {})
        leaf = world.spawn("node")
        leaf.add_component(NodeName(name="leaf"))

        children = get_children(world, leaf)
        assert children == []


class TestGetParent:
    """Tests for get_parent function."""

    def test_get_parent_of_child(self) -> None:
        """Test getting parent of a child node."""
        world = World()
        world.register_prefab("node", {})
        parent = world.spawn("node")
        child = world.spawn("node")
        child.add_relationship(ChildOf(), parent.id)

        result = get_parent(world, child)

        assert result is not None
        assert result.id == parent.id

    def test_get_parent_of_root(self) -> None:
        """Test getting parent of root node returns None."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))

        result = get_parent(world, root)
        assert result is None


class TestGetAttached:
    """Tests for get_attached function."""

    def test_get_attached_entities(self) -> None:
        """Test getting entities attached to a node."""
        world = World()
        world.register_prefab("node", {})
        world.register_prefab("item", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        item1 = world.spawn("item")
        item2 = world.spawn("item")

        item1.add_relationship(AttachedTo(), node.id)
        item2.add_relationship(AttachedTo(), node.id)

        attached = get_attached(world, node)

        assert len(attached) == 2
        attached_ids = {a.id for a in attached}
        assert item1.id in attached_ids
        assert item2.id in attached_ids

    def test_get_attached_empty(self) -> None:
        """Test getting attached from node with no attachments."""
        world = World()
        world.register_prefab("node", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="node"))

        attached = get_attached(world, node)
        assert attached == []


class TestGetNodeOf:
    """Tests for get_node_of function."""

    def test_get_node_of_attached_entity(self) -> None:
        """Test getting the node an entity is attached to."""
        world = World()
        world.register_prefab("node", {})
        world.register_prefab("item", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        item = world.spawn("item")

        item.add_relationship(AttachedTo(), node.id)

        result = get_node_of(world, item)

        assert result is not None
        assert result.id == node.id

    def test_get_node_of_unattached_entity(self) -> None:
        """Test getting node of unattached entity returns None."""
        world = World()
        world.register_prefab("item", {})
        item = world.spawn("item")

        result = get_node_of(world, item)
        assert result is None


class TestGetRoots:
    """Tests for get_roots function."""

    def test_get_single_root(self) -> None:
        """Test getting a single root node."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))
        child.add_relationship(ChildOf(), root.id)

        roots = get_roots(world)

        assert len(roots) == 1
        assert roots[0].id == root.id

    def test_get_multiple_roots(self) -> None:
        """Test getting multiple root nodes (multiple scene graphs)."""
        world = World()
        world.register_prefab("node", {})
        root1 = world.spawn("node")
        root1.add_component(NodeName(name="world"))
        root2 = world.spawn("node")
        root2.add_component(NodeName(name="ui"))

        roots = get_roots(world)

        assert len(roots) == 2
        root_ids = {r.id for r in roots}
        assert root1.id in root_ids
        assert root2.id in root_ids


class TestGetDescendants:
    """Tests for get_descendants function."""

    def test_get_descendants_depth_first(self) -> None:
        """Test getting descendants in depth-first order."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))
        child1 = world.spawn("node")
        child1.add_component(NodeName(name="child1"))
        child2 = world.spawn("node")
        child2.add_component(NodeName(name="child2"))
        grandchild = world.spawn("node")
        grandchild.add_component(NodeName(name="grandchild"))

        child1.add_relationship(ChildOf(), root.id)
        child2.add_relationship(ChildOf(), root.id)
        grandchild.add_relationship(ChildOf(), child1.id)

        descendants = list(get_descendants(world, root))

        assert len(descendants) == 3
        descendant_ids = {d.id for d in descendants}
        assert child1.id in descendant_ids
        assert child2.id in descendant_ids
        assert grandchild.id in descendant_ids

    def test_get_descendants_of_leaf(self) -> None:
        """Test getting descendants of leaf returns empty."""
        world = World()
        world.register_prefab("node", {})
        leaf = world.spawn("node")
        leaf.add_component(NodeName(name="leaf"))

        descendants = list(get_descendants(world, leaf))
        assert descendants == []


class TestGetAncestors:
    """Tests for get_ancestors function."""

    def test_get_ancestors_to_root(self) -> None:
        """Test getting ancestors from leaf to root."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))
        middle = world.spawn("node")
        middle.add_component(NodeName(name="middle"))
        leaf = world.spawn("node")
        leaf.add_component(NodeName(name="leaf"))

        middle.add_relationship(ChildOf(), root.id)
        leaf.add_relationship(ChildOf(), middle.id)

        ancestors = list(get_ancestors(world, leaf))

        assert len(ancestors) == 2
        assert ancestors[0].id == middle.id  # Immediate parent first
        assert ancestors[1].id == root.id

    def test_get_ancestors_of_root(self) -> None:
        """Test getting ancestors of root returns empty."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))

        ancestors = list(get_ancestors(world, root))
        assert ancestors == []


class TestComputePath:
    """Tests for compute_path function."""

    def test_compute_root_path(self) -> None:
        """Test computing path for root node."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="world"))

        path = compute_path(world, root)
        assert path == "/world"

    def test_compute_nested_path(self) -> None:
        """Test computing path for nested node."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="world"))
        room = world.spawn("node")
        room.add_component(NodeName(name="room"))
        table = world.spawn("node")
        table.add_component(NodeName(name="table"))

        room.add_relationship(ChildOf(), root.id)
        table.add_relationship(ChildOf(), room.id)

        path = compute_path(world, table)
        assert path == "/world/room/table"

    def test_compute_path_without_node_name(self) -> None:
        """Test computing path for entity without NodeName."""
        world = World()
        world.register_prefab("entity", {})
        entity = world.spawn("entity")

        path = compute_path(world, entity)
        assert path == ""


class TestWouldCreateCycle:
    """Tests for would_create_cycle function."""

    def test_self_reference_creates_cycle(self) -> None:
        """Test self-reference is detected as cycle."""
        world = World()
        world.register_prefab("node", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="node"))

        assert would_create_cycle(world, node, node) is True

    def test_descendant_as_parent_creates_cycle(self) -> None:
        """Test making descendant the parent creates cycle."""
        world = World()
        world.register_prefab("node", {})
        grandparent = world.spawn("node")
        grandparent.add_component(NodeName(name="gp"))
        parent = world.spawn("node")
        parent.add_component(NodeName(name="parent"))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))

        parent.add_relationship(ChildOf(), grandparent.id)
        child.add_relationship(ChildOf(), parent.id)

        # grandparent -> parent -> child
        # Setting grandparent's parent to child would create cycle
        assert would_create_cycle(world, grandparent, child) is True

    def test_valid_reparent_no_cycle(self) -> None:
        """Test valid reparent doesn't detect cycle."""
        world = World()
        world.register_prefab("node", {})
        root1 = world.spawn("node")
        root1.add_component(NodeName(name="root1"))
        root2 = world.spawn("node")
        root2.add_component(NodeName(name="root2"))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))

        child.add_relationship(ChildOf(), root1.id)

        # Moving child to root2 should not create cycle
        assert would_create_cycle(world, child, root2) is False


class TestComputeWorldTransform:
    """Tests for compute_world_transform function."""

    def test_root_node_transform(self) -> None:
        """Test world transform for root node equals local."""
        local = LocalTransform(
            position=Vec3(10.0, 20.0, 30.0),
            rotation=Quat.identity(),
            scale=Vec3(2.0, 2.0, 2.0),
        )

        world_transform = compute_world_transform(local, None)

        assert world_transform.position == local.position
        assert world_transform.rotation == local.rotation
        assert world_transform.scale == local.scale

    def test_child_node_transform(self) -> None:
        """Test world transform for child node combines with parent."""
        parent_world = WorldTransform(
            position=Vec3(100.0, 0.0, 0.0),
            rotation=Quat.identity(),
            scale=Vec3.one(),
            matrix=Mat4.from_translation(Vec3(100.0, 0.0, 0.0)),
        )
        local = LocalTransform(
            position=Vec3(10.0, 0.0, 0.0),
            rotation=Quat.identity(),
            scale=Vec3.one(),
        )

        world_transform = compute_world_transform(local, parent_world)

        assert world_transform.position.x == pytest.approx(110.0)

    def test_child_inherits_scale(self) -> None:
        """Test child inherits parent scale."""
        parent_world = WorldTransform(
            position=Vec3.zero(),
            rotation=Quat.identity(),
            scale=Vec3(2.0, 2.0, 2.0),
            matrix=Mat4.from_scale(Vec3(2.0, 2.0, 2.0)),
        )
        local = LocalTransform(
            position=Vec3(10.0, 0.0, 0.0),
            rotation=Quat.identity(),
            scale=Vec3(0.5, 0.5, 0.5),
        )

        world_transform = compute_world_transform(local, parent_world)

        # Position scaled by parent scale
        assert world_transform.position.x == pytest.approx(20.0)  # 10 * 2
        # Scale compounded
        assert world_transform.scale.x == pytest.approx(1.0)  # 2 * 0.5


class TestComputeAttachedTransform:
    """Tests for compute_attached_transform function."""

    def test_no_offset(self) -> None:
        """Test attached transform without offset equals node transform."""
        node_world = WorldTransform(
            position=Vec3(50.0, 0.0, 0.0),
            rotation=Quat.identity(),
            scale=Vec3.one(),
            matrix=Mat4.identity(),
        )

        result = compute_attached_transform(node_world, None)

        assert result == node_world

    def test_with_offset(self) -> None:
        """Test attached transform with offset."""
        node_world = WorldTransform(
            position=Vec3(100.0, 0.0, 0.0),
            rotation=Quat.identity(),
            scale=Vec3.one(),
            matrix=Mat4.identity(),
        )
        offset = LocalOffset(
            position=Vec3(5.0, 0.0, 0.0),
            rotation=Quat.identity(),
            scale=Vec3.one(),
        )

        result = compute_attached_transform(node_world, offset)

        assert result.position.x == pytest.approx(105.0)


class TestPropagateTransforms:
    """Tests for propagate_transforms function."""

    def test_propagates_to_node(self) -> None:
        """Test transform propagates to node itself."""
        world = World()
        world.register_prefab("node", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="node"))
        node.add_component(LocalTransform(position=Vec3(10.0, 0.0, 0.0)))

        propagate_transforms(world, node)

        assert node.has_component(WorldTransform)
        wt = node.get_component(WorldTransform)
        assert wt.position.x == pytest.approx(10.0)

    def test_propagates_to_descendants(self) -> None:
        """Test transform propagates to descendants."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))
        root.add_component(LocalTransform(position=Vec3(100.0, 0.0, 0.0)))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))
        child.add_component(LocalTransform(position=Vec3(10.0, 0.0, 0.0)))
        child.add_relationship(ChildOf(), root.id)

        propagate_transforms(world, root)

        child_wt = child.get_component(WorldTransform)
        assert child_wt.position.x == pytest.approx(110.0)


class TestUpdateNodePath:
    """Tests for update_node_path function."""

    def test_creates_path_component(self) -> None:
        """Test creates NodePath if not present."""
        world = World()
        world.register_prefab("node", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="test"))

        path = update_node_path(world, node)

        assert path == "/test"
        assert node.has_component(NodePath)
        assert node.get_component(NodePath).path == "/test"

    def test_updates_existing_path(self) -> None:
        """Test updates existing NodePath."""
        world = World()
        world.register_prefab("node", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="test"))
        node.add_component(NodePath(path="/old"))

        path = update_node_path(world, node)

        assert path == "/test"
        assert node.get_component(NodePath).path == "/test"


class TestUpdateDescendantPaths:
    """Tests for update_descendant_paths function."""

    def test_updates_all_descendants(self) -> None:
        """Test all descendant paths are updated."""
        world = World()
        world.register_prefab("node", {})
        root = world.spawn("node")
        root.add_component(NodeName(name="root"))
        root.add_component(NodePath(path="/old_root"))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))
        child.add_component(NodePath(path="/old_root/child"))
        grandchild = world.spawn("node")
        grandchild.add_component(NodeName(name="grandchild"))
        grandchild.add_component(NodePath(path="/old_root/child/grandchild"))

        child.add_relationship(ChildOf(), root.id)
        grandchild.add_relationship(ChildOf(), child.id)

        update_descendant_paths(world, root)

        assert root.get_component(NodePath).path == "/root"
        assert child.get_component(NodePath).path == "/root/child"
        assert grandchild.get_component(NodePath).path == "/root/child/grandchild"
