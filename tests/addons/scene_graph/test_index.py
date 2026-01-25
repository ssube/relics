"""Tests for PathIndex."""

import pytest

from relics import World
from relics.addons.scene_graph.components import NodePath
from relics.addons.scene_graph.exceptions import DuplicatePathError
from relics.addons.scene_graph.index import PathIndex


class TestPathIndexBasics:
    """Basic tests for PathIndex."""

    def test_create_index(self) -> None:
        """Test creating a PathIndex."""
        world = World()
        index = PathIndex(world)
        assert index is not None

    def test_empty_index_count(self) -> None:
        """Test empty index has count of 0."""
        world = World()
        index = PathIndex(world)
        assert index.count() == 0

    def test_empty_index_iteration(self) -> None:
        """Test iterating empty index yields nothing."""
        world = World()
        index = PathIndex(world)
        entities = list(index)
        assert len(entities) == 0

    def test_empty_index_get_entity_ids(self) -> None:
        """Test empty index returns empty set."""
        world = World()
        index = PathIndex(world)
        ids = index.get_entity_ids()
        assert ids == set()


class TestPathIndexOperations:
    """Tests for PathIndex operations."""

    def test_add_node(self) -> None:
        """Test adding a node to the index."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))

        index = PathIndex(world)
        index.add_node(entity.id, "/test")

        assert index.count() == 1
        assert index.exists("/test")
        assert index.get("/test") is not None
        assert index.get("/test").id == entity.id

    def test_get_nonexistent_path(self) -> None:
        """Test getting a nonexistent path returns None."""
        world = World()
        index = PathIndex(world)
        assert index.get("/nonexistent") is None

    def test_exists_nonexistent_path(self) -> None:
        """Test exists returns False for nonexistent path."""
        world = World()
        index = PathIndex(world)
        assert not index.exists("/nonexistent")

    def test_get_id(self) -> None:
        """Test getting entity ID by path."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity.id, "/test")

        entity_id = index.get_id("/test")
        assert entity_id == entity.id

    def test_get_id_nonexistent(self) -> None:
        """Test getting entity ID for nonexistent path."""
        world = World()
        index = PathIndex(world)
        assert index.get_id("/nonexistent") is None

    def test_get_path(self) -> None:
        """Test getting path by entity ID."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity.id, "/test")

        path = index.get_path(entity.id)
        assert path == "/test"

    def test_get_path_nonexistent(self) -> None:
        """Test getting path for nonexistent entity."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        index = PathIndex(world)
        assert index.get_path(entity.id) is None

    def test_remove_node(self) -> None:
        """Test removing a node from the index."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity.id, "/test")
        assert index.count() == 1

        index.remove_node(entity.id)
        assert index.count() == 0
        assert not index.exists("/test")

    def test_remove_nonexistent_node(self) -> None:
        """Test removing nonexistent node doesn't error."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        index = PathIndex(world)
        # Should not raise
        index.remove_node(entity.id)

    def test_update_path(self) -> None:
        """Test updating a node's path."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity.id, "/old")
        assert index.exists("/old")

        index.update_path(entity.id, "/old", "/new")
        assert not index.exists("/old")
        assert index.exists("/new")
        assert index.get("/new").id == entity.id


class TestPathIndexDuplicates:
    """Tests for duplicate path handling."""

    def test_duplicate_path_raises(self) -> None:
        """Test adding duplicate path raises DuplicatePathError."""
        world = World()
        world.register_prefab("node", {})
        entity1 = world.spawn("node")
        entity2 = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity1.id, "/test")

        with pytest.raises(DuplicatePathError) as exc_info:
            index.add_node(entity2.id, "/test")
        assert exc_info.value.path == "/test"

    def test_update_to_duplicate_path_raises(self) -> None:
        """Test updating to a duplicate path raises DuplicatePathError."""
        world = World()
        world.register_prefab("node", {})
        entity1 = world.spawn("node")
        entity2 = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity1.id, "/path1")
        index.add_node(entity2.id, "/path2")

        with pytest.raises(DuplicatePathError):
            index.update_path(entity2.id, "/path2", "/path1")

    def test_same_entity_same_path_ok(self) -> None:
        """Test adding same entity with same path is OK."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")

        index = PathIndex(world)
        index.add_node(entity.id, "/test")
        # Should not raise
        index.add_node(entity.id, "/test")
        assert index.count() == 1


class TestPathIndexLazyInit:
    """Tests for lazy initialization."""

    def test_lazy_init_from_world_state(self) -> None:
        """Test index initializes lazily from world state."""
        world = World()
        world.register_prefab("node", {})

        # Create entities with NodePath BEFORE creating index
        entity1 = world.spawn("node")
        entity1.add_component(NodePath(path="/world"))
        entity2 = world.spawn("node")
        entity2.add_component(NodePath(path="/ui"))

        # Create index - should pick up existing entities
        index = PathIndex(world)

        # First access triggers initialization
        assert index.count() == 2
        assert index.exists("/world")
        assert index.exists("/ui")
        assert index.get("/world").id == entity1.id
        assert index.get("/ui").id == entity2.id

    def test_invalidate(self) -> None:
        """Test invalidating the index."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))

        index = PathIndex(world)
        assert index.count() == 1

        index.invalidate()

        # Add another entity directly to world
        entity2 = world.spawn("node")
        entity2.add_component(NodePath(path="/test2"))

        # Index should rebuild on next access
        assert index.count() == 2


class TestPathIndexIndexView:
    """Tests for IndexView interface implementation."""

    def test_iteration(self) -> None:
        """Test iterating over indexed entities."""
        world = World()
        world.register_prefab("node", {})
        entity1 = world.spawn("node")
        entity1.add_component(NodePath(path="/a"))
        entity2 = world.spawn("node")
        entity2.add_component(NodePath(path="/b"))

        index = PathIndex(world)
        entities = list(index)
        assert len(entities) == 2

        entity_ids = {e.id for e in entities}
        assert entity1.id in entity_ids
        assert entity2.id in entity_ids

    def test_len(self) -> None:
        """Test __len__ implementation."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))

        index = PathIndex(world)
        assert len(index) == 1

    def test_get_entity_ids(self) -> None:
        """Test get_entity_ids returns correct set."""
        world = World()
        world.register_prefab("node", {})
        entity1 = world.spawn("node")
        entity1.add_component(NodePath(path="/a"))
        entity2 = world.spawn("node")
        entity2.add_component(NodePath(path="/b"))

        index = PathIndex(world)
        ids = index.get_entity_ids()

        assert len(ids) == 2
        assert entity1.id in ids
        assert entity2.id in ids

    def test_get_entity_ids_returns_copy(self) -> None:
        """Test get_entity_ids returns a copy."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")
        entity.add_component(NodePath(path="/test"))

        index = PathIndex(world)
        ids1 = index.get_entity_ids()
        ids2 = index.get_entity_ids()

        # Should be equal but not the same object
        assert ids1 == ids2
        assert ids1 is not ids2
