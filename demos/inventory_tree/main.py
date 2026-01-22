#!/usr/bin/env python3
"""Inventory Tree - Character equipment and container hierarchy demo.

Demonstrates the graph/relationship system: characters equip items,
containers hold items, and items can be nested. Shows custom Edge types,
add_relationship(), get_relationships(), hierarchy traversal, and cascade deletion.
"""

import os
import sys
from typing import Generator, List

# Add src to path for running from demos directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pydantic.dataclasses

from relics import Component, Edge, Entity, World


# =============================================================================
# Components
# =============================================================================


@pydantic.dataclasses.dataclass
class Character(Component):
    """A character that can equip items."""

    name: str


@pydantic.dataclasses.dataclass
class Item(Component):
    """An item that can be equipped or stored."""

    name: str
    weight: float


@pydantic.dataclasses.dataclass
class Stackable(Component):
    """Makes an item stackable."""

    count: int
    max_stack: int


@pydantic.dataclasses.dataclass
class Container(Component):
    """A container that can hold items."""

    name: str
    capacity: int  # Max number of items


# =============================================================================
# Edge Types (Relationships)
# =============================================================================


@pydantic.dataclasses.dataclass
class Equipped(Edge):
    """Relationship: character has item equipped in a slot."""

    slot: str  # e.g., "main_hand", "head", "chest"


@pydantic.dataclasses.dataclass
class Contains(Edge):
    """Relationship: container holds an item."""

    pass


# =============================================================================
# Utility Functions for Hierarchy Traversal
# =============================================================================


def get_children(entity: Entity, edge_type: type) -> Generator[Entity, None, None]:
    """Get all child entities connected by the given edge type.

    Args:
        entity: The parent entity.
        edge_type: The type of edge to follow.

    Yields:
        Child entities.
    """
    world = entity._world
    for edge, target_id in entity.get_relationships(edge_type):
        yield world.get_entity(target_id)


def get_parent(entity: Entity, edge_type: type) -> Entity | None:
    """Get the parent entity (if any) connected by the given edge type.

    Args:
        entity: The child entity.
        edge_type: The type of edge to follow back.

    Returns:
        The parent entity, or None if no parent.
    """
    world = entity._world
    incoming = entity.get_incoming_relationships(edge_type)
    if incoming:
        source_id, edge = incoming[0]
        return world.get_entity(source_id)
    return None


def get_slot(entity: Entity) -> str | None:
    """Get the equipment slot an item is in (if equipped).

    Args:
        entity: The item entity.

    Returns:
        The slot name, or None if not equipped.
    """
    incoming = entity.get_incoming_relationships(Equipped)
    if incoming:
        source_id, edge = incoming[0]
        return edge.slot
    return None


def get_all_descendants(
    entity: Entity, edge_type: type
) -> Generator[Entity, None, None]:
    """Recursively get all descendants via the given edge type.

    Args:
        entity: The root entity.
        edge_type: The type of edge to follow.

    Yields:
        All descendant entities.
    """
    for child in get_children(entity, edge_type):
        yield child
        yield from get_all_descendants(child, edge_type)


def destroy_with_children(world: World, entity: Entity, edge_type: type) -> int:
    """Recursively destroy an entity and all its children.

    Args:
        world: The world containing the entities.
        entity: The root entity to destroy.
        edge_type: The type of edge defining parent-child relationships.

    Returns:
        Total number of entities destroyed.
    """
    count = 0

    # First destroy all children (depth-first)
    for child in list(get_children(entity, edge_type)):
        count += destroy_with_children(world, child, edge_type)

    # Then destroy this entity
    world.remove(entity)
    count += 1

    return count


