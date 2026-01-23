"""Performance tests for procedural prefabs addon."""

import json
import os
import random
import tempfile
import time

import pydantic.dataclasses

from relics import World
from relics.addons.procedural_prefabs import (
    HasEquipped,
    ProceduralPrefabRegistry,
    destroy_with_children,
    get_children,
)
from relics.types import Component


# Test components
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int


@pydantic.dataclasses.dataclass
class Damage(Component):
    value: int


@pydantic.dataclasses.dataclass
class Name(Component):
    value: str


class TestSpawnPerformance:
    """Performance tests for entity spawning."""

    def test_spawn_simple_entities(self) -> None:
        """Test spawning many simple entities."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            prefab_json = {
                "name": "simple",
                "params": [],
                "graph": {
                    "components": [
                        {"type": "Health", "fields": {"current": 100, "maximum": 100}},
                        {"type": "Name", "fields": {"value": "Entity"}},
                    ],
                },
            }

            path = os.path.join(tmpdir, "simple.procprefab.json")
            with open(path, "w") as f:
                json.dump(prefab_json, f)

            registry.load(path)

        # Spawn 1000 simple entities
        count = 1000
        start = time.perf_counter()

        for _ in range(count):
            registry.spawn("simple")

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nSpawn {count} simple entities: {elapsed:.3f}ms")
        print(f"Average per entity: {elapsed/count:.3f}ms")

        # Generous threshold for CI
        assert elapsed < 5000, f"Spawning {count} entities took {elapsed:.3f}ms"

    def test_spawn_with_params(self) -> None:
        """Test spawning entities with parameters."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            prefab_json = {
                "name": "parameterized",
                "params": [
                    {"name": "hp", "type": "int", "default": 100},
                    {"name": "name", "type": "str", "default": "Entity"},
                ],
                "graph": {
                    "components": [
                        {
                            "type": "Health",
                            "fields": {"current": "@hp", "maximum": "@hp"},
                        },
                        {"type": "Name", "fields": {"value": "@name"}},
                    ],
                },
            }

            path = os.path.join(tmpdir, "parameterized.procprefab.json")
            with open(path, "w") as f:
                json.dump(prefab_json, f)

            registry.load(path)

        count = 1000
        start = time.perf_counter()

        for i in range(count):
            registry.spawn(
                "parameterized",
                {
                    "hp": 100 + i,
                    "name": f"Entity_{i}",
                },
            )

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nSpawn {count} parameterized entities: {elapsed:.3f}ms")
        print(f"Average per entity: {elapsed/count:.3f}ms")

        assert elapsed < 5000, f"Spawning {count} entities took {elapsed:.3f}ms"

    def test_spawn_with_attachments(self) -> None:
        """Test spawning entities with attachments."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Damage", Damage)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            weapon_json = {
                "name": "weapon",
                "params": [],
                "graph": {
                    "components": [
                        {"type": "Damage", "fields": {"value": 10}},
                    ],
                },
            }

            armor_json = {
                "name": "armor",
                "params": [],
                "graph": {
                    "components": [
                        {"type": "Name", "fields": {"value": "Armor"}},
                    ],
                },
            }

            character_json = {
                "name": "character",
                "params": [],
                "graph": {
                    "components": [
                        {"type": "Health", "fields": {"current": 100, "maximum": 100}},
                    ],
                    "attachments": [
                        {
                            "prefab": "weapon",
                            "edge_type": "HasEquipped",
                            "slot": "hand",
                        },
                        {
                            "prefab": "armor",
                            "edge_type": "HasEquipped",
                            "slot": "chest",
                        },
                    ],
                },
            }

            for name, data in [
                ("weapon", weapon_json),
                ("armor", armor_json),
                ("character", character_json),
            ]:
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(data, f)

            registry.load_directory(tmpdir)

        # Spawn 500 characters (each creates 3 entities)
        count = 500
        start = time.perf_counter()

        for _ in range(count):
            registry.spawn("character")

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nSpawn {count} characters with 2 attachments each: {elapsed:.3f}ms")
        print(f"Total entities: {count * 3}")
        print(f"Average per character: {elapsed/count:.3f}ms")

        assert elapsed < 10000, f"Spawning {count} characters took {elapsed:.3f}ms"

    def test_spawn_with_conditionals(self) -> None:
        """Test spawning entities with conditional components."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Damage", Damage)

        with tempfile.TemporaryDirectory() as tmpdir:
            prefab_json = {
                "name": "conditional",
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
                    ],
                    "conditionals": [
                        {
                            "when": {"race": "dwarf"},
                            "add": [{"type": "Damage", "fields": {"value": 15}}],
                            "derive": [],
                        },
                        {
                            "when": {"race": "elf"},
                            "add": [{"type": "Damage", "fields": {"value": 10}}],
                            "derive": [],
                        },
                    ],
                },
            }

            path = os.path.join(tmpdir, "conditional.procprefab.json")
            with open(path, "w") as f:
                json.dump(prefab_json, f)

            registry.load(path)

        races = ["dwarf", "elf", "human", "orc"]
        count = 1000
        start = time.perf_counter()

        for i in range(count):
            registry.spawn("conditional", {"race": races[i % len(races)]})

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nSpawn {count} entities with conditionals: {elapsed:.3f}ms")
        print(f"Average per entity: {elapsed/count:.3f}ms")

        assert elapsed < 5000, f"Spawning {count} entities took {elapsed:.3f}ms"


