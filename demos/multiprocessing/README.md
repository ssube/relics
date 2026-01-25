# Multiprocessing Demo

This demo shows how to use Relics ECS in a multiprocessing Python application where:

- **Process 1 (ECS)**: Runs the Relics World with entities and systems
- **Process 2 (Renderer)**: Uses pygame to render entities with minimal data

The key feature is a custom `ComponentObserver` that sends component changes via IPC to the rendering process.

## Architecture

```
┌─────────────────────────────┐     Queue      ┌─────────────────────────────┐
│      ECS Process            │    ──────>     │     Renderer Process        │
│                             │                │                             │
│  ┌─────────────────────┐    │   Messages:    │  ┌─────────────────────┐    │
│  │     World           │    │   - CREATE     │  │   RenderState       │    │
│  │  ┌───────────────┐  │    │   - UPDATE     │  │   {id: {x,y,type}}  │    │
│  │  │ Entities      │  │    │   - DESTROY    │  └─────────────────────┘    │
│  │  │ - Position    │  │    │                │                             │
│  │  │ - Sprite      │  │    │                │  ┌─────────────────────┐    │
│  │  │ - Velocity    │  │    │                │  │     Pygame          │    │
│  │  └───────────────┘  │    │                │  │  - Draw entities    │    │
│  │                     │    │                │  │  - Handle input     │    │
│  │  ┌───────────────┐  │    │                │  └─────────────────────┘    │
│  │  │ Systems       │  │    │                │                             │
│  │  │ - Movement    │  │    │                │                             │
│  │  │ - Bounds      │  │    │                │                             │
│  │  └───────────────┘  │    │                │                             │
│  │                     │    │                │                             │
│  │  ┌───────────────┐  │    │                │                             │
│  │  │ Observer      │──┼────┼─────────────>  │                             │
│  │  │ (RenderSync)  │  │    │                │                             │
│  │  └───────────────┘  │    │                │                             │
│  └─────────────────────┘    │                │                             │
└─────────────────────────────┘                └─────────────────────────────┘
```

## Running the Demo

From the project root:

```bash
python demos/multiprocessing/main.py
```

Or as a module:

```bash
python -m demos.multiprocessing.main
```

## What You'll See

- A pygame window opens showing colored shapes bouncing around
- Different shapes represent different entity types (balls, squares, triangles, stars)
- The console shows tick rates from both processes
- Close the window to exit both processes cleanly

## Key Concepts

### 1. `@monitored` for Change Tracking

The `Position` component uses the `@monitored` decorator to enable field-level change tracking:

```python
@monitored
@pydantic.dataclasses.dataclass
class Position(Component):
    x: float
    y: float
```

When any field changes (e.g., `pos.x = 100`), the World automatically notifies registered observers.

### 2. `ComponentObserver` for IPC Sync

The `RenderSyncObserver` extends `ComponentObserver` to watch Position components:

```python
class RenderSyncObserver(ComponentObserver):
    component_type = Position  # Watch this component type

    def on_component_added(self, entity, component):
        # Send CREATE message with full entity data
        self._queue.put(RenderMessage(...))

    def on_component_changed(self, entity, component, field_name, old_value, new_value):
        # Send UPDATE message with just the changed field
        self._queue.put(RenderMessage(...))

    def on_component_removed(self, entity, component):
        # Send DESTROY message
        self._queue.put(RenderMessage(...))
```

This pattern sends minimal data over IPC - only changed fields are transmitted during updates.

### 3. Minimal Render State Pattern

The renderer maintains its own minimal state, completely decoupled from ECS:

```python
class RenderState:
    def __init__(self):
        self.entities: Dict[str, Dict] = {}  # {id: {x, y, type, color}}

    def apply_message(self, msg: RenderMessage):
        if msg.msg_type == MessageType.CREATE:
            self.entities[msg.entity_id] = msg.data.copy()
        elif msg.msg_type == MessageType.UPDATE:
            self.entities[msg.entity_id].update(msg.data)
        elif msg.msg_type == MessageType.DESTROY:
            self.entities.pop(msg.entity_id, None)
```

This keeps the renderer lightweight and independent of the ECS implementation.

### 4. Process Communication via Queue

Uses Python's `multiprocessing.Queue` for thread-safe IPC:

- **render_queue**: ECS → Renderer (entity state changes)
- **control_queue**: Renderer → ECS (quit signals)

Messages are simple dataclasses that pickle efficiently for IPC.

## File Structure

```
demos/multiprocessing/
├── __init__.py          # Package marker
├── main.py              # Entry point, spawns processes
├── ecs_process.py       # ECS world logic + RenderSyncObserver
├── render_process.py    # Pygame rendering logic + RenderState
├── components.py        # ECS component definitions
├── systems.py           # ECS systems (movement, bounds)
├── messages.py          # IPC message protocol
├── config.py            # Shared configuration
└── README.md            # This file
```

## Extending the Demo

Ideas for extending this demo:

1. **Add more components**: Track rotation, scale, or health
2. **Bidirectional communication**: Send input from renderer to ECS
3. **Multiple renderer processes**: Different views of the same world
4. **Network instead of IPC**: Use sockets for distributed rendering
5. **Interpolation**: Smooth rendering between ECS updates
