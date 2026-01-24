# WebSocket Sync Addon

Real-time multiplayer synchronization over WebSocket for the Relics ECS framework.

## Installation

```bash
pip install relics[websocket]
```

## Quick Start

### Server

```python
import asyncio
from relics import World
from relics.addons.websocket import WebSocketServerDriver

async def main():
    world = World()

    # Create and attach server
    server = WebSocketServerDriver(
        host="localhost",
        port=8765,
        component_whitelist={InputState},  # Only sync these from clients
    )
    server.attach(world)
    await server.start()

    # Game loop
    while running:
        await server.process_messages()
        world.tick(0.016)
        await server.broadcast_changes()

    await server.stop()

asyncio.run(main())
```

### Client

```python
import asyncio
from relics import World
from relics.addons.websocket import WebSocketClientDriver

async def main():
    world = World()

    # Create and attach client
    client = WebSocketClientDriver(
        uri="ws://localhost:8765",
        client_id="player_1",
        component_whitelist={InputState},  # Components this client can modify
    )
    client.attach(world)

    # Connect and sync
    await client.connect()
    await client.sync()

    # Game loop
    while running:
        await client.process_messages(timeout=0.016)
        world.tick(0.016)

    await client.disconnect()

asyncio.run(main())
```

## Features

- **Full world state synchronization** on connect
- **Incremental updates** for component changes
- **Entity lifecycle events** (create/destroy)
- **Component whitelist** for security and bandwidth control
- **Heartbeat mechanism** for connection health monitoring
- **Graceful disconnect handling**
- **Automatic reconnection** support

## Protocol

The WebSocket addon uses a custom binary protocol optimized for ECS data:

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `HELLO` | Client → Server | Initial handshake with client ID |
| `WELCOME` | Server → Client | Handshake accepted |
| `REJECTED` | Server → Client | Handshake rejected with reason |
| `SYNC_REQUEST` | Client → Server | Request full world state |
| `SYNC_FULL` | Server → Client | Complete world state snapshot |
| `ENTITY_CREATED` | Bidirectional | New entity spawned |
| `ENTITY_DESTROYED` | Bidirectional | Entity removed |
| `COMPONENT_CHANGED` | Bidirectional | Component value updated |
| `HEARTBEAT` | Bidirectional | Connection health check |
| `GOODBYE` | Bidirectional | Graceful disconnect |
| `ERROR` | Server → Client | Error notification |

### Handshake Flow

```
Client                    Server
  |                         |
  |-------- HELLO --------->|
  |                         |
  |<------- WELCOME --------|
  |                         |
  |---- SYNC_REQUEST ------>|
  |                         |
  |<----- SYNC_FULL --------|
  |                         |
```

## Component Whitelist

The component whitelist controls which components can be synchronized:

```python
# Server: accept input from clients
server = WebSocketServerDriver(
    host="localhost",
    port=8765,
    component_whitelist={InputState, ChatMessage},
)

# Client: only send input and chat
client = WebSocketClientDriver(
    uri="ws://localhost:8765",
    client_id="player_1",
    component_whitelist={InputState, ChatMessage},
)
```

Components not in the whitelist:
- **Server → Client**: All components are sent (whitelist doesn't apply)
- **Client → Server**: Changes are rejected (security)

## Observers

The addon provides observers for sync events:

```python
from relics.addons.websocket import (
    SyncComponentObserver,
    SyncEntityObserver,
    create_sync_observer,
)

# Watch for synced component changes
class MySyncObserver(SyncComponentObserver):
    component_type = Position

    def on_sync_change(self, entity, component, field_name, old_value, new_value):
        print(f"Synced: {entity.id}.{field_name} = {new_value}")

# Or use the factory
observer = create_sync_observer(Position, on_change=my_callback)
```

## Error Handling

```python
from relics.addons.websocket import (
    WebSocketError,
    ConnectionError,
    HandshakeError,
    AuthorizationError,
    ProtocolError,
    SyncError,
    ReconnectionError,
)

try:
    await client.connect()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
except HandshakeError as e:
    print(f"Handshake failed: {e}")
```

## API Reference

### WebSocketServerDriver

```python
server = WebSocketServerDriver(
    host="localhost",           # Bind address
    port=8765,                  # Bind port
    component_whitelist=None,   # Set of component types to accept from clients
)

server.attach(world)            # Attach to world
await server.start()            # Start listening
await server.process_messages() # Process incoming messages
await server.broadcast_changes()# Send changes to all clients
await server.stop()             # Stop server

# Properties
server.client_count             # Number of connected clients
server.is_running               # Server running status
```

### WebSocketClientDriver

```python
client = WebSocketClientDriver(
    uri="ws://localhost:8765",  # Server URI
    client_id="player_1",       # Unique client identifier
    component_whitelist=None,   # Components this client can modify
)

client.attach(world)            # Attach to world
await client.connect()          # Connect to server
await client.sync()             # Request full world state
await client.process_messages() # Process incoming messages
await client.disconnect()       # Disconnect from server

# Properties
client.is_connected             # Connection status
client.connection_state         # Detailed connection state
```

### Connection States

```python
from relics.addons.websocket import ConnectionState

ConnectionState.DISCONNECTED    # Not connected
ConnectionState.CONNECTING      # Connection in progress
ConnectionState.HANDSHAKING     # Performing handshake
ConnectionState.SYNCING         # Synchronizing world state
ConnectionState.CONNECTED       # Fully connected and synced
ConnectionState.DISCONNECTING   # Disconnect in progress
```
