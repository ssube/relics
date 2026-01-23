"""ECS components for the ecosystem demo."""

from enum import Enum, auto
from typing import Optional

from pydantic.dataclasses import dataclass

from relics import Component, EntityId


@dataclass
class Position(Component):
    """World position in pixels."""

    x: float
    y: float


@dataclass
class Velocity(Component):
    """Movement velocity in pixels per second."""

    vx: float
    vy: float


@dataclass
class BoundingBox(Component):
    """Size for collision detection and rendering."""

    width: int
    height: int


@dataclass
class Sprite(Component):
    """Entity type for color/sprite lookup."""

    entity_type: str
    layer: int = 0  # Rendering layer (lower renders first)


class RabbitState(Enum):
    """Rabbit AI states."""

    IDLE = auto()
    FLEEING = auto()
    SEEKING = auto()


@dataclass
class RabbitAI(Component):
    """Rabbit behavior state."""

    state: RabbitState = RabbitState.IDLE


class FoxState(Enum):
    """Fox AI states."""

    IDLE = auto()
    CHASING = auto()


@dataclass
class FoxAI(Component):
    """Fox behavior state."""

    state: FoxState = FoxState.IDLE
    target_id: Optional[EntityId] = None
    sight_range: float = 200.0


@dataclass
class Obstacle(Component):
    """Marker for solid, immovable entities that block movement."""

    pass


@dataclass
class Consumable(Component):
    """Entity can be consumed (eaten)."""

    pass


@dataclass
class Color(Component):
    """Per-entity color override (RGB tuple)."""

    r: int
    g: int
    b: int


@dataclass
class Viewport(Component):
    """Camera viewport with position and dimensions.

    The viewport represents a camera in world coordinates, tracking
    the top-left corner position and the dimensions of the visible area.
    """

    width: int
    height: int
    x: float = 0.0
    y: float = 0.0


@dataclass
class CameraInput(Component):
    """Buffered input for camera movement with edge detection.

    The _prev_* fields track the previous frame's state to enable
    edge detection (pressed/released transitions).
    """

    # Movement inputs (continuous)
    move_left: bool = False
    move_right: bool = False
    move_up: bool = False
    move_down: bool = False
    sprint: bool = False  # Shift key for 2x speed

    # Button inputs (level)
    pause: bool = False  # Current pause key state
    quit: bool = False  # Current quit key state

    # Edge detection (set by input system)
    pause_pressed: bool = False  # True only on frame pause transitions to pressed
    quit_pressed: bool = False  # True only on frame quit transitions to pressed

    # Previous frame state (internal, used for edge detection)
    _prev_pause: bool = False
    _prev_quit: bool = False


@dataclass
class GameStats(Component):
    """Tracks game statistics."""

    rabbits_eaten: int = 0
    flowers_eaten: int = 0
