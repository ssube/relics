"""Renderer process logic for the multiprocessing demo.

This module contains the RenderState class for maintaining minimal entity data,
and the main render loop using pygame.
"""

import math
from multiprocessing import Queue
from queue import Empty
from typing import Dict

import pygame
from pygame.locals import QUIT

from demos.multiprocessing.config import (
    ENTITY_COLORS,
    ENTITY_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TARGET_FPS,
)
from demos.multiprocessing.messages import MessageType, RenderMessage


class RenderState:
    """Minimal entity data needed for rendering - no ECS dependency.

    Maintains a dictionary of entity render data received via IPC messages.
    This keeps the renderer completely decoupled from the ECS implementation.

    Attributes:
        entities: Dictionary mapping entity_id to render data dict.
            Each dict contains: {"x", "y", "sprite_type", "color"}
    """

    def __init__(self) -> None:
        """Initialize empty render state."""
        self.entities: Dict[str, Dict] = {}

    def apply_message(self, msg: RenderMessage) -> bool:
        """Apply a render message to update the state.

        Args:
            msg: The RenderMessage to process.

        Returns:
            True if processing should continue, False if QUIT received.
        """
        if msg.msg_type == MessageType.CREATE:
            self.entities[msg.entity_id] = msg.data.copy()
        elif msg.msg_type == MessageType.UPDATE:
            if msg.entity_id in self.entities:
                self.entities[msg.entity_id].update(msg.data)
        elif msg.msg_type == MessageType.DESTROY:
            self.entities.pop(msg.entity_id, None)
        elif msg.msg_type == MessageType.QUIT:
            return False
        return True

    def entity_count(self) -> int:
        """Return the number of entities being tracked."""
        return len(self.entities)


def draw_entity(
    screen: pygame.Surface,
    x: float,
    y: float,
    sprite_type: str,
    color: tuple,
    size: int = ENTITY_SIZE,
) -> None:
    """Draw an entity based on its sprite type.

    Args:
        screen: Pygame surface to draw on.
        x: X coordinate (center).
        y: Y coordinate (center).
        sprite_type: Type of shape to draw ("ball", "square", "triangle", "star").
        color: RGB tuple for the entity color.
        size: Size of the entity in pixels.
    """
    ix, iy = int(x), int(y)

    if sprite_type == "ball":
        # Circle
        pygame.draw.circle(screen, color, (ix, iy), size)
    elif sprite_type == "square":
        # Square (centered)
        rect = pygame.Rect(ix - size, iy - size, size * 2, size * 2)
        pygame.draw.rect(screen, color, rect)
    elif sprite_type == "triangle":
        # Equilateral triangle pointing up
        height = size * 1.732  # sqrt(3)
        points = [
            (ix, iy - size),  # Top
            (ix - size, iy + size * 0.577),  # Bottom left
            (ix + size, iy + size * 0.577),  # Bottom right
        ]
        pygame.draw.polygon(screen, color, points)
    elif sprite_type == "star":
        # 5-pointed star
        points = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            r = size if i % 2 == 0 else size * 0.5
            px = ix + r * math.cos(angle)
            py = iy - r * math.sin(angle)
            points.append((px, py))
        pygame.draw.polygon(screen, color, points)
    else:
        # Default: circle
        pygame.draw.circle(screen, color, (ix, iy), size)


def draw_hud(
    screen: pygame.Surface,
    fps: float,
    entity_count: int,
) -> None:
    """Draw HUD with FPS and entity count.

    Args:
        screen: Pygame surface to draw on.
        fps: Current frames per second.
        entity_count: Number of entities being rendered.
    """
    font = pygame.font.Font(None, 24)

    # FPS display
    fps_text = font.render(f"FPS: {fps:.0f}", True, (255, 255, 255))
    screen.blit(fps_text, (10, 10))

    # Entity count
    count_text = font.render(f"Entities: {entity_count}", True, (255, 255, 255))
    screen.blit(count_text, (10, 35))

    # Controls hint
    controls_text = font.render(
        "Close window to quit", True, (200, 200, 200)
    )
    screen.blit(controls_text, (10, SCREEN_HEIGHT - 30))


def run_render_process(render_queue: Queue, control_queue: Queue) -> None:
    """Run the pygame renderer in a separate process.

    Initializes pygame, processes IPC messages to update render state,
    and renders entities each frame.

    Args:
        render_queue: Queue for receiving render messages from ECS.
        control_queue: Queue for sending control signals (quit).
    """
    print("[Renderer] Starting render process...")

    # Initialize pygame
    pygame.init()
    pygame.display.set_caption("Relics ECS - Multiprocessing Demo")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Initialize render state
    state = RenderState()

    print("[Renderer] Starting render loop...")

    running = True
    while running:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == QUIT:
                print("[Renderer] Window closed")
                running = False

        if not running:
            break

        # Process all available messages from the queue (non-blocking)
        messages_processed = 0
        while True:
            try:
                msg = render_queue.get_nowait()
                if not state.apply_message(msg):
                    # QUIT message received
                    print("[Renderer] Received QUIT message from ECS")
                    running = False
                    break
                messages_processed += 1
            except Empty:
                break

        print(f"[Renderer] Processed {messages_processed} messages this frame")

        if not running:
            break

        # Clear screen
        screen.fill((20, 20, 30))  # Dark blue-gray background

        # Render all entities
        for entity_id, data in state.entities.items():
            draw_entity(
                screen,
                data.get("x", 0),
                data.get("y", 0),
                data.get("sprite_type", "default"),
                data.get("color", ENTITY_COLORS["default"]),
            )

        # Draw HUD
        fps = clock.get_fps()
        draw_hud(screen, fps, state.entity_count())

        # Update display
        pygame.display.flip()

        # Cap frame rate
        clock.tick(TARGET_FPS)

    # Send quit signal to ECS process
    control_queue.put("quit")

    # Cleanup
    pygame.quit()
    print("[Renderer] Render process finished")
