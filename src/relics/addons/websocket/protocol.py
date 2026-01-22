"""Message protocol for WebSocket synchronization.

Defines message types, payloads, and serialization functions for
client-server communication.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, Union, cast

from relics.persistence.serialization import _component_to_dict, _dict_to_component
from relics.types import Component, EntityId

from .exceptions import ProtocolError


class MessageType(Enum):
    """Types of messages in the sync protocol."""

    # Handshake
    HELLO = auto()
    WELCOME = auto()

    # Keep-alive
    HEARTBEAT = auto()
    HEARTBEAT_ACK = auto()

    # Disconnect
    GOODBYE = auto()

    # Sync
    SYNC_REQUEST = auto()
    SYNC_FULL = auto()

    # Entity lifecycle (server -> client only)
    ENTITY_CREATED = auto()
    ENTITY_DESTROYED = auto()

    # Component changes (bidirectional)
    COMPONENT_CHANGED = auto()

    # Error handling
    REJECTED = auto()
    ERROR = auto()


PROTOCOL_VERSION = "1.0"


# Payload dataclasses


@dataclass
class HelloPayload:
    """Payload for HELLO message (client -> server).

    Attributes:
        client_id: Unique identifier for this client.
        protocol_version: Protocol version the client supports.
        requested_whitelist: Component names the client wants to control.
    """

    client_id: str
    protocol_version: str = PROTOCOL_VERSION
    requested_whitelist: List[str] = field(default_factory=list)


@dataclass
class WelcomePayload:
    """Payload for WELCOME message (server -> client).

    Attributes:
        server_id: Unique identifier for the server.
        protocol_version: Protocol version the server supports.
        component_whitelist: Component names the client is allowed to modify.
    """

    server_id: str
    protocol_version: str = PROTOCOL_VERSION
    component_whitelist: List[str] = field(default_factory=list)


@dataclass
class HeartbeatPayload:
    """Payload for HEARTBEAT/HEARTBEAT_ACK messages.

    Attributes:
        ping_id: Identifier to match heartbeat with ack.
    """

    ping_id: int


@dataclass
class GoodbyePayload:
    """Payload for GOODBYE message.

    Attributes:
        reason: Optional reason for disconnection.
    """

    reason: str = ""


@dataclass
class SyncRequestPayload:
    """Payload for SYNC_REQUEST message (client -> server).

    Attributes:
        since_epoch: Request only changes since this epoch (0 for full sync).
    """

    since_epoch: int = 0


@dataclass
class SyncFullPayload:
    """Payload for SYNC_FULL message (server -> client).

    Attributes:
        epoch: Current world epoch.
        entities: Dict of entity_id_str -> {prefab, components: {type_name: fields}}.
    """

    epoch: int
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class EntityCreatedPayload:
    """Payload for ENTITY_CREATED message (server -> client).

    Attributes:
        entity_id: String representation of the EntityId.
        prefab: The prefab name.
        components: Dict of component_type_name -> component fields.
    """

    entity_id: str
    prefab: str
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class EntityDestroyedPayload:
    """Payload for ENTITY_DESTROYED message (server -> client).

    Attributes:
        entity_id: String representation of the EntityId.
    """

    entity_id: str


@dataclass
class ComponentChangedPayload:
    """Payload for COMPONENT_CHANGED message (bidirectional).

    Attributes:
        entity_id: String representation of the EntityId.
        component_type: Name of the component type.
        old_value: Previous component field values (may be None for server-initiated).
        new_value: New component field values.
        epoch: World epoch when change occurred.
    """

    entity_id: str
    component_type: str
    new_value: Dict[str, Any]
    old_value: Optional[Dict[str, Any]] = None
    epoch: int = 0


@dataclass
class RejectedPayload:
    """Payload for REJECTED message (server -> client).

    Attributes:
        original_sequence: Sequence number of rejected message.
        reason: Reason for rejection.
    """

    original_sequence: int
    reason: str


@dataclass
class ErrorPayload:
    """Payload for ERROR message.

    Attributes:
        code: Error code string.
        message: Human-readable error message.
    """

    code: str
    message: str


# Type alias for all payload types
Payload = Union[
    HelloPayload,
    WelcomePayload,
    HeartbeatPayload,
    GoodbyePayload,
    SyncRequestPayload,
    SyncFullPayload,
    EntityCreatedPayload,
    EntityDestroyedPayload,
    ComponentChangedPayload,
    RejectedPayload,
    ErrorPayload,
]

# Map message types to payload classes
PAYLOAD_TYPES: Dict[MessageType, Type[Payload]] = {
    MessageType.HELLO: HelloPayload,
    MessageType.WELCOME: WelcomePayload,
    MessageType.HEARTBEAT: HeartbeatPayload,
    MessageType.HEARTBEAT_ACK: HeartbeatPayload,
    MessageType.GOODBYE: GoodbyePayload,
    MessageType.SYNC_REQUEST: SyncRequestPayload,
    MessageType.SYNC_FULL: SyncFullPayload,
    MessageType.ENTITY_CREATED: EntityCreatedPayload,
    MessageType.ENTITY_DESTROYED: EntityDestroyedPayload,
    MessageType.COMPONENT_CHANGED: ComponentChangedPayload,
    MessageType.REJECTED: RejectedPayload,
    MessageType.ERROR: ErrorPayload,
}


@dataclass
class Message:
    """A protocol message with type, payload, and metadata.

    Attributes:
        type: The message type.
        payload: The message payload (type depends on message type).
        timestamp: Unix timestamp when message was created.
        sequence: Message sequence number for ordering.
    """

    type: MessageType
    payload: Payload
    timestamp: float = field(default_factory=time.time)
    sequence: int = 0

    def to_json(self) -> str:
        """Serialize message to JSON string.

        Returns:
            JSON-encoded message string.
        """
        data = {
            "type": self.type.name.lower(),
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "payload": _payload_to_dict(self.payload),
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Deserialize message from JSON string.

        Args:
            json_str: JSON-encoded message string.

        Returns:
            Deserialized Message object.

        Raises:
            ProtocolError: If message is malformed.
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Invalid JSON: {e}") from e

        if "type" not in data:
            raise ProtocolError("Message missing 'type' field")

        try:
            msg_type = MessageType[data["type"].upper()]
        except KeyError:
            raise ProtocolError(f"Unknown message type: {data['type']}")

        if "payload" not in data:
            raise ProtocolError("Message missing 'payload' field")

        payload = _dict_to_payload(msg_type, data["payload"])

        return cls(
            type=msg_type,
            payload=payload,
            timestamp=data.get("timestamp", time.time()),
            sequence=data.get("sequence", 0),
        )


def _payload_to_dict(payload: Payload) -> Dict[str, Any]:
    """Convert a payload dataclass to a dictionary.

    Args:
        payload: The payload to serialize.

    Returns:
        Dictionary representation of the payload.
    """
    if hasattr(payload, "__dataclass_fields__"):
        result = {}
        for field_name in payload.__dataclass_fields__:
            value = getattr(payload, field_name)
            result[field_name] = value
        return result
    return {}


def _dict_to_payload(msg_type: MessageType, data: Dict[str, Any]) -> Payload:
    """Convert a dictionary to the appropriate payload type.

    Args:
        msg_type: The message type to determine payload class.
        data: The dictionary to convert.

    Returns:
        The appropriate payload instance.

    Raises:
        ProtocolError: If the payload is invalid.
    """
    if msg_type not in PAYLOAD_TYPES:
        raise ProtocolError(f"No payload type for message type: {msg_type}")

    payload_class = PAYLOAD_TYPES[msg_type]
    try:
        return payload_class(**data)
    except TypeError as e:
        raise ProtocolError(f"Invalid payload for {msg_type.name}: {e}") from e


# Factory functions for creating messages


def create_hello(
    client_id: str,
    requested_whitelist: Optional[List[str]] = None,
    sequence: int = 0,
) -> Message:
    """Create a HELLO message.

    Args:
        client_id: Unique identifier for this client.
        requested_whitelist: Component names the client wants to control.
        sequence: Message sequence number.

    Returns:
        A HELLO message.
    """
    return Message(
        type=MessageType.HELLO,
        payload=HelloPayload(
            client_id=client_id,
            requested_whitelist=requested_whitelist or [],
        ),
        sequence=sequence,
    )


def create_welcome(
    server_id: str,
    component_whitelist: Optional[List[str]] = None,
    sequence: int = 0,
) -> Message:
    """Create a WELCOME message.

    Args:
        server_id: Unique identifier for the server.
        component_whitelist: Component names the client can modify.
        sequence: Message sequence number.

    Returns:
        A WELCOME message.
    """
    return Message(
        type=MessageType.WELCOME,
        payload=WelcomePayload(
            server_id=server_id,
            component_whitelist=component_whitelist or [],
        ),
        sequence=sequence,
    )


def create_heartbeat(ping_id: int, sequence: int = 0) -> Message:
    """Create a HEARTBEAT message.

    Args:
        ping_id: Identifier to match with ack.
        sequence: Message sequence number.

    Returns:
        A HEARTBEAT message.
    """
    return Message(
        type=MessageType.HEARTBEAT,
        payload=HeartbeatPayload(ping_id=ping_id),
        sequence=sequence,
    )


def create_heartbeat_ack(ping_id: int, sequence: int = 0) -> Message:
    """Create a HEARTBEAT_ACK message.

    Args:
        ping_id: Identifier matching the heartbeat.
        sequence: Message sequence number.

    Returns:
        A HEARTBEAT_ACK message.
    """
    return Message(
        type=MessageType.HEARTBEAT_ACK,
        payload=HeartbeatPayload(ping_id=ping_id),
        sequence=sequence,
    )


def create_goodbye(reason: str = "", sequence: int = 0) -> Message:
    """Create a GOODBYE message.

    Args:
        reason: Optional reason for disconnection.
        sequence: Message sequence number.

    Returns:
        A GOODBYE message.
    """
    return Message(
        type=MessageType.GOODBYE,
        payload=GoodbyePayload(reason=reason),
        sequence=sequence,
    )


def create_sync_request(since_epoch: int = 0, sequence: int = 0) -> Message:
    """Create a SYNC_REQUEST message.

    Args:
        since_epoch: Request only changes since this epoch (0 for full sync).
        sequence: Message sequence number.

    Returns:
        A SYNC_REQUEST message.
    """
    return Message(
        type=MessageType.SYNC_REQUEST,
        payload=SyncRequestPayload(since_epoch=since_epoch),
        sequence=sequence,
    )


def create_sync_full(
    epoch: int,
    entities: Dict[str, Dict[str, Any]],
    sequence: int = 0,
) -> Message:
    """Create a SYNC_FULL message.

    Args:
        epoch: Current world epoch.
        entities: Dict of entity_id_str -> entity data.
        sequence: Message sequence number.

    Returns:
        A SYNC_FULL message.
    """
    return Message(
        type=MessageType.SYNC_FULL,
        payload=SyncFullPayload(epoch=epoch, entities=entities),
        sequence=sequence,
    )


def create_entity_created(
    entity_id: EntityId,
    prefab: str,
    components: Dict[str, Dict[str, Any]],
    sequence: int = 0,
) -> Message:
    """Create an ENTITY_CREATED message.

    Args:
        entity_id: The EntityId of the created entity.
        prefab: The prefab name.
        components: Dict of component_type_name -> component fields.
        sequence: Message sequence number.

    Returns:
        An ENTITY_CREATED message.
    """
    return Message(
        type=MessageType.ENTITY_CREATED,
        payload=EntityCreatedPayload(
            entity_id=str(entity_id),
            prefab=prefab,
            components=components,
        ),
        sequence=sequence,
    )


def create_entity_destroyed(entity_id: EntityId, sequence: int = 0) -> Message:
    """Create an ENTITY_DESTROYED message.

    Args:
        entity_id: The EntityId of the destroyed entity.
        sequence: Message sequence number.

    Returns:
        An ENTITY_DESTROYED message.
    """
    return Message(
        type=MessageType.ENTITY_DESTROYED,
        payload=EntityDestroyedPayload(entity_id=str(entity_id)),
        sequence=sequence,
    )


def create_component_changed(
    entity_id: EntityId,
    component_type: str,
    new_value: Dict[str, Any],
    old_value: Optional[Dict[str, Any]] = None,
    epoch: int = 0,
    sequence: int = 0,
) -> Message:
    """Create a COMPONENT_CHANGED message.

    Args:
        entity_id: The EntityId of the entity.
        component_type: Name of the component type.
        new_value: New component field values.
        old_value: Previous component field values.
        epoch: World epoch when change occurred.
        sequence: Message sequence number.

    Returns:
        A COMPONENT_CHANGED message.
    """
    return Message(
        type=MessageType.COMPONENT_CHANGED,
        payload=ComponentChangedPayload(
            entity_id=str(entity_id),
            component_type=component_type,
            new_value=new_value,
            old_value=old_value,
            epoch=epoch,
        ),
        sequence=sequence,
    )


def create_rejected(
    original_sequence: int,
    reason: str,
    sequence: int = 0,
) -> Message:
    """Create a REJECTED message.

    Args:
        original_sequence: Sequence number of the rejected message.
        reason: Reason for rejection.
        sequence: Message sequence number.

    Returns:
        A REJECTED message.
    """
    return Message(
        type=MessageType.REJECTED,
        payload=RejectedPayload(
            original_sequence=original_sequence,
            reason=reason,
        ),
        sequence=sequence,
    )


def create_error(code: str, message: str, sequence: int = 0) -> Message:
    """Create an ERROR message.

    Args:
        code: Error code string.
        message: Human-readable error message.
        sequence: Message sequence number.

    Returns:
        An ERROR message.
    """
    return Message(
        type=MessageType.ERROR,
        payload=ErrorPayload(code=code, message=message),
        sequence=sequence,
    )


# Component serialization helpers


def serialize_component(component: Component) -> Dict[str, Any]:
    """Serialize a component to a dictionary.

    Args:
        component: The component to serialize.

    Returns:
        Dictionary of field values.
    """
    return _component_to_dict(component)


def deserialize_component(
    component_type: Type[Component],
    data: Dict[str, Any],
) -> Component:
    """Deserialize a component from a dictionary.

    Args:
        component_type: The component class.
        data: Dictionary of field values.

    Returns:
        The component instance.
    """
    return cast(Component, _dict_to_component(component_type, data))
