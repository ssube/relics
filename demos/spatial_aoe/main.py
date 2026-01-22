#!/usr/bin/env python3
"""Spatial AoE - Tactical combat with spatial queries demo.

Demonstrates the spatial index addon for efficient spatial queries.
Features area-of-effect attacks, nearest enemy targeting, and zone detection.
"""

import os
import random
import sys

# Add src to path for running from demos directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pydantic.dataclasses

from relics import Component, Entity, World, monitored
from relics.addons.spatial import (
    Position2D,
    QuadTreeBounds,
    create_spatial_index_2d,
    distance_2d,
)


# =============================================================================
# Components
# =============================================================================


@pydantic.dataclasses.dataclass
class Unit(Component):
    """A combat unit with team affiliation."""

    name: str
    team: str  # "red" or "blue"


@monitored  # Enable change tracking for health
@pydantic.dataclasses.dataclass
class Health(Component):
    """Unit health."""

    current: int
    maximum: int


# =============================================================================
# Battlefield Visualization
# =============================================================================


def print_battlefield(world: World, width: int = 60, height: int = 25) -> None:
    """Print an ASCII visualization of the battlefield.

    Args:
        world: The world containing units.
        width: Grid width in characters.
        height: Grid height in characters.
    """
    # Create empty grid
    grid = [["." for _ in range(width)] for _ in range(height)]

    # Place units on grid
    for entity in world.query().with_all([Position2D, Unit, Health]).execute_entities():
        pos = entity.get_component(Position2D)
        unit = entity.get_component(Unit)
        health = entity.get_component(Health)

        # Scale position to grid (assuming 0-100 world coords)
        gx = int(pos.x / 100.0 * (width - 1))
        gy = int(pos.y / 100.0 * (height - 1))

        # Clamp to grid bounds
        gx = max(0, min(width - 1, gx))
        gy = max(0, min(height - 1, gy))

        # Symbol based on team and health
        if health.current <= 0:
            symbol = "x"  # Dead
        elif unit.team == "red":
            symbol = "R" if health.current > health.maximum // 2 else "r"
        else:
            symbol = "B" if health.current > health.maximum // 2 else "b"

        grid[gy][gx] = symbol

    # Print grid with border
    print("+" + "-" * width + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * width + "+")
    print("Legend: R/r=Red team, B/b=Blue team, lowercase=damaged, x=dead")


# =============================================================================
# Combat Actions Using Spatial Queries
# =============================================================================


def cast_fireball(
    world: World,
    spatial_index,
    caster: Entity,
    target_x: float,
    target_y: float,
    radius: float,
    damage: int,
) -> list[Entity]:
    """Cast a fireball AoE attack using circle query.

    Args:
        world: The world.
        spatial_index: The spatial index for queries.
        caster: The casting unit (won't damage itself).
        target_x: X coordinate of fireball center.
        target_y: Y coordinate of fireball center.
        radius: Blast radius.
        damage: Base damage at center.

    Returns:
        List of entities that were hit.
    """
    caster_name = caster.get_component(Unit).name
    print(f"\n{caster_name} casts FIREBALL at ({target_x:.0f}, {target_y:.0f})!")
    print(f"  Radius: {radius}, Base damage: {damage}")

    hit_entities = []

    # Use circle query to find all entities in blast radius
    for entity in spatial_index.query_circle(target_x, target_y, radius):
        # Skip the caster
        if entity.id == caster.id:
            continue

        # Skip dead units
        health = entity.get_component(Health)
        if health.current <= 0:
            continue

        # Calculate damage falloff based on distance
        pos = entity.get_component(Position2D)
        dist = distance_2d(target_x, target_y, pos.x, pos.y)
        damage_multiplier = 1.0 - (dist / radius)
        actual_damage = max(1, int(damage * damage_multiplier))

        # Apply damage
        old_health = health.current
        health.current = max(0, health.current - actual_damage)

        unit = entity.get_component(Unit)
        status = "KILLED!" if health.current <= 0 else f"{health.current}/{health.maximum}"
        print(
            f"  Hit {unit.name} ({unit.team}) for {actual_damage} damage "
            f"({old_health} -> {status})"
        )

        hit_entities.append(entity)

    if not hit_entities:
        print("  No targets hit!")

    return hit_entities


