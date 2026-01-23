"""Camera helper functions for coordinate conversion and viewport management.

These functions operate on Viewport components to provide camera functionality.
"""

from demos.pygame.components import Viewport
from demos.pygame.config import WORLD_HEIGHT, WORLD_WIDTH


def world_to_screen(
    viewport: Viewport, world_x: float, world_y: float
) -> tuple[float, float]:
    """Convert world coordinates to screen coordinates.

    Args:
        viewport: The viewport component with camera position.
        world_x: X coordinate in world space.
        world_y: Y coordinate in world space.

    Returns:
        Tuple of (screen_x, screen_y) coordinates.
    """
    screen_x = world_x - viewport.x
    screen_y = world_y - viewport.y
    return screen_x, screen_y


def is_visible(
    viewport: Viewport, world_x: float, world_y: float, width: int, height: int
) -> bool:
    """Check if an entity at given world position is visible on screen.

    Args:
        viewport: The viewport component with camera position and dimensions.
        world_x: X coordinate in world space.
        world_y: Y coordinate in world space.
        width: Width of the entity.
        height: Height of the entity.

    Returns:
        True if the entity rectangle overlaps with the viewport.
    """
    screen_x, screen_y = world_to_screen(viewport, world_x, world_y)
    # Check if entity rectangle overlaps with screen
    return (
        screen_x + width > 0
        and screen_x < viewport.width
        and screen_y + height > 0
        and screen_y < viewport.height
    )


def clamp_to_world(viewport: Viewport) -> None:
    """Clamp viewport position to world bounds.

    Modifies the viewport in place to ensure it stays within world boundaries.

    Args:
        viewport: The viewport component to clamp.
    """
    # Camera position is top-left corner of viewport
    max_x = WORLD_WIDTH - viewport.width
    max_y = WORLD_HEIGHT - viewport.height
    viewport.x = max(0, min(viewport.x, max_x))
    viewport.y = max(0, min(viewport.y, max_y))
