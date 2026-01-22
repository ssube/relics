"""Basic ECS example demonstrating entities, components, and systems.

This example shows how to:
- Define components as Pydantic dataclasses
- Create prefabs (entity templates)
- Spawn entities from prefabs
- Create and register systems
- Run the game loop with world.tick()
"""

from pydantic.dataclasses import dataclass

from relics import Component, System, World


# Define components
@dataclass
class Position(Component):
    """2D position component."""

    x: float
    y: float


@dataclass
class Velocity(Component):
    """2D velocity component."""

    vx: float
    vy: float


@dataclass
class Health(Component):
    """Health component with current and maximum values."""

    current: int
    maximum: int


@dataclass
class Dead(Component):
    """Marker component indicating entity is dead."""

    pass


# Define systems
class MovementSystem(System):
    """System that applies velocity to position."""

    def query(self):
        """Process entities with Position and Velocity, excluding Dead."""
        return self.q.with_all([Position, Velocity]).with_none([Dead])

    def process(self, entities, components, delta):
        """Update position based on velocity."""
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)
            pos.x += vel.vx * delta
            pos.y += vel.vy * delta


class HealthSystem(System):
    """System that marks entities as dead when health reaches zero."""

    def query(self):
        """Process entities with Health, excluding already Dead ones."""
        return self.q.with_all([Health]).with_none([Dead])

    def process(self, entities, components, delta):
        """Check health and add Dead component if needed."""
        for entity in entities:
            health = entity.get_component(Health)
            if health.current <= 0:
                entity.add_component(Dead())
                print(f"Entity {entity.id} has died!")


def main():
    """Run the basic ECS example."""
    # Create world
    world = World()

    # Register prefabs
    world.register_prefab(
        "player",
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            Health: Health(current=100, maximum=100),
        },
    )

    world.register_prefab(
        "enemy",
        {
            Position: Position(x=50, y=50),
            Velocity: Velocity(vx=-1, vy=0),
            Health: Health(current=50, maximum=50),
        },
    )

    # Register systems
    world.register_system(MovementSystem())
    world.register_system(HealthSystem())

    # Spawn entities
    player = world.spawn("player", {Velocity: Velocity(vx=2, vy=1)})
    enemy1 = world.spawn("enemy")
    enemy2 = world.spawn("enemy", {Position: Position(x=100, y=0)})

    print(f"Spawned player: {player.id}")
    print(f"Spawned enemies: {enemy1.id}, {enemy2.id}")

    # Simulate for 60 frames
    for frame in range(60):
        world.tick(0.016)  # ~60 FPS

        # Print positions every 10 frames
        if frame % 10 == 0:
            pos = player.get_component(Position)
            print(f"Frame {frame}: Player at ({pos.x:.1f}, {pos.y:.1f})")

    # Final state
    print("\nFinal positions:")
    for entity in world.query().with_all([Position]).execute_entities():
        pos = entity.get_component(Position)
        dead = " (dead)" if entity.has_component(Dead) else ""
        print(f"  {entity.id}: ({pos.x:.1f}, {pos.y:.1f}){dead}")


if __name__ == "__main__":
    main()
