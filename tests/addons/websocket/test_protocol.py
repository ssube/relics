"""Tests for WebSocket protocol messages."""

import json
import time

import pytest
from pydantic.dataclasses import dataclass

from relics import Component
from relics.addons.websocket import (
    PROTOCOL_VERSION,
    ComponentChangedPayload,
    EntityCreatedPayload,
    EntityDestroyedPayload,
    ErrorPayload,
    GoodbyePayload,
    HeartbeatPayload,
    HelloPayload,
    Message,
    MessageType,
    RejectedPayload,
    SyncFullPayload,
    SyncRequestPayload,
    WelcomePayload,
    create_component_changed,
    create_entity_created,
    create_entity_destroyed,
    create_error,
    create_goodbye,
    create_heartbeat,
    create_heartbeat_ack,
    create_hello,
    create_rejected,
    create_sync_full,
    create_sync_request,
    create_welcome,
    deserialize_component,
    serialize_component,
)
from relics.addons.websocket.exceptions import ProtocolError
from relics.types import EntityId


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


class TestMessageType:
    """Tests for MessageType enum."""

    def test_all_message_types_exist(self) -> None:
        """Test that all expected message types exist."""
        expected_types = [
            "HELLO",
            "WELCOME",
            "HEARTBEAT",
            "HEARTBEAT_ACK",
            "GOODBYE",
            "SYNC_REQUEST",
            "SYNC_FULL",
            "ENTITY_CREATED",
            "ENTITY_DESTROYED",
            "COMPONENT_CHANGED",
            "REJECTED",
            "ERROR",
        ]
        for name in expected_types:
            assert hasattr(MessageType, name)

    def test_message_type_values_unique(self) -> None:
        """Test that message type values are unique."""
        values = [mt.value for mt in MessageType]
        assert len(values) == len(set(values))


class TestPayloads:
    """Tests for payload dataclasses."""

    def test_hello_payload(self) -> None:
        """Test HelloPayload creation."""
        payload = HelloPayload(
            client_id="test_client",
            requested_whitelist=["Position", "Velocity"],
        )
        assert payload.client_id == "test_client"
        assert payload.protocol_version == PROTOCOL_VERSION
        assert "Position" in payload.requested_whitelist

    def test_hello_payload_defaults(self) -> None:
        """Test HelloPayload with defaults."""
        payload = HelloPayload(client_id="test")
        assert payload.protocol_version == PROTOCOL_VERSION
        assert payload.requested_whitelist == []

    def test_welcome_payload(self) -> None:
        """Test WelcomePayload creation."""
        payload = WelcomePayload(
            server_id="server_1",
            component_whitelist=["Position"],
        )
        assert payload.server_id == "server_1"
        assert "Position" in payload.component_whitelist

    def test_heartbeat_payload(self) -> None:
        """Test HeartbeatPayload creation."""
        payload = HeartbeatPayload(ping_id=42)
        assert payload.ping_id == 42

    def test_goodbye_payload(self) -> None:
        """Test GoodbyePayload creation."""
        payload = GoodbyePayload(reason="client disconnect")
        assert payload.reason == "client disconnect"

    def test_goodbye_payload_default(self) -> None:
        """Test GoodbyePayload with default reason."""
        payload = GoodbyePayload()
        assert payload.reason == ""

    def test_sync_request_payload(self) -> None:
        """Test SyncRequestPayload creation."""
        payload = SyncRequestPayload(since_epoch=10)
        assert payload.since_epoch == 10

    def test_sync_request_payload_default(self) -> None:
        """Test SyncRequestPayload with default epoch."""
        payload = SyncRequestPayload()
        assert payload.since_epoch == 0

    def test_sync_full_payload(self) -> None:
        """Test SyncFullPayload creation."""
        entities = {
            "player:1": {
                "prefab": "player",
                "components": {"Position": {"x": 10, "y": 20}},
            },
        }
        payload = SyncFullPayload(epoch=5, entities=entities)
        assert payload.epoch == 5
        assert "player:1" in payload.entities

    def test_entity_created_payload(self) -> None:
        """Test EntityCreatedPayload creation."""
        components = {"Position": {"x": 0, "y": 0}}
        payload = EntityCreatedPayload(
            entity_id="player:1",
            prefab="player",
            components=components,
        )
        assert payload.entity_id == "player:1"
        assert payload.prefab == "player"
        assert payload.components == components

    def test_entity_destroyed_payload(self) -> None:
        """Test EntityDestroyedPayload creation."""
        payload = EntityDestroyedPayload(entity_id="player:1")
        assert payload.entity_id == "player:1"

    def test_component_changed_payload(self) -> None:
        """Test ComponentChangedPayload creation."""
        payload = ComponentChangedPayload(
            entity_id="player:1",
            component_type="Position",
            new_value={"x": 10, "y": 20},
            old_value={"x": 0, "y": 0},
            epoch=5,
        )
        assert payload.entity_id == "player:1"
        assert payload.component_type == "Position"
        assert payload.new_value["x"] == 10
        assert payload.old_value["x"] == 0
        assert payload.epoch == 5

    def test_component_changed_payload_no_old(self) -> None:
        """Test ComponentChangedPayload without old value."""
        payload = ComponentChangedPayload(
            entity_id="player:1",
            component_type="Position",
            new_value={"x": 10, "y": 20},
        )
        assert payload.old_value is None
        assert payload.epoch == 0

    def test_rejected_payload(self) -> None:
        """Test RejectedPayload creation."""
        payload = RejectedPayload(
            original_sequence=42,
            reason="Not authorized",
        )
        assert payload.original_sequence == 42
        assert payload.reason == "Not authorized"

    def test_error_payload(self) -> None:
        """Test ErrorPayload creation."""
        payload = ErrorPayload(
            code="INVALID_ENTITY",
            message="Entity not found",
        )
        assert payload.code == "INVALID_ENTITY"
        assert payload.message == "Entity not found"


