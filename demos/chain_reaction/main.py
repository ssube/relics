#!/usr/bin/env python3
"""Chain Reaction - Explosive barrels chain reaction demo.

Demonstrates reactive observers: when one barrel explodes, it damages nearby
barrels, potentially triggering a chain reaction. Shows @monitored components,
OnComponentChanged, OnEntityDestroyed, custom events, and world.emit().
"""

import math
import os
import random
import sys

# Add src to path for running from demos directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from typing import Any

import pydantic.dataclasses

from relics import (
    Component,
    CustomEvent,
    Entity,
    OnComponentChanged,
    OnCustomEvent,
    OnEntityDestroyed,
    World,
    monitored,
)


# =============================================================================
# Components
# =============================================================================


@pydantic.dataclasses.dataclass
class Position(Component):
    """2D position in the world."""

    x: float
    y: float


@monitored  # Enable change tracking for OnComponentChanged
@pydantic.dataclasses.dataclass
class Health(Component):
    """Entity health with current and maximum values."""

    current: int
    maximum: int


@pydantic.dataclasses.dataclass
class Explosive(Component):
    """Makes an entity explosive when destroyed."""

    blast_radius: float
    blast_damage: int


@pydantic.dataclasses.dataclass
class Barrel(Component):
    """Marker component for barrel entities."""

    pass


# =============================================================================
# Custom Events
# =============================================================================


@pydantic.dataclasses.dataclass
class ExplosionEvent(CustomEvent):
    """Fired when an explosion occurs."""

    origin_x: float
    origin_y: float
    radius: float
    damage: int
    source_id: str  # String representation of source entity ID


# =============================================================================
# Observers
# =============================================================================


