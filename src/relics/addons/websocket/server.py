"""WebSocket server driver for real-time synchronization."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, cast

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from relics.persistence.serialization import _component_to_dict
from relics.types import Component, EntityId

from .base import SyncDriver
from .exceptions import ProtocolError
from .observers import (
    SyncComponentObserver,
    SyncEntityObserver,
    create_entity_observer,
    create_sync_observer,
)
from .protocol import (
    ComponentChangedPayload,
    HelloPayload,
    Message,
    MessageType,
    SyncRequestPayload,
    create_component_changed,
    create_entity_created,
    create_entity_destroyed,
    create_error,
    create_goodbye,
    create_heartbeat,
    create_heartbeat_ack,
    create_rejected,
    create_sync_full,
    create_welcome,
)
from .types import ClientConnection, ConnectionState

if TYPE_CHECKING:
    from relics.entity import Entity
    from relics.world import World


logger = logging.getLogger(__name__)


class WebSocketServerDriver(SyncDriver):
    """WebSocket server for real-time world synchronization.

    Listens for client connections and synchronizes component changes between
    all connected clients. The server is authoritative for entity lifecycle
    and non-whitelisted components.

    Example:
        >>> server = WebSocketServerDriver(
        ...     host="localhost",
        ...     port=8765,
        ...     component_whitelist={InputState, PlayerCommand},
        ... )
        >>> server.attach(world)
        >>> await server.start()
        >>>
        >>> # In game loop
        >>> while running:
        ...     await server.process_messages(timeout=0.016)
        ...     world.tick(0.016)
        ...     await server.broadcast_changes()
        >>>
        >>> await server.stop()

    Attributes:
        host: Server host address.
        port: Server port number.
        clients: Connected clients indexed by client_id.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        component_whitelist: Optional[Set[Type[Component]]] = None,
        server_id: Optional[str] = None,
        heartbeat_interval: float = 5.0,
        heartbeat_timeout: float = 15.0,
    ) -> None:
        """Create a WebSocket server driver.

        Args:
            host: Host address to bind to.
            port: Port number to listen on.
            component_whitelist: Component types clients can modify.
                All other components are server-authoritative.
            server_id: Unique identifier for this server.
            heartbeat_interval: Interval between heartbeat messages.
            heartbeat_timeout: Time before considering a client disconnected.
        """
        self.host = host
        self.port = port
        self._component_whitelist: Set[str] = {
            c.__name__ for c in (component_whitelist or set())
        }
        self._server_id = server_id or f"server_{id(self)}"
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout

        self._state = ConnectionState.DISCONNECTED
        self._server: Optional[Any] = None  # websockets server
        self._world: Optional["World"] = None
        self._clients: Dict[str, ClientConnection] = {}
        self._websocket_to_client: Dict[ServerConnection, str] = {}
        self._observers: List[SyncComponentObserver | SyncEntityObserver] = []
        self._sequence: int = 0
        self._pending_broadcasts: asyncio.Queue[Message] = asyncio.Queue()
        self._running: bool = False

    @property
    def state(self) -> ConnectionState:
        """Current server state."""
        return self._state

    @property
    def clients(self) -> Dict[str, ClientConnection]:
        """Connected clients."""
        return self._clients.copy()

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._clients)

    def is_client_authoritative_for(
        self, client_id: str, component_type: Type[Component]
    ) -> bool:
        """Check if a client is authoritative for a component type.

        Args:
            client_id: The client to check.
            component_type: The component type to check.

        Returns:
            True if the client can modify this component type.
        """
        if client_id not in self._clients:
            return False
        client = self._clients[client_id]
        return component_type.__name__ in client.component_whitelist

    async def start(self) -> None:
        """Start the WebSocket server.

        Raises:
            ConnectionError: If server cannot be started.
        """
        if self._state != ConnectionState.DISCONNECTED:
            return

        self._state = ConnectionState.CONNECTING
        self._running = True

        try:
            self._server = await serve(
                self._handle_connection,
                self.host,
                self.port,
            )
        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            self._running = False
            msg = f"Failed to start server on {self.host}:{self.port}: {e}"
            raise ConnectionError(msg) from e

        self._state = ConnectionState.READY
        logger.info(f"WebSocket server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server gracefully."""
        if self._state == ConnectionState.DISCONNECTED:
            return

        self._state = ConnectionState.CLOSING
        self._running = False

        # Send goodbye to all clients
        goodbye = create_goodbye(
            reason="server shutdown",
            sequence=self._next_sequence(),
        )
        await self._broadcast(goodbye)

        # Close all client connections
        for client in list(self._clients.values()):
            try:
                await client.websocket.close()
            except Exception:
                pass

        self._clients.clear()
        self._websocket_to_client.clear()

        # Stop the server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._state = ConnectionState.DISCONNECTED
        logger.info("WebSocket server stopped")

    # SyncDriver interface methods (server doesn't use these directly)

    async def connect(self) -> None:
        """Start the server (alias for start())."""
        await self.start()

    async def disconnect(self) -> None:
        """Stop the server (alias for stop())."""
        await self.stop()

    def attach(self, world: "World") -> None:
        """Attach this server to a world.

        Registers observers to detect changes that need to be broadcast.

        Args:
            world: The World to synchronize.
        """
        self._world = world
        self._register_observers()

    def detach(self) -> None:
        """Detach this server from its current world."""
        self._unregister_observers()
        self._world = None

    async def sync(self) -> None:
        """Server doesn't need to sync - it's the source of truth."""
        pass

    async def process_messages(self, timeout: float = 0.0) -> None:
        """Process is handled by connection handlers.

        For server, this method is a no-op as messages are processed
        in the connection handler coroutines.
        """
        # Messages are processed in _handle_connection
        # This is here for interface compatibility
        await asyncio.sleep(0)

    async def broadcast_changes(self) -> None:
        """Broadcast all pending changes to connected clients."""
        while not self._pending_broadcasts.empty():
            try:
                msg = self._pending_broadcasts.get_nowait()
                await self._broadcast(msg)
            except asyncio.QueueEmpty:
                break

    async def send_heartbeats(self) -> None:
        """Send heartbeat to all connected clients."""
        heartbeat = create_heartbeat(
            ping_id=self._next_sequence(),
            sequence=self._next_sequence(),
        )
        await self._broadcast(heartbeat)

    # Connection handling

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        """Handle a new WebSocket connection.

        Args:
            websocket: The WebSocket connection.
        """
        client_id: Optional[str] = None

        try:
            # Wait for HELLO message
            client_id = await self._handle_handshake(websocket)
            if not client_id:
                return

            logger.info(f"Client {client_id} connected")

            # Process messages until disconnection
            async for data in websocket:
                if not self._running:
                    break
                try:
                    msg = Message.from_json(str(data))
                    await self._handle_message(client_id, msg)
                except ProtocolError as e:
                    logger.warning(f"Protocol error from {client_id}: {e}")
                    error = create_error(
                        code="PROTOCOL_ERROR",
                        message=str(e),
                        sequence=self._next_sequence(),
                    )
                    await self._send_to_client(client_id, error)

        except ConnectionClosed:
            logger.info(f"Client {client_id or 'unknown'} disconnected")
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            if client_id:
                self._remove_client(client_id)

    async def _handle_handshake(self, websocket: ServerConnection) -> Optional[str]:
        """Handle the handshake with a new client.

        Args:
            websocket: The WebSocket connection.

        Returns:
            The client ID if handshake succeeds, None otherwise.
        """
        try:
            data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            msg = Message.from_json(str(data))
        except asyncio.TimeoutError:
            logger.warning("Handshake timeout")
            await websocket.close()
            return None
        except ProtocolError as e:
            logger.warning(f"Handshake protocol error: {e}")
            await websocket.close()
            return None

        if msg.type != MessageType.HELLO:
            logger.warning(f"Expected HELLO, got {msg.type.name}")
            await websocket.close()
            return None

        hello = cast(HelloPayload, msg.payload)
        client_id = hello.client_id

        # Check for duplicate client ID
        if client_id in self._clients:
            logger.warning(f"Duplicate client ID: {client_id}")
            error = create_error(
                code="DUPLICATE_CLIENT_ID",
                message=f"Client ID '{client_id}' is already connected",
                sequence=self._next_sequence(),
            )
            await websocket.send(error.to_json())
            await websocket.close()
            return None

        # Compute effective whitelist (intersection with server's allowed list)
        requested = set(hello.requested_whitelist)
        effective = requested & self._component_whitelist

        # Register client
        self._clients[client_id] = ClientConnection(
            client_id=client_id,
            websocket=websocket,
            component_whitelist=effective,
        )
        self._websocket_to_client[websocket] = client_id

        # Send WELCOME
        welcome = create_welcome(
            server_id=self._server_id,
            component_whitelist=list(effective),
            sequence=self._next_sequence(),
        )
        await websocket.send(welcome.to_json())

        logger.info(f"Client {client_id} handshake complete, whitelist: {effective}")
        return client_id

    async def _handle_message(self, client_id: str, msg: Message) -> None:
        """Handle a message from a client.

        Args:
            client_id: The client that sent the message.
            msg: The message to handle.
        """
        if msg.type == MessageType.HEARTBEAT:
            # Respond with ack
            payload = cast(Any, msg.payload)
            ack = create_heartbeat_ack(
                ping_id=payload.ping_id,
                sequence=self._next_sequence(),
            )
            await self._send_to_client(client_id, ack)

        elif msg.type == MessageType.HEARTBEAT_ACK:
            # Client acknowledged our heartbeat
            pass

        elif msg.type == MessageType.SYNC_REQUEST:
            payload = cast(SyncRequestPayload, msg.payload)
            await self._handle_sync_request(client_id, payload)

        elif msg.type == MessageType.COMPONENT_CHANGED:
            payload = cast(ComponentChangedPayload, msg.payload)
            await self._handle_component_changed(client_id, payload, msg.sequence)

        elif msg.type == MessageType.GOODBYE:
            logger.info(f"Client {client_id} sent GOODBYE")
            # Connection will be closed by the async for loop

    async def _handle_sync_request(
        self, client_id: str, payload: SyncRequestPayload
    ) -> None:
        """Handle a sync request from a client.

        Args:
            client_id: The client requesting sync.
            payload: The sync request payload.
        """
        if not self._world:
            return

        # Build full world state
        entities_data: Dict[str, Dict[str, Any]] = {}

        for entity_id, components in self._world._entities.items():
            entity_data: Dict[str, Any] = {
                "prefab": entity_id.prefab,
                "components": {},
            }

            for comp_type, comp_instance in components.items():
                entity_data["components"][comp_type.__name__] = _component_to_dict(
                    comp_instance
                )

            entities_data[str(entity_id)] = entity_data

        sync_full = create_sync_full(
            epoch=self._world.epoch,
            entities=entities_data,
            sequence=self._next_sequence(),
        )

        await self._send_to_client(client_id, sync_full)
        logger.info(f"Sent full sync to {client_id}, {len(entities_data)} entities")

    async def _handle_component_changed(
        self,
        client_id: str,
        payload: ComponentChangedPayload,
        original_sequence: int,
    ) -> None:
        """Handle a component change from a client.

        Args:
            client_id: The client that made the change.
            payload: The change payload.
            original_sequence: The sequence number of the original message.
        """
        if not self._world:
            return

        client = self._clients.get(client_id)
        if not client:
            return

        # Check if client is allowed to change this component
        if payload.component_type not in client.component_whitelist:
            logger.warning(
                "Client %s attempted unauthorized change to %s",
                client_id,
                payload.component_type,
            )
            rejected = create_rejected(
                original_sequence=original_sequence,
                reason=f"Not authorized to modify {payload.component_type}",
                sequence=self._next_sequence(),
            )
            await self._send_to_client(client_id, rejected)
            return

        # Find the entity
        entity_id = EntityId.parse(payload.entity_id)
        if not self._world.has_entity(entity_id):
            logger.warning(f"Component change for unknown entity: {entity_id}")
            rejected = create_rejected(
                original_sequence=original_sequence,
                reason=f"Unknown entity: {entity_id}",
                sequence=self._next_sequence(),
            )
            await self._send_to_client(client_id, rejected)
            return

        # Find the component type
        if payload.component_type not in self._world._component_types:
            logger.warning(f"Unknown component type: {payload.component_type}")
            rejected = create_rejected(
                original_sequence=original_sequence,
                reason=f"Unknown component type: {payload.component_type}",
                sequence=self._next_sequence(),
            )
            await self._send_to_client(client_id, rejected)
            return

        # Apply the change to the world
        comp_type = self._world._component_types[payload.component_type]
        entity = self._world.get_entity(entity_id)

        if entity.has_component(comp_type):
            component = entity.get_component(comp_type)
            # Update fields directly
            for field_name, value in payload.new_value.items():
                if hasattr(component, field_name):
                    setattr(component, field_name, value)
        else:
            # Add the component
            try:
                new_component = comp_type(**payload.new_value)
                entity.add_component(new_component)
            except Exception as e:
                logger.warning(
                    "Failed to create component %s: %s", payload.component_type, e
                )
                rejected = create_rejected(
                    original_sequence=original_sequence,
                    reason=f"Failed to create component: {e}",
                    sequence=self._next_sequence(),
                )
                await self._send_to_client(client_id, rejected)
                return

        # Broadcast change to other clients
        broadcast_msg = create_component_changed(
            entity_id=entity_id,
            component_type=payload.component_type,
            new_value=payload.new_value,
            old_value=payload.old_value,
            epoch=self._world.epoch,
            sequence=self._next_sequence(),
        )
        await self._broadcast_except(broadcast_msg, client_id)

    # Observer registration

    def _register_observers(self) -> None:
        """Register observers to detect world changes."""
        if not self._world:
            return

        # Observe entity lifecycle
        entity_observer = create_entity_observer(
            on_created=self._on_entity_created,
            on_destroyed=self._on_entity_destroyed,
        )
        self._observers.append(entity_observer)
        self._world.observe(entity_observer)

        # Observe component changes for server-authoritative components
        # (components NOT in whitelist)
        for comp_type in self._world._component_types.values():
            if comp_type.__name__ not in self._component_whitelist:
                observer = create_sync_observer(
                    component_type=comp_type,
                    on_change=self._on_server_component_change,
                )
                self._observers.append(observer)
                self._world.observe(observer)

    def _unregister_observers(self) -> None:
        """Unregister all observers."""
        self._observers.clear()

    def _on_entity_created(self, entity: "Entity") -> None:
        """Handle entity creation.

        Queues a broadcast message for the new entity.

        Args:
            entity: The entity that was created.
        """
        if not self._world:
            return

        # Build component data - access through world, not entity directly
        components: Dict[str, Dict[str, Any]] = {}
        entity_components = self._world._entities.get(entity.id, {})
        for comp_type, comp_instance in entity_components.items():
            components[comp_type.__name__] = _component_to_dict(comp_instance)

        msg = create_entity_created(
            entity_id=entity.id,
            prefab=entity.id.prefab,
            components=components,
            sequence=self._next_sequence(),
        )
        self._pending_broadcasts.put_nowait(msg)

    def _on_entity_destroyed(self, entity: "Entity") -> None:
        """Handle entity destruction.

        Queues a broadcast message for the destroyed entity.

        Args:
            entity: The entity that was destroyed.
        """
        msg = create_entity_destroyed(
            entity_id=entity.id,
            sequence=self._next_sequence(),
        )
        self._pending_broadcasts.put_nowait(msg)

    def _on_server_component_change(
        self,
        entity: "Entity",
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Handle server-authoritative component change.

        Queues a broadcast message for the change.

        Args:
            entity: The entity that changed.
            component: The current (mutated) component instance.
            field_name: The name of the field that changed.
            old_value: Previous field value.
            new_value: New field value.
        """
        if not self._world:
            return

        msg = create_component_changed(
            entity_id=entity.id,
            component_type=type(component).__name__,
            new_value=_component_to_dict(component),
            old_value=None,  # Field-level change, not full component
            epoch=self._world.epoch,
            sequence=self._next_sequence(),
        )
        self._pending_broadcasts.put_nowait(msg)

    # Client management

    def _remove_client(self, client_id: str) -> None:
        """Remove a client from the server.

        Args:
            client_id: The client to remove.
        """
        if client_id in self._clients:
            client = self._clients.pop(client_id)
            self._websocket_to_client.pop(client.websocket, None)
            logger.info(f"Client {client_id} removed")

    # Message sending

    async def _send_to_client(self, client_id: str, msg: Message) -> None:
        """Send a message to a specific client.

        Args:
            client_id: The client to send to.
            msg: The message to send.
        """
        client = self._clients.get(client_id)
        if client:
            try:
                await client.websocket.send(msg.to_json())
            except ConnectionClosed:
                self._remove_client(client_id)

    async def _broadcast(self, msg: Message) -> None:
        """Broadcast a message to all connected clients.

        Args:
            msg: The message to broadcast.
        """
        disconnected: List[str] = []

        for client_id, client in self._clients.items():
            try:
                await client.websocket.send(msg.to_json())
            except ConnectionClosed:
                disconnected.append(client_id)

        for client_id in disconnected:
            self._remove_client(client_id)

    async def _broadcast_except(self, msg: Message, exclude_client_id: str) -> None:
        """Broadcast a message to all clients except one.

        Args:
            msg: The message to broadcast.
            exclude_client_id: Client to exclude from broadcast.
        """
        disconnected: List[str] = []

        for client_id, client in self._clients.items():
            if client_id == exclude_client_id:
                continue
            try:
                await client.websocket.send(msg.to_json())
            except ConnectionClosed:
                disconnected.append(client_id)

        for client_id in disconnected:
            self._remove_client(client_id)

    def _next_sequence(self) -> int:
        """Get the next sequence number."""
        self._sequence += 1
        return self._sequence
