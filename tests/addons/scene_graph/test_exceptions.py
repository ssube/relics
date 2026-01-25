"""Tests for scene graph exceptions."""

import pytest

from relics.addons.scene_graph.exceptions import (
    CycleDetectedError,
    DuplicatePathError,
    InvalidNodeError,
    SceneGraphError,
)
from relics.errors import RelicError


class TestSceneGraphError:
    """Tests for SceneGraphError base exception."""

    def test_is_relic_error(self) -> None:
        """Test that SceneGraphError inherits from RelicError."""
        assert issubclass(SceneGraphError, RelicError)
        assert issubclass(SceneGraphError, Exception)

    def test_can_raise(self) -> None:
        """Test that SceneGraphError can be raised."""
        with pytest.raises(SceneGraphError):
            raise SceneGraphError("test error")

    def test_message(self) -> None:
        """Test error message."""
        error = SceneGraphError("test message")
        assert str(error) == "test message"


class TestDuplicatePathError:
    """Tests for DuplicatePathError exception."""

    def test_inherits_from_scene_graph_error(self) -> None:
        """Test that DuplicatePathError inherits from SceneGraphError."""
        assert issubclass(DuplicatePathError, SceneGraphError)

    def test_stores_path(self) -> None:
        """Test that the path is stored."""
        error = DuplicatePathError("/world/room_1")
        assert error.path == "/world/room_1"

    def test_message_includes_path(self) -> None:
        """Test error message includes the path."""
        error = DuplicatePathError("/world/room_1")
        assert "/world/room_1" in str(error)

    def test_can_catch_as_scene_graph_error(self) -> None:
        """Test catching as SceneGraphError."""
        with pytest.raises(SceneGraphError):
            raise DuplicatePathError("/test/path")

    def test_can_catch_as_relic_error(self) -> None:
        """Test catching as RelicError."""
        with pytest.raises(RelicError):
            raise DuplicatePathError("/test/path")


class TestCycleDetectedError:
    """Tests for CycleDetectedError exception."""

    def test_inherits_from_scene_graph_error(self) -> None:
        """Test that CycleDetectedError inherits from SceneGraphError."""
        assert issubclass(CycleDetectedError, SceneGraphError)

    def test_stores_paths(self) -> None:
        """Test that child and parent paths are stored."""
        error = CycleDetectedError("/world/room", "/world/room/table")
        assert error.child_path == "/world/room"
        assert error.parent_path == "/world/room/table"

    def test_message_includes_paths(self) -> None:
        """Test error message includes both paths."""
        error = CycleDetectedError("/world/room", "/world/room/table")
        message = str(error)
        assert "/world/room" in message
        assert "/world/room/table" in message

    def test_can_catch_as_scene_graph_error(self) -> None:
        """Test catching as SceneGraphError."""
        with pytest.raises(SceneGraphError):
            raise CycleDetectedError("/a", "/b")


class TestInvalidNodeError:
    """Tests for InvalidNodeError exception."""

    def test_inherits_from_scene_graph_error(self) -> None:
        """Test that InvalidNodeError inherits from SceneGraphError."""
        assert issubclass(InvalidNodeError, SceneGraphError)

    def test_stores_entity_id(self) -> None:
        """Test that entity ID is stored."""
        error = InvalidNodeError("entity_123")
        assert error.entity_id == "entity_123"

    def test_message_includes_entity_id(self) -> None:
        """Test error message includes the entity ID."""
        error = InvalidNodeError("entity_123")
        assert "entity_123" in str(error)

    def test_message_mentions_node_name(self) -> None:
        """Test error message mentions missing NodeName."""
        error = InvalidNodeError("entity_123")
        assert "NodeName" in str(error)

    def test_can_catch_as_scene_graph_error(self) -> None:
        """Test catching as SceneGraphError."""
        with pytest.raises(SceneGraphError):
            raise InvalidNodeError("test_id")
