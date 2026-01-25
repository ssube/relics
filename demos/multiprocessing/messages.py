"""IPC message protocol for communication between ECS and renderer processes."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict


class MessageType(Enum):
    """Types of messages sent between processes."""

    CREATE = auto()   # New entity created
    UPDATE = auto()   # Entity component changed
    DESTROY = auto()  # Entity removed
    QUIT = auto()     # Signal to shut down


@dataclass
class RenderMessage:
    """Message sent from ECS process to renderer process.

    Attributes:
        entity_id: Unique identifier for the entity (string form of EntityId).
        msg_type: Type of message (CREATE, UPDATE, DESTROY, QUIT).
        data: Dictionary containing message-specific data.
            - CREATE: {"x", "y", "sprite_type", "color"}
            - UPDATE: {field_name: new_value}
            - DESTROY: {}
            - QUIT: {}
    """

    entity_id: str
    msg_type: MessageType
    data: Dict[str, Any]
