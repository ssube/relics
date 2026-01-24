"""Comprehensive round-trip tests for world persistence.

These tests verify that world state is preserved exactly after persist/reload
cycles. Tests ensure entities, components, and relationships are deeply equal
across JSON, SQLite, and in-memory drivers.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

import pytest
from pydantic.dataclasses import dataclass

from relics import Component, Edge, World
from relics.persistence import (
    InMemoryPersistenceDriver,
    JSONPersistenceDriver,
    SQLitePersistenceDriver,
)
from relics.types import EntityId


# =============================================================================
# Test Components
# =============================================================================


@dataclass
class Position(Component):
    """Test component for position with float fields."""

    x: float
    y: float


@dataclass
class Health(Component):
    """Test component for health with int fields."""

    current: int
    maximum: int


@dataclass
class Inventory(Component):
    """Test component with list field."""

    items: List[str]
    capacity: int


@dataclass
class Stats(Component):
    """Test component with dict and list fields."""

    attributes: Dict[str, int]
    modifiers: List[float]


@dataclass
class Config(Component):
    """Test component with optional and boolean fields."""

    name: str
    value: Optional[int] = None
    enabled: bool = True


@dataclass
class AllyTo(Edge):
    """Test edge type with default field value."""

    trust_level: float = 1.0


@dataclass
class OwnsItem(Edge):
    """Test edge type with required fields."""

    item_name: str
    quantity: int = 1


# =============================================================================
# Helper Functions
# =============================================================================


def get_component_fields(comp: Component) -> List[str]:
    """Get field names from a component, handling various formats.

    Args:
        comp: The component to get fields from.

    Returns:
        List of field names.
    """
    if hasattr(comp, "__pydantic_fields__"):
        return list(comp.__pydantic_fields__.keys())
    elif hasattr(comp, "model_fields"):
        return list(comp.model_fields.keys())
    elif hasattr(comp, "__dataclass_fields__"):
        return list(comp.__dataclass_fields__.keys())
    else:
        return [k for k in comp.__dict__.keys() if not k.startswith("_")]


def components_equal(comp1: Component, comp2: Component) -> bool:
    """Compare two components for deep equality.

    Args:
        comp1: First component.
        comp2: Second component.

    Returns:
        True if components are deeply equal.
    """
    if type(comp1) != type(comp2):
        return False

    fields = get_component_fields(comp1)
    for field_name in fields:
        val1 = getattr(comp1, field_name)
        val2 = getattr(comp2, field_name)

        if isinstance(val1, (list, dict)):
            if val1 != val2:
                return False
        elif val1 != val2:
            return False

    return True


def assert_worlds_equal(original: World, loaded: World) -> None:
    """Deep comparison helper that verifies world equality.

    Args:
        original: The original world.
        loaded: The loaded world.

    Raises:
        AssertionError: If worlds are not equal.
    """
    # 1. Metadata equality
    assert original.epoch == loaded.epoch, (
        f"Epoch mismatch: {original.epoch} != {loaded.epoch}"
    )

    # 2. Entity equality - same entity IDs
    original_ids: Set[EntityId] = set(original._entities.keys())
    loaded_ids: Set[EntityId] = set(loaded._entities.keys())
    assert original_ids == loaded_ids, (
        f"Entity IDs mismatch. "
        f"Missing: {original_ids - loaded_ids}, "
        f"Extra: {loaded_ids - original_ids}"
    )

    # 3. Component equality - for each entity
    for entity_id in original_ids:
        orig_components = original._entities[entity_id]
        load_components = loaded._entities[entity_id]

        # Same component types
        orig_types = set(orig_components.keys())
        load_types = set(load_components.keys())
        assert orig_types == load_types, (
            f"Component types mismatch for {entity_id}. "
            f"Missing: {orig_types - load_types}, "
            f"Extra: {load_types - orig_types}"
        )

        # Component field values match
        for comp_type in orig_types:
            orig_comp = orig_components[comp_type]
            load_comp = load_components[comp_type]
            assert components_equal(orig_comp, load_comp), (
                f"Component {comp_type.__name__} mismatch for {entity_id}. "
                f"Original: {orig_comp}, Loaded: {load_comp}"
            )

    # 4. Relationship equality
    orig_rel_sources = set(original._relationships.keys())
    load_rel_sources = set(loaded._relationships.keys())
    assert orig_rel_sources == load_rel_sources, (
        f"Relationship sources mismatch. "
        f"Missing: {orig_rel_sources - load_rel_sources}, "
        f"Extra: {load_rel_sources - orig_rel_sources}"
    )

    for source_id in orig_rel_sources:
        orig_edge_types = original._relationships[source_id]
        load_edge_types = loaded._relationships[source_id]

        # Same edge types
        orig_types = set(orig_edge_types.keys())
        load_types = set(load_edge_types.keys())
        assert orig_types == load_types, (
            f"Edge types mismatch for source {source_id}. "
            f"Missing: {orig_types - load_types}, "
            f"Extra: {load_types - orig_types}"
        )

        # Same targets and edge data
        for edge_type in orig_types:
            orig_edges = orig_edge_types[edge_type]
            load_edges = load_edge_types[edge_type]

            orig_targets = set(orig_edges.keys())
            load_targets = set(load_edges.keys())
            assert orig_targets == load_targets, (
                f"Targets mismatch for {source_id}->{edge_type.__name__}. "
                f"Missing: {orig_targets - load_targets}, "
                f"Extra: {load_targets - orig_targets}"
            )

            for target_id in orig_targets:
                orig_edge = orig_edges[target_id]
                load_edge = load_edges[target_id]
                assert components_equal(orig_edge, load_edge), (
                    f"Edge data mismatch for "
                    f"{source_id}->{edge_type.__name__}->{target_id}. "
                    f"Original: {orig_edge}, Loaded: {load_edge}"
                )

    # 5. Prefab equality
    orig_prefabs = set(original._prefabs.keys())
    load_prefabs = set(loaded._prefabs.keys())
    assert orig_prefabs == load_prefabs, (
        f"Prefab names mismatch. "
        f"Missing: {orig_prefabs - load_prefabs}, "
        f"Extra: {load_prefabs - orig_prefabs}"
    )

    for prefab_name in orig_prefabs:
        orig_components = original._prefabs[prefab_name]
        load_components = loaded._prefabs[prefab_name]

        orig_types = set(orig_components.keys())
        load_types = set(load_components.keys())
        assert orig_types == load_types, (
            f"Prefab {prefab_name} component types mismatch. "
            f"Missing: {orig_types - load_types}, "
            f"Extra: {load_types - orig_types}"
        )

        for comp_type in orig_types:
            orig_comp = orig_components[comp_type]
            load_comp = load_components[comp_type]
            assert components_equal(orig_comp, load_comp), (
                f"Prefab {prefab_name} component {comp_type.__name__} mismatch. "
                f"Original: {orig_comp}, Loaded: {load_comp}"
            )


def create_test_world() -> World:
    """Create a world with various components, entities, and relationships.

    Returns:
        A populated World instance for testing.
    """
    world = World()

    # Register prefabs with various complexity
    world.register_prefab(
        "player",
        {
            Position: Position(x=0.0, y=0.0),
            Health: Health(current=100, maximum=100),
        },
    )
    world.register_prefab(
        "item",
        {
            Position: Position(x=0.0, y=0.0),
            Config: Config(name="default_item", value=None, enabled=True),
        },
    )
    world.register_prefab(
        "container",
        {
            Position: Position(x=0.0, y=0.0),
            Inventory: Inventory(items=[], capacity=10),
        },
    )
    world.register_prefab(
        "character",
        {
            Position: Position(x=0.0, y=0.0),
            Health: Health(current=50, maximum=50),
            Stats: Stats(attributes={"str": 10, "dex": 10}, modifiers=[1.0]),
        },
    )

    # Spawn entities with overrides
    player1 = world.spawn(
        "player",
        {
            Position: Position(x=10.5, y=20.5),
            Health: Health(current=80, maximum=100),
        },
    )
    player2 = world.spawn(
        "player",
        {
            Position: Position(x=-5.0, y=15.0),
            Health: Health(current=100, maximum=100),
        },
    )

    item1 = world.spawn(
        "item",
        {
            Position: Position(x=12.0, y=22.0),
            Config: Config(name="sword", value=50, enabled=True),
        },
    )
    item2 = world.spawn(
        "item",
        {
            Position: Position(x=13.0, y=23.0),
            Config: Config(name="shield", value=30, enabled=False),
        },
    )

    container1 = world.spawn(
        "container",
        {
            Position: Position(x=0.0, y=0.0),
            Inventory: Inventory(items=["gold", "potion", "key"], capacity=20),
        },
    )

    npc = world.spawn(
        "character",
        {
            Position: Position(x=100.0, y=100.0),
            Stats: Stats(
                attributes={"str": 15, "dex": 12, "int": 8},
                modifiers=[1.5, 0.8, 1.2],
            ),
        },
    )

    # Create relationships
    player1.add_relationship(AllyTo(trust_level=0.9), player2.id)
    player2.add_relationship(AllyTo(trust_level=0.85), player1.id)
    player1.add_relationship(OwnsItem(item_name="sword", quantity=1), item1.id)
    player1.add_relationship(OwnsItem(item_name="shield", quantity=1), item2.id)
    player2.add_relationship(OwnsItem(item_name="treasure", quantity=5), container1.id)
    player1.add_relationship(AllyTo(trust_level=0.5), npc.id)

    # Advance epoch
    for _ in range(5):
        world.tick(0.016)

    return world


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def component_registry() -> Dict[str, Type[Component]]:
    """Registry of all test component types."""
    return {
        "Position": Position,
        "Health": Health,
        "Inventory": Inventory,
        "Stats": Stats,
        "Config": Config,
    }


@pytest.fixture
def edge_registry() -> Dict[str, Type[Edge]]:
    """Registry of all test edge types."""
    return {
        "AllyTo": AllyTo,
        "OwnsItem": OwnsItem,
    }


@pytest.fixture
def json_driver() -> JSONPersistenceDriver:
    """Create a JSON persistence driver."""
    return JSONPersistenceDriver()


@pytest.fixture
def sqlite_driver() -> SQLitePersistenceDriver:
    """Create a SQLite persistence driver."""
    return SQLitePersistenceDriver()


@pytest.fixture
def memory_driver() -> InMemoryPersistenceDriver:
    """Create an in-memory persistence driver."""
    return InMemoryPersistenceDriver()


# =============================================================================
# TestRoundTripJSON
# =============================================================================


class TestRoundTripJSON:
    """Tests for JSON driver round-trip equality."""

    def test_basic_entities_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test simple entity with Position is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=10.5, y=20.5)})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_entities_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test multiple entities with same prefab are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=1, y=1)})
        world.spawn("player", {Position: Position(x=2, y=2)})
        world.spawn("player", {Position: Position(x=3, y=3)})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_component_types_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test entities with various component types are preserved."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.spawn(
            "player",
            {
                Position: Position(x=5.5, y=10.5),
                Health: Health(current=75, maximum=100),
            },
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_complex_types_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test lists, dicts, nested data are preserved."""
        world = World()
        world.register_prefab(
            "character",
            {
                Stats: Stats(attributes={}, modifiers=[]),
                Inventory: Inventory(items=[], capacity=10),
            },
        )
        world.spawn(
            "character",
            {
                Stats: Stats(
                    attributes={"str": 15, "dex": 12, "int": 8},
                    modifiers=[1.5, 0.8, 1.2, 2.0],
                ),
                Inventory: Inventory(
                    items=["sword", "shield", "potion", "key"],
                    capacity=50,
                ),
            },
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_relationships_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test single relationship type is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        p1 = world.spawn("player", {Position: Position(x=1, y=1)})
        p2 = world.spawn("player", {Position: Position(x=2, y=2)})
        p1.add_relationship(AllyTo(trust_level=0.75), p2.id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_relationship_types_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test multiple edge types are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("item", {Config: Config(name="item")})
        p1 = world.spawn("player")
        p2 = world.spawn("player")
        item = world.spawn("item")
        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)
        p1.add_relationship(OwnsItem(item_name="sword", quantity=1), item.id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_bidirectional_relationships_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test A->B and B->A relationships are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        p2.add_relationship(AllyTo(trust_level=0.85), p1.id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_prefabs_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test prefab definitions are preserved."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=5.0, y=10.0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.register_prefab(
            "enemy",
            {
                Position: Position(x=0.0, y=0.0),
                Health: Health(current=50, maximum=50),
            },
        )
        world.spawn("player")
        world.spawn("enemy")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_epoch_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test world epoch is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")
        for _ in range(15):
            world.tick(0.016)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_full_world_equal(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test complete world with all features is preserved."""
        world = create_test_world()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()


# =============================================================================
# TestRoundTripSQLite
# =============================================================================


class TestRoundTripSQLite:
    """Tests for SQLite driver round-trip equality."""

    def test_basic_entities_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test simple entity with Position is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=10.5, y=20.5)})

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_entities_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test multiple entities with same prefab are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=1, y=1)})
        world.spawn("player", {Position: Position(x=2, y=2)})
        world.spawn("player", {Position: Position(x=3, y=3)})

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_component_types_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test entities with various component types are preserved."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.spawn(
            "player",
            {
                Position: Position(x=5.5, y=10.5),
                Health: Health(current=75, maximum=100),
            },
        )

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_complex_types_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test lists, dicts, nested data are preserved."""
        world = World()
        world.register_prefab(
            "character",
            {
                Stats: Stats(attributes={}, modifiers=[]),
                Inventory: Inventory(items=[], capacity=10),
            },
        )
        world.spawn(
            "character",
            {
                Stats: Stats(
                    attributes={"str": 15, "dex": 12, "int": 8},
                    modifiers=[1.5, 0.8, 1.2, 2.0],
                ),
                Inventory: Inventory(
                    items=["sword", "shield", "potion", "key"],
                    capacity=50,
                ),
            },
        )

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_relationships_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test single relationship type is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        p1 = world.spawn("player", {Position: Position(x=1, y=1)})
        p2 = world.spawn("player", {Position: Position(x=2, y=2)})
        p1.add_relationship(AllyTo(trust_level=0.75), p2.id)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_relationship_types_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test multiple edge types are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("item", {Config: Config(name="item")})
        p1 = world.spawn("player")
        p2 = world.spawn("player")
        item = world.spawn("item")
        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)
        p1.add_relationship(OwnsItem(item_name="sword", quantity=1), item.id)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_bidirectional_relationships_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test A->B and B->A relationships are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        p2.add_relationship(AllyTo(trust_level=0.85), p1.id)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_prefabs_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test prefab definitions are preserved."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=5.0, y=10.0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.register_prefab(
            "enemy",
            {
                Position: Position(x=0.0, y=0.0),
                Health: Health(current=50, maximum=50),
            },
        )
        world.spawn("player")
        world.spawn("enemy")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_epoch_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test world epoch is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")
        for _ in range(15):
            world.tick(0.016)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_full_world_equal(
        self,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test complete world with all features is preserved."""
        world = create_test_world()

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            sqlite_driver.save(world, temp_path)
            world2 = World()
            sqlite_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()


# =============================================================================
# TestRoundTripInMemory
# =============================================================================


class TestRoundTripInMemory:
    """Tests for in-memory driver round-trip equality."""

    def test_basic_entities_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test simple entity with Position is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=10.5, y=20.5)})

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry)
        assert_worlds_equal(world, world2)

    def test_multiple_entities_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test multiple entities with same prefab are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player", {Position: Position(x=1, y=1)})
        world.spawn("player", {Position: Position(x=2, y=2)})
        world.spawn("player", {Position: Position(x=3, y=3)})

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry)
        assert_worlds_equal(world, world2)

    def test_multiple_component_types_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test entities with various component types are preserved."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.spawn(
            "player",
            {
                Position: Position(x=5.5, y=10.5),
                Health: Health(current=75, maximum=100),
            },
        )

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry)
        assert_worlds_equal(world, world2)

    def test_complex_types_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test lists, dicts, nested data are preserved."""
        world = World()
        world.register_prefab(
            "character",
            {
                Stats: Stats(attributes={}, modifiers=[]),
                Inventory: Inventory(items=[], capacity=10),
            },
        )
        world.spawn(
            "character",
            {
                Stats: Stats(
                    attributes={"str": 15, "dex": 12, "int": 8},
                    modifiers=[1.5, 0.8, 1.2, 2.0],
                ),
                Inventory: Inventory(
                    items=["sword", "shield", "potion", "key"],
                    capacity=50,
                ),
            },
        )

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry)
        assert_worlds_equal(world, world2)

    def test_relationships_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test single relationship type is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        p1 = world.spawn("player", {Position: Position(x=1, y=1)})
        p2 = world.spawn("player", {Position: Position(x=2, y=2)})
        p1.add_relationship(AllyTo(trust_level=0.75), p2.id)

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry, edge_registry)
        assert_worlds_equal(world, world2)

    def test_multiple_relationship_types_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test multiple edge types are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("item", {Config: Config(name="item")})
        p1 = world.spawn("player")
        p2 = world.spawn("player")
        item = world.spawn("item")
        p1.add_relationship(AllyTo(trust_level=0.8), p2.id)
        p1.add_relationship(OwnsItem(item_name="sword", quantity=1), item.id)

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry, edge_registry)
        assert_worlds_equal(world, world2)

    def test_bidirectional_relationships_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test A->B and B->A relationships are preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        p1 = world.spawn("player")
        p2 = world.spawn("player")
        p1.add_relationship(AllyTo(trust_level=0.9), p2.id)
        p2.add_relationship(AllyTo(trust_level=0.85), p1.id)

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry, edge_registry)
        assert_worlds_equal(world, world2)

    def test_prefabs_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test prefab definitions are preserved."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=5.0, y=10.0),
                Health: Health(current=100, maximum=100),
            },
        )
        world.register_prefab(
            "enemy",
            {
                Position: Position(x=0.0, y=0.0),
                Health: Health(current=50, maximum=50),
            },
        )
        world.spawn("player")
        world.spawn("enemy")

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry)
        assert_worlds_equal(world, world2)

    def test_epoch_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test world epoch is preserved."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.spawn("player")
        for _ in range(15):
            world.tick(0.016)

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry)
        assert_worlds_equal(world, world2)

    def test_full_world_equal(
        self,
        memory_driver: InMemoryPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test complete world with all features is preserved."""
        world = create_test_world()

        memory_driver.save(world, "test")
        world2 = World()
        memory_driver.load(world2, "test", component_registry, edge_registry)
        assert_worlds_equal(world, world2)


# =============================================================================
# TestRoundTripCrossDriver
# =============================================================================


class TestRoundTripCrossDriver:
    """Tests that verify worlds can be saved with one driver and loaded correctly
    with another (where applicable)."""

    def test_json_to_sqlite_equal(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Save JSON, load into new world, save SQLite, compare."""
        world = create_test_world()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as jf:
            json_path = jf.name
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as sf:
            sqlite_path = sf.name

        try:
            # Save to JSON
            json_driver.save(world, json_path)

            # Load from JSON
            world_from_json = World()
            json_driver.load(
                world_from_json, json_path, component_registry, edge_registry
            )

            # Save to SQLite
            sqlite_driver.save(world_from_json, sqlite_path)

            # Load from SQLite
            world_from_sqlite = World()
            sqlite_driver.load(
                world_from_sqlite, sqlite_path, component_registry, edge_registry
            )

            # Compare original to final
            assert_worlds_equal(world, world_from_sqlite)
        finally:
            Path(json_path).unlink()
            Path(sqlite_path).unlink()

    def test_sqlite_to_json_equal(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Save SQLite, load into new world, save JSON, compare."""
        world = create_test_world()

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as sf:
            sqlite_path = sf.name
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as jf:
            json_path = jf.name

        try:
            # Save to SQLite
            sqlite_driver.save(world, sqlite_path)

            # Load from SQLite
            world_from_sqlite = World()
            sqlite_driver.load(
                world_from_sqlite, sqlite_path, component_registry, edge_registry
            )

            # Save to JSON
            json_driver.save(world_from_sqlite, json_path)

            # Load from JSON
            world_from_json = World()
            json_driver.load(
                world_from_json, json_path, component_registry, edge_registry
            )

            # Compare original to final
            assert_worlds_equal(world, world_from_json)
        finally:
            Path(sqlite_path).unlink()
            Path(json_path).unlink()


# =============================================================================
# TestEdgeCases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in persistence."""

    def test_empty_world(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        memory_driver: InMemoryPersistenceDriver,
    ) -> None:
        """Test world with no entities."""
        world = World()

        # JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        try:
            json_driver.save(world, json_path)
            world2 = World()
            json_driver.load(world2, json_path)
            assert_worlds_equal(world, world2)
        finally:
            Path(json_path).unlink()

        # SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            sqlite_path = f.name
        try:
            sqlite_driver.save(world, sqlite_path)
            world3 = World()
            sqlite_driver.load(world3, sqlite_path)
            assert_worlds_equal(world, world3)
        finally:
            Path(sqlite_path).unlink()

        # Memory
        memory_driver.save(world, "empty")
        world4 = World()
        memory_driver.load(world4, "empty")
        assert_worlds_equal(world, world4)

    def test_empty_lists(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test components with empty list fields."""
        world = World()
        world.register_prefab(
            "container",
            {
                Inventory: Inventory(items=[], capacity=0),
                Stats: Stats(attributes={}, modifiers=[]),
            },
        )
        world.spawn("container")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_none_optional_fields(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test optional fields set to None."""
        world = World()
        world.register_prefab("item", {Config: Config(name="test", value=None)})
        world.spawn("item", {Config: Config(name="item1", value=None, enabled=True)})
        world.spawn("item", {Config: Config(name="item2", value=42, enabled=False)})

        # JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        try:
            json_driver.save(world, json_path)
            world2 = World()
            json_driver.load(world2, json_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(json_path).unlink()

        # SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            sqlite_path = f.name
        try:
            sqlite_driver.save(world, sqlite_path)
            world3 = World()
            sqlite_driver.load(world3, sqlite_path, component_registry)
            assert_worlds_equal(world, world3)
        finally:
            Path(sqlite_path).unlink()

    def test_negative_numbers(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test negative int/float values."""
        world = World()
        world.register_prefab(
            "entity",
            {
                Position: Position(x=-100.5, y=-200.75),
                Health: Health(current=-10, maximum=-50),
            },
        )
        world.spawn(
            "entity",
            {
                Position: Position(x=-0.001, y=-999999.999),
                Health: Health(current=-1, maximum=-1),
            },
        )

        # JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        try:
            json_driver.save(world, json_path)
            world2 = World()
            json_driver.load(world2, json_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(json_path).unlink()

        # SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            sqlite_path = f.name
        try:
            sqlite_driver.save(world, sqlite_path)
            world3 = World()
            sqlite_driver.load(world3, sqlite_path, component_registry)
            assert_worlds_equal(world, world3)
        finally:
            Path(sqlite_path).unlink()

    def test_unicode_strings(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test unicode in string fields."""
        world = World()
        world.register_prefab("item", {Config: Config(name="test")})
        world.spawn("item", {Config: Config(name="Hello World!")})
        world.spawn("item", {Config: Config(name="Special chars: @#$%^&*()")})

        # JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        try:
            json_driver.save(world, json_path)
            world2 = World()
            json_driver.load(world2, json_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(json_path).unlink()

        # SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            sqlite_path = f.name
        try:
            sqlite_driver.save(world, sqlite_path)
            world3 = World()
            sqlite_driver.load(world3, sqlite_path, component_registry)
            assert_worlds_equal(world, world3)
        finally:
            Path(sqlite_path).unlink()

    def test_large_lists(
        self,
        json_driver: JSONPersistenceDriver,
        sqlite_driver: SQLitePersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test components with large list data."""
        world = World()
        large_items = [f"item_{i}" for i in range(100)]
        large_modifiers = [float(i) * 0.1 for i in range(100)]
        world.register_prefab(
            "container",
            {
                Inventory: Inventory(items=large_items, capacity=1000),
                Stats: Stats(attributes={"count": 100}, modifiers=large_modifiers),
            },
        )
        world.spawn("container")

        # JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        try:
            json_driver.save(world, json_path)
            world2 = World()
            json_driver.load(world2, json_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(json_path).unlink()

        # SQLite
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            sqlite_path = f.name
        try:
            sqlite_driver.save(world, sqlite_path)
            world3 = World()
            sqlite_driver.load(world3, sqlite_path, component_registry)
            assert_worlds_equal(world, world3)
        finally:
            Path(sqlite_path).unlink()

    def test_circular_relationships(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test A->B->C->A relationships."""
        world = World()
        world.register_prefab("node", {Position: Position(x=0, y=0)})
        a = world.spawn("node")
        b = world.spawn("node")
        c = world.spawn("node")
        a.add_relationship(AllyTo(trust_level=0.5), b.id)
        b.add_relationship(AllyTo(trust_level=0.6), c.id)
        c.add_relationship(AllyTo(trust_level=0.7), a.id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_self_referential_relationship(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test entity with relationship to itself."""
        world = World()
        world.register_prefab("entity", {Position: Position(x=0, y=0)})
        e = world.spawn("entity")
        e.add_relationship(AllyTo(trust_level=1.0), e.id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_entity_without_components(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
    ) -> None:
        """Test entity with prefab but no additional components."""
        world = World()
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )
        # Spawn without overrides - uses prefab defaults
        world.spawn("player")
        world.spawn("player")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()

    def test_multiple_relationships_same_target(
        self,
        json_driver: JSONPersistenceDriver,
        component_registry: Dict[str, Type[Component]],
        edge_registry: Dict[str, Type[Edge]],
    ) -> None:
        """Test different edge types to same target."""
        world = World()
        world.register_prefab("entity", {Position: Position(x=0, y=0)})
        a = world.spawn("entity")
        b = world.spawn("entity")

        # Multiple different edge types from a to b
        a.add_relationship(AllyTo(trust_level=0.9), b.id)
        a.add_relationship(OwnsItem(item_name="bond", quantity=1), b.id)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            json_driver.save(world, temp_path)
            world2 = World()
            json_driver.load(world2, temp_path, component_registry, edge_registry)
            assert_worlds_equal(world, world2)
        finally:
            Path(temp_path).unlink()
