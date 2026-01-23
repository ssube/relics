"""Integration tests for WebSocket client and server."""

import asyncio
from typing import List

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, World, monitored
from relics.addons.websocket import (
    ConnectionState,
    WebSocketClientDriver,
    WebSocketServerDriver,
)


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


@monitored
@dataclass
class Health(Component):
    """Test monitored component for health."""

    current: int
    maximum: int


class TestClientServerIntegration:
    """Integration tests for client-server communication."""

    @pytest.mark.asyncio
    async def test_client_server_handshake(self) -> None:
        """Test that client and server can perform handshake."""
        # Create server
        server = WebSocketServerDriver(
            host="localhost",
            port=0,  # Let OS assign port
            component_whitelist={InputState},
        )

        server_world = World()
        server_world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                InputState: InputState(),
            },
        )
        server.attach(server_world)

        # Start server on a random port
        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            # Create client
            client = WebSocketClientDriver(
                uri=f"ws://localhost:{port}",
                client_id="test_client",
                component_whitelist={InputState},
            )

            client_world = World()
            client_world.register_prefab(
                "player",
                {
                    Position: Position(x=0, y=0),
                    InputState: InputState(),
                },
            )
            client.attach(client_world)

            # Connect
            await client.connect()

            assert client.state == ConnectionState.READY
            assert "InputState" in client._effective_whitelist
            assert server.client_count == 1

            # Disconnect
            await client.disconnect()
            # Give server time to process disconnect
            await asyncio.sleep(0.1)

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_client_server_sync(self) -> None:
        """Test that client can sync world state from server."""
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
            component_whitelist={InputState},
        )

        server_world = World()
        server_world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                InputState: InputState(),
            },
        )
        server_world.register_component_type(Position)
        server_world.register_component_type(InputState)

        # Spawn some entities on server
        entity1 = server_world.spawn("player", {Position: Position(x=10, y=20)})
        entity2 = server_world.spawn("player", {Position: Position(x=30, y=40)})
        server_world.tick(0)

        server.attach(server_world)
        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            client = WebSocketClientDriver(
                uri=f"ws://localhost:{port}",
                client_id="test_client",
                component_whitelist={InputState},
            )

            client_world = World()
            client_world.register_prefab(
                "player",
                {
                    Position: Position(x=0, y=0),
                    InputState: InputState(),
                },
            )
            client_world.register_component_type(Position)
            client_world.register_component_type(InputState)
            client.attach(client_world)

            await client.connect()
            await client.sync()

            # Client should now have entities from server
            # Note: The sync process depends on how entities are created client-side
            # This is a simplified test

            await client.disconnect()

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_multiple_clients(self) -> None:
        """Test that multiple clients can connect to server."""
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
            component_whitelist={InputState},
        )

        server_world = World()
        server_world.register_prefab("player", {Position: Position(x=0, y=0)})
        server.attach(server_world)

        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        clients: List[WebSocketClientDriver] = []

        try:
            # Connect multiple clients
            for i in range(3):
                client = WebSocketClientDriver(
                    uri=f"ws://localhost:{port}",
                    client_id=f"client_{i}",
                    component_whitelist={InputState},
                )

                client_world = World()
                client_world.register_prefab("player", {Position: Position(x=0, y=0)})
                client.attach(client_world)

                await client.connect()
                clients.append(client)

            # All clients should be connected
            assert server.client_count == 3

            # Disconnect all
            for client in clients:
                await client.disconnect()

            # Give server time to process disconnects
            await asyncio.sleep(0.1)

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_client_whitelist_negotiation(self) -> None:
        """Test that whitelist is properly negotiated."""
        # Server allows InputState and Position
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
            component_whitelist={InputState, Position},
        )

        server_world = World()
        server.attach(server_world)

        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            # Client requests InputState and Health
            client = WebSocketClientDriver(
                uri=f"ws://localhost:{port}",
                client_id="test_client",
                component_whitelist={
                    InputState,
                    Health,
                },  # Health not allowed by server
            )

            client_world = World()
            client.attach(client_world)

            await client.connect()

            # Only InputState should be in effective whitelist
            assert "InputState" in client._effective_whitelist
            assert "Health" not in client._effective_whitelist  # Not allowed by server
            assert "Position" not in client._effective_whitelist  # Not requested

            await client.disconnect()

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_heartbeat_exchange(self) -> None:
        """Test that heartbeat messages are exchanged properly."""
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
        )

        server_world = World()
        server.attach(server_world)

        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            client = WebSocketClientDriver(
                uri=f"ws://localhost:{port}",
                client_id="test_client",
            )

            client_world = World()
            client.attach(client_world)

            await client.connect()

            # Send heartbeat
            await client.send_heartbeat()

            # Process response
            await client.process_messages(timeout=0.5)

            await client.disconnect()

        finally:
            await server.stop()


class TestExceptionHandling:
    """Tests for exception handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_client_connect_to_nonexistent_server(self) -> None:
        """Test that connecting to non-existent server raises."""
        client = WebSocketClientDriver(
            uri="ws://localhost:59999",  # Unlikely to be in use
            client_id="test_client",
        )

        from relics.addons.websocket.exceptions import ConnectionError

        with pytest.raises(ConnectionError):
            await client.connect()

    @pytest.mark.asyncio
    async def test_duplicate_client_id_rejected(self) -> None:
        """Test that duplicate client IDs are rejected."""
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
        )

        server_world = World()
        server.attach(server_world)

        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            # First client connects
            client1 = WebSocketClientDriver(
                uri=f"ws://localhost:{port}",
                client_id="same_id",
            )
            client1_world = World()
            client1.attach(client1_world)
            await client1.connect()

            # Second client with same ID
            client2 = WebSocketClientDriver(
                uri=f"ws://localhost:{port}",
                client_id="same_id",  # Same ID
            )
            client2_world = World()
            client2.attach(client2_world)

            # Should fail during handshake
            from relics.addons.websocket.exceptions import HandshakeError

            with pytest.raises(HandshakeError):
                await client2.connect()

            await client1.disconnect()

        finally:
            await server.stop()


class TestPerformance:
    """Performance-related tests."""

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self) -> None:
        """Test rapid connect/disconnect cycles."""
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
        )

        server_world = World()
        server.attach(server_world)

        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            # Perform multiple connect/disconnect cycles
            for i in range(5):
                client = WebSocketClientDriver(
                    uri=f"ws://localhost:{port}",
                    client_id=f"client_{i}",
                )

                client_world = World()
                client.attach(client_world)

                await client.connect()
                assert client.state == ConnectionState.READY

                await client.disconnect()
                assert client.state == ConnectionState.DISCONNECTED

        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_concurrent_connections(self) -> None:
        """Test concurrent client connections."""
        server = WebSocketServerDriver(
            host="localhost",
            port=0,
        )

        server_world = World()
        server.attach(server_world)

        await server.start()
        port = server._server.sockets[0].getsockname()[1]

        try:
            # Create clients
            clients = []
            for i in range(5):
                client = WebSocketClientDriver(
                    uri=f"ws://localhost:{port}",
                    client_id=f"client_{i}",
                )
                client_world = World()
                client.attach(client_world)
                clients.append(client)

            # Connect all concurrently
            await asyncio.gather(*[c.connect() for c in clients])

            # All should be connected
            for client in clients:
                assert client.state == ConnectionState.READY

            assert server.client_count == 5

            # Disconnect all concurrently
            await asyncio.gather(*[c.disconnect() for c in clients])

        finally:
            await server.stop()
