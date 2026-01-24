"""Tests for documentation examples.

This module ensures that every code example in the documentation has a
corresponding test to verify it works correctly.

Test organization mirrors documentation structure:
- README.md examples
- docs/GETTING_STARTED.md examples
- docs/WORLD.md examples
- docs/OBSERVERS.md examples
- docs/SYSTEMS.md examples
- docs/RELATIONSHIPS.md examples
- docs/ENTITIES_COMPONENTS.md examples
"""

from typing import Any, Dict, List, Optional, Tuple, Type

import pytest
from pydantic.dataclasses import dataclass

from relics import (
    Component,
    ComponentObserver,
    CustomEvent,
    Edge,
    Entity,
    EntityObserver,
    Frequency,
    OnComponentAdded,
    OnComponentChanged,
    OnComponentRemoved,
    OnCustomEvent,
    OnEntityCreated,
    OnEntityDestroyed,
    OnRelationshipAdded,
    OnRelationshipRemoved,
    QueryBuilder,
    RelationshipObserver,
    RelationshipValidationError,
    RunOrder,
    System,
    World,
    is_monitored,
    monitored,
)
from relics.types import EntityId


# =============================================================================
# Component Definitions (used across multiple tests)
# =============================================================================


@dataclass
class Position(Component):
    """Position component - used in README Quick Start."""

    x: float
    y: float


@dataclass
class Velocity(Component):
    """Velocity component with dx/dy - standardized field names per docs."""

    dx: float
    dy: float


@dataclass
class Health(Component):
    """Health component - used in README Quick Start."""

    current: int
    maximum: int


@dataclass
class Dead(Component):
    """Marker component for dead entities."""

    pass


@dataclass
class Team(Component):
    """Team component from README."""

    team_id: str
    name: str = ""


@dataclass
class Shield(Component):
    """Shield component for dynamic addition."""

    amount: int


# =============================================================================
# README.md Quick Start Example Tests
# =============================================================================


class TestReadmeQuickStart:
    """Tests for README.md Quick Start example."""

    def test_quick_start_component_definitions(self) -> None:
        """Test README component definitions work."""
        pos = Position(x=0, y=0)
        vel = Velocity(dx=1.0, dy=0.5)

        assert pos.x == 0
        assert pos.y == 0
        assert vel.dx == 1.0
        assert vel.dy == 0.5

    def test_quick_start_world_and_prefab(self) -> None:
        """Test README world creation and prefab registration."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=0, dy=0)},
        )

        player = world.spawn("player", {Position: Position(x=10, y=20)})

        pos = player.get_component(Position)
        assert pos.x == 10
        assert pos.y == 20

    def test_quick_start_query_and_manipulate(self) -> None:
        """Test README query and component manipulation."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=1.0, dy=0.5)},
        )

        player = world.spawn("player")

        for entity in world.query().with_all([Position, Velocity]).execute_entities():
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)
            pos.x += vel.dx
            pos.y += vel.dy

        final_pos = player.get_component(Position)
        assert final_pos.x == 1.0
        assert final_pos.y == 0.5

    def test_quick_start_tick(self) -> None:
        """Test README tick advancement."""
        world = World()
        assert world.epoch == 0

        world.tick(0.016)  # ~60 FPS as documented
        assert world.epoch == 1


# =============================================================================
# README.md Entity and Prefab Examples
# =============================================================================


class TestReadmeEntitiesAndPrefabs:
    """Tests for README entity and prefab examples."""

    def test_spawn_with_overrides(self) -> None:
        """Test README spawn with component overrides."""
        world = World()
        world.register_prefab(
            "enemy",
            {
                Position: Position(x=0, y=0),
                Health: Health(current=100, maximum=100),
            },
        )

        enemy1 = world.spawn("enemy")
        enemy2 = world.spawn("enemy", {Position: Position(x=50, y=50)})

        pos1 = enemy1.get_component(Position)
        pos2 = enemy2.get_component(Position)

        assert pos1.x == 0
        assert pos2.x == 50
        assert pos2.y == 50

    def test_component_operations(self) -> None:
        """Test README component operations."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        entity = world.spawn("player")

        # Add component
        entity.add_component(Health(current=100, maximum=100))
        assert entity.has_component(Health) is True

        # Get component
        health = entity.get_component(Health)
        assert health.current == 100

        # Remove component
        entity.remove_component(Health)
        assert entity.has_component(Health) is False


# =============================================================================
# README.md Relationships (Edges) Examples
# =============================================================================


@dataclass
class AllyTo(Edge):
    """Alliance relationship from README."""

    trust_level: float = 1.0

    def validate(self, source: Entity, target: Entity) -> bool:
        """Validate alliance - can't ally with self."""
        if source.id == target.id:
            raise RelationshipValidationError("Cannot ally with self")
        return True


@dataclass
class ParentOf(Edge):
    """Parent-child relationship from README."""

    pass