def find_nearest_enemy(
    spatial_index,
    unit: Entity,
    max_count: int = 3,
) -> list[tuple[Entity, float]]:
    """Find the nearest enemies using nearest query.

    Args:
        spatial_index: The spatial index for queries.
        unit: The unit looking for enemies.
        max_count: Maximum number of enemies to return.

    Returns:
        List of (entity, distance) tuples for nearest enemies.
    """
    my_unit = unit.get_component(Unit)
    my_pos = unit.get_component(Position2D)

    print(f"\n{my_unit.name} scanning for enemies...")

    # Query nearest units
    nearest = spatial_index.query_nearest(my_pos.x, my_pos.y, max_count + 5)

    enemies = []
    for entity, dist in nearest:
        if entity.id == unit.id:
            continue

        other_unit = entity.get_component(Unit)
        health = entity.get_component(Health)

        # Skip dead units
        if health.current <= 0:
            continue

        # Skip allies
        if other_unit.team == my_unit.team:
            continue

        enemies.append((entity, dist))
        if len(enemies) >= max_count:
            break

    if enemies:
        print(f"  Found {len(enemies)} enemies:")
        for entity, dist in enemies:
            other_unit = entity.get_component(Unit)
            other_health = entity.get_component(Health)
            print(
                f"    {other_unit.name} ({other_unit.team}) at distance {dist:.1f} "
                f"[{other_health.current}/{other_health.maximum}]"
            )
    else:
        print("  No enemies found!")

    return enemies


