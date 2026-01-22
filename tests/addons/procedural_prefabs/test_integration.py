"""Integration tests for procedural prefabs addon."""

import json
import os
import random
import tempfile

import pytest
import pydantic.dataclasses

from relics import World
from relics.types import Component

from relics.addons.procedural_prefabs import (
    ProceduralPrefabRegistry,
    HasEquipped,
    IsWearing,
    HasAttached,
    create_cascade_observer,
    get_children,
    get_holder,
    get_root,
    destroy_with_children,
)


# Test components
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int


@pydantic.dataclasses.dataclass
class Damage(Component):
    value: int
    damage_type: str = "physical"


@pydantic.dataclasses.dataclass
class Armor(Component):
    value: int


@pydantic.dataclasses.dataclass
class Name(Component):
    value: str


@pydantic.dataclasses.dataclass
class Stats(Component):
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10


class TestFullCharacterGeneration:
    """Test full character generation workflow."""

    def test_spawn_character_with_equipment(self) -> None:
        """Test spawning a character with full equipment."""
        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)

        # Register component types
        registry.register_component_type("Health", Health)
        registry.register_component_type("Damage", Damage)
        registry.register_component_type("Armor", Armor)
        registry.register_component_type("Name", Name)
        registry.register_component_type("Stats", Stats)

        # Create weapon prefabs
        sword_json = {
            "name": "sword",
            "params": [],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "Steel Sword"}},
                    {"type": "Damage", "fields": {"value": 15, "damage_type": "slashing"}},
                ],
            },
        }

        axe_json = {
            "name": "axe",
            "params": [],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "Battle Axe"}},
                    {"type": "Damage", "fields": {"value": 20, "damage_type": "slashing"}},
                ],
            },
        }

        # Create armor prefab
        armor_json = {
            "name": "plate_armor",
            "params": [],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "Plate Armor"}},
                    {"type": "Armor", "fields": {"value": 15}},
                ],
            },
        }

        # Create character prefab
        character_json = {
            "name": "warrior",
            "params": [
                {"name": "name", "type": "str", "required": True},
                {"name": "race", "type": "str", "default": "human"},
            ],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "@name"}},
                    {
                        "type": "Health",
                        "fields": {"current": 150, "maximum": 150},
                        "when": {"race": "dwarf"},
                    },
                    {
                        "type": "Health",
                        "fields": {"current": 100, "maximum": 100},
                    },
                    {"type": "Stats", "fields": {}},
                ],
                "conditionals": [
                    {
                        "when": {"race": "dwarf"},
                        "derive": [
                            {"target": "constitution", "operation": "set", "value": 14},
                        ],
                        "add": [],
                    },
                ],
                "attachments": [
                    {
                        "from_list": "weapons",
                        "edge_type": "HasEquipped",
                        "slot": "main_hand",
                    },
                    {
                        "prefab": "plate_armor",
                        "edge_type": "IsWearing",
                        "slot": "chest",
                    },
                ],
                "lists": {
                    "weapons": ["sword", "axe"],
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save prefabs
            for name, data in [
                ("sword", sword_json),
                ("axe", axe_json),
                ("plate_armor", armor_json),
                ("warrior", character_json),
            ]:
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            # Load all prefabs
            registry.load_directory(tmpdir)

        # Spawn a dwarf warrior
        character = registry.spawn("warrior", {
            "name": "Gimli",
            "race": "dwarf",
        })
        world.tick(0)

        # Check character
        assert character.has_component(Name)
        assert character.get_component(Name).value == "Gimli"

        assert character.has_component(Health)
        # Dwarf should have 150 HP
        assert character.get_component(Health).current == 150

        # Check equipped weapon
        equipped = list(get_children(character, HasEquipped))
        assert len(equipped) == 1
        weapon = equipped[0]
        assert weapon.has_component(Damage)

        # Check worn armor
        wearing = list(get_children(character, IsWearing))
        assert len(wearing) == 1
        armor = wearing[0]
        assert armor.has_component(Armor)
        assert armor.get_component(Armor).value == 15

    def test_nested_attachments(self) -> None:
        """Test spawning entities with nested attachments."""
        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)

        registry.register_component_type("Name", Name)

        # Create nested prefabs
        gem_json = {
            "name": "gem",
            "params": [],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "Ruby"}},
                ],
            },
        }

        sword_json = {
            "name": "sword",
            "params": [],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "Sword"}},
                ],
                "attachments": [
                    {
                        "prefab": "gem",
                        "edge_type": "HasAttached",
                        "slot": "pommel",
                    },
                ],
            },
        }

        character_json = {
            "name": "character",
            "params": [],
            "graph": {
                "components": [
                    {"type": "Name", "fields": {"value": "Hero"}},
                ],
                "attachments": [
                    {
                        "prefab": "sword",
                        "edge_type": "HasEquipped",
                        "slot": "main_hand",
                    },
                ],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            for name, data in [
                ("gem", gem_json),
                ("sword", sword_json),
                ("character", character_json),
            ]:
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            registry.load_directory(tmpdir)

        character = registry.spawn("character")
        world.tick(0)

        # Check hierarchy
        assert character.get_component(Name).value == "Hero"

        # Character -> Sword
        swords = list(get_children(character, HasEquipped))
        assert len(swords) == 1
        sword = swords[0]
        assert sword.get_component(Name).value == "Sword"

        # Sword -> Gem
        gems = list(get_children(sword, HasAttached))
        assert len(gems) == 1
        gem = gems[0]
        assert gem.get_component(Name).value == "Ruby"

        # Verify root finding
        assert get_root(gem).id == character.id
        assert get_holder(sword).id == character.id
        assert get_holder(gem).id == sword.id


class TestCascadeDeletionIntegration:
    """Test cascade deletion with full workflow."""

    def test_cascade_delete_full_hierarchy(self) -> None:
        """Test cascade deletion of full hierarchy using destroy_with_children."""
        world = World()

        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Name", Name)

        # Create prefabs
        with tempfile.TemporaryDirectory() as tmpdir:
            gem_json = {
                "name": "gem",
                "params": [],
                "graph": {"components": [{"type": "Name", "fields": {"value": "Gem"}}]},
            }

            sword_json = {
                "name": "sword",
                "params": [],
                "graph": {
                    "components": [{"type": "Name", "fields": {"value": "Sword"}}],
                    "attachments": [
                        {"prefab": "gem", "edge_type": "HasAttached", "slot": "pommel"},
                    ],
                },
            }

            character_json = {
                "name": "character",
                "params": [],
                "graph": {
                    "components": [{"type": "Name", "fields": {"value": "Hero"}}],
                    "attachments": [
                        {"prefab": "sword", "edge_type": "HasEquipped", "slot": "hand"},
                    ],
                },
            }

            for name, data in [
                ("gem", gem_json),
                ("sword", sword_json),
                ("character", character_json),
            ]:
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            registry.load_directory(tmpdir)

        character = registry.spawn("character")
        world.tick(0)

        # Get IDs before deletion
        sword = list(get_children(character, HasEquipped))[0]
        gem = list(get_children(sword, HasAttached))[0]

        char_id = character.id
        sword_id = sword.id
        gem_id = gem.id

        # Use destroy_with_children for reliable cascade deletion
        destroy_with_children(world, character)

        # All should be gone
        assert not world.has_entity(char_id)
        assert not world.has_entity(sword_id)
        assert not world.has_entity(gem_id)


class TestDeterministicGeneration:
    """Test deterministic entity generation."""

    def test_same_seed_produces_same_results(self) -> None:
        """Test that same seed produces identical results."""
        results = []

        for _ in range(3):
            world = World()
            registry = ProceduralPrefabRegistry(world, rng_seed=42)
            registry.register_component_type("Name", Name)

            with tempfile.TemporaryDirectory() as tmpdir:
                sword_json = {
                    "name": "sword",
                    "params": [],
                    "graph": {"components": [{"type": "Name", "fields": {"value": "Sword"}}]},
                }

                axe_json = {
                    "name": "axe",
                    "params": [],
                    "graph": {"components": [{"type": "Name", "fields": {"value": "Axe"}}]},
                }

                character_json = {
                    "name": "character",
                    "params": [],
                    "graph": {
                        "components": [],
                        "attachments": [
                            {"from_list": "weapons", "edge_type": "HasEquipped", "slot": "hand"},
                        ],
                        "lists": {"weapons": ["sword", "axe"]},
                    },
                }

                for name, data in [
                    ("sword", sword_json),
                    ("axe", axe_json),
                    ("character", character_json),
                ]:
                    path = os.path.join(tmpdir, f"{name}.procprefab.json")
                    with open(path, "w") as f:
                        json.dump(data, f)

                registry.load_directory(tmpdir)

            # Spawn multiple characters
            weapon_names = []
            for _ in range(5):
                char = registry.spawn("character")
                weapon = list(get_children(char, HasEquipped))[0]
                weapon_names.append(weapon.get_component(Name).value)

            results.append(weapon_names)

        # All runs should produce identical sequences
        assert results[0] == results[1]
        assert results[1] == results[2]


class TestParamInheritanceIntegration:
    """Test parameter inheritance in complex scenarios."""

    def test_quality_inheritance(self) -> None:
        """Test quality parameter inheritance through hierarchy."""
        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Damage", Damage)

        with tempfile.TemporaryDirectory() as tmpdir:
            weapon_json = {
                "name": "weapon",
                "params": [
                    {"name": "quality", "type": "int", "default": 1},
                ],
                "graph": {
                    "components": [
                        {"type": "Damage", "fields": {"value": "@quality"}},
                    ],
                },
            }

            character_json = {
                "name": "character",
                "params": [
                    {"name": "quality", "type": "int", "default": 10},
                ],
                "graph": {
                    "components": [],
                    "attachments": [
                        {
                            "prefab": "weapon",
                            "edge_type": "HasEquipped",
                            "slot": "hand",
                            # Inherit quality from parent
                        },
                    ],
                },
            }

            for name, data in [
                ("weapon", weapon_json),
                ("character", character_json),
            ]:
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            registry.load_directory(tmpdir)

        # Spawn with high quality
        character = registry.spawn("character", {"quality": 25})
        weapon = list(get_children(character, HasEquipped))[0]

        # Weapon should inherit quality
        assert weapon.get_component(Damage).value == 25

    def test_selective_inheritance(self) -> None:
        """Test selective parameter inheritance."""
        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Damage", Damage)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            weapon_json = {
                "name": "weapon",
                "params": [
                    {"name": "quality", "type": "int", "default": 1},
                    {"name": "prefix", "type": "str", "default": ""},
                ],
                "graph": {
                    "components": [
                        {"type": "Damage", "fields": {"value": "@quality"}},
                    ],
                },
            }

            character_json = {
                "name": "character",
                "params": [
                    {"name": "quality", "type": "int", "default": 10},
                    {"name": "prefix", "type": "str", "default": "Epic"},
                ],
                "graph": {
                    "components": [],
                    "attachments": [
                        {
                            "prefab": "weapon",
                            "edge_type": "HasEquipped",
                            "slot": "hand",
                            "inherit_params": ["quality"],  # Only inherit quality
                        },
                    ],
                },
            }

            for name, data in [
                ("weapon", weapon_json),
                ("character", character_json),
            ]:
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            registry.load_directory(tmpdir)

        character = registry.spawn("character", {"quality": 30, "prefix": "Legendary"})
        weapon = list(get_children(character, HasEquipped))[0]

        # Quality should be inherited
        assert weapon.get_component(Damage).value == 30


class TestConditionalComponentsIntegration:
    """Test conditional components in full workflow."""

    def test_race_based_stats(self) -> None:
        """Test race-based stat modifications."""
        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Stats", Stats)

        with tempfile.TemporaryDirectory() as tmpdir:
            character_json = {
                "name": "character",
                "params": [
                    {"name": "race", "type": "str", "required": True},
                ],
                "graph": {
                    "components": [
                        {
                            "type": "Health",
                            "fields": {"current": 150, "maximum": 150},
                            "when": {"race": "dwarf"},
                        },
                        {
                            "type": "Health",
                            "fields": {"current": 80, "maximum": 80},
                            "when": {"race": "elf"},
                        },
                        {
                            "type": "Health",
                            "fields": {"current": 100, "maximum": 100},
                        },
                        {"type": "Stats", "fields": {}},
                    ],
                    "conditionals": [
                        {
                            "when": {"race": "dwarf"},
                            "add": [],
                            "derive": [],
                        },
                        {
                            "when": {"race": "elf"},
                            "add": [],
                            "derive": [],
                        },
                    ],
                },
            }

            path = os.path.join(tmpdir, "character.procprefab.json")
            with open(path, "w") as f:
                json.dump(character_json, f)

            registry.load_directory(tmpdir)

        # Spawn different races
        dwarf = registry.spawn("character", {"race": "dwarf"})
        elf = registry.spawn("character", {"race": "elf"})
        human = registry.spawn("character", {"race": "human"})

        # Check health based on race
        assert dwarf.get_component(Health).current == 150
        assert elf.get_component(Health).current == 80
        assert human.get_component(Health).current == 100  # Default
