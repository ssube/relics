"""ECS component definitions for the multiprocessing demo."""

import os
import sys

# Add src to path for running from demos directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pydantic.dataclasses

from relics import Component, monitored


@monitored
@pydantic.dataclasses.dataclass
class Position(Component):
    """2D position in the simulation world.

    This component is @monitored to enable change tracking for IPC sync.
    """

    x: float
    y: float


@pydantic.dataclasses.dataclass
class Sprite(Component):
    """Visual representation data for an entity.

    Attributes:
        entity_type: String identifier for the entity type (e.g., "ball", "square").
        r: Red color component (0-255).
        g: Green color component (0-255).
        b: Blue color component (0-255).
    """

    entity_type: str
    r: int
    g: int
    b: int


@pydantic.dataclasses.dataclass
class Velocity(Component):
    """2D velocity for entity movement.

    Attributes:
        vx: Velocity in the x direction (pixels per second).
        vy: Velocity in the y direction (pixels per second).
    """

    vx: float
    vy: float
