"""Integration tests for scene graph addon."""

import math

import pytest

from relics import World
from relics.addons.scene_graph import (
    AttachedTo,
    ChildOf,
    LocalOffset,
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
    create_child_node,
    create_root_node,
    get_attached,
    get_children,
    get_descendants,
    get_node,
    get_parent,
    get_roots,
    setup_scene_graph,
)
from relics.addons.scene_graph.types import Quat, Vec3


class TestFullHierarchy:
    """Tests for complete scene graph hierarchies."""

    def test_create_and_traverse_hierarchy(self) -> None:
        """Test creating and traversing a complete hierarchy."""
        world = World()
        index = setup_scene_graph(world)

        # Build a tavern scene
        root = create_root_node(world, "world")
        tavern = create_child_node(
            world,
            "tavern",
            root,
            local_transform=LocalTransform(position=Vec3(100.0, 0.0, 0.0)),
        )
        bar = create_child_node(
            world,
            "bar",
            tavern,
            local_transform=LocalTransform(position=Vec3(10.0, 0.0, 5.0)),
        )
        _table1 = create_child_node(  # noqa: F841
            world,
            "table_1",
            tavern,
            local_transform=LocalTransform(position=Vec3(-20.0, 0.0, 0.0)),
        )
        _table2 = create_child_node(  # noqa: F841
            world,
            "table_2",
            tavern,
            local_transform=LocalTransform(position=Vec3(-20.0, 0.0, 10.0)),
        )
        world.tick(0)

        # Verify paths
        assert index.get("/world/tavern/bar") is not None
        assert index.get("/world/tavern/table_1") is not None
        assert index.get("/world/tavern/table_2") is not None

        # Verify hierarchy
        tavern_children = get_children(world, tavern)
        assert len(tavern_children) == 3

        all_descendants = list(get_descendants(world, root))
        assert len(all_descendants) == 4  # tavern, bar, table1, table2

        # Verify world transforms
        bar_wt = bar.get_component(WorldTransform)
        assert bar_wt.position.x == pytest.approx(110.0)  # 100 + 10
        assert bar_wt.position.z == pytest.approx(5.0)

    def test_reparent_subtree(self) -> None:
        """Test reparenting an entire subtree."""
        world = World()
        index = setup_scene_graph(world)

        root = create_root_node(world, "world")
        room1 = create_child_node(world, "room_1", root)
        room2 = create_child_node(world, "room_2", root)
        furniture = create_child_node(world, "furniture", room1)
        item = create_child_node(world, "item", furniture)
        world.tick(0)

        # Verify initial paths
        assert index.get("/world/room_1/furniture/item").id == item.id

        # Move furniture to room2
        furniture.remove_relationship(ChildOf, room1.id)
        furniture.add_relationship(ChildOf(), room2.id)
        world.tick(0)

        # Verify updated paths
        assert not index.exists("/world/room_1/furniture")
        assert index.exists("/world/room_2/furniture")
        assert index.exists("/world/room_2/furniture/item")

    def test_detach_to_new_root(self) -> None:
        """Test detaching a node to become a new root."""
        world = World()
        _index = setup_scene_graph(world)  # noqa: F841

        root = create_root_node(world, "world")
        room = create_child_node(world, "room", root)
        table = create_child_node(world, "table", room)
        world.tick(0)

        # Verify initial state
        roots_before = get_roots(world)
        assert len(roots_before) == 1

        # Detach room
        room.remove_relationship(ChildOf, root.id)
        world.tick(0)

        # Room is now a root
        roots_after = get_roots(world)
        assert len(roots_after) == 2

        # Paths updated
        assert room.get_component(NodePath).path == "/room"
        assert table.get_component(NodePath).path == "/room/table"


