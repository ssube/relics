"""Camera helper for coordinate conversion and viewport management."""

from demo.config import SCREEN_HEIGHT, SCREEN_WIDTH, WORLD_HEIGHT, WORLD_WIDTH


class Camera:
    """
    Scrolling viewport camera for rendering.

    The camera tracks a position in world coordinates and provides
    conversion between world and screen coordinates.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0):
        """Initialize camera at given world position."""
        self.x = x
        self.y = y

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        screen_x = world_x - self.x
        screen_y = world_y - self.y
        return screen_x, screen_y

    def is_visible(
        self, world_x: float, world_y: float, width: int, height: int
    ) -> bool:
        """Check if an entity at given world position is visible on screen."""
        screen_x, screen_y = self.world_to_screen(world_x, world_y)
        # Check if entity rectangle overlaps with screen
        return (
            screen_x + width > 0
            and screen_x < SCREEN_WIDTH
            and screen_y + height > 0
            and screen_y < SCREEN_HEIGHT
        )

    def clamp_to_world(self) -> None:
        """Clamp camera position to world bounds."""
        # Camera position is top-left corner of viewport
        max_x = WORLD_WIDTH - SCREEN_WIDTH
        max_y = WORLD_HEIGHT - SCREEN_HEIGHT
        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))
