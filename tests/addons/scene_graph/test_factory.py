"""Tests for scene graph factory functions."""

import pytest

from relics import World
from relics.addons.scene_graph.components import (
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
)
from relics.addons.scene_graph.edges import ChildOf
from relics.addons.scene_graph.factory import (
    SCENE_NODE_PREFAB,
    create_child_node,
    create_root_node,
    setup_scene_graph,
)
from relics.addons.scene_graph.index import PathIndex
from relics.addons.scene_graph.types import Vec3


class TestSetupSceneGraph:
    """Tests for setup_scene_graph function."""

    def test_returns_path_index(self) -> None:
        """Test setup returns a PathIndex."""
        world = World()
        index = setup_scene_graph(world)

        assert isinstance(index, PathIndex)

    def test_registers_prefab(self) -> None:
        """Test setup registers the scene node prefab."""
        world = World()
        setup_scene_graph(world)

        # Should be able to spawn from prefab
        node = world.spawn(SCENE_NODE_PREFAB)
        assert node is not None
        assert node.id.prefab == SCENE_NODE_PREFAB

    def test_registers_observers(self) -> None:
        """Test setup registers observers when auto_register=True."""
        world = World()
        index = setup_scene_graph(world, auto_register_observers=True)

        # Create a node - observers should handle path and transform
        node = world.spawn(SCENE_NODE_PREFAB)
        node.add_component(NodeName(name="test"))
        node.add_component(LocalTransform.identity())
        world.tick(0)

        # PathIndex should have the node
        assert index.exists("/test")

    def test_skip_observers(self) -> None:
        """Test setup skips observers when auto_register=False."""
        world = World()
        index = setup_scene_graph(world, auto_register_observers=False)

        # Create a node
        node = world.spawn(SCENE_NODE_PREFAB)
        node.add_component(NodeName(name="test"))
        world.tick(0)

        # Without observers, node won't be in index automatically
        # (unless we add NodePath component manually)
        assert not index.exists("/test")

    def test_skip_prefab_registration(self) -> None:
        """Test setup skips prefab when register_prefab=False."""
        world = World()
        setup_scene_graph(world, register_prefab=False)

        # Should raise because prefab not registered
        with pytest.raises(Exception):
            world.spawn(SCENE_NODE_PREFAB)


class TestCreateRootNode:
    """Tests for create_root_node function."""

    def test_creates_node_with_name(self) -> None:
        """Test creates node with NodeName component."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")

        assert root.has_component(NodeName)
        assert root.get_component(NodeName).name == "world"

    def test_creates_node_with_transform(self) -> None:
        """Test creates node with LocalTransform component."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")

        assert root.has_component(LocalTransform)
        lt = root.get_component(LocalTransform)
        assert lt.position == Vec3.zero()

    def test_node_has_path_after_tick(self) -> None:
        """Test node has NodePath after tick (via observers)."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        world.tick(0)

        assert root.has_component(NodePath)
        assert root.get_component(NodePath).path == "/world"

    def test_root_has_no_parent(self) -> None:
        """Test root node has no ChildOf relationship."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")

        relationships = root.get_relationships(ChildOf)
        assert len(relationships) == 0

    def test_spawns_from_prefab(self) -> None:
        """Test uses scene node prefab by default."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")

        assert root.id.prefab == SCENE_NODE_PREFAB


class TestCreateChildNode:
    """Tests for create_child_node function."""

    def test_creates_node_with_parent(self) -> None:
        """Test creates node with ChildOf relationship to parent."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        child = create_child_node(world, "room", root)

        relationships = child.get_relationships(ChildOf)
        assert len(relationships) == 1
        _, parent_id = relationships[0]
        assert parent_id == root.id

    def test_node_has_name(self) -> None:
        """Test child node has NodeName component."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        child = create_child_node(world, "room", root)

        assert child.has_component(NodeName)
        assert child.get_component(NodeName).name == "room"

    def test_node_has_transform(self) -> None:
        """Test child node has LocalTransform component."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        child = create_child_node(world, "room", root)

        assert child.has_component(LocalTransform)

    def test_custom_transform(self) -> None:
        """Test creating child with custom local transform."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        transform = LocalTransform(position=Vec3(100.0, 50.0, 0.0))
        child = create_child_node(world, "room", root, local_transform=transform)

        lt = child.get_component(LocalTransform)
        assert lt.position.x == pytest.approx(100.0)
        assert lt.position.y == pytest.approx(50.0)

    def test_child_path_after_tick(self) -> None:
        """Test child has correct path after tick."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        child = create_child_node(world, "room", root)
        world.tick(0)

        assert child.has_component(NodePath)
        assert child.get_component(NodePath).path == "/world/room"

    def test_grandchild_path(self) -> None:
        """Test nested children have correct paths."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(world, "room", root)
        table = create_child_node(world, "table", room)
        world.tick(0)

        assert table.get_component(NodePath).path == "/world/room/table"


class TestSceneNodePrefab:
    """Tests for the SCENE_NODE_PREFAB constant."""

    def test_prefab_name(self) -> None:
        """Test prefab name is _scene_node."""
        assert SCENE_NODE_PREFAB == "_scene_node"

    def test_prefab_spawn(self) -> None:
        """Test spawning from prefab works."""
        world = World()
        setup_scene_graph(world)

        node = world.spawn(SCENE_NODE_PREFAB)
        assert node is not None


class TestIntegrationWithIndex:
    """Integration tests for factory with PathIndex."""

    def test_index_populated_after_creation(self) -> None:
        """Test PathIndex is populated after creating nodes."""
        world = World()
        index = setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(world, "room", root)
        _table = create_child_node(world, "table", room)  # noqa: F841
        world.tick(0)

        assert index.exists("/world")
        assert index.exists("/world/room")
        assert index.exists("/world/room/table")

    def test_query_created_nodes(self) -> None:
        """Test querying nodes created via factory."""
        world = World()
        index = setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(world, "room", root)
        world.tick(0)

        queried_room = index.get("/world/room")
        assert queried_room is not None
        assert queried_room.id == room.id


class TestTransformPropagation:
    """Tests for transform propagation through factory-created nodes."""

    def test_world_transform_propagates(self) -> None:
        """Test world transform propagates through hierarchy."""
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        room = create_child_node(
            world,
            "room",
            root,
            local_transform=LocalTransform(position=Vec3(100.0, 0.0, 0.0)),
        )
        table = create_child_node(
            world,
            "table",
            room,
            local_transform=LocalTransform(position=Vec3(10.0, 0.0, 0.0)),
        )
        world.tick(0)

        # Table should be at 100 + 10 = 110
        table_wt = table.get_component(WorldTransform)
        assert table_wt.position.x == pytest.approx(110.0)
