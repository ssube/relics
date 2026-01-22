"""Tests for ProceduralPrefabRegistry."""

import json
import os
import tempfile

import pytest
import pydantic.dataclasses

from relics import World
from relics.types import Component

from relics.addons.procedural_prefabs.exceptions import (
    PrefabListNotFoundError,
    ProcPrefabNotFoundError,
)
from relics.addons.procedural_prefabs.prefab import (
    ComponentVariant,
    GraphDefinition,
    ParamDefinition,
    ProceduralPrefab,
)
from relics.addons.procedural_prefabs.registry import ProceduralPrefabRegistry


# Test components
@pydantic.dataclasses.dataclass
class Health(Component):
    current: int
    maximum: int


@pydantic.dataclasses.dataclass
class Damage(Component):
    value: int


class TestProceduralPrefabRegistryBasics:
    """Tests for basic registry operations."""

    def test_create_empty_registry(self) -> None:
        """Test creating an empty registry."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        assert registry.list_prefabs() == []

    def test_register_prefab(self) -> None:
        """Test registering a prefab."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        prefab = ProceduralPrefab(
            name="test",
            params=[],
            graph=GraphDefinition(components=[]),
        )
        registry.register(prefab)

        assert registry.has("test")
        assert registry.get("test") is prefab

    def test_get_nonexistent_prefab(self) -> None:
        """Test getting a nonexistent prefab raises error."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        with pytest.raises(ProcPrefabNotFoundError):
            registry.get("nonexistent")

    def test_has_prefab(self) -> None:
        """Test has method."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        assert not registry.has("test")

        prefab = ProceduralPrefab(
            name="test",
            params=[],
            graph=GraphDefinition(components=[]),
        )
        registry.register(prefab)

        assert registry.has("test")

    def test_list_prefabs(self) -> None:
        """Test listing prefabs."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        prefab1 = ProceduralPrefab(
            name="test1",
            params=[],
            graph=GraphDefinition(components=[]),
        )
        prefab2 = ProceduralPrefab(
            name="test2",
            params=[],
            graph=GraphDefinition(components=[]),
        )
        registry.register(prefab1)
        registry.register(prefab2)

        prefabs = registry.list_prefabs()
        assert "test1" in prefabs
        assert "test2" in prefabs


class TestProceduralPrefabRegistryLists:
    """Tests for prefab list operations."""

    def test_register_list(self) -> None:
        """Test registering a prefab list."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        registry.register_list("weapons", ["sword", "axe", "mace"])

        assert registry.has_list("weapons")
        assert registry.get_list("weapons") == ["sword", "axe", "mace"]

    def test_get_nonexistent_list(self) -> None:
        """Test getting a nonexistent list raises error."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        with pytest.raises(PrefabListNotFoundError):
            registry.get_list("nonexistent")

    def test_has_list(self) -> None:
        """Test has_list method."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        assert not registry.has_list("weapons")
        registry.register_list("weapons", ["sword"])
        assert registry.has_list("weapons")

    def test_list_prefab_lists(self) -> None:
        """Test listing prefab lists."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        registry.register_list("weapons", ["sword"])
        registry.register_list("armor", ["plate"])

        lists = registry.list_prefab_lists()
        assert "weapons" in lists
        assert "armor" in lists


class TestProceduralPrefabRegistryComponentTypes:
    """Tests for component type registration."""

    def test_register_component_type(self) -> None:
        """Test registering a component type."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        registry.register_component_type("Health", Health)
        registry.register_component_type("Damage", Damage)

        # Should be able to spawn a prefab using these types
        prefab = ProceduralPrefab(
            name="test",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": 100, "maximum": 100},
                    ),
                ],
            ),
        )
        registry.register(prefab)

        entity = registry.spawn("test")
        assert entity.has_component(Health)