class TestEntityAttachment:
    """Tests for attaching game entities to nodes."""

    def test_attach_entity_to_node(self) -> None:
        """Test attaching an entity to a scene node."""
        world = World()
        setup_scene_graph(world)

        world.register_prefab("item", {})

        root = create_root_node(world, "world")
        table = create_child_node(
            world,
            "table",
            root,
            local_transform=LocalTransform(position=Vec3(50.0, 0.0, 0.0)),
        )
        world.tick(0)

        # Create and attach item
        mug = world.spawn("item")
        mug.add_component(LocalOffset(position=Vec3(0.0, 1.0, 0.0)))  # On top
        mug.add_relationship(AttachedTo(), table.id)
        world.tick(0)

        # Item should have world transform
        assert mug.has_component(WorldTransform)
        mug_wt = mug.get_component(WorldTransform)
        assert mug_wt.position.x == pytest.approx(50.0)
        assert mug_wt.position.y == pytest.approx(1.0)

    def test_attached_entity_follows_node(self) -> None:
        """Test attached entity updates when node moves."""
        world = World()
        setup_scene_graph(world)

        world.register_prefab("item", {})

        root = create_root_node(world, "world")
        table = create_child_node(
            world,
            "table",
            root,
            local_transform=LocalTransform(position=Vec3(0.0, 0.0, 0.0)),
        )
        world.tick(0)

        mug = world.spawn("item")
        mug.add_relationship(AttachedTo(), table.id)
        world.tick(0)

        # Move table
        table.get_component(LocalTransform).position = Vec3(100.0, 0.0, 0.0)
        world.tick(0)

        # Mug should follow
        mug_wt = mug.get_component(WorldTransform)
        assert mug_wt.position.x == pytest.approx(100.0)

    def test_multiple_attachments(self) -> None:
        """Test multiple entities attached to same node."""
        world = World()
        setup_scene_graph(world)

        world.register_prefab("item", {})

        root = create_root_node(world, "world")
        table = create_child_node(world, "table", root)
        world.tick(0)

        items = []
        for i in range(5):
            item = world.spawn("item")
            item.add_component(LocalOffset(position=Vec3(float(i), 0.0, 0.0)))
            item.add_relationship(AttachedTo(), table.id)
            items.append(item)
        world.tick(0)

        # All items should have world transforms
        for item in items:
            assert item.has_component(WorldTransform)

        # Query attached items
        attached = get_attached(world, table)
        assert len(attached) == 5

    def test_detach_entity(self) -> None:
        """Test detaching an entity from a node."""
        world = World()
        setup_scene_graph(world)

        world.register_prefab("item", {})

        root = create_root_node(world, "world")
        table = create_child_node(world, "table", root)
        world.tick(0)

        item = world.spawn("item")
        item.add_relationship(AttachedTo(), table.id)
        world.tick(0)

        # Detach
        item.remove_relationship(AttachedTo, table.id)
        world.tick(0)

        # Item still has WorldTransform but won't update automatically
        attached = get_attached(world, table)
        assert len(attached) == 0


class TestMultipleSceneGraphs:
    """Tests for multiple independent scene graphs."""

    def test_two_scene_graphs(self) -> None:
        """Test creating and managing two independent scene graphs."""
        world = World()
        index = setup_scene_graph(world)

        # World scene graph
        world_root = create_root_node(world, "world")
        _room = create_child_node(world, "room", world_root)  # noqa: F841
        world.tick(0)

        # UI scene graph
        ui_root = create_root_node(world, "ui")
        _panel = create_child_node(world, "panel", ui_root)  # noqa: F841
        world.tick(0)

        # Verify separate roots
        roots = get_roots(world)
        assert len(roots) == 2

        # Verify paths are separate
        assert index.exists("/world/room")
        assert index.exists("/ui/panel")

        # Verify hierarchies are independent
        world_children = list(get_descendants(world, world_root))
        ui_children = list(get_descendants(world, ui_root))

        world_child_ids = {c.id for c in world_children}
        ui_child_ids = {c.id for c in ui_children}

        assert not world_child_ids.intersection(ui_child_ids)


