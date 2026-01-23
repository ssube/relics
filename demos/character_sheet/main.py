#!/usr/bin/env python3
"""Character Sheet Demo - Procedural character generation with formatted output."""

import argparse
import os
import random
import sys

# Add src to path for running from demos directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from relics import World
from relics.addons.procedural_prefabs import (
    ProceduralPrefabRegistry,
    HasEquipped,
    IsWearing,
    get_children,
)

from demos.character_sheet.components import (
    Identity,
    CharacterClass,
    Appearance,
    Equipment,
    WeaponStats,
    ArmorStats,
)


# Name pools for random character generation
FIRST_NAMES = {
    "human": ["Marcus", "Elena", "Roland", "Lyra", "Thomas", "Sarah"],
    "elf": ["Aelindra", "Thalanil", "Sylvaris", "Elowen", "Caelum", "Miriel"],
    "dwarf": ["Thorin", "Brunhild", "Gimrik", "Helga", "Durotan", "Ingrid"],
    "orc": ["Grommash", "Ulgra", "Thrall", "Nazgra", "Kargath", "Shagra"],
}

TITLES = {
    "warrior": ["the Bold", "Ironshield", "Battleborn", "the Valiant", ""],
    "ranger": ["Shadowstep", "the Swift", "Windwalker", "the Hunter", ""],
    "mage": ["the Wise", "Spellweaver", "the Arcane", "Flamecaller", ""],
    "rogue": ["Shadowblade", "the Cunning", "Nightwalker", "the Silent", ""],
}

RACES = ["human", "elf", "dwarf", "orc"]
CLASSES = ["warrior", "ranger", "mage", "rogue"]


def cm_to_feet_inches(cm: int) -> str:
    """Convert centimeters to feet and inches string."""
    total_inches = cm / 2.54
    feet = int(total_inches // 12)
    inches = int(total_inches % 12)
    return f"{feet}'{inches}\""


def kg_to_lbs(kg: float) -> int:
    """Convert kilograms to pounds."""
    return int(kg * 2.205)


def format_character_sheet(
    identity: Identity,
    char_class: CharacterClass,
    appearance: Appearance,
    weapon: tuple[Equipment, WeaponStats] | None,
    armor: tuple[Equipment, ArmorStats] | None,
) -> str:
    """Format a character sheet as ASCII art."""
    width = 58

    lines = []
    lines.append("+" + "=" * width + "+")
    lines.append("|" + "CHARACTER SHEET".center(width) + "|")
    lines.append("+" + "=" * width + "+")

    # Identity section
    name_display = identity.name
    if identity.title:
        name_display += f" {identity.title}"
    lines.append("|  " + f"Name: {name_display}".ljust(width - 2) + "|")

    race_cls = f"Race: {char_class.race.title():<14}Class: {char_class.cls.title()}"
    lines.append("|  " + race_cls.ljust(width - 2) + "|")
    lines.append("+" + "=" * width + "+")

    # Appearance section
    lines.append("|  " + "APPEARANCE".ljust(width - 2) + "|")
    lines.append("|  " + "-" * 10 + " " * (width - 12) + "|")

    hair_eyes = f"Hair: {appearance.hair_color:<14}Eyes: {appearance.eye_color}"
    lines.append("|  " + hair_eyes.ljust(width - 2) + "|")

    height_str = cm_to_feet_inches(appearance.height_cm)
    height_weight = (
        f"Height: {height_str} ({appearance.height_cm}cm)  "
        f"Weight: {kg_to_lbs(appearance.weight_kg)} lbs ({appearance.weight_kg}kg)"
    )
    lines.append("|  " + height_weight.ljust(width - 2) + "|")
    lines.append("+" + "=" * width + "+")

    # Equipment section
    lines.append("|  " + "EQUIPMENT".ljust(width - 2) + "|")
    lines.append("|  " + "-" * 9 + " " * (width - 11) + "|")

    if weapon:
        equip, stats = weapon
        weapon_line = f"[Weapon] {equip.name}"
        lines.append("|  " + weapon_line.ljust(width - 2) + "|")

        two_handed = ", Two-handed" if stats.two_handed else ""
        damage_line = f"         Damage: {stats.damage} ({stats.damage_type.title()}){two_handed}"
        lines.append("|  " + damage_line.ljust(width - 2) + "|")
        lines.append("|" + " " * width + "|")

    if armor:
        equip, stats = armor
        armor_line = f"[Armor]  {equip.name}"
        lines.append("|  " + armor_line.ljust(width - 2) + "|")

        defense_line = f"         Defense: {stats.defense} ({stats.armor_type.title()})"
        lines.append("|  " + defense_line.ljust(width - 2) + "|")

    lines.append("+" + "=" * width + "+")

    return "\n".join(lines)


def main() -> None:
    """Generate and print a random character sheet."""
    parser = argparse.ArgumentParser(description="Generate a random RPG character sheet")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--race", choices=RACES, help="Character race")
    parser.add_argument("--cls", choices=CLASSES, help="Character class")
    args = parser.parse_args()

    # Set up random seed
    if args.seed is not None:
        seed = args.seed
    else:
        seed = random.randint(0, 999999)

    print(f"Seed: {seed}")
    print()

    rng = random.Random(seed)

    # Choose race and class
    race = args.race if args.race else rng.choice(RACES)
    cls = args.cls if args.cls else rng.choice(CLASSES)

    # Generate random name
    first_name = rng.choice(FIRST_NAMES[race])
    title = rng.choice(TITLES[cls])

    # Create world and registry
    world = World()
    registry = ProceduralPrefabRegistry(world, rng_seed=seed)

    # Register component types
    registry.register_component_type("Identity", Identity)
    registry.register_component_type("CharacterClass", CharacterClass)
    registry.register_component_type("Appearance", Appearance)
    registry.register_component_type("Equipment", Equipment)
    registry.register_component_type("WeaponStats", WeaponStats)
    registry.register_component_type("ArmorStats", ArmorStats)

    # Load prefabs from the prefabs directory
    prefabs_dir = os.path.join(os.path.dirname(__file__), "prefabs")
    registry.load_directory(prefabs_dir)

    # Spawn character
    character = registry.spawn("character", {
        "name": first_name,
        "title": title,
        "race": race,
        "cls": cls,
    })
    world.tick(0)

    # Get character components
    identity = character.get_component(Identity)
    char_class = character.get_component(CharacterClass)
    appearance = character.get_component(Appearance)

    # Get equipment
    weapon = None
    equipped = list(get_children(character, HasEquipped))
    if equipped:
        weapon_entity = equipped[0]
        weapon = (
            weapon_entity.get_component(Equipment),
            weapon_entity.get_component(WeaponStats),
        )

    armor = None
    wearing = list(get_children(character, IsWearing))
    if wearing:
        armor_entity = wearing[0]
        armor = (
            armor_entity.get_component(Equipment),
            armor_entity.get_component(ArmorStats),
        )

    # Print character sheet
    sheet = format_character_sheet(identity, char_class, appearance, weapon, armor)
    print(sheet)


if __name__ == "__main__":
    main()
