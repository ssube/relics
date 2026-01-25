"""Tests for scene graph components."""

import pytest
from pydantic import ValidationError

from relics.addons.scene_graph.components import (
    LocalOffset,
    LocalTransform,
    NodeName,
    NodePath,
    WorldTransform,
)
from relics.addons.scene_graph.types import Mat4, Quat, Vec3
from relics.monitored import is_monitored


class TestNodeName:
    """Tests for NodeName component."""

    def test_create_with_name(self) -> None:
        """Test creating NodeName with a name."""
        node = NodeName(name="test_node")
        assert node.name == "test_node"

    def test_requires_name(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError):
            NodeName()  # type: ignore

    def test_is_monitored(self) -> None:
        """Test that NodeName is monitored for changes."""
        assert is_monitored(NodeName)


class TestNodePath:
    """Tests for NodePath component."""

    def test_create_with_path(self) -> None:
        """Test creating NodePath with a path."""
        path = NodePath(path="/world/room_1")
        assert path.path == "/world/room_1"

    def test_requires_path(self) -> None:
        """Test that path is required."""
        with pytest.raises(ValidationError):
            NodePath()  # type: ignore

    def test_is_monitored(self) -> None:
        """Test that NodePath is monitored for changes."""
        assert is_monitored(NodePath)


class TestLocalTransform:
    """Tests for LocalTransform component."""

    def test_default_values(self) -> None:
        """Test default values are identity transform."""
        transform = LocalTransform()
        assert transform.position == Vec3.zero()
        assert transform.rotation == Quat.identity()
        assert transform.scale == Vec3.one()

    def test_explicit_values(self) -> None:
        """Test creating with explicit values."""
        pos = Vec3(1.0, 2.0, 3.0)
        rot = Quat(0.0, 0.0, 0.0, 1.0)
        scale = Vec3(2.0, 2.0, 2.0)
        transform = LocalTransform(position=pos, rotation=rot, scale=scale)
        assert transform.position == pos
        assert transform.rotation == rot
        assert transform.scale == scale

    def test_identity_factory(self) -> None:
        """Test identity factory method."""
        transform = LocalTransform.identity()
        assert transform.position == Vec3.zero()
        assert transform.rotation == Quat.identity()
        assert transform.scale == Vec3.one()

    def test_is_monitored(self) -> None:
        """Test that LocalTransform is monitored for changes."""
        assert is_monitored(LocalTransform)


class TestWorldTransform:
    """Tests for WorldTransform component."""

    def test_default_values(self) -> None:
        """Test default values are identity transform."""
        transform = WorldTransform()
        assert transform.position == Vec3.zero()
        assert transform.rotation == Quat.identity()
        assert transform.scale == Vec3.one()
        assert transform.matrix == Mat4.identity()

    def test_explicit_values(self) -> None:
        """Test creating with explicit values."""
        pos = Vec3(1.0, 2.0, 3.0)
        rot = Quat(0.0, 0.0, 0.0, 1.0)
        scale = Vec3(2.0, 2.0, 2.0)
        matrix = Mat4.from_trs(pos, rot, scale)
        transform = WorldTransform(
            position=pos, rotation=rot, scale=scale, matrix=matrix
        )
        assert transform.position == pos
        assert transform.rotation == rot
        assert transform.scale == scale
        assert transform.matrix == matrix

    def test_identity_factory(self) -> None:
        """Test identity factory method."""
        transform = WorldTransform.identity()
        assert transform.position == Vec3.zero()
        assert transform.rotation == Quat.identity()
        assert transform.scale == Vec3.one()
        assert transform.matrix == Mat4.identity()

    def test_from_local(self) -> None:
        """Test creating world transform from local transform."""
        local = LocalTransform(
            position=Vec3(10.0, 20.0, 30.0),
            rotation=Quat.identity(),
            scale=Vec3(2.0, 2.0, 2.0),
        )
        world = WorldTransform.from_local(local)
        assert world.position == local.position
        assert world.rotation == local.rotation
        assert world.scale == local.scale
        # Matrix should be computed
        assert world.matrix == Mat4.from_trs(
            local.position, local.rotation, local.scale
        )

    def test_is_monitored(self) -> None:
        """Test that WorldTransform is monitored for changes."""
        assert is_monitored(WorldTransform)


class TestLocalOffset:
    """Tests for LocalOffset component."""

    def test_default_values(self) -> None:
        """Test default values are identity offset."""
        offset = LocalOffset()
        assert offset.position == Vec3.zero()
        assert offset.rotation == Quat.identity()
        assert offset.scale == Vec3.one()

    def test_explicit_values(self) -> None:
        """Test creating with explicit values."""
        pos = Vec3(5.0, 0.0, 0.0)
        rot = Quat.identity()
        scale = Vec3(0.5, 0.5, 0.5)
        offset = LocalOffset(position=pos, rotation=rot, scale=scale)
        assert offset.position == pos
        assert offset.rotation == rot
        assert offset.scale == scale

    def test_identity_factory(self) -> None:
        """Test identity factory method."""
        offset = LocalOffset.identity()
        assert offset.position == Vec3.zero()
        assert offset.rotation == Quat.identity()
        assert offset.scale == Vec3.one()

    def test_is_monitored(self) -> None:
        """Test that LocalOffset is monitored for changes."""
        assert is_monitored(LocalOffset)


class TestComponentMutability:
    """Tests for component mutability with monitoring."""

    def test_local_transform_mutable(self) -> None:
        """Test that LocalTransform fields can be mutated."""
        transform = LocalTransform()
        new_pos = Vec3(5.0, 10.0, 15.0)
        transform.position = new_pos
        assert transform.position == new_pos

    def test_world_transform_mutable(self) -> None:
        """Test that WorldTransform fields can be mutated."""
        transform = WorldTransform()
        new_pos = Vec3(100.0, 200.0, 300.0)
        transform.position = new_pos
        assert transform.position == new_pos

    def test_node_name_mutable(self) -> None:
        """Test that NodeName can be mutated."""
        node = NodeName(name="old_name")
        node.name = "new_name"
        assert node.name == "new_name"

    def test_node_path_mutable(self) -> None:
        """Test that NodePath can be mutated."""
        path = NodePath(path="/old/path")
        path.path = "/new/path"
        assert path.path == "/new/path"

    def test_local_offset_mutable(self) -> None:
        """Test that LocalOffset can be mutated."""
        offset = LocalOffset()
        new_pos = Vec3(1.0, 2.0, 3.0)
        offset.position = new_pos
        assert offset.position == new_pos
