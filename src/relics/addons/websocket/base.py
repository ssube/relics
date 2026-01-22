"""Base classes for synchronization drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from relics.world import World


class SyncDriver(ABC):
    """Abstract base class for real-time synchronization drivers.

    SyncDriver differs from PersistenceDriver in that it handles real-time,
    incremental synchronization rather than full save/load operations.

    Subclasses must implement methods for connecting, disconnecting,
    attaching/detaching from worlds, and processing sync messages.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the sync endpoint.

        Raises:
            ConnectionError: If connection cannot be established.
            HandshakeError: If handshake fails.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection.

        Should send appropriate goodbye messages and clean up resources.
        """
        ...

    @abstractmethod
    def attach(self, world: "World") -> None:
        """Attach this driver to a world.

        Registers necessary observers and prepares for synchronization.

        Args:
            world: The World to synchronize.
        """
        ...

    @abstractmethod
    def detach(self) -> None:
        """Detach this driver from its current world.

        Unregisters observers and stops synchronization.
        """
        ...

    @abstractmethod
    async def sync(self) -> None:
        """Request and apply a full synchronization.

        Typically used after initial connection or reconnection.

        Raises:
            SyncError: If synchronization fails.
        """
        ...

    @abstractmethod
    async def process_messages(self, timeout: float = 0.0) -> None:
        """Process incoming messages from the connection.

        Args:
            timeout: Maximum time to wait for messages in seconds.
                0.0 means non-blocking (process available messages only).

        Raises:
            ProtocolError: If a malformed message is received.
        """
        ...