class TestReadmeRelationships:
    """Tests for README relationships examples."""

    def test_create_and_query_relationships(self) -> None:
        """Test README relationship creation and querying."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")
        ally = world.spawn("player")

        # Create relationship
        player.add_relationship(AllyTo(trust_level=0.9), ally.id)

        # Query outgoing relationships
        outgoing = player.get_relationships(AllyTo)
        assert len(outgoing) == 1
        edge, target_id = outgoing[0]
        assert edge.trust_level == 0.9
        assert target_id == ally.id

        # Query incoming relationships
        incoming = ally.get_incoming_relationships(AllyTo)
        assert len(incoming) == 1
        source_id, edge = incoming[0]
        assert source_id == player.id

        # Check relationships
        assert player.has_relationship(AllyTo, ally.id) is True
        assert ally.has_incoming_relationship(AllyTo, player.id) is True

        # Remove relationship
        player.remove_relationship(AllyTo, ally.id)
        assert player.has_relationship(AllyTo, ally.id) is False

    def test_relationship_validation(self) -> None:
        """Test README relationship validation example."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")

        # Cannot ally with self
        with pytest.raises(RelationshipValidationError, match="Cannot ally with self"):
            player.add_relationship(AllyTo(), player.id)


# =============================================================================
# README.md Query System Examples
# =============================================================================


