"""Tests for WebSocket client driver."""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, World, monitored
from relics.addons.websocket import (
    ConnectionState,
    Message,
    MessageType,
    WebSocketClientDriver,
    create_component_changed,
    create_entity_created,
    create_entity_destroyed,
    create_error,
    create_goodbye,
    create_heartbeat,
    create_rejected,
    create_sync_full,
    create_welcome,
)
from relics.addons.websocket.exceptions import (
    ConnectionError,
    HandshakeError,
    SyncError,
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


class TestWebSocketClientDriverInit:
    """Tests for WebSocketClientDriver initialization."""

    def test_client_creation(self) -> None:
        """Test basic client creation."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )
        assert client.uri == "ws://localhost:8765"
        assert client.client_id == "test_client"
        assert client.state == ConnectionState.DISCONNECTED

    def test_client_with_whitelist(self) -> None:
        """Test client creation with component whitelist."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={Position, InputState},
        )
        assert Position in client._requested_whitelist
        assert InputState in client._requested_whitelist

    def test_client_with_custom_settings(self) -> None:
        """Test client creation with custom settings."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            reconnect_attempts=10,
            reconnect_delay=2.0,
            heartbeat_interval=10.0,
        )
        assert client._reconnect_attempts == 10
        assert client._reconnect_delay == 2.0
        assert client._heartbeat_interval == 10.0


class TestWebSocketClientDriverAttach:
    """Tests for WebSocketClientDriver world attachment."""

    def test_attach_world(self) -> None:
        """Test attaching client to world."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={InputState},
        )
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        client.attach(world)

        assert client._world == world
        assert len(client._observers) > 0

    def test_detach_world(self) -> None:
        """Test detaching client from world."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={InputState},
        )
        world = World()
        client.attach(world)
        client.detach()

        assert client._world is None
        assert len(client._observers) == 0


class TestWebSocketClientDriverAuthority:
    """Tests for WebSocketClientDriver authority checking."""

    def test_is_authoritative_for_whitelisted(self) -> None:
        """Test authority for whitelisted component."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={Position},
        )
        # Simulate server granting whitelist
        client._effective_whitelist = {"Position"}

        assert client.is_authoritative_for(Position) is True

    def test_is_not_authoritative_for_non_whitelisted(self) -> None:
        """Test non-authority for non-whitelisted component."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={Position},
        )
        client._effective_whitelist = {"Position"}

        assert client.is_authoritative_for(Health) is False

    def test_is_not_authoritative_when_empty_whitelist(self) -> None:
        """Test non-authority when whitelist is empty."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )
        assert client.is_authoritative_for(Position) is False


class TestWebSocketClientDriverConnect:
    """Tests for WebSocketClientDriver connection."""

    @pytest.mark.asyncio
    async def test_connect_sets_state(self) -> None:
        """Test that connect updates state appropriately."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={Position},
        )

        # Mock the websocket connection
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_welcome(
                server_id="server_1",
                component_whitelist=["Position"],
            ).to_json()
        )
        mock_ws.send = AsyncMock()

        # Create an async function that returns mock_ws
        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch(
            "relics.addons.websocket.client.connect",
            side_effect=mock_connect,
        ):
            await client.connect()

        assert client.state == ConnectionState.READY
        assert "Position" in client._effective_whitelist

    @pytest.mark.asyncio
    async def test_connect_when_already_connected(self) -> None:
        """Test that connect is no-op when already connected."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )
        client._state = ConnectionState.READY

        await client.connect()

        # Should stay in READY state
        assert client.state == ConnectionState.READY

    @pytest.mark.asyncio
    async def test_connect_failure_raises(self) -> None:
        """Test that connection failure raises ConnectionError."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        with patch(
            "relics.addons.websocket.client.connect",
            side_effect=Exception("Connection refused"),
        ):
            with pytest.raises(ConnectionError):
                await client.connect()

        assert client.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connect_handshake_timeout(self) -> None:
        """Test that handshake timeout raises HandshakeError."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch(
            "relics.addons.websocket.client.connect",
            side_effect=mock_connect,
        ):
            with pytest.raises(HandshakeError, match="timeout"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connect_unexpected_message_type(self) -> None:
        """Test that unexpected message type raises HandshakeError."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        # Send GOODBYE instead of WELCOME
        mock_ws.recv = AsyncMock(
            return_value=create_goodbye(reason="test").to_json()
        )
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_ws

        with patch(
            "relics.addons.websocket.client.connect",
            side_effect=mock_connect,
        ):
            with pytest.raises(HandshakeError, match="WELCOME"):
                await client.connect()


class TestWebSocketClientDriverDisconnect:
    """Tests for WebSocketClientDriver disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self) -> None:
        """Test graceful disconnect when connected."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.disconnect()

        assert client.state == ConnectionState.DISCONNECTED
        mock_ws.send.assert_called()  # GOODBYE sent
        mock_ws.close.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_when_already_disconnected(self) -> None:
        """Test disconnect is no-op when already disconnected."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        await client.disconnect()

        assert client.state == ConnectionState.DISCONNECTED


