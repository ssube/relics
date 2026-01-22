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
class FlowerMarker(Component):
    """Marker component for flowers."""

    pass


@dataclass
class TreeMarker(Component):
    """Marker component for trees."""

    pass


@dataclass
class StoneMarker(Component):
    """Marker component for stones."""

    pass


@dataclass
class Consumable(Component):
    """Entity can be consumed (eaten)."""

    pass


@dataclass
class CameraMarker(Component):
    """Marker component for the camera entity."""

    pass


@dataclass
class CameraInput(Component):
    """Buffered input for camera movement."""

    move_left: bool = False
    move_right: bool = False
    move_up: bool = False
    move_down: bool = False