def detect_in_zone(
    spatial_index,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
    zone_name: str = "zone",
) -> dict[str, list[Entity]]:
    """Detect all units in a rectangular zone.

    Args:
        spatial_index: The spatial index for queries.
        min_x: Zone minimum X.
        min_y: Zone minimum Y.
        max_x: Zone maximum X.
        max_y: Zone maximum Y.
        zone_name: Name of the zone for display.

    Returns:
        Dictionary mapping team names to lists of entities in zone.
    """
    print(f"\nScanning {zone_name} ({min_x:.0f},{min_y:.0f}) to ({max_x:.0f},{max_y:.0f})...")

    teams: dict[str, list[Entity]] = {"red": [], "blue": []}

    for entity in spatial_index.query_rectangle(min_x, min_y, max_x, max_y):
        health = entity.get_component(Health)
        if health.current <= 0:
            continue

        unit = entity.get_component(Unit)
        teams[unit.team].append(entity)

    print(f"  Red team: {len(teams['red'])} units")
    for entity in teams["red"]:
        unit = entity.get_component(Unit)
        health = entity.get_component(Health)
        print(f"    - {unit.name} [{health.current}/{health.maximum}]")

    print(f"  Blue team: {len(teams['blue'])} units")
    for entity in teams["blue"]:
        unit = entity.get_component(Unit)
        health = entity.get_component(Health)
        print(f"    - {unit.name} [{health.current}/{health.maximum}]")

    return teams


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run the spatial AoE combat demo."""
    # Seed for reproducible output
    random.seed(42)

    print("=== Spatial AoE Combat Demo ===\n")

    # Create world
    world = World()

    # Register unit prefab with Position2D from spatial addon
    world.register_prefab(
        "unit",
        {
            Position2D: Position2D(x=0.0, y=0.0),
            Unit: Unit(name="", team=""),
            Health: Health(current=100, maximum=100),
        },
    )

    # Create spatial index with observer auto-registration
    print("Creating spatial index (100x100 battlefield)...")
    spatial_index = create_spatial_index_2d(
        world,
        # QuadTreeBounds uses center + half-extents: center at (50,50), extends 50 in each direction
        bounds=QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50),
        materialized=True,
        auto_register_observer=True,
    )

    # Spawn red team (clustered on left side)
    print("\nSpawning Red team (5 units)...")
    red_names = ["RedLead", "RedArcher", "RedKnight", "RedMage", "RedScout"]
    red_units = []
    for i, name in enumerate(red_names):
        unit = world.spawn(
            "unit",
            {
                Position2D: Position2D(
                    x=random.uniform(10.0, 35.0),
                    y=random.uniform(30.0, 70.0),
                ),
                Unit: Unit(name=name, team="red"),
                Health: Health(current=100, maximum=100),
            },
        )
        red_units.append(unit)
        pos = unit.get_component(Position2D)
        print(f"  {name} at ({pos.x:.1f}, {pos.y:.1f})")

    # Spawn blue team (clustered on right side)
    print("\nSpawning Blue team (5 units)...")
    blue_names = ["BlueLead", "BlueArcher", "BlueKnight", "BlueMage", "BlueScout"]
    blue_units = []
    for i, name in enumerate(blue_names):
        unit = world.spawn(
            "unit",
            {
                Position2D: Position2D(
                    x=random.uniform(65.0, 90.0),
                    y=random.uniform(30.0, 70.0),
                ),
                Unit: Unit(name=name, team="blue"),
                Health: Health(current=100, maximum=100),
            },
        )
        blue_units.append(unit)
        pos = unit.get_component(Position2D)
        print(f"  {name} at ({pos.x:.1f}, {pos.y:.1f})")

    # Process initial spawns
    world.tick(0)

    print(f"\nTotal units in spatial index: {spatial_index.count()}")

    # Show initial battlefield
    print("\n=== Initial Battlefield ===")
    print_battlefield(world)

    # === DEMONSTRATION 1: Zone Detection ===
    print("\n" + "=" * 50)
    print("DEMO 1: Zone Detection (query_rectangle)")
    print("=" * 50)

    # Detect units in left zone
    detect_in_zone(spatial_index, 0, 0, 50, 100, "Left Half")

    # Detect units in center zone
    detect_in_zone(spatial_index, 35, 35, 65, 65, "Center Zone")

    # === DEMONSTRATION 2: Nearest Enemy Targeting ===
    print("\n" + "=" * 50)
    print("DEMO 2: Nearest Enemy Targeting (query_nearest)")
    print("=" * 50)

    # Red leader finds nearest enemies
    find_nearest_enemy(spatial_index, red_units[0])

    # Blue leader finds nearest enemies
    find_nearest_enemy(spatial_index, blue_units[0])

    # === DEMONSTRATION 3: AoE Attack ===
    print("\n" + "=" * 50)
    print("DEMO 3: Area of Effect Attack (query_circle)")
    print("=" * 50)

    # Red mage casts fireball at blue team cluster
    red_mage = red_units[3]  # RedMage

    # Find center of blue team
    blue_x = sum(u.get_component(Position2D).x for u in blue_units) / len(blue_units)
    blue_y = sum(u.get_component(Position2D).y for u in blue_units) / len(blue_units)

    cast_fireball(
        world, spatial_index, red_mage,
        target_x=blue_x,
        target_y=blue_y,
        radius=20.0,
        damage=60,
    )

    # Process damage
    world.tick(0)

    # Show battlefield after attack
    print("\n=== Battlefield After Red's Fireball ===")
    print_battlefield(world)

    # Blue mage retaliates
    blue_mage = blue_units[3]  # BlueMage
    blue_health = blue_mage.get_component(Health)

    if blue_health.current > 0:
        # Find center of red team
        red_x = sum(u.get_component(Position2D).x for u in red_units) / len(red_units)
        red_y = sum(u.get_component(Position2D).y for u in red_units) / len(red_units)

        cast_fireball(
            world, spatial_index, blue_mage,
            target_x=red_x,
            target_y=red_y,
            radius=25.0,  # Larger radius
            damage=50,    # Slightly less damage
        )

        world.tick(0)
    else:
        print("\nBlueMage was killed and cannot retaliate!")

    # === FINAL STATE ===
    print("\n" + "=" * 50)
    print("FINAL STATE")
    print("=" * 50)

    print_battlefield(world)

    # Count survivors
    print("\n=== Survivors ===")
    red_alive = 0
    blue_alive = 0

    for entity in spatial_index.query_rectangle(0, 0, 100, 100):
        unit = entity.get_component(Unit)
        health = entity.get_component(Health)

        if health.current > 0:
            if unit.team == "red":
                red_alive += 1
            else:
                blue_alive += 1
            print(f"  {unit.name} ({unit.team}): {health.current}/{health.maximum}")

    print(f"\nRed team: {red_alive}/5 alive")
    print(f"Blue team: {blue_alive}/5 alive")

    if red_alive > blue_alive:
        print("\nRed team wins!")
    elif blue_alive > red_alive:
        print("\nBlue team wins!")
    else:
        print("\nIt's a draw!")


if __name__ == "__main__":
    main()