class HealthMonitor(OnComponentChanged):
    """Monitors health changes and triggers explosions when entities die."""

    component_type = Health

    def __init__(self) -> None:
        """Initialize the health monitor."""
        super().__init__()
        self._pending_explosions: list[tuple[Entity, Explosive, Position]] = []

    def on_component_changed(
        self,
        entity: Entity,
        component: Health,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Check if entity died and queue explosion if explosive.

        Args:
            entity: The entity whose health changed.
            component: The current health component.
            field_name: The name of the field that changed.
            old_value: Previous field value.
            new_value: New field value.
        """
        # Only react to 'current' field changes
        if field_name != "current":
            return

        # Check if entity just died (was alive, now at 0 or below)
        if old_value > 0 and new_value <= 0:
            print(f"  {entity.id} died!")

            # If explosive, queue an explosion event
            if entity.has_component(Explosive):
                explosive = entity.get_component(Explosive)
                pos = entity.get_component(Position)
                # Store for processing after we finish iterating
                self._pending_explosions.append((entity, explosive, pos))

    def process_pending(self) -> None:
        """Process pending explosions (call after tick to avoid modification during iteration)."""
        for entity, explosive, pos in self._pending_explosions:
            print(f"  {entity.id} explodes! (radius={explosive.blast_radius}, damage={explosive.blast_damage})")

            # Emit explosion event
            self.world.emit(
                ExplosionEvent(
                    origin_x=pos.x,
                    origin_y=pos.y,
                    radius=explosive.blast_radius,
                    damage=explosive.blast_damage,
                    source_id=str(entity.id),
                )
            )

            # Remove the destroyed entity
            self.world.remove(entity)

        self._pending_explosions.clear()


class ExplosionHandler(OnCustomEvent):
    """Handles explosion events and applies damage to nearby entities."""

    event_type = ExplosionEvent

    def on_event(self, event: ExplosionEvent) -> None:
        """Apply blast damage to entities within radius.

        Args:
            event: The explosion event to handle.
        """
        # Find all entities with Health and Position within blast radius
        for entity in self.world.query().with_all([Health, Position]).execute_entities():
            # Skip the source (already dead/removed or being removed)
            if str(entity.id) == event.source_id:
                continue

            pos = entity.get_component(Position)
            distance = math.sqrt(
                (pos.x - event.origin_x) ** 2 + (pos.y - event.origin_y) ** 2
            )

            if distance <= event.radius:
                health = entity.get_component(Health)
                # Damage falls off with distance
                damage_multiplier = 1.0 - (distance / event.radius)
                actual_damage = int(event.damage * damage_multiplier)

                if actual_damage > 0:
                    old_health = health.current
                    health.current = max(0, health.current - actual_damage)
                    print(
                        f"    {entity.id} takes {actual_damage} damage "
                        f"({old_health} -> {health.current})"
                    )


class DestructionLogger(OnEntityDestroyed):
    """Logs when entities are destroyed."""

    prefab = "barrel"  # Only watch barrel entities

    def on_entity_destroyed(self, entity: Entity) -> None:
        """Log entity destruction.

        Args:
            entity: The entity being destroyed.
        """
        print(f"  [LOG] Barrel {entity.id} removed from world")


# =============================================================================
# Utility Functions
# =============================================================================


def distance(p1: Position, p2: Position) -> float:
    """Calculate distance between two positions."""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def print_battlefield(world: World) -> None:
    """Print ASCII visualization of the battlefield."""
    width, height = 50, 20
    grid = [["." for _ in range(width)] for _ in range(height)]

    # Place barrels on grid
    for entity in world.query().with_all([Position, Health, Barrel]).execute_entities():
        pos = entity.get_component(Position)
        health = entity.get_component(Health)

        # Scale position to grid
        gx = int(pos.x / 100.0 * (width - 1))
        gy = int(pos.y / 100.0 * (height - 1))

        # Clamp to grid bounds
        gx = max(0, min(width - 1, gx))
        gy = max(0, min(height - 1, gy))

        # Symbol based on health
        if health.current > 50:
            symbol = "O"  # Healthy
        elif health.current > 0:
            symbol = "o"  # Damaged
        else:
            symbol = "X"  # Dead (shouldn't appear normally)

        grid[gy][gx] = symbol

    # Print grid
    print("+" + "-" * width + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * width + "+")


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run the chain reaction simulation."""
    # Seed for reproducible output
    random.seed(42)

    print("=== Chain Reaction Demo ===\n")

    # Create world
    world = World()

    # Register barrel prefab
    world.register_prefab(
        "barrel",
        {
            Position: Position(x=0.0, y=0.0),
            Health: Health(current=100, maximum=100),
            Explosive: Explosive(blast_radius=25.0, blast_damage=80),
            Barrel: Barrel(),
        },
    )

    # Register observers
    health_monitor = HealthMonitor()
    world.observe(health_monitor)
    world.observe(ExplosionHandler())
    world.observe(DestructionLogger())

    # Spawn barrels in a cluster
    print("Spawning barrels in a cluster...")
    barrel_positions = [
        (50.0, 50.0),  # Center barrel (will be hit first)
        (35.0, 50.0),  # Left
        (65.0, 50.0),  # Right
        (50.0, 35.0),  # Top
        (50.0, 65.0),  # Bottom
        (35.0, 35.0),  # Top-left
        (65.0, 35.0),  # Top-right
        (35.0, 65.0),  # Bottom-left
        (65.0, 65.0),  # Bottom-right
        (20.0, 50.0),  # Far left (should survive)
        (80.0, 50.0),  # Far right (should survive)
    ]

    for x, y in barrel_positions:
        barrel = world.spawn("barrel", {Position: Position(x=x, y=y)})
        print(f"  Spawned {barrel.id} at ({x}, {y})")

    print(f"\nTotal barrels: {len(barrel_positions)}")
    print("\nInitial battlefield:")
    print_battlefield(world)

    # Trigger the chain reaction by damaging the center barrel
    print("\n--- Triggering chain reaction! ---")
    print("Shooting the center barrel...\n")

    # Find the center barrel and damage it
    for entity in world.query().with_all([Position, Health, Barrel]).execute_entities():
        pos = entity.get_component(Position)
        if abs(pos.x - 50.0) < 1.0 and abs(pos.y - 50.0) < 1.0:
            health = entity.get_component(Health)
            print(f"Dealing 100 damage to {entity.id}...")
            health.current = 0  # This triggers OnComponentChanged
            break

    # Process the chain reaction over multiple ticks
    max_iterations = 10
    for i in range(max_iterations):
        print(f"\n--- Tick {i + 1} ---")

        # Process observer queue
        world.tick(0)

        # Process any pending explosions
        health_monitor.process_pending()

        # Process explosion damage (which may create more pending explosions)
        world.tick(0)

        # Check if any barrels remain
        remaining = list(
            world.query().with_all([Position, Health, Barrel]).execute_entities()
        )
        alive = [e for e in remaining if e.get_component(Health).current > 0]

        print(f"\nBarrels remaining: {len(remaining)}, Alive: {len(alive)}")

        if len(health_monitor._pending_explosions) == 0 and all(
            e.get_component(Health).current > 0 for e in remaining
        ):
            print("Chain reaction complete!")
            break

    # Final state
    print("\n=== Final State ===")
    print_battlefield(world)

    surviving = list(
        world.query().with_all([Position, Health, Barrel]).execute_entities()
    )
    print(f"\nSurviving barrels: {len(surviving)}")
    for entity in surviving:
        pos = entity.get_component(Position)
        health = entity.get_component(Health)
        print(f"  {entity.id}: pos=({pos.x}, {pos.y}), health={health.current}/{health.maximum}")


if __name__ == "__main__":
    main()
