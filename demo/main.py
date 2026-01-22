"""
Main entry point for the Relics ECS ecosystem demo.

Run with: python -m demo.main
"""

import sys

import pygame
from pygame.locals import K_ESCAPE, K_SPACE, KEYDOWN, QUIT

from relics import World

from demo.camera import Camera
from demo.config import SCREEN_HEIGHT, SCREEN_WIDTH, TARGET_FPS
from demo.prefabs import register_prefabs, spawn_initial_entities
from demo.systems import (
    BoundsSystem,
    CameraSystem,
    CollisionSystem,
    FoxAISystem,
    InputSystem,
    MovementSystem,
    RabbitAISystem,
    RenderSystem,
)


def draw_pause_overlay(screen: pygame.Surface) -> None:
    """Draw pause overlay with text."""
    # Semi-transparent overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))

    # Pause text
    font = pygame.font.Font(None, 74)
    text = font.render("PAUSED", True, (255, 255, 255))
    text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(text, text_rect)

    # Instructions
    small_font = pygame.font.Font(None, 36)
    instructions = small_font.render("Press SPACE to resume", True, (200, 200, 200))
    inst_rect = instructions.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
    screen.blit(instructions, inst_rect)


def draw_hud(screen: pygame.Surface, world: World, fps: float) -> None:
    """Draw HUD with entity counts, stats, and FPS."""
    font = pygame.font.Font(None, 24)

    # Count entities
    from demo.components import CameraMarker, Consumable, FoxAI, GameStats, RabbitAI

    rabbit_count = sum(1 for _ in world.query().with_all([RabbitAI]).execute_ids())
    fox_count = sum(1 for _ in world.query().with_all([FoxAI]).execute_ids())
    flower_count = sum(1 for _ in world.query().with_all([Consumable]).execute_ids())

    # Get game stats from camera entity
    rabbits_eaten = 0
    flowers_eaten = 0
    for cam in world.query().with_all([CameraMarker, GameStats]).execute_entities():
        stats = cam.get_component(GameStats)
        rabbits_eaten = stats.rabbits_eaten
        flowers_eaten = stats.flowers_eaten
        break

    # FPS display
    fps_text = font.render(f"FPS: {fps:.0f}", True, (255, 255, 255))
    screen.blit(fps_text, (10, 10))

    # Entity counts
    counts_text = font.render(
        f"Rabbits: {rabbit_count}  Foxes: {fox_count}  Flowers: {flower_count}",
        True,
        (255, 255, 255)
    )
    screen.blit(counts_text, (10, 35))

    # Game stats
    stats_text = font.render(
        f"Eaten - Rabbits: {rabbits_eaten}  Flowers: {flowers_eaten}",
        True,
        (255, 255, 255)
    )
    screen.blit(stats_text, (10, 60))

    # Controls hint
    controls_text = font.render(
        "WASD: Move camera  Shift: Sprint  SPACE: Pause  ESC: Quit",
        True,
        (200, 200, 200)
    )
    screen.blit(controls_text, (10, SCREEN_HEIGHT - 30))


def main() -> None:
    """Main entry point for the demo."""
    # Initialize pygame
    pygame.init()
    pygame.display.set_caption("Relics ECS - Ecosystem Demo")
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Create world and register prefabs
    world = World()
    register_prefabs(world)

    # Register ECS systems
    world.register_system(RabbitAISystem())
    world.register_system(FoxAISystem())
    world.register_system(CameraSystem())
    world.register_system(MovementSystem())
    world.register_system(BoundsSystem())
    world.register_system(CollisionSystem())

    # Spawn initial entities
    spawn_initial_entities(world)

    # Create non-ECS systems that need pygame access
    camera = Camera()
    input_system = InputSystem(world)
    render_system = RenderSystem(screen, camera, world)

    # Game state
    running = True
    paused = False

    print("Demo started!")
    print("Controls: WASD to scroll, SPACE to pause, ESC to quit")

    while running:
        # Get delta time
        delta = clock.tick(TARGET_FPS) / 1000.0
        fps = clock.get_fps()

        # Handle events
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    paused = not paused
                    if paused:
                        print("Paused")
                    else:
                        print("Resumed")

        # Update input (always, even when paused for responsiveness)
        input_system.update()

        # Update simulation (only when not paused)
        if not paused:
            world.tick(delta)

        # Render
        render_system.render()
        draw_hud(screen, world, fps)

        if paused:
            draw_pause_overlay(screen)

        pygame.display.flip()

    # Cleanup
    pygame.quit()
    print("Demo ended.")
    sys.exit(0)


if __name__ == "__main__":
    main()
