#!/usr/bin/env python3
"""Hello ECS - Minimal bouncing particles demo.

The simplest possible Relics demo: particles bouncing in a box.
Demonstrates core ECS concepts: World, Components, Prefabs, Systems, and the tick loop.
"""

import os
import random
import sys

# Add src to path for running from demos directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pydantic.dataclasses

from relics import Component, Entity, System, World


# =============================================================================
# Components - Pure data containers
# =============================================================================


@pydantic.dataclasses.dataclass
class Position(Component):
    """2D position in the simulation box."""

    x: float
    y: float


@pydantic.dataclasses.dataclass
class Velocity(Component):
    """2D velocity for movement."""

    dx: float
    dy: float


# =============================================================================
# Systems - Logic that processes entities
# =============================================================================


class MovementSystem(System):
    """Updates positions based on velocity and bounces off walls."""

    def __init__(self, box_size: float = 100.0) -> None:
        """Initialize with simulation box size.

        Args:
            box_size: Width and height of the simulation box (0 to box_size).
        """
        super().__init__()
        self.box_size = box_size

    def query(self):
        """Query entities with Position and Velocity."""
        return self.world.query().with_all([Position, Velocity])

    def process(self, entities: list[Entity], components: list, delta: float) -> None:
        """Move all particles and bounce off walls.

        Args:
            entities: List of entities matching the query.
            components: Component lists (unused, we get components directly).
            delta: Time elapsed since last tick in seconds.
        """
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            # Update position
            pos.x += vel.dx * delta
            pos.y += vel.dy * delta

            # Bounce off walls (0 to box_size box)
            if pos.x < 0:
                pos.x = -pos.x
                vel.dx = -vel.dx
            elif pos.x > self.box_size:
                pos.x = 2 * self.box_size - pos.x
                vel.dx = -vel.dx

            if pos.y < 0:
                pos.y = -pos.y
                vel.dy = -vel.dy
            elif pos.y > self.box_size:
                pos.y = 2 * self.box_size - pos.y
                vel.dy = -vel.dy


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run the bouncing particles simulation."""
    # Seed for reproducible output
    random.seed(42)

    # Create the world
    world = World()

    # Register a prefab (template) for particles
    world.register_prefab(
        "particle",
        {
            Position: Position(x=0.0, y=0.0),
            Velocity: Velocity(dx=0.0, dy=0.0),
        },
    )

    # Register the movement system
    world.register_system(MovementSystem(box_size=100.0))

    # Spawn 5 particles with random positions and velocities
    print("Spawning 5 particles...")
    for i in range(5):
        particle = world.spawn(
            "particle",
            {
                Position: Position(
                    x=random.uniform(10.0, 90.0),
                    y=random.uniform(10.0, 90.0),
                ),
                Velocity: Velocity(
                    dx=random.uniform(-50.0, 50.0),
                    dy=random.uniform(-50.0, 50.0),
                ),
            },
        )
        pos = particle.get_component(Position)
        vel = particle.get_component(Velocity)
        print(f"  Particle {i}: pos=({pos.x:.1f}, {pos.y:.1f}), vel=({vel.dx:.1f}, {vel.dy:.1f})")

    # Run simulation for 10 ticks
    print("\nRunning simulation (10 ticks, dt=0.1s)...")
    dt = 0.1  # 100ms per tick
    for tick in range(10):
        world.tick(dt)

        # Print positions every 5 ticks
        if (tick + 1) % 5 == 0:
            print(f"\nTick {tick + 1}:")
            for i, entity in enumerate(
                world.query().with_all([Position]).execute_entities()
            ):
                pos = entity.get_component(Position)
                print(f"  Particle {i}: ({pos.x:.1f}, {pos.y:.1f})")

    print("\nSimulation complete!")
    print(f"Final epoch: {world.epoch}")


if __name__ == "__main__":
    main()
