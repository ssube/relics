"""Constants and configuration for the ecosystem demo."""

# Display settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WORLD_WIDTH = 2000
WORLD_HEIGHT = 2000
TARGET_FPS = 60

# Entity counts (ranges for randomization)
RABBIT_COUNT_MIN = 10
RABBIT_COUNT_MAX = 15
FOX_COUNT_MIN = 5
FOX_COUNT_MAX = 10
TREE_COUNT_MIN = 20
TREE_COUNT_MAX = 30
STONE_COUNT_MIN = 10
STONE_COUNT_MAX = 15
FLOWER_COUNT_MIN = 10
FLOWER_COUNT_MAX = 20

# Entity sizes
RABBIT_SIZE = 16
FOX_SIZE = 32
TREE_SIZE = 32
STONE_SIZE = 16
FLOWER_SIZE = 16
CAMERA_SIZE = 1  # Camera entity has minimal size

# AI behavior ranges
FOX_SIGHT_RANGE = 350.0  # Distance fox can detect/lose rabbits
RABBIT_FLEE_RANGE = 200.0  # Distance rabbit will flee from fox
RABBIT_SEEK_RANGE = 500.0  # Distance rabbit will seek flowers

# Movement speeds (pixels per second)
RABBIT_SPEED = 50.0
FOX_SPEED = 40.0
CAMERA_SPEED = 200.0  # Scroll speed

# Respawn settings
SAFE_SPAWN_DISTANCE = 250.0  # Minimum distance from foxes for rabbit respawn

# Colors (RGB tuples)
COLORS = {
    "GRASS": (34, 139, 34),
    "RABBIT": (255, 255, 255),
    "FOX": (255, 0, 0),
    "TREE": (139, 69, 19),
    "STONE": (128, 128, 128),
    "FLOWER": (128, 0, 128),
    "PAUSE_OVERLAY": (0, 0, 0, 128),
    "PAUSE_TEXT": (255, 255, 255),
}

# Entity type names (for sprite lookup)
ENTITY_RABBIT = "rabbit"
ENTITY_FOX = "fox"
ENTITY_TREE = "tree"
ENTITY_STONE = "stone"
ENTITY_FLOWER = "flower"
ENTITY_CAMERA = "camera"
