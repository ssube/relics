"""Tests for PrefabSpawner."""

import random

import pydantic.dataclasses
import pytest

from relics import World
from relics.addons.procedural_prefabs.context import GenerationContext
from relics.addons.procedural_prefabs.edges import HasAttached, HasEquipped
from relics.addons.procedural_prefabs.exceptions import (
    AttachmentSelectionError,
    CyclicAttachmentError,
    ParamValidationError,
    PrefabListNotFoundError,
    ProcPrefabNotFoundError,
)
from relics.addons.procedural_prefabs.prefab import (
    AttachmentDefinition,
    ComponentVariant,
    GraphDefinition,
    ParamDefinition,
    ProceduralPrefab,
)
from relics.addons.procedural_prefabs.spawner import PrefabSpawner
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


# Test registry
TEST_REGISTRY = {
    "Health": Health,
    "Damage": Damage,
    "Name": Name,
}


class TestPrefabSpawnerBasics:
    """Tests for basic spawner operations."""

    def test_spawn_simple_prefab(self) -> None:
        """Test spawning a simple prefab."""
        world = World()
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

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        entity = spawner.spawn("test")
        assert entity is not None
        assert entity.has_component(Health)
        assert entity.get_component(Health).current == 100

    def test_spawn_with_params(self) -> None:
        """Test spawning with parameters."""
        world = World()
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

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        entity = spawner.spawn("test", params={"hp": 200})
        assert entity.get_component(Health).current == 200
        assert entity.get_component(Health).maximum == 200

    def test_spawn_nonexistent_prefab(self) -> None:
        """Test spawning a nonexistent prefab raises error."""
        world = World()
        spawner = PrefabSpawner(
            registry={},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(ProcPrefabNotFoundError):
            spawner.spawn("nonexistent")


class TestPrefabSpawnerParamValidation:
    """Tests for parameter validation."""

    def test_required_param_missing(self) -> None:
        """Test that missing required param raises error."""
        world = World()
        prefab = ProceduralPrefab(
            name="test",
            params=[ParamDefinition(name="race", required=True)],
            graph=GraphDefinition(components=[]),
        )

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(ParamValidationError, match="Required parameter"):
            spawner.spawn("test")

    def test_required_param_provided(self) -> None:
        """Test that providing required param succeeds."""
        world = World()
        prefab = ProceduralPrefab(
            name="test",
            params=[ParamDefinition(name="race", required=True)],
            graph=GraphDefinition(components=[]),
        )

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        entity = spawner.spawn("test", params={"race": "elf"})
        assert entity is not None

    def test_default_param_applied(self) -> None:
        """Test that default param is applied when not provided."""
        world = World()
        prefab = ProceduralPrefab(
            name="test",
            params=[ParamDefinition(name="level", default=1)],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Damage",
                        fields={"value": "@level"},
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        entity = spawner.spawn("test")
        assert entity.get_component(Damage).value == 1

    def test_invalid_param_value(self) -> None:
        """Test that invalid param value raises error."""
        world = World()
        prefab = ProceduralPrefab(
            name="test",
            params=[
                ParamDefinition(
                    name="race",
                    allowed_values=["human", "elf", "dwarf"],
                )
            ],
            graph=GraphDefinition(components=[]),
        )

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(ParamValidationError, match="not in allowed"):
            spawner.spawn("test", params={"race": "orc"})


class TestPrefabSpawnerAttachments:
    """Tests for attachment spawning."""

    def test_spawn_static_attachment(self) -> None:
        """Test spawning with a static attachment."""
        world = World()

        weapon_prefab = ProceduralPrefab(
            name="sword",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Damage",
                        fields={"value": 10},
                    ),
                ],
            ),
        )

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": 100, "maximum": 100},
                    ),
                ],
                attachments=[
                    AttachmentDefinition(
                        prefab="sword",
                        edge_type="HasEquipped",
                        slot="main_hand",
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"sword": weapon_prefab, "character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        character = spawner.spawn("character")

        # Check character
        assert character.has_component(Health)

        # Check attachment relationship
        relationships = character.get_relationships(HasEquipped)
        assert len(relationships) == 1

        edge, target_id = relationships[0]
        assert edge.slot == "main_hand"

        # Check attached entity
        weapon = world.get_entity(target_id)
        assert weapon.has_component(Damage)
        assert weapon.get_component(Damage).value == 10

    def test_spawn_attachment_from_list(self) -> None:
        """Test spawning attachment from a list."""
        world = World()
        rng = random.Random(42)

        sword_prefab = ProceduralPrefab(
            name="sword",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Name",
                        fields={"value": "sword"},
                    ),
                ],
            ),
        )

        axe_prefab = ProceduralPrefab(
            name="axe",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Name",
                        fields={"value": "axe"},
                    ),
                ],
            ),
        )

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        from_list="weapons",
                        edge_type="HasEquipped",
                        slot="main_hand",
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={
                "sword": sword_prefab,
                "axe": axe_prefab,
                "character": character_prefab,
            },
            prefab_lists={"weapons": ["sword", "axe"]},
            world=world,
            component_registry=TEST_REGISTRY,
            rng=rng,
        )

        character = spawner.spawn("character")
        relationships = character.get_relationships(HasEquipped)
        assert len(relationships) == 1

    def test_spawn_attachment_skip(self) -> None:
        """Test skipping an attachment."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": 100, "maximum": 100},
                    ),
                ],
                attachments=[
                    AttachmentDefinition(skip=True, slot="main_hand"),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        character = spawner.spawn("character")
        relationships = character.get_relationships(HasEquipped)
        assert len(relationships) == 0

    def test_spawn_optional_attachment_missing(self) -> None:
        """Test optional attachment with missing list."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        from_list="nonexistent",
                        optional=True,
                        slot="hand",
                    ),
                ],
                lists={"nonexistent": []},  # Empty list
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        character = spawner.spawn("character")
        relationships = character.get_relationships(HasAttached)
        assert len(relationships) == 0

    def test_spawn_nonoptional_attachment_fails(self) -> None:
        """Test non-optional attachment with empty list fails."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        from_list="empty_list",
                        optional=False,
                        slot="hand",
                    ),
                ],
                lists={"empty_list": []},
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(AttachmentSelectionError, match="No prefab resolved"):
            spawner.spawn("character")

    def test_attachment_list_not_found(self) -> None:
        """Test attachment from non-existent list raises error."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        from_list="nonexistent",
                        slot="hand",
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(PrefabListNotFoundError):
            spawner.spawn("character")