class TestReadmeQuerySystem:
    """Tests for README query system examples."""

    def test_query_with_all_and_none(self) -> None:
        """Test README component-based queries with_all and with_none."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=0, dy=0)},
        )

        player = world.spawn("player")
        dead_player = world.spawn("player")
        dead_player.add_component(Dead())

        # Query moving entities excluding dead
        moving = list(
            world.query()
            .with_all([Position, Velocity])
            .with_none([Dead])
            .execute_entities()
        )

        assert len(moving) == 1
        assert moving[0].id == player.id

    def test_query_with_relationship(self) -> None:
        """Test README relationship queries."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")
        ally = world.spawn("player")
        player.add_relationship(AllyTo(), ally.id)

        # Query allies of player
        allies_of_player = list(
            world.query().with_incoming(AllyTo, source=player.id).execute_entities()
        )

        assert len(allies_of_player) == 1
        assert allies_of_player[0].id == ally.id

        # Query entities with any alliance
        with_allies = list(
            world.query().with_relationship(AllyTo).execute_entities()
        )
        assert len(with_allies) == 1
        assert with_allies[0].id == player.id

    def test_query_with_filter(self) -> None:
        """Test README filter predicate queries."""
        world = World()
        world.register_prefab(
            "player",
            {Health: Health(current=100, maximum=100)},
        )

        healthy = world.spawn("player")
        wounded = world.spawn("player", {Health: Health(current=15, maximum=100)})

        # Filter for low health
        low_health = list(
            world.query()
            .with_all([Health])
            .with_filter(lambda e: e.get_component(Health).current < 20)
            .execute_entities()
        )

        assert len(low_health) == 1
        assert low_health[0].id == wounded.id

    def test_query_iterate_batch_processing(self) -> None:
        """Test README batch iteration for performance."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=1.0, dy=0.5)},
        )

        world.spawn("player")
        world.spawn("player", {Position: Position(x=10, y=10)})

        delta = 0.016
        query = (
            world.query()
            .with_all([Position, Velocity])
            .iterate([Position, Velocity])
        )

        positions_updated = 0
        for entity_id, pos, vel in query.execute_components():
            pos.x += vel.dx * delta
            positions_updated += 1

        assert positions_updated == 2


# =============================================================================
# README.md Systems Examples
# =============================================================================


class TestReadmeSystems:
    """Tests for README systems examples."""

    def test_movement_system_pattern(self) -> None:
        """Test README MovementSystem pattern."""
        execution_count = [0]

        class MovementSystem(System):
            def query(self) -> QueryBuilder:
                return (
                    self.q.with_all([Position, Velocity])
                    .with_none([Dead])
                    .iterate([Position, Velocity])
                )

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {}

            def frequency(self) -> Frequency:
                return Frequency.EVERY_TICK

            def process(
                self, entities: List[Entity], components: List[List[Component]], delta: float
            ) -> None:
                execution_count[0] += 1
                positions, velocities = components
                for i in range(len(entities)):
                    positions[i].x += velocities[i].dx * delta
                    positions[i].y += velocities[i].dy * delta

        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=1.0, dy=0.5)},
        )

        world.spawn("player")
        world.register_system(MovementSystem())
        world.tick(1.0)

        assert execution_count[0] == 1

    def test_system_dependencies(self) -> None:
        """Test README system dependencies example."""
        execution_order: List[str] = []

        class InputSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("Input")

        class CollisionSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("Collision")

        class MovementSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {
                    RunOrder.AFTER: [InputSystem],
                    RunOrder.BEFORE: [CollisionSystem],
                }

            def process(self, entities, components, delta) -> None:
                execution_order.append("Movement")

        world = World()
        world.register_system(CollisionSystem())
        world.register_system(MovementSystem())
        world.register_system(InputSystem())
        world.tick(0.016)

        assert execution_order.index("Input") < execution_order.index("Movement")
        assert execution_order.index("Movement") < execution_order.index("Collision")


# =============================================================================
# README.md Observers Examples
# =============================================================================


class TestReadmeObservers:
    """Tests for README observers examples."""

    def test_single_event_observer(self) -> None:
        """Test README OnComponentAdded observer."""
        events: List[Tuple[EntityId, int]] = []

        class DeathObserver(OnComponentAdded):
            component_type = Dead

            def on_component_added(self, entity: Entity, component: Component) -> None:
                events.append((entity.id, 1))

        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        world.observe(DeathObserver())

        player = world.spawn("player")
        player.add_component(Dead())
        world.tick(0)

        assert len(events) == 1
        assert events[0][0] == player.id

    def test_multi_event_component_observer(self) -> None:
        """Test README ComponentObserver (multi-event)."""
        events: List[str] = []

        class HealthTracker(ComponentObserver):
            component_type = Health

            def on_component_added(self, entity: Entity, component: Component) -> None:
                events.append(f"added:{entity.id}")

            def on_component_removed(self, entity: Entity, component: Component) -> None:
                events.append(f"removed:{entity.id}")

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.observe(HealthTracker())

        player = world.spawn("player")
        player.add_component(Health(current=100, maximum=100))
        world.tick(0)

        assert f"added:{player.id}" in events

        player.remove_component(Health)
        world.tick(0)

        assert f"removed:{player.id}" in events

    def test_entity_observer(self) -> None:
        """Test README EntityObserver."""
        events: List[str] = []

        class PlayerLifecycle(EntityObserver):
            prefab = "player"

            def on_entity_created(self, entity: Entity) -> None:
                events.append(f"created:{entity.id}")

            def on_entity_destroyed(self, entity: Entity) -> None:
                events.append(f"destroyed:{entity.id}")

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.observe(PlayerLifecycle())

        player = world.spawn("player")
        world.tick(0)

        assert f"created:{player.id}" in events

        world.remove(player)
        world.tick(0)

        assert f"destroyed:{player.id}" in events

    def test_relationship_observer(self) -> None:
        """Test README RelationshipObserver."""
        events: List[str] = []

        class AllianceTracker(RelationshipObserver):
            edge_type = AllyTo

            def on_relationship_added(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                events.append(f"allied:{source.id}:{target.id}")

            def on_relationship_removed(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                events.append(f"broke:{source.id}:{target.id}")

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.observe(AllianceTracker())

        player = world.spawn("player")
        ally = world.spawn("player")

        player.add_relationship(AllyTo(trust_level=1.0), ally.id)
        world.tick(0)

        assert f"allied:{player.id}:{ally.id}" in events

        player.remove_relationship(AllyTo, ally.id)
        world.tick(0)

        assert f"broke:{player.id}:{ally.id}" in events


# =============================================================================
# README.md Custom Events Examples
# =============================================================================


@dataclass
class EntityDied(CustomEvent):
    """Custom event from README."""

    entity_id: EntityId
    killer_id: Optional[EntityId] = None


@dataclass
class LevelCompleted(CustomEvent):
    """Custom event from README."""

    level_id: str
    score: int


class TestReadmeCustomEvents:
    """Tests for README custom events examples."""

    def test_emit_and_observe_custom_event(self) -> None:
        """Test README custom event emission and observation."""
        received: List[EntityDied] = []

        class ScoreObserver(OnCustomEvent):
            event_type = EntityDied

            def on_event(self, event: CustomEvent) -> None:
                received.append(event)  # type: ignore

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.observe(ScoreObserver())

        player = world.spawn("player")
        attacker = world.spawn("player")

        # Emit event
        world.emit(EntityDied(entity_id=player.id, killer_id=attacker.id))
        world.tick(0)

        assert len(received) == 1
        assert received[0].entity_id == player.id
        assert received[0].killer_id == attacker.id


# =============================================================================
# README.md Change Tracking Examples
# =============================================================================


@monitored
@dataclass
class TrackedHealth(Component):
    """Monitored health component from README."""

    current: int
    maximum: int


class TestReadmeChangeTracking:
    """Tests for README @monitored change tracking examples."""

    def test_monitored_decorator_order(self) -> None:
        """Test README @monitored decorator order (critical: @monitored before @dataclass)."""
        assert is_monitored(TrackedHealth) is True

        health = TrackedHealth(current=100, maximum=100)
        assert is_monitored(health) is True

    def test_change_tracking_observer(self) -> None:
        """Test README OnComponentChanged with @monitored."""
        changes: List[Tuple[str, int, int]] = []

        class HealthChangeObserver(OnComponentChanged):
            component_type = TrackedHealth

            def on_component_changed(
                self,
                entity: Entity,
                component: Component,
                field_name: str,
                old_value: Any,
                new_value: Any,
            ) -> None:
                if field_name == "current":
                    damage = old_value - new_value
                    if damage > 0:
                        changes.append((field_name, old_value, new_value))

        world = World()
        world.register_prefab(
            "player",
            {TrackedHealth: TrackedHealth(current=100, maximum=100)},
        )

        world.observe(HealthChangeObserver())

        entity = world.spawn("player")
        health = entity.get_component(TrackedHealth)
        health._bind_to_world(world, entity.id)

        # Take damage
        health.current = 80
        world.tick(0)

        assert len(changes) == 1
        assert changes[0] == ("current", 100, 80)


# =============================================================================
# README.md Secondary Indexes Examples
# =============================================================================


class TestReadmeIndexes:
    """Tests for README secondary indexes examples."""

    def test_lazy_index(self) -> None:
        """Test README lazy index example."""
        world = World()
        world.register_prefab(
            "player",
            {Health: Health(current=100, maximum=100)},
        )

        world.spawn("player")
        world.spawn("player")

        # Create lazy index
        world.create_index(
            name="alive_players",
            query=world.query().with_all([Health]).with_none([Dead]),
            materialized=False,
        )

        # Use index
        count = 0
        for entity in world.index("alive_players"):
            count += 1

        assert count == 2

    def test_materialized_index(self) -> None:
        """Test README materialized index example."""
        world = World()
        world.register_prefab(
            "player",
            {Health: Health(current=15, maximum=100)},  # Low health
        )

        world.spawn("player")

        # Create materialized index with filter
        world.create_index(
            name="low_health",
            query=world.query()
            .with_all([Health])
            .with_filter(lambda e: e.get_component(Health).current < 20),
            watches=[Health],
            materialized=True,
        )

        count = world.index("low_health").count()
        assert count == 1


# =============================================================================
# GETTING_STARTED.md Examples
# =============================================================================


class TestGettingStarted:
    """Tests for docs/GETTING_STARTED.md examples."""

    def test_world_creation_and_properties(self) -> None:
        """Test GETTING_STARTED world creation."""
        world = World()

        assert world.id is not None
        assert world.epoch == 0

    def test_component_design_pure_data(self) -> None:
        """Test GETTING_STARTED good component design (pure data)."""

        @dataclass
        class GoodPosition(Component):
            x: float
            y: float

        pos = GoodPosition(x=10, y=20)
        assert pos.x == 10
        assert pos.y == 20

    def test_prefab_registration_and_spawning(self) -> None:
        """Test GETTING_STARTED prefab registration and spawning."""
        world = World()

        # Register prefabs
        world.register_prefab(
            "player",
            {
                Position: Position(x=0.0, y=0.0),
                Velocity: Velocity(dx=0.0, dy=0.0),
                Health: Health(current=100, maximum=100),
            },
        )

        world.register_prefab(
            "enemy",
            {
                Position: Position(x=10.0, y=10.0),
                Health: Health(current=50, maximum=50),
            },
        )

        # Spawn
        player = world.spawn("player")
        assert player.prefab == "player"

        # Spawn with custom position
        enemy = world.spawn("enemy", overrides={Position: Position(x=50.0, y=30.0)})
        pos = enemy.get_component(Position)
        assert pos.x == 50.0
        assert pos.y == 30.0

    def test_query_execution_methods(self) -> None:
        """Test GETTING_STARTED query execution methods."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=1, dy=1)},
        )

        player = world.spawn("player")

        # execute_ids
        ids = list(world.query().with_all([Position]).execute_ids())
        assert player.id in ids

        # execute_entities
        entities = list(world.query().with_all([Position]).execute_entities())
        assert len(entities) == 1
        assert entities[0].id == player.id

        # execute_components with iterate
        for entity_id, pos, vel in (
            world.query()
            .with_all([Position, Velocity])
            .iterate([Position, Velocity])
            .execute_components()
        ):
            assert entity_id == player.id
            assert isinstance(pos, Position)
            assert isinstance(vel, Velocity)

    def test_system_groups(self) -> None:
        """Test GETTING_STARTED system groups example."""
        execution_order: List[str] = []

        class GameSystem(System):
            group = "game"

            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("game")

        class InputSystem(System):
            group = "input"

            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("input")

        world = World()
        world.register_system(GameSystem())
        world.register_system(InputSystem())

        # Normal tick
        world.tick(0.016)
        assert "game" in execution_order
        assert "input" in execution_order

        execution_order.clear()

        # Paused - skip game group
        world.tick(0.016, exclude_groups=["game"])
        assert "game" not in execution_order
        assert "input" in execution_order


