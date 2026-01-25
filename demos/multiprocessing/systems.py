"""ECS systems for the multiprocessing demo."""

from typing import List

from relics import Entity, System

from demos.multiprocessing.components import Position, Velocity
from demos.multiprocessing.config import WORLD_HEIGHT, WORLD_WIDTH


class MovementSystem(System):
    """Updates entity positions based on their velocities."""

    def query(self):
        """Query entities with Position and Velocity components."""
        return self.world.query().with_all([Position, Velocity])

    def process(self, entities: List[Entity], components: list, delta: float) -> None:
        """Update positions based on velocity.

        Args:
            entities: List of entities matching the query.
            components: Component lists (unused, we get components directly).
            delta: Time elapsed since last tick in seconds.
        """
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            # Update position based on velocity
            pos.x += vel.vx * delta
            pos.y += vel.vy * delta


class BoundsSystem(System):
    """Bounces entities off world boundaries."""

    def __init__(self, width: float = WORLD_WIDTH, height: float = WORLD_HEIGHT) -> None:
        """Initialize with world bounds.

        Args:
            width: Width of the world in pixels.
            height: Height of the world in pixels.
        """
        super().__init__()
        self.width = width
        self.height = height

    def query(self):
        """Query entities with Position and Velocity components."""
        return self.world.query().with_all([Position, Velocity])

    def process(self, entities: List[Entity], components: list, delta: float) -> None:
        """Bounce entities off world edges.

        Args:
            entities: List of entities matching the query.
            components: Component lists (unused).
            delta: Time elapsed since last tick in seconds.
        """
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            # Bounce off left/right walls
            if pos.x < 0:
                pos.x = -pos.x
                vel.vx = -vel.vx
            elif pos.x > self.width:
                pos.x = 2 * self.width - pos.x
                vel.vx = -vel.vx

            # Bounce off top/bottom walls
            if pos.y < 0:
                pos.y = -pos.y
                vel.vy = -vel.vy
            elif pos.y > self.height:
                pos.y = 2 * self.height - pos.y
                vel.vy = -vel.vy