class TestPrefabSpawnerParamInheritance:
    """Tests for parameter inheritance in attachments."""

    def test_inherit_all_params(self) -> None:
        """Test inheriting all params to child."""
        world = World()

        weapon_prefab = ProceduralPrefab(
            name="weapon",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Damage",
                        fields={"value": "@quality"},
                    ),
                ],
            ),
        )

        character_prefab = ProceduralPrefab(
            name="character",
            params=[ParamDefinition(name="quality", default=10)],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        prefab="weapon",
                        slot="hand",
                        # inherit_params=None means inherit all
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"weapon": weapon_prefab, "character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        character = spawner.spawn("character", params={"quality": 15})
        relationships = character.get_relationships(HasAttached)
        assert len(relationships) == 1

        _, weapon_id = relationships[0]
        weapon = world.get_entity(weapon_id)
        assert weapon.get_component(Damage).value == 15

    def test_inherit_specific_params(self) -> None:
        """Test inheriting specific params to child."""
        world = World()

        weapon_prefab = ProceduralPrefab(
            name="weapon",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Damage",
                        fields={"value": "@quality"},
                    ),
                ],
            ),
        )

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        prefab="weapon",
                        slot="hand",
                        inherit_params=["quality"],
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"weapon": weapon_prefab, "character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        character = spawner.spawn(
            "character",
            params={"quality": 20, "other": "ignored"},
        )
        relationships = character.get_relationships(HasAttached)
        _, weapon_id = relationships[0]
        weapon = world.get_entity(weapon_id)
        assert weapon.get_component(Damage).value == 20

    def test_override_params(self) -> None:
        """Test overriding params in child."""
        world = World()

        weapon_prefab = ProceduralPrefab(
            name="weapon",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Damage",
                        fields={"value": "@damage"},
                    ),
                ],
            ),
        )

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        prefab="weapon",
                        slot="hand",
                        override_params={"damage": 99},
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"weapon": weapon_prefab, "character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        character = spawner.spawn("character")
        relationships = character.get_relationships(HasAttached)
        _, weapon_id = relationships[0]
        weapon = world.get_entity(weapon_id)
        assert weapon.get_component(Damage).value == 99


class TestPrefabSpawnerCycleDetection:
    """Tests for cyclic attachment detection."""

    def test_direct_cycle_detection(self) -> None:
        """Test direct cycle detection (A -> A)."""
        world = World()

        recursive_prefab = ProceduralPrefab(
            name="recursive",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(prefab="recursive", slot="self"),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"recursive": recursive_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(CyclicAttachmentError):
            spawner.spawn("recursive")

    def test_indirect_cycle_detection(self) -> None:
        """Test indirect cycle detection (A -> B -> A)."""
        world = World()

        prefab_a = ProceduralPrefab(
            name="a",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(prefab="b", slot="to_b"),
                ],
            ),
        )

        prefab_b = ProceduralPrefab(
            name="b",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(prefab="a", slot="to_a"),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"a": prefab_a, "b": prefab_b},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        with pytest.raises(CyclicAttachmentError):
            spawner.spawn("a")