class TestProceduralPrefabRegistrySpawning:
    """Tests for spawning through the registry."""

    def test_spawn_simple(self) -> None:
        """Test spawning a simple prefab."""
        world = World()
        registry = ProceduralPrefabRegistry(world, rng_seed=42)
        registry.register_component_type("Health", Health)

        prefab = ProceduralPrefab(
            name="test",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": 100, "maximum": 100},
                    ),
                ],
            ),
        )
        registry.register(prefab)

        entity = registry.spawn("test")
        assert entity.has_component(Health)
        assert entity.get_component(Health).current == 100

    def test_spawn_with_params(self) -> None:
        """Test spawning with parameters."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        registry.register_component_type("Health", Health)

        prefab = ProceduralPrefab(
            name="test",
            params=[ParamDefinition(name="hp")],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": "@hp", "maximum": "@hp"},
                    ),
                ],
            ),
        )
        registry.register(prefab)

        entity = registry.spawn("test", {"hp": 200})
        assert entity.get_component(Health).current == 200

    def test_set_seed(self) -> None:
        """Test setting RNG seed."""
        world = World()
        registry = ProceduralPrefabRegistry(world)

        registry.set_seed(42)

        # Should not raise any errors
        assert True


class TestProceduralPrefabRegistryJSONLoading:
    """Tests for JSON file loading."""

    def test_load_simple_prefab(self) -> None:
        """Test loading a simple prefab from JSON."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        registry.register_component_type("Health", Health)

        prefab_json = {
            "name": "character",
            "params": [
                {"name": "hp", "type": "int", "default": 100},
            ],
            "graph": {
                "components": [
                    {
                        "type": "Health",
                        "fields": {"current": "@hp", "maximum": "@hp"},
                    },
                ],
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".procprefab.json",
            delete=False,
        ) as f:
            json.dump(prefab_json, f)
            f.flush()
            temp_path = f.name

        try:
            registry.load(temp_path)

            assert registry.has("character")
            prefab = registry.get("character")
            assert prefab.name == "character"
            assert len(prefab.params) == 1
            assert prefab.params[0].name == "hp"
            assert prefab.params[0].default == 100
        finally:
            os.unlink(temp_path)

    def test_load_prefab_with_conditionals(self) -> None:
        """Test loading a prefab with conditionals."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        registry.register_component_type("Health", Health)
        registry.register_component_type("Damage", Damage)

        prefab_json = {
            "name": "character",
            "params": [
                {"name": "class", "type": "str", "required": True},
            ],
            "graph": {
                "components": [
                    {
                        "type": "Health",
                        "fields": {"current": 100, "maximum": 100},
                    },
                ],
                "conditionals": [
                    {
                        "when": {"class": "warrior"},
                        "add": [
                            {"type": "Damage", "fields": {"value": 20}},
                        ],
                        "derive": [
                            {"target": "strength", "operation": "set", "value": 10},
                        ],
                    },
                ],
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".procprefab.json",
            delete=False,
        ) as f:
            json.dump(prefab_json, f)
            f.flush()
            temp_path = f.name

        try:
            registry.load(temp_path)
            prefab = registry.get("character")

            assert prefab.graph.conditionals is not None
            assert len(prefab.graph.conditionals) == 1

            cond = prefab.graph.conditionals[0]
            assert cond.when.conditions == {"class": "warrior"}
            assert len(cond.add) == 1
            assert len(cond.derive) == 1
        finally:
            os.unlink(temp_path)

    def test_load_prefab_with_attachments(self) -> None:
        """Test loading a prefab with attachments."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        registry.register_component_type("Health", Health)

        prefab_json = {
            "name": "character",
            "params": [],
            "graph": {
                "components": [],
                "attachments": [
                    {
                        "prefab": "sword",
                        "edge_type": "HasEquipped",
                        "slot": "main_hand",
                        "optional": True,
                    },
                    {
                        "from_list": "armors",
                        "slot": "chest",
                    },
                ],
                "lists": {
                    "armors": ["plate", "leather", "cloth"],
                },
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".procprefab.json",
            delete=False,
        ) as f:
            json.dump(prefab_json, f)
            f.flush()
            temp_path = f.name

        try:
            registry.load(temp_path)
            prefab = registry.get("character")

            assert prefab.graph.attachments is not None
            assert len(prefab.graph.attachments) == 2

            att1 = prefab.graph.attachments[0]
            assert att1.prefab == "sword"
            assert att1.edge_type == "HasEquipped"
            assert att1.slot == "main_hand"
            assert att1.optional is True

            att2 = prefab.graph.attachments[1]
            assert att2.from_list == "armors"

            assert prefab.graph.lists == {"armors": ["plate", "leather", "cloth"]}
        finally:
            os.unlink(temp_path)

    def test_load_directory(self) -> None:
        """Test loading all prefabs from a directory."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        registry.register_component_type("Health", Health)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple prefab files
            for name in ["prefab1", "prefab2", "prefab3"]:
                prefab_json = {
                    "name": name,
                    "params": [],
                    "graph": {"components": []},
                }
                path = os.path.join(tmpdir, f"{name}.procprefab.json")
                with open(path, "w") as f:
                    json.dump(prefab_json, f)

            # Also create a non-prefab file that should be ignored
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("This is not a prefab")

            count = registry.load_directory(tmpdir)

            assert count == 3
            assert registry.has("prefab1")
            assert registry.has("prefab2")
            assert registry.has("prefab3")

    def test_load_prefab_with_when_clause(self) -> None:
        """Test loading a prefab with component when clauses."""
        world = World()
        registry = ProceduralPrefabRegistry(world)
        registry.register_component_type("Health", Health)

        prefab_json = {
            "name": "character",
            "params": [{"name": "race", "type": "str"}],
            "graph": {
                "components": [
                    {
                        "type": "Health",
                        "fields": {"current": 150, "maximum": 150},
                        "when": {"race": "dwarf"},
                    },
                    {
                        "type": "Health",
                        "fields": {"current": 100, "maximum": 100},
                    },
                ],
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".procprefab.json",
            delete=False,
        ) as f:
            json.dump(prefab_json, f)
            f.flush()
            temp_path = f.name

        try:
            registry.load(temp_path)
            prefab = registry.get("character")

            # First variant has when clause
            assert prefab.graph.components[0].when is not None
            assert prefab.graph.components[0].when.conditions == {"race": "dwarf"}

            # Second variant is default
            assert prefab.graph.components[1].when is None
        finally:
            os.unlink(temp_path)