class TestMessage:
    """Tests for Message class."""

    def test_message_creation(self) -> None:
        """Test basic message creation."""
        msg = Message(
            type=MessageType.HELLO,
            payload=HelloPayload(client_id="test"),
            sequence=1,
        )
        assert msg.type == MessageType.HELLO
        assert msg.sequence == 1
        assert isinstance(msg.timestamp, float)

    def test_message_to_json(self) -> None:
        """Test message serialization to JSON."""
        msg = Message(
            type=MessageType.HELLO,
            payload=HelloPayload(client_id="test_client"),
            sequence=1,
        )
        json_str = msg.to_json()
        data = json.loads(json_str)

        assert data["type"] == "hello"
        assert data["sequence"] == 1
        assert data["payload"]["client_id"] == "test_client"
        assert "timestamp" in data

    def test_message_from_json(self) -> None:
        """Test message deserialization from JSON."""
        json_str = json.dumps(
            {
                "type": "hello",
                "sequence": 1,
                "timestamp": time.time(),
                "payload": {
                    "client_id": "test_client",
                    "protocol_version": "1.0",
                    "requested_whitelist": ["Position"],
                },
            }
        )
        msg = Message.from_json(json_str)

        assert msg.type == MessageType.HELLO
        assert msg.sequence == 1
        assert isinstance(msg.payload, HelloPayload)
        assert msg.payload.client_id == "test_client"

    def test_message_roundtrip(self) -> None:
        """Test message serialization roundtrip."""
        original = Message(
            type=MessageType.COMPONENT_CHANGED,
            payload=ComponentChangedPayload(
                entity_id="player:1",
                component_type="Position",
                new_value={"x": 10.5, "y": 20.5},
            ),
            sequence=42,
        )
        json_str = original.to_json()
        restored = Message.from_json(json_str)

        assert restored.type == original.type
        assert restored.sequence == original.sequence
        assert isinstance(restored.payload, ComponentChangedPayload)
        assert restored.payload.entity_id == "player:1"
        assert restored.payload.new_value["x"] == 10.5

    def test_message_from_json_invalid_json(self) -> None:
        """Test that invalid JSON raises ProtocolError."""
        with pytest.raises(ProtocolError, match="Invalid JSON"):
            Message.from_json("not valid json {")

    def test_message_from_json_missing_type(self) -> None:
        """Test that missing type raises ProtocolError."""
        with pytest.raises(ProtocolError, match="missing 'type'"):
            Message.from_json('{"payload": {}}')

    def test_message_from_json_unknown_type(self) -> None:
        """Test that unknown type raises ProtocolError."""
        with pytest.raises(ProtocolError, match="Unknown message type"):
            Message.from_json('{"type": "unknown", "payload": {}}')

    def test_message_from_json_missing_payload(self) -> None:
        """Test that missing payload raises ProtocolError."""
        with pytest.raises(ProtocolError, match="missing 'payload'"):
            Message.from_json('{"type": "hello"}')

    def test_message_from_json_invalid_payload(self) -> None:
        """Test that invalid payload raises ProtocolError."""
        with pytest.raises(ProtocolError, match="Invalid payload"):
            Message.from_json('{"type": "hello", "payload": {"invalid": "field"}}')


