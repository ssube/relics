"""Persistence and secondary indexes example.

This example shows how to:
- Save and load world state to JSON
- Create and use relics (named snapshots)
- Create lazy and materialized indexes
- Use export_entity for debugging
"""

import tempfile
from pathlib import Path

from pydantic.dataclasses import dataclass

from relics import (
    Component,
    Edge,
    World,
    list_relics,
    load,
    load_relic,
    save,
    save_relic,
)


# Define components
@dataclass
class Position(Component):
    """2D position component."""

    x: float
    y: float


@dataclass
class Health(Component):
    """Health component."""

    current: int
    maximum: int


@dataclass
class Inventory(Component):
    """Inventory component with items."""

    gold: int = 0
    items: int = 0


@dataclass
class Dead(Component):
    """Marker component for dead entities."""

    pass


# Define edges
@dataclass
class AllyTo(Edge):
    """Alliance relationship."""

    trust_level: float = 1.0


def demo_basic_persistence():
    """Demonstrate basic save/load."""
    print("=== Basic Persistence ===\n")

    # Create temporary directory for saves
    with tempfile.TemporaryDirectory() as temp_dir:
        save_path = Path(temp_dir) / "game.json"

        # Create and populate world
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
                Inventory: Inventory(gold=0, items=0),
            },
        )

        player = world.spawn(
            "player",
            {
                Position: Position(x=10, y=20),
                Inventory: Inventory(gold=500, items=5),
            },
        )
        ally = world.spawn("player", {Position: Position(x=15, y=20)})

        # Add relationship
        player.add_relationship(AllyTo(trust_level=0.9), ally.id)

        # Advance time
        for _ in range(100):
            world.tick(0.016)

        print(f"World epoch before save: {world.epoch}")
        print(f"Player position: ({player.get_component(Position).x}, "
              f"{player.get_component(Position).y})")
        print(f"Player gold: {player.get_component(Inventory).gold}")

        # Save world state
        save(world, save_path)
        print(f"\nSaved world to {save_path}")

        # Load into new world
        world2 = World()
        component_registry = {
            "Position": Position,
            "Health": Health,
            "Inventory": Inventory,
        }
        edge_registry = {"AllyTo": AllyTo}

        load(world2, save_path, component_registry, edge_registry)

        print(f"\nLoaded world epoch: {world2.epoch}")

        # Verify data
        loaded_player = world2.get_entity(player.id)
        pos = loaded_player.get_component(Position)
        inv = loaded_player.get_component(Inventory)
        print(f"Loaded player position: ({pos.x}, {pos.y})")
        print(f"Loaded player gold: {inv.gold}")

        # Verify relationship
        rels = loaded_player.get_relationships(AllyTo)
        print(f"Loaded player has {len(rels)} ally relationship(s)")


def demo_relics():
    """Demonstrate named snapshots (relics)."""
    print("\n=== Relics (Named Snapshots) ===\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create world
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )

        player = world.spawn("player")

        # Save initial state
        save_relic(world, "start", temp_dir)
        print("Saved relic: 'start'")

        # Progress game
        for _ in range(50):
            world.tick(0.016)

        pos = player.get_component(Position)
        pos.x = 100
        pos.y = 50

        # Save mid-game state
        save_relic(world, "midgame", temp_dir)
        print("Saved relic: 'midgame'")

        # Continue and take damage
        for _ in range(50):
            world.tick(0.016)

        health = player.get_component(Health)
        health.current = 30

        # Save before boss
        save_relic(world, "before_boss", temp_dir)
        print("Saved relic: 'before_boss'")

        # List all relics
        print("\nAvailable relics:")
        relics = list_relics(temp_dir)
        for info in relics:
            print(f"  - {info.name} (epoch: {info.epoch}, created: {info.created_at})")

        # Load earlier state
        print("\nLoading 'midgame' relic...")
        world2 = World()
        load_relic(
            world2, "midgame", temp_dir, component_registry={"Position": Position, "Health": Health}
        )

        loaded_player = world2.get_entity(player.id)
        pos = loaded_player.get_component(Position)
        health = loaded_player.get_component(Health)

        print(f"Loaded state - Position: ({pos.x}, {pos.y}), Health: {health.current}")
        print(f"Loaded epoch: {world2.epoch}")


def demo_indexes():
    """Demonstrate secondary indexes."""
    print("\n=== Secondary Indexes ===\n")

    # Create world
    world = World()
    world.register_prefab(
        "player",
        {
            Position: Position(x=0, y=0),
            Health: Health(current=100, maximum=100),
        },
    )

    # Spawn multiple entities with varying health
    for i in range(20):
        health_value = 100 - (i * 4)  # 100, 96, 92, ..., 24
        world.spawn(
            "player",
            {
                Position: Position(x=i * 10, y=0),
                Health: Health(current=health_value, maximum=100),
            },
        )

    # Mark some as dead
    entities = list(world.query().with_all([Health]).execute_entities())
    for entity in entities[15:]:  # Last 5 are dead
        entity.add_component(Dead())

    # Create lazy index for alive entities
    world.create_index(
        name="alive",
        query=world.query().with_all([Health]).with_none([Dead]),
        materialized=False,
    )

    # Create materialized index for low health entities
    world.create_index(
        name="low_health",
        query=world.query()
        .with_all([Health])
        .with_none([Dead])
        .with_filter(lambda e: e.get_component(Health).current < 50),
        watches=[Health],
        materialized=True,
    )

    # Create materialized index for critical health
    world.create_index(
        name="critical",
        query=world.query()
        .with_all([Health])
        .with_none([Dead])
        .with_filter(lambda e: e.get_component(Health).current < 30),
        watches=[Health],
        materialized=True,
    )

    print("Indexes created:")
    print(f"  - 'alive': {world.index('alive').count()} entities")
    print(f"  - 'low_health': {world.index('low_health').count()} entities")
    print(f"  - 'critical': {world.index('critical').count()} entities")

    # Use indexes
    print("\nLow health entities:")
    for entity in world.index("low_health"):
        health = entity.get_component(Health)
        print(f"  {entity.id}: {health.current}/{health.maximum}")

    print("\nCritical health entities:")
    for entity in world.index("critical"):
        health = entity.get_component(Health)
        print(f"  {entity.id}: {health.current}/{health.maximum}")


def demo_export():
    """Demonstrate entity export for debugging."""
    print("\n=== Entity Export ===\n")

    # Create world
    world = World()
    world.register_prefab(
        "player",
        {
            Position: Position(x=0, y=0),
            Health: Health(current=100, maximum=100),
            Inventory: Inventory(gold=0, items=0),
        },
    )

    player = world.spawn(
        "player",
        {
            Position: Position(x=50, y=75),
            Inventory: Inventory(gold=1000, items=10),
        },
    )
    ally = world.spawn("player", {Position: Position(x=55, y=75)})

    player.add_relationship(AllyTo(trust_level=0.95), ally.id)

    # Export entity
    export_data = world.export_entity(player.id)

    print("Exported player data:")
    print(f"  ID: {export_data['id']}")
    print(f"  Prefab: {export_data['prefab']}")
    print("  Components:")
    for comp_name, comp_data in export_data["components"].items():
        print(f"    {comp_name}: {comp_data}")
    print("  Relationships:")
    for edge_type, rels in export_data.get("relationships", {}).items():
        for rel in rels:
            print(f"    {edge_type} -> {rel['target']}: {rel['edge']}")


def main():
    """Run all persistence and index demos."""
    demo_basic_persistence()
    demo_relics()
    demo_indexes()
    demo_export()


if __name__ == "__main__":
    main()