class TestListSelectionPerformance:
    """Performance tests for list-based attachment selection."""

    def test_random_selection_from_large_list(self) -> None:
        """Test random selection from large prefab list."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create many weapon prefabs
            weapon_names = []
            for i in range(100):
                name = f"weapon_{i}"
                weapon_names.append(name)
                weapon_json = {
                    "name": name,
                    "params": [],
                    "graph": {
                        "components": [
                            {"type": "Name", "fields": {"value": name}},
                        ],
                    },
                }
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(weapon_json, f)

            # Character that selects from list
            character_json = {
                "name": "character",
                "params": [],
                "graph": {
                    "components": [],
                    "attachments": [
                        {
                            "from_list": "weapons",
                            "edge_type": "HasEquipped",
                            "slot": "hand",
                        },
                    ],
                    "lists": {"weapons": weapon_names},
                },
            }
            path = os.path.join(tmpdir, "character.procprefab.json")
            with open(path, "w") as f:
                json.dump(character_json, f)

            registry.load_directory(tmpdir)

        count = 500
        start = time.perf_counter()

        for _ in range(count):
            registry.spawn("character")

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nSpawn {count} entities selecting from 100-item list: {elapsed:.3f}ms")
        print(f"Average per entity: {elapsed/count:.3f}ms")

        assert elapsed < 10000, f"Spawning {count} entities took {elapsed:.3f}ms"


class TestCascadeDeletionPerformance:
    """Performance tests for cascade deletion."""

    def test_cascade_delete_deep_hierarchy(self) -> None:
        """Test cascade deletion of deep hierarchies using destroy_with_children."""
        random.seed(42)

        world = World()

        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a chain of prefabs: level_0 -> level_1 -> level_2 -> level_3
            for i in range(4):
                prefab = {
                    "name": f"level_{i}",
                    "params": [],
                    "graph": {
                        "components": [
                            {"type": "Name", "fields": {"value": f"Level {i}"}},
                        ],
                    },
                }
                if i < 3:
                    prefab["graph"]["attachments"] = [
                        {
                            "prefab": f"level_{i+1}",
                            "edge_type": "HasEquipped",
                            "slot": "child",
                        },
                    ]

                path = os.path.join(tmpdir, f"level_{i}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(prefab, f)

            registry.load_directory(tmpdir)

        # Spawn hierarchies
        count = 200
        entities = []
        for _ in range(count):
            entities.append(registry.spawn("level_0"))

        world.tick(0)

        # Delete all roots using destroy_with_children for reliable cascade
        start = time.perf_counter()

        for entity in entities:
            destroy_with_children(world, entity)

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nCascade delete {count} hierarchies (4 levels each): {elapsed:.3f}ms")
        print(f"Total entities deleted: {count * 4}")
        print(f"Average per hierarchy: {elapsed/count:.3f}ms")

        assert elapsed < 10000, f"Cascade delete took {elapsed:.3f}ms"


class TestQueryPerformance:
    """Performance tests for entity queries."""

    def test_get_children_performance(self) -> None:
        """Test get_children performance with many children."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            child_json = {
                "name": "child",
                "params": [],
                "graph": {
                    "components": [
                        {"type": "Name", "fields": {"value": "Child"}},
                    ],
                },
            }

            path = os.path.join(tmpdir, "child.procprefab.json")
            with open(path, "w") as f:
                json.dump(child_json, f)

            registry.load(path)

        # Create parent with many children manually
        world.register_prefab("parent", {Name: Name(value="Parent")})
        parent = world.spawn("parent")

        num_children = 100
        for i in range(num_children):
            child = registry.spawn("child")
            parent.add_relationship(HasEquipped(slot=f"slot_{i}"), child.id)

        world.tick(0)

        # Query children many times
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            children = list(get_children(parent, HasEquipped))
            assert len(children) == num_children

        elapsed = (time.perf_counter() - start) * 1000

        print(
            f"\nGet {num_children} children x {iterations} iterations: {elapsed:.3f}ms"
        )
        print(f"Average per query: {elapsed/iterations:.3f}ms")

        assert elapsed < 5000, f"Querying children took {elapsed:.3f}ms"


class TestMemoryEfficiency:
    """Tests for memory efficiency."""

    def test_many_entities_memory(self) -> None:
        """Test spawning many entities doesn't cause issues."""
        random.seed(42)

        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Name", Name)

        with tempfile.TemporaryDirectory() as tmpdir:
            prefab_json = {
                "name": "entity",
                "params": [],
                "graph": {
                    "components": [
                        {"type": "Health", "fields": {"current": 100, "maximum": 100}},
                        {"type": "Name", "fields": {"value": "Entity"}},
                    ],
                },
            }

            path = os.path.join(tmpdir, "entity.procprefab.json")
            with open(path, "w") as f:
                json.dump(prefab_json, f)

            registry.load(path)

        # Spawn many entities
        count = 5000
        start = time.perf_counter()

        entities = []
        for _ in range(count):
            entities.append(registry.spawn("entity"))

        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nSpawn {count} entities: {elapsed:.3f}ms")

        # Verify all entities exist
        for entity in entities:
            assert world.has_entity(entity.id)

        # Generous threshold
        assert elapsed < 30000, f"Spawning {count} entities took {elapsed:.3f}ms"