class TestMessageFactories:
    """Tests for message factory functions."""

    def test_create_hello(self) -> None:
        """Test create_hello factory."""
        msg = create_hello(
            client_id="test_client",
            requested_whitelist=["Position"],
            sequence=1,
        )
        assert msg.type == MessageType.HELLO
        assert msg.sequence == 1
        assert isinstance(msg.payload, HelloPayload)
        assert msg.payload.client_id == "test_client"

    def test_create_hello_no_whitelist(self) -> None:
        """Test create_hello with no whitelist."""
        msg = create_hello(client_id="test")
        assert msg.payload.requested_whitelist == []

    def test_create_welcome(self) -> None:
        """Test create_welcome factory."""
        msg = create_welcome(
            server_id="server_1",
            component_whitelist=["Position"],
            sequence=2,
        )
        assert msg.type == MessageType.WELCOME
        assert isinstance(msg.payload, WelcomePayload)
        assert msg.payload.server_id == "server_1"

    def test_create_heartbeat(self) -> None:
        """Test create_heartbeat factory."""
        msg = create_heartbeat(ping_id=42, sequence=3)
        assert msg.type == MessageType.HEARTBEAT
        assert isinstance(msg.payload, HeartbeatPayload)
        assert msg.payload.ping_id == 42

    def test_create_heartbeat_ack(self) -> None:
        """Test create_heartbeat_ack factory."""
        msg = create_heartbeat_ack(ping_id=42, sequence=4)
        assert msg.type == MessageType.HEARTBEAT_ACK
        assert msg.payload.ping_id == 42

    def test_create_goodbye(self) -> None:
        """Test create_goodbye factory."""
        msg = create_goodbye(reason="test disconnect", sequence=5)
        assert msg.type == MessageType.GOODBYE
        assert isinstance(msg.payload, GoodbyePayload)
        assert msg.payload.reason == "test disconnect"

    def test_create_sync_request(self) -> None:
        """Test create_sync_request factory."""
        msg = create_sync_request(since_epoch=10, sequence=6)
        assert msg.type == MessageType.SYNC_REQUEST
        assert isinstance(msg.payload, SyncRequestPayload)
        assert msg.payload.since_epoch == 10

    def test_create_sync_full(self) -> None:
        """Test create_sync_full factory."""
        entities = {"player:1": {"prefab": "player", "components": {}}}
        msg = create_sync_full(epoch=5, entities=entities, sequence=7)
        assert msg.type == MessageType.SYNC_FULL
        assert isinstance(msg.payload, SyncFullPayload)
        assert msg.payload.epoch == 5

    def test_create_entity_created(self) -> None:
        """Test create_entity_created factory."""
        entity_id = EntityId(prefab="player", sequence=1)
        components = {"Position": {"x": 0, "y": 0}}
        msg = create_entity_created(
            entity_id=entity_id,
            prefab="player",
            components=components,
            sequence=8,
        )
        assert msg.type == MessageType.ENTITY_CREATED
        assert isinstance(msg.payload, EntityCreatedPayload)
        assert msg.payload.prefab == "player"

    def test_create_entity_destroyed(self) -> None:
        """Test create_entity_destroyed factory."""
        entity_id = EntityId(prefab="player", sequence=1)
        msg = create_entity_destroyed(entity_id=entity_id, sequence=9)
        assert msg.type == MessageType.ENTITY_DESTROYED
        assert isinstance(msg.payload, EntityDestroyedPayload)

    def test_create_component_changed(self) -> None:
        """Test create_component_changed factory."""
        entity_id = EntityId(prefab="player", sequence=1)
        msg = create_component_changed(
            entity_id=entity_id,
            component_type="Position",
            new_value={"x": 10, "y": 20},
            old_value={"x": 0, "y": 0},
            epoch=5,
            sequence=10,
        )
        assert msg.type == MessageType.COMPONENT_CHANGED
        assert isinstance(msg.payload, ComponentChangedPayload)
        assert msg.payload.new_value["x"] == 10

    def test_create_rejected(self) -> None:
        """Test create_rejected factory."""
        msg = create_rejected(
            original_sequence=42,
            reason="Not authorized",
            sequence=11,
        )
        assert msg.type == MessageType.REJECTED
        assert isinstance(msg.payload, RejectedPayload)
        assert msg.payload.original_sequence == 42

    def test_create_error(self) -> None:
        """Test create_error factory."""
        msg = create_error(
            code="INVALID_ENTITY",
            message="Entity not found",
            sequence=12,
        )
        assert msg.type == MessageType.ERROR
        assert isinstance(msg.payload, ErrorPayload)
        assert msg.payload.code == "INVALID_ENTITY"


class TestComponentSerialization:
    """Tests for component serialization helpers."""

    def test_serialize_component(self) -> None:
        """Test serializing a component."""
        component = Position(x=10.5, y=20.5)
        data = serialize_component(component)
        assert data["x"] == 10.5
        assert data["y"] == 20.5

    def test_deserialize_component(self) -> None:
        """Test deserializing a component."""
        data = {"x": 10.5, "y": 20.5}
        component = deserialize_component(Position, data)
        assert isinstance(component, Position)
        assert component.x == 10.5
        assert component.y == 20.5

    def test_serialize_deserialize_roundtrip(self) -> None:
        """Test component serialization roundtrip."""
        original = Position(x=123.456, y=789.012)
        data = serialize_component(original)
        restored = deserialize_component(Position, data)
        assert restored.x == original.x
        assert restored.y == original.y