class TestTransformPropagation:
    """Tests for transform propagation through hierarchies."""

    def test_deep_hierarchy_transform(self) -> None:
        """Test transform propagation through deep hierarchy."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "root")
        current = root

        # Create 10-level deep hierarchy
        for i in range(10):
            child = create_child_node(
                world,
                f"level_{i}",
                current,
                local_transform=LocalTransform(position=Vec3(10.0, 0.0, 0.0)),
            )
            current = child
        world.tick(0)

        # Deepest node should be at 10 * 10 = 100
        leaf_wt = current.get_component(WorldTransform)
        assert leaf_wt.position.x == pytest.approx(100.0)

    def test_rotation_propagation(self) -> None:
        """Test rotation propagation through hierarchy."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "root")
        # Rotate 90 degrees around Z axis
        arm = create_child_node(
            world,
            "arm",
            root,
            local_transform=LocalTransform(
                position=Vec3.zero(),
                rotation=Quat.from_axis_angle(Vec3.unit_z(), math.pi / 2),
            ),
        )
        # Child positioned along X axis
        hand = create_child_node(
            world,
            "hand",
            arm,
            local_transform=LocalTransform(position=Vec3(10.0, 0.0, 0.0)),
        )
        world.tick(0)

        # Hand should be rotated to Y axis
        hand_wt = hand.get_component(WorldTransform)
        assert hand_wt.position.x == pytest.approx(0.0, abs=1e-6)
        assert hand_wt.position.y == pytest.approx(10.0, abs=1e-6)

    def test_scale_propagation(self) -> None:
        """Test scale propagation through hierarchy."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "root")
        # Scale 2x
        parent = create_child_node(
            world,
            "parent",
            root,
            local_transform=LocalTransform(scale=Vec3(2.0, 2.0, 2.0)),
        )
        # Child at (10, 0, 0)
        child = create_child_node(
            world,
            "child",
            parent,
            local_transform=LocalTransform(position=Vec3(10.0, 0.0, 0.0)),
        )
        world.tick(0)

        # Child position should be scaled
        child_wt = child.get_component(WorldTransform)
        assert child_wt.position.x == pytest.approx(20.0)  # 10 * 2
        # Child scale should compound
        assert child_wt.scale.x == pytest.approx(2.0)


class TestQueryFunctions:
    """Tests for query utility functions."""

    def test_get_node_by_path(self) -> None:
        """Test getting nodes by path."""
        world = World()
        index = setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(world, "room", root)
        table = create_child_node(world, "table", room)
        world.tick(0)

        # Query by path
        found_table = get_node(world, "/world/room/table", index)
        assert found_table is not None
        assert found_table.id == table.id

        # Query nonexistent
        not_found = get_node(world, "/world/kitchen", index)
        assert not_found is None

    def test_hierarchy_queries(self) -> None:
        """Test parent/child/descendant queries."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(world, "room", root)
        table = create_child_node(world, "table", room)
        chair = create_child_node(world, "chair", room)
        world.tick(0)

        # Get parent
        table_parent = get_parent(world, table)
        assert table_parent.id == room.id

        # Get children
        room_children = get_children(world, room)
        assert len(room_children) == 2
        child_ids = {c.id for c in room_children}
        assert table.id in child_ids
        assert chair.id in child_ids

        # Get descendants
        all_descendants = list(get_descendants(world, root))
        assert len(all_descendants) == 3  # room, table, chair


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_rename_node(self) -> None:
        """Test renaming a node updates paths correctly."""
        world = World()
        index = setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(world, "old_room", root)
        _table = create_child_node(world, "table", room)  # noqa: F841
        world.tick(0)

        # Rename room
        room.get_component(NodeName).name = "new_room"
        world.tick(0)

        # Paths should update
        assert not index.exists("/world/old_room")
        assert index.exists("/world/new_room")
        assert index.exists("/world/new_room/table")

    def test_empty_scene_graph(self) -> None:
        """Test operations on empty scene graph."""
        world = World()
        index = setup_scene_graph(world)

        roots = get_roots(world)
        assert len(roots) == 0
        assert index.count() == 0

    def test_single_node_graph(self) -> None:
        """Test single node (root only) scene graph."""
        world = World()
        _index = setup_scene_graph(world)  # noqa: F841

        root = create_root_node(world, "solo")
        world.tick(0)

        roots = get_roots(world)
        assert len(roots) == 1

        children = get_children(world, root)
        assert len(children) == 0

        parent = get_parent(world, root)
        assert parent is None

        descendants = list(get_descendants(world, root))
        assert len(descendants) == 0
