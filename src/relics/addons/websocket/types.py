"""Type definitions for WebSocket synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Set

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection

    from relics.types import EntityId


class ConnectionState(Enum):
    """State of a WebSocket connection."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    SYNCING = auto()
    READY = auto()
    RECONNECTING = auto()
    CLOSING = auto()


@dataclass
class ClientConnection:
    """Tracks state for a connected client.

    Attributes:
        client_id: Unique identifier for this client.
        websocket: The WebSocket connection.
        component_whitelist: Component type names this client can modify.
        entity_id: Optional entity controlled by this client.
        subscribed_regions: Regions this client is interested in (v0.2).
        sequence: Last sequence number received from this client.
    """

    client_id: str
    websocket: "ServerConnection"
    component_whitelist: Set[str] = field(default_factory=set)
    entity_id: Optional["EntityId"] = None
    subscribed_regions: Set[str] = field(default_factory=set)
    sequence: int = 0
