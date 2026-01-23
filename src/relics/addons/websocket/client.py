"""WebSocket client driver for real-time synchronization."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, cast

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from relics.persistence.serialization import _component_to_dict
from relics.types import Component, EntityId

from .base import SyncDriver
from .exceptions import (
    AuthorizationError,
    ConnectionError,
    HandshakeError,
    ProtocolError,
    ReconnectionError,
    SyncError,
)
from .observers import SyncComponentObserver, create_sync_observer
from .protocol import (
    PROTOCOL_VERSION,
    ComponentChangedPayload,
    EntityCreatedPayload,
    EntityDestroyedPayload,
    ErrorPayload,
    Message,
    MessageType,
    RejectedPayload,
    SyncFullPayload,
    WelcomePayload,
    create_component_changed,
    create_goodbye,
    create_heartbeat,
    create_heartbeat_ack,
    create_hello,
    create_sync_request,
)
from .types import ConnectionState

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    from relics.entity import Entity
    from relics.world import World


logger = logging.getLogger(__name__)


class WebSocketClientDriver(SyncDriver):
    """WebSocket client for real-time world synchronization.

    Connects to a WebSocket server to synchronize component changes.
    The client can only modify components in its whitelist; entity
    creation/destruction is server-only.

    Example:
        >>> client = WebSocketClientDriver(
        ...     uri="ws://localhost:8765",
        ...     client_id="player_1",
        ...     component_whitelist={Position, InputState},
        ... )
        >>> client.attach(world)
        >>> await client.connect()
        >>> await client.sync()
        >>>
        >>> # In game loop
        >>> while running:
        ...     await client.process_messages(timeout=0.016)
        ...     world.tick(0.016)
        >>>
        >>> await client.disconnect()

    Attributes:
        uri: WebSocket server URI.
        client_id: Unique identifier for this client.
        state: Current connection state.
    """

    def __init__(
        self,
        uri: str,
        client_id: str,
        component_whitelist: Optional[Set[Type[Component]]] = None,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0,
        heartbeat_interval: float = 5.0,
    ) -> None:
        """Create a WebSocket client driver.

        Args:
            uri: WebSocket server URI (e.g., "ws://localhost:8765").
            client_id: Unique identifier for this client.
            component_whitelist: Component types this client wants to control.
            reconnect_attempts: Maximum reconnection attempts.
            reconnect_delay: Base delay between reconnection attempts.
            heartbeat_interval: Interval between heartbeat messages.
        """
        self.uri = uri
        self.client_id = client_id
        self._requested_whitelist: Set[Type[Component]] = component_whitelist or set()
        self._effective_whitelist: Set[str] = set()
        self._reconnect_attempts = reconnect_attempts
        self._reconnect_delay = reconnect_delay
        self._heartbeat_interval = heartbeat_interval

        self._state = ConnectionState.DISCONNECTED
        self._websocket: Optional["ClientConnection"] = None
        self._world: Optional["World"] = None
        self._observers: List[SyncComponentObserver] = []
        self._sequence: int = 0
        self._last_heartbeat_id: int = 0
        self._server_id: Optional[str] = None
        self._pending_messages: asyncio.Queue[Message] = asyncio.Queue()

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    def is_authoritative_for(self, component_type: Type[Component]) -> bool:
        """Check if this client is authoritative for a component type.

        Args:
            component_type: The component type to check.

        Returns:
            True if this client can modify this component type.
        """
        return component_type.__name__ in self._effective_whitelist

    async def connect(self) -> None:
        """Connect to the WebSocket server and perform handshake.

        Raises:
            ConnectionError: If connection cannot be established.
            HandshakeError: If handshake fails.
        """
        if self._state != ConnectionState.DISCONNECTED:
            return

        self._state = ConnectionState.CONNECTING

        try:
            self._websocket = await connect(self.uri)
        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            raise ConnectionError(f"Failed to connect to {self.uri}: {e}") from e

        self._state = ConnectionState.CONNECTED

        # Send HELLO
        whitelist_names = [c.__name__ for c in self._requested_whitelist]
        hello = create_hello(
            client_id=self.client_id,
            requested_whitelist=whitelist_names,
            sequence=self._next_sequence(),
        )
        await self._send(hello)

        # Wait for WELCOME
        try:
            msg = await self._receive(timeout=10.0)
        except asyncio.TimeoutError:
            await self._close()
            raise HandshakeError("Handshake timeout waiting for WELCOME")

        if msg.type != MessageType.WELCOME:
            await self._close()
            raise HandshakeError(f"Expected WELCOME, got {msg.type.name}")

        welcome = cast(WelcomePayload, msg.payload)
        self._server_id = welcome.server_id

        if welcome.protocol_version != PROTOCOL_VERSION:
            logger.warning(
                f"Protocol version mismatch: client={PROTOCOL_VERSION}, "
                f"server={welcome.protocol_version}"
            )

        # Compute effective whitelist (intersection of requested and allowed)
        requested_names = {c.__name__ for c in self._requested_whitelist}
        server_whitelist = set(welcome.component_whitelist)
        self._effective_whitelist = requested_names & server_whitelist

        logger.info(
            f"Connected to server {self._server_id}, "
            f"whitelist: {self._effective_whitelist}"
        )

        self._state = ConnectionState.READY

    async def disconnect(self) -> None:
        """Gracefully disconnect from the server."""
        if self._state == ConnectionState.DISCONNECTED:
            return

        self._state = ConnectionState.CLOSING

        if self._websocket:
            try:
                goodbye = create_goodbye(
                    reason="client disconnect",
                    sequence=self._next_sequence(),
                )
                await self._send(goodbye)
            except Exception:
                pass  # Best effort

            await self._close()

        self._state = ConnectionState.DISCONNECTED

    def attach(self, world: "World") -> None:
        """Attach this driver to a world.

        Registers observers for whitelisted components to detect local changes.

        Args:
            world: The World to synchronize.
        """
        self._world = world
        self._register_observers()

    def detach(self) -> None:
        """Detach this driver from its current world."""
        self._unregister_observers()
        self._world = None

    async def sync(self) -> None:
        """Request and apply a full synchronization from the server.

        Raises:
            SyncError: If synchronization fails.
        """
        if self._state != ConnectionState.READY:
            raise SyncError("Cannot sync: not connected")

        self._state = ConnectionState.SYNCING

        sync_req = create_sync_request(
            since_epoch=0,
            sequence=self._next_sequence(),
        )
        await self._send(sync_req)

        try:
            msg = await self._receive(timeout=30.0)
        except asyncio.TimeoutError:
            self._state = ConnectionState.READY
            raise SyncError("Sync timeout waiting for SYNC_FULL")

        if msg.type != MessageType.SYNC_FULL:
            self._state = ConnectionState.READY
            raise SyncError(f"Expected SYNC_FULL, got {msg.type.name}")

        payload = cast(SyncFullPayload, msg.payload)
        self._apply_full_sync(payload)

        self._state = ConnectionState.READY
        logger.info(f"Full sync complete, epoch={payload.epoch}")

    async def process_messages(self, timeout: float = 0.0) -> None:
        """Process incoming messages from the server.

        Args:
            timeout: Maximum time to wait for messages in seconds.
                0.0 means non-blocking.

        Raises:
            ProtocolError: If a malformed message is received.
        """
        if self._state not in (ConnectionState.READY, ConnectionState.SYNCING):
            return

        if not self._websocket:
            return

        try:
            if timeout > 0:
                msg = await self._receive(timeout=timeout)
                await self._handle_message(msg)
            else:
                # Non-blocking: process all available messages
                while True:
                    try:
                        msg = await self._receive(timeout=0.001)
                        await self._handle_message(msg)
                    except asyncio.TimeoutError:
                        break
        except ConnectionClosed:
            await self._handle_disconnect()

    async def send_heartbeat(self) -> None:
        """Send a heartbeat message to the server."""
        if self._state != ConnectionState.READY:
            return

        self._last_heartbeat_id += 1
        heartbeat = create_heartbeat(
            ping_id=self._last_heartbeat_id,
            sequence=self._next_sequence(),
        )
        await self._send(heartbeat)

    async def _reconnect(self) -> None:
        """Attempt to reconnect to the server."""
        self._state = ConnectionState.RECONNECTING
        delay = self._reconnect_delay

        for attempt in range(self._reconnect_attempts):
            logger.info(
                f"Reconnection attempt {attempt + 1}/{self._reconnect_attempts}"
            )

            try:
                self._state = ConnectionState.DISCONNECTED
                await self.connect()
                await self.sync()
                return
            except Exception as e:
                logger.warning(f"Reconnection failed: {e}")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        self._state = ConnectionState.DISCONNECTED
        raise ReconnectionError(
            f"Failed to reconnect after {self._reconnect_attempts} attempts"
        )

    def _register_observers(self) -> None:
        """Register observers for whitelisted components."""
        if not self._world:
            return

        for comp_type in self._requested_whitelist:
            observer = create_sync_observer(
                component_type=comp_type,
                on_change=self._on_local_change,
                filter_fn=lambda t: self.is_authoritative_for(t),
            )
            self._observers.append(observer)
            self._world.observe(observer)

    def _unregister_observers(self) -> None:
        """Unregister all observers."""
        # Note: World doesn't support unregistering observers currently
        # Observers will be garbage collected when world is replaced
        self._observers.clear()

    def _on_local_change(
        self,
        entity: "Entity",
        old_value: Optional[Component],
        new_value: Component,
    ) -> None:
        """Handle local component change.

        Queues the change for sending to server.

        Args:
            entity: The entity that changed.
            old_value: Previous component value (None for additions).
            new_value: New component value.
        """
        if not self.is_authoritative_for(type(new_value)):
            return

        msg = create_component_changed(
            entity_id=entity.id,
            component_type=type(new_value).__name__,
            new_value=_component_to_dict(new_value),
            old_value=_component_to_dict(old_value) if old_value else None,
            epoch=self._world.epoch if self._world else 0,
            sequence=self._next_sequence(),
        )
        self._pending_messages.put_nowait(msg)

    async def _send_pending(self) -> None:
        """Send all pending messages to the server."""
        while not self._pending_messages.empty():
            try:
                msg = self._pending_messages.get_nowait()
                await self._send(msg)
            except asyncio.QueueEmpty:
                break

    async def _handle_message(self, msg: Message) -> None:
        """Handle an incoming message from the server.

        Args:
            msg: The message to handle.
        """
        if msg.type == MessageType.HEARTBEAT:
            payload = cast(Any, msg.payload)
            ack = create_heartbeat_ack(
                ping_id=payload.ping_id,
                sequence=self._next_sequence(),
            )
            await self._send(ack)

        elif msg.type == MessageType.HEARTBEAT_ACK:
            # Server acknowledged our heartbeat
            pass

        elif msg.type == MessageType.COMPONENT_CHANGED:
            payload = cast(ComponentChangedPayload, msg.payload)
            self._apply_component_change(payload)

        elif msg.type == MessageType.ENTITY_CREATED:
            payload = cast(EntityCreatedPayload, msg.payload)
            self._apply_entity_created(payload)

        elif msg.type == MessageType.ENTITY_DESTROYED:
            payload = cast(EntityDestroyedPayload, msg.payload)
            self._apply_entity_destroyed(payload)

        elif msg.type == MessageType.REJECTED:
            payload = cast(RejectedPayload, msg.payload)
            logger.warning(
                f"Message {payload.original_sequence} rejected: {payload.reason}"
            )

        elif msg.type == MessageType.ERROR:
            payload = cast(ErrorPayload, msg.payload)
            logger.error(f"Server error [{payload.code}]: {payload.message}")

        elif msg.type == MessageType.GOODBYE:
            logger.info("Server sent GOODBYE")
            await self._handle_disconnect()

    async def _handle_disconnect(self) -> None:
        """Handle unexpected disconnection."""
        await self._close()
        self._state = ConnectionState.DISCONNECTED
        # Could trigger reconnection here if desired

    def _apply_full_sync(self, payload: SyncFullPayload) -> None:
        """Apply a full sync payload to the world.

        Args:
            payload: The SYNC_FULL payload.
        """
        if not self._world:
            return

        # Clear and rebuild world state
        # Note: This is a simplified implementation. A production version
        # would need more careful handling of existing entities.
        for entity_id_str, entity_data in payload.entities.items():
            entity_id = EntityId.parse(entity_id_str)

            # Check if entity already exists
            if self._world.has_entity(entity_id):
                entity = self._world.get_entity(entity_id)
                # Update components from server for non-authoritative types
                for comp_name, comp_fields in entity_data.get("components", {}).items():
                    if comp_name not in self._effective_whitelist:
                        self._update_component(entity, comp_name, comp_fields)
            else:
                # Entity doesn't exist locally - this shouldn't happen in normal
                # operation since entity creation is server-only
                logger.warning(f"Sync includes unknown entity: {entity_id}")

    def _apply_component_change(self, payload: ComponentChangedPayload) -> None:
        """Apply a component change from the server.

        Args:
            payload: The COMPONENT_CHANGED payload.
        """
        if not self._world:
            return

        # Skip changes for components we're authoritative for
        if payload.component_type in self._effective_whitelist:
            return

        entity_id = EntityId.parse(payload.entity_id)
        if not self._world.has_entity(entity_id):
            logger.warning(f"Component change for unknown entity: {entity_id}")
            return

        entity = self._world.get_entity(entity_id)
        self._update_component(entity, payload.component_type, payload.new_value)

    def _apply_entity_created(self, payload: EntityCreatedPayload) -> None:
        """Apply an entity creation from the server.

        Args:
            payload: The ENTITY_CREATED payload.
        """
        if not self._world:
            return

        # Check if prefab exists
        if payload.prefab not in self._world._prefabs:
            logger.warning(f"Unknown prefab: {payload.prefab}")
            return

        # Spawn the entity with the server's ID
        # Note: This requires the world to support spawning with specific IDs
        # For now, we'll use the standard spawn and hope IDs match
        entity_id = EntityId.parse(payload.entity_id)

        if self._world.has_entity(entity_id):
            logger.warning(f"Entity already exists: {entity_id}")
            return

        # Build overrides from server's component data
        overrides: Dict[Type[Component], Component] = {}
        for comp_name, comp_fields in payload.components.items():
            if comp_name in self._world._component_types:
                comp_type = self._world._component_types[comp_name]
                try:
                    overrides[comp_type] = comp_type(**comp_fields)
                except Exception as e:
                    logger.warning(f"Failed to create component {comp_name}: {e}")

        # Use internal entity creation with specific ID
        # This is a simplified approach - production code would need
        # a proper method for this
        self._create_entity_with_id(entity_id, payload.prefab, overrides)

    def _apply_entity_destroyed(self, payload: EntityDestroyedPayload) -> None:
        """Apply an entity destruction from the server.

        Args:
            payload: The ENTITY_DESTROYED payload.
        """
        if not self._world:
            return

        entity_id = EntityId.parse(payload.entity_id)
        if self._world.has_entity(entity_id):
            self._world.remove(entity_id)
        else:
            logger.warning(f"Destroy for unknown entity: {entity_id}")

    def _update_component(
        self,
        entity: "Entity",
        comp_name: str,
        comp_fields: Dict[str, Any],
    ) -> None:
        """Update a component on an entity.

        Args:
            entity: The entity to update.
            comp_name: The component type name.
            comp_fields: The new field values.
        """
        if not self._world:
            return

        if comp_name not in self._world._component_types:
            logger.warning(f"Unknown component type: {comp_name}")
            return

        comp_type = self._world._component_types[comp_name]

        # Check if entity has this component
        if entity.has_component(comp_type):
            component = entity.get_component(comp_type)
            # Update fields directly
            for field_name, value in comp_fields.items():
                if hasattr(component, field_name):
                    setattr(component, field_name, value)
        else:
            # Add the component
            try:
                new_component = comp_type(**comp_fields)
                entity.add_component(new_component)
            except Exception as e:
                logger.warning(f"Failed to add component {comp_name}: {e}")

    def _create_entity_with_id(
        self,
        entity_id: EntityId,
        prefab: str,
        overrides: Dict[Type[Component], Component],
    ) -> None:
        """Create an entity with a specific ID.

        This is a workaround since World.spawn generates its own IDs.

        Args:
            entity_id: The specific EntityId to use.
            prefab: The prefab name.
            overrides: Component overrides.
        """
        if not self._world:
            return

        # Directly manipulate world internals (not ideal but necessary)
        components: Dict[Type[Component], Component] = {}

        # Copy prefab components
        if prefab in self._world._prefabs:
            import copy

            for comp_type, comp_instance in self._world._prefabs[prefab].items():
                if comp_type in overrides:
                    components[comp_type] = overrides[comp_type]
                elif (
                    hasattr(comp_instance, "_is_monitored")
                    and comp_instance._is_monitored
                ):
                    components[comp_type] = copy.copy(comp_instance)
                else:
                    components[comp_type] = comp_instance

        # Apply overrides not in prefab
        for comp_type, comp_instance in overrides.items():
            if comp_type not in components:
                components[comp_type] = comp_instance

        # Store entity
        self._world._entities[entity_id] = components

        # Update indexes
        if prefab not in self._world._prefab_index:
            self._world._prefab_index[prefab] = set()
        self._world._prefab_index[prefab].add(entity_id)

        for comp_type, comp_instance in components.items():
            if comp_type not in self._world._component_index:
                self._world._component_index[comp_type] = set()
            self._world._component_index[comp_type].add(entity_id)

            if hasattr(comp_instance, "_bind_to_world"):
                comp_instance._bind_to_world(self._world, entity_id)

    def _next_sequence(self) -> int:
        """Get the next sequence number."""
        self._sequence += 1
        return self._sequence

    async def _send(self, msg: Message) -> None:
        """Send a message to the server.

        Args:
            msg: The message to send.
        """
        if self._websocket:
            await self._websocket.send(msg.to_json())

    async def _receive(self, timeout: float) -> Message:
        """Receive a message from the server.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            The received message.

        Raises:
            asyncio.TimeoutError: If timeout expires.
            ProtocolError: If message is malformed.
        """
        if not self._websocket:
            raise ConnectionError("Not connected")

        data = await asyncio.wait_for(
            self._websocket.recv(),
            timeout=timeout,
        )
        return Message.from_json(str(data))

    async def _close(self) -> None:
        """Close the WebSocket connection."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