def calculate_total_weight(entity: Entity) -> float:
    """Calculate total weight of an entity and all items it contains.

    Args:
        entity: The entity to calculate weight for.

    Returns:
        Total weight including all contained items.
    """
    weight = 0.0

    # Add this entity's weight if it's an item
    if entity.has_component(Item):
        item = entity.get_component(Item)
        multiplier = 1
        if entity.has_component(Stackable):
            multiplier = entity.get_component(Stackable).count
        weight += item.weight * multiplier

    # Add weight of contained items
    for child in get_children(entity, Contains):
        weight += calculate_total_weight(child)

    # Add weight of equipped items
    for child in get_children(entity, Equipped):
        weight += calculate_total_weight(child)

    return weight


# =============================================================================
# Pretty Printing
# =============================================================================


def print_inventory_tree(entity: Entity, indent: int = 0) -> None:
    """Print an ASCII tree representation of an entity's inventory.

    Args:
        entity: The root entity to print.
        indent: Current indentation level.
    """
    prefix = "  " * indent

    # Format entity description
    if entity.has_component(Character):
        char = entity.get_component(Character)
        desc = f"[Character] {char.name}"
    elif entity.has_component(Container):
        container = entity.get_component(Container)
        children = list(get_children(entity, Contains))
        desc = f"[Container] {container.name} ({len(children)}/{container.capacity})"
    elif entity.has_component(Item):
        item = entity.get_component(Item)
        desc = f"[Item] {item.name} ({item.weight}kg)"
        if entity.has_component(Stackable):
            stack = entity.get_component(Stackable)
            desc += f" x{stack.count}"
    else:
        desc = f"[Unknown] {entity.id}"

    # Add slot info if equipped
    slot = get_slot(entity)
    if slot:
        desc = f"{desc} <{slot}>"

    print(f"{prefix}{desc}")

    # Print equipped items
    equipped = list(get_children(entity, Equipped))
    if equipped:
        for child in equipped:
            print_inventory_tree(child, indent + 1)

    # Print contained items
    contained = list(get_children(entity, Contains))
    if contained:
        for child in contained:
            print_inventory_tree(child, indent + 1)


# =============================================================================
# Main
# =============================================================================


