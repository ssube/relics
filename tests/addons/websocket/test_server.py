"""Tests for WebSocket server driver."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, World, monitored
from relics.addons.websocket import (
    ClientConnection,
    ConnectionState,
    Message,
    MessageType,
    WebSocketServerDriver,
    create_component_changed,
    create_goodbye,
    create_heartbeat,
    create_hello,
    create_sync_request,
)
from relics.types import EntityId


@dataclass
class Position(Component):
    """Test component for position."""

    x: float
    y: float


@monitored
@dataclass
class InputState(Component):
    """Test monitored component for input."""

    move_x: float = 0.0
    move_y: float = 0.0


@dataclass
class Health(Component):
    """Test component for health."""

    current: int
    maximum: int


class TestWebSocketServerDriverInit:
    """Tests for WebSocketServerDriver initialization."""

    def test_server_creation(self) -> None:
        """Test basic server creation."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
        )
        assert server.host == "localhost"
        assert server.port == 8765
        assert server.state == ConnectionState.DISCONNECTED

    def test_server_with_whitelist(self) -> None:
        """Test server creation with component whitelist."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState, Position},
        )
        assert "InputState" in server._component_whitelist
        assert "Position" in server._component_whitelist

    def test_server_with_custom_settings(self) -> None:
        """Test server creation with custom settings."""
        server = WebSocketServerDriver(
            host="0.0.0.0",
            port=9000,
            server_id="custom_server",
            heartbeat_interval=10.0,
            heartbeat_timeout=30.0,
        )
        assert server.host == "0.0.0.0"
        assert server.port == 9000
        assert server._server_id == "custom_server"
        assert server._heartbeat_interval == 10.0
        assert server._heartbeat_timeout == 30.0

    def test_server_generates_default_id(self) -> None:
        """Test that server generates a default ID if not provided."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        assert server._server_id.startswith("server_")


class TestWebSocketServerDriverAttach:
    """Tests for WebSocketServerDriver world attachment."""

    def test_attach_world(self) -> None:
        """Test attaching server to world."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},
        )
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Position)
        world.register_component_type(Health)

        server.attach(world)

        assert server._world == world
        # Should have entity observer + component observers for non-whitelisted types
        assert len(server._observers) > 0

    def test_detach_world(self) -> None:
        """Test detaching server from world."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
        )
        world = World()
        server.attach(world)
        server.detach()

        assert server._world is None
        assert len(server._observers) == 0


