"""Camera helper for coordinate conversion and viewport management."""

from demos.pygame.config import WORLD_HEIGHT, WORLD_WIDTH

class Camera:
    """
    Scrolling viewport camera for rendering.

    The camera tracks a position in world coordinates and provides
    conversion between world and screen coordinates.
    """

    def __init__(self, width: int, height: int, x: float = 0.0, y: float = 0.0):
        """Initialize camera with viewport dimensions at given world position."""
        self.width = width
        self.height = height
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
            and screen_x < self.width
            and screen_y + height > 0
            and screen_y < self.height
        )

    def clamp_to_world(self) -> None:
        """Clamp camera position to world bounds."""
        # Camera position is top-left corner of viewport
        max_x = WORLD_WIDTH - self.width
        max_y = WORLD_HEIGHT - self.height
        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))
