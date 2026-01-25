"""Shared configuration for the multiprocessing demo."""

# Screen/window dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# World dimensions (simulation space, can be larger than screen)
WORLD_WIDTH = 800
WORLD_HEIGHT = 600

# Rendering settings
TARGET_FPS = 60
ENTITY_SIZE = 10

# Simulation settings
TICK_RATE = 60  # ECS ticks per second
NUM_ENTITIES = 50

# Entity colors by type
ENTITY_COLORS = {
    "ball": (65, 105, 225),      # Royal Blue
    "square": (220, 20, 60),     # Crimson
    "triangle": (50, 205, 50),   # Lime Green
    "star": (255, 215, 0),       # Gold
    "default": (255, 255, 255),  # White
}

# Entity types for spawning
ENTITY_TYPES = list(ENTITY_COLORS.keys())