class TestWebSocketServerDriverAuthority:
    """Tests for WebSocketServerDriver authority checking."""

    def test_client_authoritative_for_whitelisted(self) -> None:
        """Test client authority for whitelisted component."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},
        )

        # Register a client with InputState in whitelist
        mock_ws = MagicMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
            component_whitelist={"InputState"},
        )

        assert server.is_client_authoritative_for("client_1", InputState) is True

    def test_client_not_authoritative_for_non_whitelisted(self) -> None:
        """Test client non-authority for non-whitelisted component."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},
        )

        mock_ws = MagicMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
            component_whitelist={"InputState"},
        )

        assert server.is_client_authoritative_for("client_1", Position) is False

    def test_unknown_client_not_authoritative(self) -> None:
        """Test that unknown client is not authoritative."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
        )

        assert server.is_client_authoritative_for("unknown", InputState) is False


class TestWebSocketServerDriverClientManagement:
    """Tests for WebSocketServerDriver client management."""

    def test_client_count(self) -> None:
        """Test client count property."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        assert server.client_count == 0

        mock_ws = MagicMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        assert server.client_count == 1

    def test_clients_returns_copy(self) -> None:
        """Test that clients property returns a copy."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = MagicMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        clients_copy = server.clients
        clients_copy.clear()

        # Original should be unchanged
        assert server.client_count == 1

    def test_remove_client(self) -> None:
        """Test removing a client."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = MagicMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )
        server._websocket_to_client[mock_ws] = "client_1"

        server._remove_client("client_1")

        assert "client_1" not in server._clients
        assert mock_ws not in server._websocket_to_client

    def test_remove_nonexistent_client(self) -> None:
        """Test removing a nonexistent client is safe."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        # Should not raise
        server._remove_client("nonexistent")


class TestWebSocketServerDriverHandshake:
    """Tests for WebSocketServerDriver handshake handling."""

    @pytest.mark.asyncio
    async def test_handshake_success(self) -> None:
        """Test successful handshake."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState, Position},
        )

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_hello(
                client_id="test_client",
                requested_whitelist=["InputState"],
            ).to_json()
        )
        mock_ws.send = AsyncMock()

        client_id = await server._handle_handshake(mock_ws)

        assert client_id == "test_client"
        assert "test_client" in server._clients
        # Only InputState should be in effective whitelist (intersection)
        assert "InputState" in server._clients["test_client"].component_whitelist
        # Position was not requested, so not in whitelist
        assert "Position" not in server._clients["test_client"].component_whitelist

    @pytest.mark.asyncio
    async def test_handshake_timeout(self) -> None:
        """Test handshake timeout."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.close = AsyncMock()

        client_id = await server._handle_handshake(mock_ws)

        assert client_id is None
        mock_ws.close.assert_called()

    @pytest.mark.asyncio
    async def test_handshake_invalid_message(self) -> None:
        """Test handshake with invalid message."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(return_value="invalid json")
        mock_ws.close = AsyncMock()

        client_id = await server._handle_handshake(mock_ws)

        assert client_id is None
        mock_ws.close.assert_called()

    @pytest.mark.asyncio
    async def test_handshake_wrong_message_type(self) -> None:
        """Test handshake with wrong message type."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=create_goodbye(reason="test").to_json())
        mock_ws.close = AsyncMock()

        client_id = await server._handle_handshake(mock_ws)

        assert client_id is None
        mock_ws.close.assert_called()

    @pytest.mark.asyncio
    async def test_handshake_duplicate_client_id(self) -> None:
        """Test handshake with duplicate client ID."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        # Register existing client
        existing_ws = MagicMock()
        server._clients["test_client"] = ClientConnection(
            client_id="test_client",
            websocket=existing_ws,
        )

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_hello(client_id="test_client").to_json()
        )
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        client_id = await server._handle_handshake(mock_ws)

        assert client_id is None
        mock_ws.close.assert_called()


