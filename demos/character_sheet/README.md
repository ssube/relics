# Character Sheet Demo

This demo showcases the procedural prefabs addon by generating randomized RPG characters with equipment and printing formatted character sheets to stdout.

## Features

- Procedural character generation with race and class parameters
- Race-based appearance variations (height, weight, hair/eye colors)
- Class-based equipment selection (weapons and armor)
- Random name generation from race-specific name pools
- Formatted ASCII character sheet output
- Deterministic generation with seed support

## Usage

```bash
# Run with random seed
python demos/character_sheet/main.py

# Run with specific seed for reproducibility
python demos/character_sheet/main.py --seed 42

# Run with specific race and class
python demos/character_sheet/main.py --race dwarf --cls warrior

# Combine options
python demos/character_sheet/main.py --seed 123 --race elf --cls ranger
```

## Available Races

- **Human**: Average build, versatile
- **Elf**: Tall and slender, silver hair
- **Dwarf**: Short and stocky, red hair
- **Orc**: Tall and muscular, dark features

## Available Classes

- **Warrior**: Heavy armor, swords and axes
- **Ranger**: Medium armor, bows and swords
- **Mage**: Robes, staves (currently swords)
- **Rogue**: Light armor, swords and bows

## Example Output

```
Seed: 42

+============================================================+
|                     CHARACTER SHEET                        |
+============================================================+
|  Name: Thorin the Bold                                     |
|  Race: Dwarf           Class: Warrior                      |
+============================================================+
|  APPEARANCE                                                |
|  ----------                                                |
|  Hair: Red             Eyes: Brown                         |
|  Height: 4'2" (127cm)  Weight: 165 lbs (75kg)              |
+============================================================+
|  EQUIPMENT                                                 |
|  ---------                                                 |
|  [Weapon] Iron Sword                                       |
|           Damage: 8 (Slashing)                             |
|                                                            |
|  [Armor]  Plate Armor                                      |
|           Defense: 18 (Heavy)                              |
+============================================================+
```

## Procedural Prefab Structure

The demo uses the following prefab files:

- `character.procprefab.json` - Main character template with conditionals
- `sword.procprefab.json` - Sword weapon variants
- `axe.procprefab.json` - Axe weapon variants
- `bow.procprefab.json` - Bow weapon variants
- `armor.procprefab.json` - Heavy/medium/light armor
- `clothing.procprefab.json` - Robes and light clothing

## Components

- `Identity` - Character name and title
- `CharacterClass` - Race and class information
- `Appearance` - Physical attributes
- `Equipment` - Item name, type, material, quality
- `WeaponStats` - Damage and damage type
- `ArmorStats` - Defense and armor type
