"""ECS process logic for the multiprocessing demo.

This module contains observers that bridge ECS and renderer via IPC,
and the main ECS process loop.
"""

import random
import time
from multiprocessing import Queue
from queue import Empty
from typing import Any, ClassVar, Optional

from relics import Entity, World
from relics.observer import OnComponentChanged, OnEntityCreated, OnEntityDestroyed
from relics.types import Component

from demos.multiprocessing.components import Position, Sprite, Velocity
from demos.multiprocessing.config import (
    ENTITY_COLORS,
    ENTITY_TYPES,
    NUM_ENTITIES,
    TICK_RATE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)
from demos.multiprocessing.messages import MessageType, RenderMessage
from demos.multiprocessing.systems import BoundsSystem, MovementSystem


class EntityCreatedObserver(OnEntityCreated):
    """Observer that sends CREATE messages when entities are spawned.

    Watches for new entities with Position components and sends their
    initial render data to the renderer process.
    """

    prefab: ClassVar[Optional[str]] = None  # Watch all prefabs

    def __init__(self, render_queue: Queue) -> None:
        """Initialize with a multiprocessing Queue for IPC.

        Args:
            render_queue: Queue to send RenderMessages to the renderer.
        """
        super().__init__()
        self._queue = render_queue

    def on_entity_created(self, entity: Entity) -> None:
        """Send CREATE message when an entity is spawned.

        Only sends message if the entity has a Position component.

        Args:
            entity: The entity that was created.
        """
        if not entity.has_component(Position):
            return

        pos = entity.get_component(Position)

        # Get sprite data if available
        sprite = None
        if entity.has_component(Sprite):
            sprite = entity.get_component(Sprite)

        self._queue.put(
            RenderMessage(
                entity_id=str(entity.id),
                msg_type=MessageType.CREATE,
                data={
                    "x": pos.x,
                    "y": pos.y,
                    "sprite_type": sprite.entity_type if sprite else "default",
                    "color": (sprite.r, sprite.g, sprite.b)
                    if sprite
                    else (255, 255, 255),
                },
            )
        )


class EntityDestroyedObserver(OnEntityDestroyed):
    """Observer that sends DESTROY messages when entities are removed."""

    prefab: ClassVar[Optional[str]] = None  # Watch all prefabs

    def __init__(self, render_queue: Queue) -> None:
        """Initialize with a multiprocessing Queue for IPC.

        Args:
            render_queue: Queue to send RenderMessages to the renderer.
        """
        super().__init__()
        self._queue = render_queue

    def on_entity_destroyed(self, entity: Entity) -> None:
        """Send DESTROY message when an entity is removed.

        Args:
            entity: The entity that was destroyed.
        """
        self._queue.put(
            RenderMessage(
                entity_id=str(entity.id),
                msg_type=MessageType.DESTROY,
                data={},
            )
        )


class PositionChangedObserver(OnComponentChanged):
    """Observer that sends UPDATE messages when Position components change.

    Watches Position component changes and sends only the changed fields
    to minimize IPC overhead.
    """

    component_type = Position

    def __init__(self, render_queue: Queue) -> None:
        """Initialize with a multiprocessing Queue for IPC.

        Args:
            render_queue: Queue to send RenderMessages to the renderer.
        """
        super().__init__()
        self._queue = render_queue

    def on_component_changed(
        self,
        entity: Entity,
        component: Component,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Send UPDATE message when Position fields change.

        Only sends the changed field to minimize IPC overhead.

        Args:
            entity: The entity whose component changed.
            component: The Position component that changed.
            field_name: Name of the changed field ("x" or "y").
            old_value: Previous value of the field.
            new_value: New value of the field.
        """
        self._queue.put(
            RenderMessage(
                entity_id=str(entity.id),
                msg_type=MessageType.UPDATE,
                data={field_name: new_value},
            )
        )


def run_ecs_process(render_queue: Queue, control_queue: Queue) -> None:
    """Run the ECS world simulation in a separate process.

    Creates a World with entities and systems, registers observers to
    sync state changes to the renderer, and runs the tick loop until
    a quit signal is received.

    Args:
        render_queue: Queue for sending render messages to the renderer.
        control_queue: Queue for receiving control signals (quit).
    """
    print("[ECS] Starting ECS process...")

    # Seed for reproducible behavior during development
    random.seed(42)

    # Create the world
    world = World()

    # Register observers for IPC sync
    world.observe(EntityCreatedObserver(render_queue))
    world.observe(EntityDestroyedObserver(render_queue))
    world.observe(PositionChangedObserver(render_queue))

    # Register prefabs for different entity types
    for entity_type in ENTITY_TYPES:
        if entity_type == "default":
            continue
        color = ENTITY_COLORS[entity_type]
        world.register_prefab(
            entity_type,
            {
                Position: Position(x=0.0, y=0.0),
                Velocity: Velocity(vx=0.0, vy=0.0),
                Sprite: Sprite(
                    entity_type=entity_type,
                    r=color[0],
                    g=color[1],
                    b=color[2],
                ),
            },
        )

    # Register systems
    world.register_system(MovementSystem())
    world.register_system(BoundsSystem(width=WORLD_WIDTH, height=WORLD_HEIGHT))

    # Spawn initial entities with random positions and velocities
    print(f"[ECS] Spawning {NUM_ENTITIES} entities...")
    available_types = [t for t in ENTITY_TYPES if t != "default"]
    for i in range(NUM_ENTITIES):
        entity_type = random.choice(available_types)
        world.spawn(
            entity_type,
            {
                Position: Position(
                    x=random.uniform(50.0, WORLD_WIDTH - 50.0),
                    y=random.uniform(50.0, WORLD_HEIGHT - 50.0),
                ),
                Velocity: Velocity(
                    vx=random.uniform(-200.0, 200.0),
                    vy=random.uniform(-200.0, 200.0),
                ),
            },
        )

    # Process the initial entity creation events
    world.tick(0)

    print("[ECS] Starting tick loop...")

    # Tick loop
    tick_interval = 1.0 / TICK_RATE
    last_time = time.perf_counter()
    tick_count = 0
    last_stats_time = last_time

    running = True
    while running:
        current_time = time.perf_counter()
        delta = current_time - last_time
        last_time = current_time

        # Check for quit signal (non-blocking)
        try:
            signal = control_queue.get_nowait()
            if signal == "quit":
                print("[ECS] Received quit signal")
                running = False
                break
        except Empty:
            pass

        # Run the ECS tick
        world.tick(delta)
        tick_count += 1

        # Print stats every second
        if current_time - last_stats_time >= 1.0:
            tps = tick_count / (current_time - last_stats_time)
            print(f"[ECS] Tick rate: {tps:.1f} ticks/sec")
            tick_count = 0
            last_stats_time = current_time

        # Sleep to maintain tick rate
        elapsed = time.perf_counter() - current_time
        sleep_time = tick_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Send quit message to renderer
    render_queue.put(
        RenderMessage(
            entity_id="",
            msg_type=MessageType.QUIT,
            data={},
        )
    )

    print("[ECS] ECS process finished")