# =============================================================================
# WORLD.md Examples
# =============================================================================


class TestWorldDoc:
    """Tests for docs/WORLD.md examples."""

    def test_world_custom_id(self) -> None:
        """Test WORLD custom world ID."""
        world = World(world_id="my-game-world")
        assert world.id == "my-game-world"

    def test_entity_retrieval_and_removal(self) -> None:
        """Test WORLD entity retrieval examples."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")
        entity_id = player.id

        # Get entity by ID
        same_player = world.get_entity(entity_id)
        assert same_player.id == player.id

        # Check if exists
        assert world.has_entity(entity_id) is True

        # Remove by Entity handle
        world.remove(player)
        assert world.has_entity(entity_id) is False

    def test_entity_id_parsing(self) -> None:
        """Test WORLD EntityId parsing."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")

        # Parse from string
        entity_id = EntityId.parse(str(player.id))
        assert entity_id.prefab == "player"

    def test_tick_cycle(self) -> None:
        """Test WORLD tick cycle documentation."""
        world = World()

        # Epoch increments
        assert world.epoch == 0
        world.tick(1 / 60)  # 60 FPS
        assert world.epoch == 1

    def test_delta_time_patterns(self) -> None:
        """Test WORLD delta time examples."""
        world = World()

        # Fixed timestep
        FIXED_DELTA = 1 / 60
        world.tick(FIXED_DELTA)
        assert world.epoch == 1

    def test_system_group_filtering(self) -> None:
        """Test WORLD system group filtering."""
        executed: List[str] = []

        class GameSys(System):
            group = "game"

            def query(self) -> QueryBuilder:
                return self.q

            def process(self, e, c, d) -> None:
                executed.append("game")

        class RenderSys(System):
            group = "render"

            def query(self) -> QueryBuilder:
                return self.q

            def process(self, e, c, d) -> None:
                executed.append("render")

        world = World()
        world.register_system(GameSys())
        world.register_system(RenderSys())

        # Run all
        world.tick(0.016)
        assert "game" in executed
        assert "render" in executed

        executed.clear()

        # Only specific groups
        world.tick(0.016, include_groups=["render"])
        assert "game" not in executed
        assert "render" in executed

        executed.clear()

        # Exclude groups
        world.tick(0.016, exclude_groups=["game"])
        assert "game" not in executed
        assert "render" in executed

    def test_export_entity(self) -> None:
        """Test WORLD export_entity example."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=10.0, y=20.0)},
        )

        player = world.spawn("player")

        data = world.export_entity(player.id)

        assert data["id"] == str(player.id)
        assert data["prefab"] == "player"
        assert "Position" in data["components"]
        assert data["components"]["Position"]["x"] == 10.0


# =============================================================================
# OBSERVERS.md Examples
# =============================================================================


class TestObserversDoc:
    """Tests for docs/OBSERVERS.md examples."""

    def test_on_entity_created_with_prefab_filter(self) -> None:
        """Test OBSERVERS OnEntityCreated with prefab filter."""
        events: List[EntityId] = []

        class AllEntitiesLogger(OnEntityCreated):
            prefab = None  # All prefabs

            def on_entity_created(self, entity: Entity) -> None:
                events.append(entity.id)

        class PlayerOnlyLogger(OnEntityCreated):
            prefab = "player"

            def on_entity_created(self, entity: Entity) -> None:
                events.append(entity.id)

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        world.observe(AllEntitiesLogger())

        world.spawn("player")
        world.spawn("enemy")
        world.tick(0)

        assert len(events) == 2  # All entities logged

    def test_on_entity_destroyed(self) -> None:
        """Test OBSERVERS OnEntityDestroyed."""
        destroyed: List[EntityId] = []

        class DeathLogger(OnEntityDestroyed):
            prefab = "enemy"

            def on_entity_destroyed(self, entity: Entity) -> None:
                destroyed.append(entity.id)

        world = World()
        world.register_prefab("enemy", {Position: Position(x=0, y=0)})

        world.observe(DeathLogger())

        enemy = world.spawn("enemy")
        world.tick(0)

        world.remove(enemy)
        world.tick(0)

        assert enemy.id in destroyed

    def test_on_component_added(self) -> None:
        """Test OBSERVERS OnComponentAdded."""
        added: List[Tuple[EntityId, int]] = []

        class HealthAddedHandler(OnComponentAdded):
            component_type = Health

            def on_component_added(self, entity: Entity, component: Component) -> None:
                added.append((entity.id, component.current))  # type: ignore

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        world.observe(HealthAddedHandler())

        player = world.spawn("player")
        player.add_component(Health(current=100, maximum=100))
        world.tick(0)

        assert len(added) == 1
        assert added[0] == (player.id, 100)

    def test_on_component_removed(self) -> None:
        """Test OBSERVERS OnComponentRemoved."""
        removed: List[EntityId] = []

        class ShieldRemovedHandler(OnComponentRemoved):
            component_type = Shield

            def on_component_removed(self, entity: Entity, component: Component) -> None:
                removed.append(entity.id)

        world = World()
        world.register_prefab("player", {Shield: Shield(amount=50)})

        world.observe(ShieldRemovedHandler())

        player = world.spawn("player")
        player.remove_component(Shield)
        world.tick(0)

        assert player.id in removed

    def test_on_relationship_added(self) -> None:
        """Test OBSERVERS OnRelationshipAdded."""
        events: List[Tuple[EntityId, EntityId]] = []

        @dataclass
        class BelongsTo(Edge):
            pass

        class TeamJoinHandler(OnRelationshipAdded):
            edge_type = BelongsTo

            def on_relationship_added(
                self, source: Entity, edge: Edge, target: Entity
            ) -> None:
                events.append((source.id, target.id))

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})
        world.register_prefab("team", {})

        world.observe(TeamJoinHandler())

        player = world.spawn("player")
        team = world.spawn("team")

        player.add_relationship(BelongsTo(), team.id)
        world.tick(0)

        assert (player.id, team.id) in events

    def test_observer_event_queuing(self) -> None:
        """Test OBSERVERS event queuing at tick."""
        processed_at_epochs: List[int] = []

        class Observer(OnEntityCreated):
            prefab = None

            def on_entity_created(self, entity: Entity) -> None:
                processed_at_epochs.append(self.world.epoch)

        world = World()
        world.register_prefab("player", {})

        world.observe(Observer())

        world.spawn("player")  # Queued
        # Not processed yet
        world.tick(0.016)  # Processed at epoch 1

        assert processed_at_epochs[0] == 1


# =============================================================================
# SYSTEMS.md Examples
# =============================================================================


class TestSystemsDoc:
    """Tests for docs/SYSTEMS.md examples."""

    def test_system_wildcard_after(self) -> None:
        """Test SYSTEMS System.WILDCARD in AFTER (run last)."""
        execution_order: List[str] = []

        class CleanupSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.AFTER: [System.WILDCARD]}

            def process(self, entities, components, delta) -> None:
                execution_order.append("Cleanup")

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("A")

        class SystemB(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("B")

        world = World()
        world.register_system(CleanupSystem())
        world.register_system(SystemA())
        world.register_system(SystemB())
        world.tick(0.016)

        # Cleanup should be last
        assert execution_order[-1] == "Cleanup"

    def test_system_wildcard_before(self) -> None:
        """Test SYSTEMS System.WILDCARD in BEFORE (run first)."""
        execution_order: List[str] = []

        class InitSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def deps(self) -> Dict[RunOrder, List[Type[System]]]:
                return {RunOrder.BEFORE: [System.WILDCARD]}

            def process(self, entities, components, delta) -> None:
                execution_order.append("Init")

        class SystemA(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_order.append("A")

        world = World()
        world.register_system(SystemA())
        world.register_system(InitSystem())
        world.tick(0.016)

        # Init should be first
        assert execution_order[0] == "Init"

    def test_system_paused(self) -> None:
        """Test SYSTEMS system paused property."""
        execution_count = [0]

        class TestSystem(System):
            def query(self) -> QueryBuilder:
                return self.q

            def process(self, entities, components, delta) -> None:
                execution_count[0] += 1

        world = World()
        system = TestSystem()
        world.register_system(system)

        # Run normally
        world.tick(0.016)
        assert execution_count[0] == 1

        # Pause and run
        system.paused = True
        world.tick(0.016)
        assert execution_count[0] == 1  # Didn't run

        # Unpause and run
        system.paused = False
        world.tick(0.016)
        assert execution_count[0] == 2

    def test_frequency_every_n_ticks(self) -> None:
        """Test SYSTEMS Frequency.every_n_ticks."""
        freq = Frequency.every_n_ticks(3)

        assert freq.should_run(1, 0.016) is False
        assert freq.should_run(2, 0.016) is False
        assert freq.should_run(3, 0.016) is True
        assert freq.should_run(4, 0.016) is False
        assert freq.should_run(6, 0.016) is True

    def test_frequency_fixed_interval(self) -> None:
        """Test SYSTEMS Frequency.fixed_interval."""
        freq = Frequency.fixed_interval(1.0)

        # Not enough time
        assert freq.should_run(1, 0.5) is False
        # Accumulated enough
        assert freq.should_run(2, 0.6) is True
        # Reset
        assert freq.should_run(3, 0.3) is False


# =============================================================================
# Complete Example (from README.md)
# =============================================================================


class TestCompleteExample:
    """Test the complete example from README.md."""

    def test_complete_game_example(self) -> None:
        """Test README complete example runs without error."""

        @monitored
        @dataclass
        class CompleteHealth(Component):
            current: int
            maximum: int

        @dataclass
        class CompleteDead(Component):
            pass

        @dataclass
        class CompleteTeam(Component):
            team_id: str

        @dataclass
        class CompleteAllyTo(Edge):
            trust_level: float = 1.0

        @dataclass
        class CompleteEntityDied(CustomEvent):
            entity_id: EntityId

        class CompleteMovementSystem(System):
            def query(self) -> QueryBuilder:
                return (
                    self.q.with_all([Position, Velocity])
                    .with_none([CompleteDead])
                    .iterate([Position, Velocity])
                )

            def process(
                self, entities: List[Entity], components: List[List[Component]], delta: float
            ) -> None:
                positions, velocities = components
                for i in range(len(entities)):
                    positions[i].x += velocities[i].dx * delta
                    positions[i].y += velocities[i].dy * delta

        class CompleteDeathObserver(OnComponentAdded):
            component_type = CompleteDead

            def on_component_added(self, entity: Entity, component: Component) -> None:
                self.world.emit(CompleteEntityDied(entity.id))

        # Main
        world = World()

        # Register prefabs
        world.register_prefab(
            "player",
            {
                Position: Position(x=0, y=0),
                Velocity: Velocity(dx=0, dy=0),
                CompleteHealth: CompleteHealth(current=100, maximum=100),
                CompleteTeam: CompleteTeam(team_id="heroes"),
            },
        )

        # Register systems and observers
        world.register_system(CompleteMovementSystem())
        world.observe(CompleteDeathObserver())

        # Spawn entities
        player = world.spawn("player")
        ally = world.spawn("player", {Position: Position(x=10, y=0)})

        # Create alliance
        player.add_relationship(CompleteAllyTo(trust_level=1.0), ally.id)

        # Game loop (abbreviated)
        for _ in range(10):
            vel = player.get_component(Velocity)
            vel.dx = 1.0
            vel.dy = 0.5
            world.tick(0.016)

        # Query allies
        allies_query = world.query().with_incoming(CompleteAllyTo, source=player.id)
        ally_count = sum(1 for _ in allies_query.execute_entities())
        assert ally_count == 1

        # Get final position
        pos = player.get_component(Position)
        assert pos.x > 0  # Has moved
        assert pos.y > 0


# =============================================================================
# RELATIONSHIPS.md Examples
# =============================================================================


@dataclass
class BelongsTo(Edge):
    """Team membership relationship from RELATIONSHIPS.md."""

    role: str = "member"

    def validate(self, source: Entity, target: Entity) -> bool:
        return target.prefab == "team"


@dataclass
class Follows(Edge):
    """Follow relationship with data from RELATIONSHIPS.md."""

    priority: int = 0
    distance: float = 5.0


@dataclass
class Targets(Edge):
    """Targeting relationship from RELATIONSHIPS.md."""

    priority: int = 0
    locked: bool = False

    def validate(self, source: Entity, target: Entity) -> bool:
        # Can't target yourself
        if source.id == target.id:
            return False
        # Target must have health
        return target.has_component(Health)


@dataclass
class AffectedBy(Edge):
    """Status effect relationship from RELATIONSHIPS.md."""

    duration: float
    stacks: int = 1


class TestRelationshipsDoc:
    """Tests for docs/RELATIONSHIPS.md examples."""

    def test_edge_with_data(self) -> None:
        """Test RELATIONSHIPS edge with data."""
        world = World()
        world.register_prefab("npc", {Position: Position(x=0, y=0)})

        player = world.spawn("npc")
        npc1 = world.spawn("npc")
        npc2 = world.spawn("npc")

        # Multiple relationships of same type
        player.add_relationship(Follows(priority=1), npc1.id)
        player.add_relationship(Follows(priority=2, distance=10.0), npc2.id)

        follows = player.get_relationships(Follows)
        assert len(follows) == 2

    def test_edge_validation(self) -> None:
        """Test RELATIONSHIPS edge validation."""
        world = World()
        world.register_prefab("team", {})
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        player = world.spawn("player")
        team = world.spawn("team")

        # Valid relationship
        player.add_relationship(BelongsTo(role="captain"), team.id)
        assert player.has_relationship(BelongsTo, team.id)

        # Invalid relationship (not a team target)
        other_player = world.spawn("player")
        with pytest.raises(RelationshipValidationError):
            player.add_relationship(BelongsTo(), other_player.id)

    def test_targeting_system_pattern(self) -> None:
        """Test RELATIONSHIPS targeting validation pattern."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        attacker = world.spawn("player")
        defender = world.spawn("player")

        # Valid targeting
        attacker.add_relationship(Targets(priority=1), defender.id)
        assert attacker.has_relationship(Targets, defender.id)

        # Cannot target self
        with pytest.raises(RelationshipValidationError):
            attacker.add_relationship(Targets(), attacker.id)

    def test_get_outgoing_relationships(self) -> None:
        """Test RELATIONSHIPS get_relationships (outgoing)."""
        world = World()
        world.register_prefab("npc", {Position: Position(x=0, y=0)})

        player = world.spawn("npc")
        npc1 = world.spawn("npc")
        npc2 = world.spawn("npc")

        player.add_relationship(Follows(priority=1), npc1.id)
        player.add_relationship(Follows(priority=2), npc2.id)

        follows = player.get_relationships(Follows)
        for edge, target_id in follows:
            assert isinstance(edge, Follows)
            assert target_id in [npc1.id, npc2.id]

    def test_get_incoming_relationships(self) -> None:
        """Test RELATIONSHIPS get_incoming_relationships."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        target = world.spawn("player")
        attacker1 = world.spawn("player")
        attacker2 = world.spawn("player")

        attacker1.add_relationship(Targets(), target.id)
        attacker2.add_relationship(Targets(), target.id)

        incoming = target.get_incoming_relationships(Targets)
        assert len(incoming) == 2

        for source_id, edge in incoming:
            assert source_id in [attacker1.id, attacker2.id]
            assert isinstance(edge, Targets)

    def test_has_incoming_relationship(self) -> None:
        """Test RELATIONSHIPS has_incoming_relationship."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        target = world.spawn("player")
        attacker = world.spawn("player")

        # No incoming yet
        assert target.has_incoming_relationship(Targets) is False
        assert target.has_incoming_relationship(Targets, attacker.id) is False

        # Add relationship
        attacker.add_relationship(Targets(), target.id)

        # Now has incoming
        assert target.has_incoming_relationship(Targets) is True
        assert target.has_incoming_relationship(Targets, attacker.id) is True

    def test_relationship_query_with_relationship(self) -> None:
        """Test RELATIONSHIPS with_relationship query."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        attacker = world.spawn("player")
        defender = world.spawn("player")

        attacker.add_relationship(Targets(), defender.id)

        # Find entities that are targeting something
        targeting = list(
            world.query().with_relationship(Targets).execute_entities()
        )
        assert len(targeting) == 1
        assert targeting[0].id == attacker.id

        # Find entities targeting a specific target
        attackers = list(
            world.query().with_relationship(Targets, defender.id).execute_entities()
        )
        assert len(attackers) == 1
        assert attackers[0].id == attacker.id

    def test_relationship_query_with_incoming(self) -> None:
        """Test RELATIONSHIPS with_incoming query."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        attacker = world.spawn("player")
        defender = world.spawn("player")

        attacker.add_relationship(Targets(), defender.id)

        # Find entities being targeted
        targeted = list(
            world.query().with_incoming(Targets).execute_entities()
        )
        assert len(targeted) == 1
        assert targeted[0].id == defender.id

        # Find entities targeted by specific attacker
        victims = list(
            world.query().with_incoming(Targets, attacker.id).execute_entities()
        )
        assert len(victims) == 1
        assert victims[0].id == defender.id

    def test_status_effects_pattern(self) -> None:
        """Test RELATIONSHIPS status effects pattern (AffectedBy)."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})
        world.register_prefab("effect_source", {})

        player = world.spawn("player")
        poison_source = world.spawn("effect_source")

        # Apply status effect
        player.add_relationship(
            AffectedBy(duration=10.0, stacks=3),
            poison_source.id,
        )

        # Query entities with status effects
        affected = list(
            world.query().with_relationship(AffectedBy).execute_entities()
        )
        assert len(affected) == 1
        assert affected[0].id == player.id

        # Get effect details
        effects = player.get_relationships(AffectedBy)
        assert len(effects) == 1
        edge, source_id = effects[0]
        assert edge.duration == 10.0
        assert edge.stacks == 3

    def test_automatic_relationship_cleanup(self) -> None:
        """Test RELATIONSHIPS automatic cleanup on entity removal."""
        world = World()
        world.register_prefab("player", {Health: Health(current=100, maximum=100)})

        player = world.spawn("player")
        target = world.spawn("player")

        player.add_relationship(Targets(), target.id)

        # Verify relationship exists
        assert player.has_relationship(Targets, target.id)
        assert target.has_incoming_relationship(Targets, player.id)

        # Remove target
        world.remove(target)

        # Relationship should be cleaned up
        # (accessing stale relationship would error)
        relationships = player.get_relationships(Targets)
        assert len(relationships) == 0


# =============================================================================
# ENTITIES_COMPONENTS.md Examples
# =============================================================================


class TestEntitiesComponentsDoc:
    """Tests for docs/ENTITIES_COMPONENTS.md examples."""

    def test_entity_id_structure(self) -> None:
        """Test ENTITIES_COMPONENTS EntityId structure."""
        entity_id = EntityId(prefab="player", sequence=1234567890)

        # String representation
        assert str(entity_id) == "player_1234567890"

        # Parse from string
        parsed = EntityId.parse("player_1234567890")
        assert parsed == entity_id

        # Use as dictionary key
        entity_data = {entity_id: {"score": 100}}
        assert entity_data[entity_id]["score"] == 100

    def test_entity_handle(self) -> None:
        """Test ENTITIES_COMPONENTS Entity handle."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")

        # Handle properties
        assert player.prefab == "player"
        assert player.id.prefab == "player"

        # Multiple handles to same entity
        player2 = world.get_entity(player.id)
        assert player == player2

    def test_entity_handle_lifecycle(self) -> None:
        """Test ENTITIES_COMPONENTS Entity handle lifecycle."""
        from relics import EntityNotFoundError

        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")

        # Handle is valid
        pos = player.get_component(Position)
        assert pos is not None

        # Remove entity
        world.remove(player)

        # Handle is now stale
        with pytest.raises(EntityNotFoundError):
            player.get_component(Position)

    def test_component_add_duplicate_error(self) -> None:
        """Test ENTITIES_COMPONENTS DuplicateComponentError."""
        from relics import DuplicateComponentError

        world = World()
        world.register_prefab("player", {})

        player = world.spawn("player")
        player.add_component(Position(x=10.0, y=20.0))

        with pytest.raises(DuplicateComponentError):
            player.add_component(Position(x=0.0, y=0.0))

    def test_component_remove_not_found_error(self) -> None:
        """Test ENTITIES_COMPONENTS ComponentNotFoundError."""
        from relics import ComponentNotFoundError

        world = World()
        world.register_prefab("player", {})

        player = world.spawn("player")

        with pytest.raises(ComponentNotFoundError):
            player.remove_component(Position)

    def test_component_update_immutable_pattern(self) -> None:
        """Test ENTITIES_COMPONENTS immutable component update pattern."""
        world = World()
        world.register_prefab("player", {Position: Position(x=0, y=0)})

        player = world.spawn("player")

        # Get current component
        pos = player.get_component(Position)

        # Create new component with updated values
        new_pos = Position(x=pos.x + 10, y=pos.y + 5)

        # Replace
        player.remove_component(Position)
        player.add_component(new_pos)

        # Verify update
        updated_pos = player.get_component(Position)
        assert updated_pos.x == 10
        assert updated_pos.y == 5

    def test_prefab_with_extra_components(self) -> None:
        """Test ENTITIES_COMPONENTS spawn with extra components."""
        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Velocity: Velocity(dx=0, dy=0)},
        )

        # Spawn with extra component not in prefab
        player = world.spawn("player", overrides={Shield: Shield(amount=50)})

        # Has prefab components
        assert player.has_component(Position)
        assert player.has_component(Velocity)

        # Also has extra component
        assert player.has_component(Shield)
        shield = player.get_component(Shield)
        assert shield.amount == 50

    def test_list_and_get_prefabs(self) -> None:
        """Test ENTITIES_COMPONENTS list_prefabs and get_prefab."""
        from relics import get_prefab, list_prefabs

        world = World()
        world.register_prefab(
            "player",
            {Position: Position(x=0, y=0), Health: Health(current=100, maximum=100)},
        )
        world.register_prefab("enemy", {Position: Position(x=10, y=10)})

        # List all prefabs
        names = list_prefabs(world)
        assert "player" in names
        assert "enemy" in names

        # Get specific prefab
        prefab_components = get_prefab(world, "player")
        assert Position in prefab_components
        assert Health in prefab_components

    def test_nested_data_component(self) -> None:
        """Test ENTITIES_COMPONENTS nested data in components."""
        from typing import List

        @dataclass
        class Vector2:
            x: float
            y: float

        @dataclass
        class Polygon(Component):
            vertices: List[Vector2]

        world = World()
        world.register_prefab("shape", {})

        shape = world.spawn("shape")
        shape.add_component(
            Polygon(
                vertices=[
                    Vector2(x=0, y=0),
                    Vector2(x=1, y=0),
                    Vector2(x=0.5, y=1),
                ]
            )
        )

        poly = shape.get_component(Polygon)
        assert len(poly.vertices) == 3
        assert poly.vertices[0].x == 0
