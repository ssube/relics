"""Tests for scene graph edge types."""

from relics import World
from relics.addons.scene_graph.components import NodeName
from relics.addons.scene_graph.edges import AttachedTo, ChildOf


class TestChildOf:
    """Tests for ChildOf edge."""

    def test_create_childof(self) -> None:
        """Test creating a ChildOf edge."""
        edge = ChildOf()
        assert edge is not None

    def test_validate_different_entities(self) -> None:
        """Test validation passes for different entities."""
        world = World()
        world.register_prefab("node", {})
        parent = world.spawn("node")
        child = world.spawn("node")

        edge = ChildOf()
        assert edge.validate(child, parent) is True

    def test_validate_self_reference_fails(self) -> None:
        """Test validation fails for self-reference."""
        world = World()
        world.register_prefab("node", {})
        entity = world.spawn("node")

        edge = ChildOf()
        assert edge.validate(entity, entity) is False

    def test_childof_relationship(self) -> None:
        """Test creating a ChildOf relationship."""
        world = World()
        world.register_prefab("node", {})
        parent = world.spawn("node")
        parent.add_component(NodeName(name="parent"))
        child = world.spawn("node")
        child.add_component(NodeName(name="child"))

        child.add_relationship(ChildOf(), parent.id)

        # Verify relationship exists
        relationships = child.get_relationships(ChildOf)
        assert len(relationships) == 1
        edge, target_id = relationships[0]
        assert target_id == parent.id

    def test_childof_incoming_relationship(self) -> None:
        """Test querying incoming ChildOf relationships."""
        world = World()
        world.register_prefab("node", {})
        parent = world.spawn("node")
        child1 = world.spawn("node")
        child2 = world.spawn("node")

        child1.add_relationship(ChildOf(), parent.id)
        child2.add_relationship(ChildOf(), parent.id)

        # Query children of parent
        incoming = parent.get_incoming_relationships(ChildOf)
        assert len(incoming) == 2
        source_ids = {src_id for src_id, _ in incoming}
        assert child1.id in source_ids
        assert child2.id in source_ids


class TestAttachedTo:
    """Tests for AttachedTo edge."""

    def test_create_attachedto(self) -> None:
        """Test creating an AttachedTo edge."""
        edge = AttachedTo()
        assert edge is not None

    def test_validate_always_passes(self) -> None:
        """Test validation always passes (no constraints)."""
        world = World()
        world.register_prefab("entity", {})
        world.register_prefab("node", {})
        entity = world.spawn("entity")
        node = world.spawn("node")

        edge = AttachedTo()
        assert edge.validate(entity, node) is True

    def test_attachedto_relationship(self) -> None:
        """Test creating an AttachedTo relationship."""
        world = World()
        world.register_prefab("node", {})
        world.register_prefab("item", {})
        node = world.spawn("node")
        node.add_component(NodeName(name="table"))
        item = world.spawn("item")

        item.add_relationship(AttachedTo(), node.id)

        # Verify relationship exists
        relationships = item.get_relationships(AttachedTo)
        assert len(relationships) == 1
        edge, target_id = relationships[0]
        assert target_id == node.id

    def test_attachedto_incoming_relationship(self) -> None:
        """Test querying incoming AttachedTo relationships."""
        world = World()
        world.register_prefab("node", {})
        world.register_prefab("item", {})
        node = world.spawn("node")
        item1 = world.spawn("item")
        item2 = world.spawn("item")

        item1.add_relationship(AttachedTo(), node.id)
        item2.add_relationship(AttachedTo(), node.id)

        # Query entities attached to node
        incoming = node.get_incoming_relationships(AttachedTo)
        assert len(incoming) == 2
        source_ids = {src_id for src_id, _ in incoming}
        assert item1.id in source_ids
        assert item2.id in source_ids

    def test_multiple_attachments(self) -> None:
        """Test that an entity can attach to multiple nodes."""
        world = World()
        world.register_prefab("node", {})
        world.register_prefab("item", {})
        node1 = world.spawn("node")
        node2 = world.spawn("node")
        item = world.spawn("item")

        item.add_relationship(AttachedTo(), node1.id)
        item.add_relationship(AttachedTo(), node2.id)

        # Verify both relationships exist
        relationships = item.get_relationships(AttachedTo)
        assert len(relationships) == 2


class TestEdgePydanticDataclass:
    """Tests for edge pydantic dataclass behavior."""

    def test_childof_is_dataclass(self) -> None:
        """Test that ChildOf is a pydantic dataclass."""
        edge = ChildOf()
        # Should not raise
        assert hasattr(edge, "__dataclass_fields__") or hasattr(
            edge, "__pydantic_fields__"
        )

    def test_attachedto_is_dataclass(self) -> None:
        """Test that AttachedTo is a pydantic dataclass."""
        edge = AttachedTo()
        # Should not raise
        assert hasattr(edge, "__dataclass_fields__") or hasattr(
            edge, "__pydantic_fields__"
        )
