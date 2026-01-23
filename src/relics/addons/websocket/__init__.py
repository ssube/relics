"""WebSocket synchronization addon for real-time multiplayer.

This addon provides WebSocket-based drivers for synchronizing world state
between a server and multiple clients in real-time.

Components:
    - WebSocketClientDriver: Client that connects to a server for sync
    - WebSocketServerDriver: Server that accepts client connections

The protocol supports:
    - Handshake with component whitelist negotiation
    - Full world state synchronization
    - Incremental component change propagation
    - Entity lifecycle events (create/destroy)
    - Heartbeat for connection health monitoring
    - Graceful disconnect handling

Example - Server:
    >>> from relics import World
    >>> from relics.addons.websocket import WebSocketServerDriver
    >>>
    >>> world = World()
    >>> server = WebSocketServerDriver(
    ...     host="localhost",
    ...     port=8765,
    ...     component_whitelist={InputState},
    ... )
    >>> server.attach(world)
    >>> await server.start()
    >>>
    >>> while running:
    ...     await server.process_messages()
    ...     world.tick(0.016)
    ...     await server.broadcast_changes()
    >>>
    >>> await server.stop()

Example - Client:
    >>> from relics import World
    >>> from relics.addons.websocket import WebSocketClientDriver
    >>>
    >>> world = World()
    >>> client = WebSocketClientDriver(
    ...     uri="ws://localhost:8765",
    ...     client_id="player_1",
    ...     component_whitelist={InputState},
    ... )
    >>> client.attach(world)
    >>> await client.connect()
    >>> await client.sync()
    >>>
    >>> while running:
    ...     await client.process_messages(timeout=0.016)
    ...     world.tick(0.016)
    >>>
    >>> await client.disconnect()
"""

from .base import SyncDriver
from .client import WebSocketClientDriver
from .exceptions import (
    AuthorizationError,
    ConnectionError,
    HandshakeError,
    ProtocolError,
    ReconnectionError,
    SyncError,
    WebSocketError,
)
from .observers import (
    OnChangeCallback,
    OnEntityCallback,
    SyncComponentObserver,
    SyncEntityObserver,
    create_entity_observer,
    create_sync_observer,
)
from .protocol import (
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
    Payload,
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
from .server import WebSocketServerDriver
from .types import ClientConnection, ConnectionState

__all__ = [
    # Base classes
    "SyncDriver",
    # Drivers
    "WebSocketClientDriver",
    "WebSocketServerDriver",
    # Types
    "ClientConnection",
    "ConnectionState",
    # Protocol
    "PROTOCOL_VERSION",
    "Message",
    "MessageType",
    "Payload",
    # Payloads
    "HelloPayload",
    "WelcomePayload",
    "HeartbeatPayload",
    "GoodbyePayload",
    "SyncRequestPayload",
    "SyncFullPayload",
    "EntityCreatedPayload",
    "EntityDestroyedPayload",
    "ComponentChangedPayload",
    "RejectedPayload",
    "ErrorPayload",
    # Message factories
    "create_hello",
    "create_welcome",
    "create_heartbeat",
    "create_heartbeat_ack",
    "create_goodbye",
    "create_sync_request",
    "create_sync_full",
    "create_entity_created",
    "create_entity_destroyed",
    "create_component_changed",
    "create_rejected",
    "create_error",
    "serialize_component",
    "deserialize_component",
    # Observers
    "SyncComponentObserver",
    "SyncEntityObserver",
    "OnChangeCallback",
    "OnEntityCallback",
    "create_sync_observer",
    "create_entity_observer",
    # Exceptions
    "WebSocketError",
    "ConnectionError",
    "HandshakeError",
    "AuthorizationError",
    "ProtocolError",
    "SyncError",
    "ReconnectionError",
]