class TestPrefabSpawnerContextMerging:
    """Tests for context and params merging."""

    def test_spawn_with_existing_context_and_params(self) -> None:
        """Test that params are merged into existing context."""
        world = World()
        prefab = ProceduralPrefab(
            name="test",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": "@hp", "maximum": "@max_hp"},
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        # Create a context with some params
        existing_context = GenerationContext(params={"hp": 50})

        # Spawn with existing context AND additional params
        entity = spawner.spawn("test", params={"max_hp": 100}, context=existing_context)

        # Both params should be available
        health = entity.get_component(Health)
        assert health.current == 50  # From existing context
        assert health.maximum == 100  # From additional params

    def test_spawn_with_context_params_override(self) -> None:
        """Test that params override existing context params."""
        world = World()
        prefab = ProceduralPrefab(
            name="test",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(
                        component_type="Health",
                        fields={"current": "@hp", "maximum": "@hp"},
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"test": prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        # Create a context with hp=50
        existing_context = GenerationContext(params={"hp": 50})

        # Spawn with same param but different value
        entity = spawner.spawn("test", params={"hp": 200}, context=existing_context)

        # New params should override
        health = entity.get_component(Health)
        assert health.current == 200
        assert health.maximum == 200


class TestPrefabSpawnerAttachmentResolution:
    """Tests for attachment prefab resolution edge cases."""

    def test_attachment_from_list_with_none_resolution(self) -> None:
        """Test attachment from_list when list name resolves to None."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        from_list="@missing_param",  # doesn't exist
                        optional=True,
                        slot="hand",
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        # Spawn without providing the param - list name resolves to None
        character = spawner.spawn("character")
        relationships = character.get_relationships(HasAttached)
        assert len(relationships) == 0  # Optional attachment skipped

    def test_attachment_skip_flag(self) -> None:
        """Test attachment with skip flag set."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        skip=True,  # Skip this attachment
                        slot="hand",
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        # Should skip the attachment
        character = spawner.spawn("character")
        relationships = character.get_relationships(HasAttached)
        assert len(relationships) == 0

    def test_attachment_prefab_resolves_to_none(self) -> None:
        """Test attachment when static prefab reference resolves to None."""
        world = World()

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(
                        prefab="@missing_param",  # param that doesn't exist
                        optional=True,
                        slot="hand",
                    ),
                ],
            ),
        )

        spawner = PrefabSpawner(
            registry={"character": character_prefab},
            prefab_lists={},
            world=world,
            component_registry=TEST_REGISTRY,
        )

        # Without the param, prefab resolves to None
        character = spawner.spawn("character")
        relationships = character.get_relationships(HasAttached)
        assert len(relationships) == 0


class TestPrefabSpawnerDeterminism:
    """Tests for deterministic spawning."""

    def test_seeded_rng_produces_same_results(self) -> None:
        """Test that seeded RNG produces deterministic results."""
        sword_prefab = ProceduralPrefab(
            name="sword",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(component_type="Name", fields={"value": "sword"})
                ],
            ),
        )

        axe_prefab = ProceduralPrefab(
            name="axe",
            params=[],
            graph=GraphDefinition(
                components=[
                    ComponentVariant(component_type="Name", fields={"value": "axe"})
                ],
            ),
        )

        character_prefab = ProceduralPrefab(
            name="character",
            params=[],
            graph=GraphDefinition(
                components=[],
                attachments=[
                    AttachmentDefinition(from_list="weapons", slot="hand"),
                ],
            ),
        )

        results = []
        for _ in range(2):
            world = World()
            rng = random.Random(42)  # Same seed each time

            spawner = PrefabSpawner(
                registry={
                    "sword": sword_prefab,
                    "axe": axe_prefab,
                    "character": character_prefab,
                },
                prefab_lists={"weapons": ["sword", "axe"]},
                world=world,
                component_registry=TEST_REGISTRY,
                rng=rng,
            )

            character = spawner.spawn("character")
            relationships = character.get_relationships(HasAttached)
            _, weapon_id = relationships[0]
            weapon = world.get_entity(weapon_id)
            results.append(weapon.get_component(Name).value)

        # Same seed should produce same weapon selection
        assert results[0] == results[1]