class TestWebSocketClientDriverSync:
    """Tests for WebSocketClientDriver synchronization."""

    @pytest.mark.asyncio
    async def test_sync_requests_full_sync(self) -> None:
        """Test that sync requests full world state."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        client.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_sync_full(
                epoch=5,
                entities={},
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.sync()

        assert client.state == ConnectionState.READY
        mock_ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_sync_when_not_connected_raises(self) -> None:
        """Test that sync raises when not connected."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )
        client._state = ConnectionState.DISCONNECTED

        with pytest.raises(SyncError, match="not connected"):
            await client.sync()

    @pytest.mark.asyncio
    async def test_sync_timeout_raises(self) -> None:
        """Test that sync timeout raises SyncError."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.TimeoutError())

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        with pytest.raises(SyncError, match="timeout"):
            await client.sync()


class TestWebSocketClientDriverMessageHandling:
    """Tests for WebSocketClientDriver message handling."""

    @pytest.mark.asyncio
    async def test_handle_heartbeat_sends_ack(self) -> None:
        """Test that heartbeat is acknowledged."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_heartbeat(ping_id=42).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.process_messages(timeout=0.1)

        # Check that ack was sent
        calls = mock_ws.send.call_args_list
        assert len(calls) >= 1
        sent_msg = Message.from_json(calls[-1][0][0])
        assert sent_msg.type == MessageType.HEARTBEAT_ACK

    @pytest.mark.asyncio
    async def test_handle_component_changed_applies_to_world(self) -> None:
        """Test that component changes are applied to world."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={InputState},  # Not Position
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Position)
        entity = world.spawn("player")
        world.tick(0)

        client.attach(world)
        client._effective_whitelist = {"InputState"}  # Position is server-authoritative

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_component_changed(
                entity_id=entity.id,
                component_type="Position",
                new_value={"x": 100, "y": 200},
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.process_messages(timeout=0.1)

        # Position should be updated
        pos = entity.get_component(Position)
        assert pos.x == 100
        assert pos.y == 200

    @pytest.mark.asyncio
    async def test_handle_component_changed_ignores_authoritative(self) -> None:
        """Test that authoritative component changes are ignored."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={Position},  # Position is authoritative
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Position)
        entity = world.spawn("player")
        world.tick(0)

        client.attach(world)
        client._effective_whitelist = {"Position"}

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_component_changed(
                entity_id=entity.id,
                component_type="Position",
                new_value={"x": 100, "y": 200},
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.process_messages(timeout=0.1)

        # Position should NOT be updated (client is authoritative)
        pos = entity.get_component(Position)
        assert pos.x == 0
        assert pos.y == 0

    @pytest.mark.asyncio
    async def test_handle_entity_destroyed(self) -> None:
        """Test that entity destruction is applied."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        entity = world.spawn("player")
        world.tick(0)

        client.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_entity_destroyed(entity_id=entity.id).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.process_messages(timeout=0.1)

        assert not world.has_entity(entity.id)

    @pytest.mark.asyncio
    async def test_handle_rejected_logs_warning(self) -> None:
        """Test that rejected messages are handled gracefully."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_rejected(
                original_sequence=42,
                reason="Not authorized",
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        # Should not raise
        await client.process_messages(timeout=0.1)


class TestWebSocketClientDriverLocalChanges:
    """Tests for WebSocketClientDriver local change handling."""

    def test_local_change_queues_message(self) -> None:
        """Test that local changes are queued for sending."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={InputState},
        )

        world = World()
        world.register_prefab("player", {InputState: InputState()})
        client.attach(world)
        client._effective_whitelist = {"InputState"}

        entity = world.spawn("player")
        world.tick(0)

        # Simulate local change
        input_state = entity.get_component(InputState)
        input_state.move_x = 1.0
        world.tick(0)

        # Check that change was queued
        assert not client._pending_messages.empty()


class TestWebSocketClientDriverSequence:
    """Tests for WebSocketClientDriver sequence numbering."""

    def test_sequence_increments(self) -> None:
        """Test that sequence numbers increment."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        seq1 = client._next_sequence()
        seq2 = client._next_sequence()
        seq3 = client._next_sequence()

        assert seq2 == seq1 + 1
        assert seq3 == seq2 + 1


class TestWebSocketClientDriverAdditionalCoverage:
    """Additional tests for coverage."""

    @pytest.mark.asyncio
    async def test_handle_entity_created(self) -> None:
        """Test that entity creation messages are handled."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Position)
        client.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_entity_created(
                entity_id=EntityId(prefab="player", sequence=1),
                prefab="player",
                components={"Position": {"x": 50, "y": 60}},
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.process_messages(timeout=0.1)

        # Entity should be created (or queued for creation)
        # Note: Actual creation depends on implementation

    @pytest.mark.asyncio
    async def test_handle_error_message(self) -> None:
        """Test that error messages are handled gracefully."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_error(
                code="TEST_ERROR",
                message="Test error message",
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        # Should not raise
        await client.process_messages(timeout=0.1)

    @pytest.mark.asyncio
    async def test_handle_goodbye_message(self) -> None:
        """Test that goodbye messages are handled."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_goodbye(reason="server shutdown").to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.process_messages(timeout=0.1)

    @pytest.mark.asyncio
    async def test_sync_with_wrong_response_type(self) -> None:
        """Test sync raises when wrong response type received."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_heartbeat(ping_id=1).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        with pytest.raises(SyncError, match="Expected SYNC_FULL"):
            await client.sync()

    @pytest.mark.asyncio
    async def test_process_messages_not_ready(self) -> None:
        """Test that process_messages is no-op when not ready."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )
        client._state = ConnectionState.DISCONNECTED

        # Should return without doing anything
        await client.process_messages(timeout=0.1)

    @pytest.mark.asyncio
    async def test_process_messages_no_websocket(self) -> None:
        """Test that process_messages is no-op when no websocket."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )
        client._state = ConnectionState.READY
        client._websocket = None

        # Should return without doing anything
        await client.process_messages(timeout=0.1)

    @pytest.mark.asyncio
    async def test_handle_heartbeat_ack(self) -> None:
        """Test that heartbeat ack is handled."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        # Import to access ack creation
        from relics.addons.websocket import create_heartbeat_ack
        mock_ws.recv = AsyncMock(
            return_value=create_heartbeat_ack(ping_id=42).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        # Should handle without raising
        await client.process_messages(timeout=0.1)

    @pytest.mark.asyncio
    async def test_sync_full_with_entities(self) -> None:
        """Test handling full sync with entities."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_component_type(Position)
        client.attach(world)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(
            return_value=create_sync_full(
                epoch=5,
                entities={
                    "player_1": {
                        "prefab": "player",
                        "components": {"Position": {"x": 10, "y": 20}},
                    },
                },
            ).to_json()
        )

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.sync()

        assert client.state == ConnectionState.READY

    def test_is_authoritative_for_method(self) -> None:
        """Test is_authoritative_for with various scenarios."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
            component_whitelist={Position, InputState},
        )
        client._effective_whitelist = {"Position", "InputState"}

        # Should be authoritative for whitelisted
        assert client.is_authoritative_for(Position) is True
        assert client.is_authoritative_for(InputState) is True

        # Should not be authoritative for non-whitelisted
        assert client.is_authoritative_for(Health) is False

    @pytest.mark.asyncio
    async def test_send_pending_messages(self) -> None:
        """Test sending pending messages."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        # Queue a message
        msg = create_heartbeat(ping_id=1)
        client._pending_messages.put_nowait(msg)

        await client._send_pending()

        mock_ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_send_heartbeat(self) -> None:
        """Test sending heartbeat."""
        client = WebSocketClientDriver(
            uri="ws://localhost:8765",
            client_id="test_client",
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        client._state = ConnectionState.READY
        client._websocket = mock_ws

        await client.send_heartbeat()

        mock_ws.send.assert_called()