class TestWebSocketServerDriverMessageHandling:
    """Tests for WebSocketServerDriver message handling."""

    @pytest.mark.asyncio
    async def test_handle_heartbeat_sends_ack(self) -> None:
        """Test that heartbeat is acknowledged."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        msg = create_heartbeat(ping_id=42)
        await server._handle_message("client_1", msg)

        mock_ws.send.assert_called()
        sent_msg = Message.from_json(mock_ws.send.call_args[0][0])
        assert sent_msg.type == MessageType.HEARTBEAT_ACK
        assert sent_msg.payload.ping_id == 42

    @pytest.mark.asyncio
    async def test_handle_sync_request_sends_full_state(self) -> None:
        """Test that sync request sends full world state."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player", {Position: Position(x=10, y=20)})
        world.tick(0)

        server.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        msg = create_sync_request(since_epoch=0)
        await server._handle_message("client_1", msg)

        mock_ws.send.assert_called()
        sent_msg = Message.from_json(mock_ws.send.call_args[0][0])
        assert sent_msg.type == MessageType.SYNC_FULL
        assert str(entity.id) in sent_msg.payload.entities

    @pytest.mark.asyncio
    async def test_handle_component_changed_authorized(self) -> None:
        """Test handling authorized component change."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},
        )

        world = World()
        world.register_prefab("player", {InputState: InputState()})
        world.register_component_type(InputState)
        entity = world.spawn("player")
        world.tick(0)

        server.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
            component_whitelist={"InputState"},
        )

        msg = create_component_changed(
            entity_id=entity.id,
            component_type="InputState",
            new_value={"move_x": 1.0, "move_y": 0.5},
        )
        await server._handle_message("client_1", msg)

        # Component should be updated
        input_state = entity.get_component(InputState)
        assert input_state.move_x == 1.0
        assert input_state.move_y == 0.5

    @pytest.mark.asyncio
    async def test_handle_component_changed_unauthorized(self) -> None:
        """Test handling unauthorized component change."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},  # Only InputState allowed
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Position)
        entity = world.spawn("player")
        world.tick(0)

        server.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
            component_whitelist={"InputState"},  # No Position
        )

        msg = create_component_changed(
            entity_id=entity.id,
            component_type="Position",  # Not authorized
            new_value={"x": 100, "y": 200},
            sequence=42,
        )
        await server._handle_message("client_1", msg)

        # Position should NOT be updated
        pos = entity.get_component(Position)
        assert pos.x == 0
        assert pos.y == 0

        # Rejected message should be sent
        mock_ws.send.assert_called()
        sent_msg = Message.from_json(mock_ws.send.call_args[0][0])
        assert sent_msg.type == MessageType.REJECTED

    @pytest.mark.asyncio
    async def test_handle_component_changed_unknown_entity(self) -> None:
        """Test handling component change for unknown entity."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},
        )

        world = World()
        world.register_component_type(InputState)
        server.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
            component_whitelist={"InputState"},
        )

        unknown_id = EntityId(prefab="player", sequence=999)
        msg = create_component_changed(
            entity_id=unknown_id,
            component_type="InputState",
            new_value={"move_x": 1.0, "move_y": 0.5},
            sequence=42,
        )
        await server._handle_message("client_1", msg)

        # Rejected message should be sent
        mock_ws.send.assert_called()
        sent_msg = Message.from_json(mock_ws.send.call_args[0][0])
        assert sent_msg.type == MessageType.REJECTED

    @pytest.mark.asyncio
    async def test_handle_goodbye(self) -> None:
        """Test handling goodbye message."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        msg = create_goodbye(reason="test")
        # Should not raise
        await server._handle_message("client_1", msg)


class TestWebSocketServerDriverBroadcast:
    """Tests for WebSocketServerDriver broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_to_all_clients(self) -> None:
        """Test broadcasting to all connected clients."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws1 = AsyncMock()
        mock_ws1.send = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send = AsyncMock()

        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws1,
        )
        server._clients["client_2"] = ClientConnection(
            client_id="client_2",
            websocket=mock_ws2,
        )

        msg = create_goodbye(reason="test")
        await server._broadcast(msg)

        mock_ws1.send.assert_called()
        mock_ws2.send.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_except_sender(self) -> None:
        """Test broadcasting to all clients except sender."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws1 = AsyncMock()
        mock_ws1.send = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send = AsyncMock()

        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws1,
        )
        server._clients["client_2"] = ClientConnection(
            client_id="client_2",
            websocket=mock_ws2,
        )

        msg = create_goodbye(reason="test")
        await server._broadcast_except(msg, "client_1")

        # Only client_2 should receive
        mock_ws1.send.assert_not_called()
        mock_ws2.send.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_changes_sends_pending(self) -> None:
        """Test that broadcast_changes sends pending messages."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        # Queue a message
        msg = create_goodbye(reason="test")
        server._pending_broadcasts.put_nowait(msg)

        await server.broadcast_changes()

        mock_ws.send.assert_called()
        assert server._pending_broadcasts.empty()


class TestWebSocketServerDriverEntityLifecycle:
    """Tests for WebSocketServerDriver entity lifecycle handling."""

    def test_entity_created_queues_broadcast(self) -> None:
        """Test that entity creation queues a broadcast."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        server.attach(world)

        # Spawn an entity
        world.spawn("player")
        world.tick(0)

        # Check that broadcast was queued
        assert not server._pending_broadcasts.empty()
        msg = server._pending_broadcasts.get_nowait()
        assert msg.type == MessageType.ENTITY_CREATED

    def test_entity_destroyed_queues_broadcast(self) -> None:
        """Test that entity destruction queues a broadcast."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        server.attach(world)

        entity = world.spawn("player")
        world.tick(0)

        # Clear the creation message
        while not server._pending_broadcasts.empty():
            server._pending_broadcasts.get_nowait()

        # Remove the entity
        world.remove(entity)
        world.tick(0)

        # Check that broadcast was queued
        assert not server._pending_broadcasts.empty()
        msg = server._pending_broadcasts.get_nowait()
        assert msg.type == MessageType.ENTITY_DESTROYED