def main() -> None:
    """Run the inventory tree demo."""
    print("=== Inventory Tree Demo ===\n")

    # Create world
    world = World()

    # Register prefabs
    world.register_prefab("character", {Character: Character(name="")})
    world.register_prefab(
        "item",
        {Item: Item(name="", weight=0.0)},
    )
    world.register_prefab(
        "stackable_item",
        {
            Item: Item(name="", weight=0.0),
            Stackable: Stackable(count=1, max_stack=99),
        },
    )
    world.register_prefab(
        "container",
        {
            Item: Item(name="", weight=0.0),  # Containers are also items
            Container: Container(name="", capacity=10),
        },
    )

    # Create a character
    print("Creating character 'Adventurer'...")
    adventurer = world.spawn(
        "character",
        {Character: Character(name="Adventurer")},
    )

    # Create and equip a sword
    print("Creating and equipping Iron Sword...")
    sword = world.spawn(
        "item",
        {Item: Item(name="Iron Sword", weight=3.5)},
    )
    adventurer.add_relationship(Equipped(slot="main_hand"), sword.id)

    # Create and equip a shield
    print("Creating and equipping Wooden Shield...")
    shield = world.spawn(
        "item",
        {Item: Item(name="Wooden Shield", weight=4.0)},
    )
    adventurer.add_relationship(Equipped(slot="off_hand"), shield.id)

    # Create and equip a helmet
    print("Creating and equipping Leather Helmet...")
    helmet = world.spawn(
        "item",
        {Item: Item(name="Leather Helmet", weight=1.0)},
    )
    adventurer.add_relationship(Equipped(slot="head"), helmet.id)

    # Create a backpack (container) and equip it
    print("Creating and equipping Backpack...")
    backpack = world.spawn(
        "container",
        {
            Item: Item(name="Backpack", weight=0.5),
            Container: Container(name="Backpack", capacity=8),
        },
    )
    adventurer.add_relationship(Equipped(slot="back"), backpack.id)

    # Add items to backpack
    print("Adding items to backpack...")

    # Health potions (stackable)
    potions = world.spawn(
        "stackable_item",
        {
            Item: Item(name="Health Potion", weight=0.2),
            Stackable: Stackable(count=5, max_stack=10),
        },
    )
    backpack.add_relationship(Contains(), potions.id)

    # Gold coins (stackable)
    gold = world.spawn(
        "stackable_item",
        {
            Item: Item(name="Gold Coin", weight=0.01),
            Stackable: Stackable(count=47, max_stack=999),
        },
    )
    backpack.add_relationship(Contains(), gold.id)

    # Torch
    torch = world.spawn(
        "item",
        {Item: Item(name="Torch", weight=0.5)},
    )
    backpack.add_relationship(Contains(), torch.id)

    # Create a nested container: a pouch inside the backpack
    print("Creating Coin Pouch inside Backpack...")
    pouch = world.spawn(
        "container",
        {
            Item: Item(name="Coin Pouch", weight=0.1),
            Container: Container(name="Coin Pouch", capacity=3),
        },
    )
    backpack.add_relationship(Contains(), pouch.id)

    # Add gems to the pouch
    ruby = world.spawn(
        "item",
        {Item: Item(name="Ruby", weight=0.05)},
    )
    pouch.add_relationship(Contains(), ruby.id)

    emerald = world.spawn(
        "item",
        {Item: Item(name="Emerald", weight=0.05)},
    )
    pouch.add_relationship(Contains(), emerald.id)

    # Tick to process events
    world.tick(0)

    # Print the full inventory tree
    print("\n=== Inventory Tree ===\n")
    print_inventory_tree(adventurer)

    # Calculate total weight
    total_weight = calculate_total_weight(adventurer)
    print(f"\nTotal carried weight: {total_weight:.2f}kg")

    # Demonstrate traversal
    print("\n=== Traversal Examples ===\n")

    # Get all equipped items
    print("Equipped items:")
    for item in get_children(adventurer, Equipped):
        slot = get_slot(item)
        item_comp = item.get_component(Item)
        print(f"  [{slot}] {item_comp.name}")

    # Get all items in backpack (non-recursive)
    print("\nBackpack contents (direct):")
    for item in get_children(backpack, Contains):
        item_comp = item.get_component(Item)
        print(f"  - {item_comp.name}")

    # Get all items in backpack (recursive)
    print("\nBackpack contents (all descendants):")
    for item in get_all_descendants(backpack, Contains):
        item_comp = item.get_component(Item)
        depth = 0
        parent = item
        while (parent := get_parent(parent, Contains)) is not None:
            depth += 1
        print(f"  {'  ' * depth}- {item_comp.name}")

    # Demonstrate finding parent
    print("\nParent relationships:")
    ruby_parent = get_parent(ruby, Contains)
    if ruby_parent and ruby_parent.has_component(Container):
        print(f"  Ruby is in: {ruby_parent.get_component(Container).name}")

    pouch_parent = get_parent(pouch, Contains)
    if pouch_parent and pouch_parent.has_component(Container):
        print(f"  Coin Pouch is in: {pouch_parent.get_component(Container).name}")

    # Demonstrate cascade deletion
    print("\n=== Cascade Deletion ===\n")
    print("Dropping the Coin Pouch (and all its contents)...")

    # First, count descendants
    descendants = list(get_all_descendants(pouch, Contains))
    print(f"Pouch contains {len(descendants)} items")

    # Remove from backpack and destroy
    backpack.remove_relationship(Contains, pouch.id)
    destroyed = destroy_with_children(world, pouch, Contains)
    print(f"Destroyed {destroyed} entities")

    # Tick to process
    world.tick(0)

    # Print updated tree
    print("\n=== Updated Inventory ===\n")
    print_inventory_tree(adventurer)

    # Updated weight
    new_weight = calculate_total_weight(adventurer)
    print(f"\nTotal carried weight: {new_weight:.2f}kg (was {total_weight:.2f}kg)")


if __name__ == "__main__":
    main()