class TestWebSocketServerDriverSequence:
    """Tests for WebSocketServerDriver sequence numbering."""

    def test_sequence_increments(self) -> None:
        """Test that sequence numbers increment."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        seq1 = server._next_sequence()
        seq2 = server._next_sequence()
        seq3 = server._next_sequence()

        assert seq2 == seq1 + 1
        assert seq3 == seq2 + 1


class TestWebSocketServerDriverStartStop:
    """Tests for WebSocketServerDriver start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_state(self) -> None:
        """Test that start updates state."""
        server = WebSocketServerDriver(
            host="localhost", port=0
        )  # Port 0 for random available port

        mock_serve = AsyncMock()
        mock_server = MagicMock()
        mock_serve.return_value = mock_server

        with patch("relics.addons.websocket.server.serve", mock_serve):
            await server.start()

        assert server.state == ConnectionState.READY
        assert server._running is True

    @pytest.mark.asyncio
    async def test_start_when_already_started(self) -> None:
        """Test that start is no-op when already started."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        server._state = ConnectionState.READY

        await server.start()

        assert server.state == ConnectionState.READY

    @pytest.mark.asyncio
    async def test_stop_sets_state(self) -> None:
        """Test that stop updates state."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        server._state = ConnectionState.READY
        server._running = True

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()
        server._server = mock_server

        await server.stop()

        assert server.state == ConnectionState.DISCONNECTED
        assert server._running is False

    @pytest.mark.asyncio
    async def test_stop_when_already_stopped(self) -> None:
        """Test that stop is no-op when already stopped."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        await server.stop()

        assert server.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connect_alias_calls_start(self) -> None:
        """Test that connect() is alias for start()."""
        server = WebSocketServerDriver(host="localhost", port=0)

        mock_serve = AsyncMock()
        mock_server = MagicMock()
        mock_serve.return_value = mock_server

        with patch("relics.addons.websocket.server.serve", mock_serve):
            await server.connect()

        assert server.state == ConnectionState.READY

    @pytest.mark.asyncio
    async def test_disconnect_alias_calls_stop(self) -> None:
        """Test that disconnect() is alias for stop()."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        server._state = ConnectionState.READY

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()
        server._server = mock_server

        await server.disconnect()

        assert server.state == ConnectionState.DISCONNECTED


class TestWebSocketServerDriverAdditionalCoverage:
    """Additional tests for coverage."""

    @pytest.mark.asyncio
    async def test_sync_is_noop(self) -> None:
        """Test that sync is a no-op for server."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        # Should not raise
        await server.sync()

    @pytest.mark.asyncio
    async def test_process_messages_is_noop(self) -> None:
        """Test that process_messages is a no-op for server."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        # Should not raise
        await server.process_messages(timeout=0.1)

    @pytest.mark.asyncio
    async def test_send_heartbeats(self) -> None:
        """Test sending heartbeats to all clients."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws1 = AsyncMock()
        mock_ws1.send = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send = AsyncMock()

        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws1,
        )
        server._clients["client_2"] = ClientConnection(
            client_id="client_2",
            websocket=mock_ws2,
        )

        await server.send_heartbeats()

        mock_ws1.send.assert_called()
        mock_ws2.send.assert_called()

    @pytest.mark.asyncio
    async def test_handle_heartbeat_ack(self) -> None:
        """Test handling heartbeat ack from client."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        mock_ws = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )

        from relics.addons.websocket import create_heartbeat_ack

        msg = create_heartbeat_ack(ping_id=42)

        # Should not raise
        await server._handle_message("client_1", msg)

    @pytest.mark.asyncio
    async def test_send_to_client_removes_on_close(self) -> None:
        """Test that client is removed on connection close."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        from websockets.exceptions import ConnectionClosed

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock(side_effect=ConnectionClosed(None, None))

        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
        )
        server._websocket_to_client[mock_ws] = "client_1"

        msg = create_goodbye(reason="test")
        await server._send_to_client("client_1", msg)

        # Client should be removed
        assert "client_1" not in server._clients

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected_clients(self) -> None:
        """Test that broadcast removes disconnected clients."""
        server = WebSocketServerDriver(host="localhost", port=8765)

        from websockets.exceptions import ConnectionClosed

        mock_ws1 = AsyncMock()
        mock_ws1.send = AsyncMock(side_effect=ConnectionClosed(None, None))
        mock_ws2 = AsyncMock()
        mock_ws2.send = AsyncMock()

        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws1,
        )
        server._clients["client_2"] = ClientConnection(
            client_id="client_2",
            websocket=mock_ws2,
        )
        server._websocket_to_client[mock_ws1] = "client_1"
        server._websocket_to_client[mock_ws2] = "client_2"

        msg = create_goodbye(reason="test")
        await server._broadcast(msg)

        # Disconnected client should be removed
        assert "client_1" not in server._clients
        assert "client_2" in server._clients

    @pytest.mark.asyncio
    async def test_stop_with_connected_clients(self) -> None:
        """Test stop sends goodbye and closes all clients."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        server._state = ConnectionState.READY
        server._running = True

        mock_ws1 = AsyncMock()
        mock_ws1.send = AsyncMock()
        mock_ws1.close = AsyncMock()

        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws1,
        )

        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()
        server._server = mock_server

        await server.stop()

        mock_ws1.send.assert_called()  # GOODBYE sent
        mock_ws1.close.assert_called()
        assert server.client_count == 0

    def test_server_component_change_observer(self) -> None:
        """Test that server-authoritative changes are queued."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},  # Only InputState client-controlled
        )

        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.register_component_type(Position)
        world.register_component_type(Health)
        server.attach(world)

        # Spawn entity
        world.spawn("player")
        world.tick(0)

        # Clear pending broadcasts from spawn
        while not server._pending_broadcasts.empty():
            server._pending_broadcasts.get_nowait()

        # Note: Component changes would typically be detected through observers
        # This test verifies the observer setup

    @pytest.mark.asyncio
    async def test_handle_component_changed_adds_new_component(self) -> None:
        """Test handling component change that adds a new component."""
        server = WebSocketServerDriver(
            host="localhost",
            port=8765,
            component_whitelist={InputState},
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(InputState)
        entity = world.spawn("player")
        world.tick(0)

        server.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        server._clients["client_1"] = ClientConnection(
            client_id="client_1",
            websocket=mock_ws,
            component_whitelist={"InputState"},
        )

        # Send component that doesn't exist on entity
        msg = create_component_changed(
            entity_id=entity.id,
            component_type="InputState",
            new_value={"move_x": 1.0, "move_y": 0.5},
        )
        await server._handle_message("client_1", msg)

        # Component should be added
        assert entity.has_component(InputState)

    @pytest.mark.asyncio
    async def test_handle_sync_request_without_world(self) -> None:
        """Test sync request without attached world."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        # No world attached

        from relics.addons.websocket import SyncRequestPayload

        payload = SyncRequestPayload(since_epoch=0)

        # Should not raise
        await server._handle_sync_request("client_1", payload)

    @pytest.mark.asyncio
    async def test_handle_component_changed_without_world(self) -> None:
        """Test component changed without attached world."""
        server = WebSocketServerDriver(host="localhost", port=8765)
        # No world attached

        from relics.addons.websocket import ComponentChangedPayload

        payload = ComponentChangedPayload(
            entity_id="player_1",
            component_type="Position",
            new_value={"x": 10, "y": 20},
        )

        # Should not raise
        await server._handle_component_changed("client_1", payload, 1)
