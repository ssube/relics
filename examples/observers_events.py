"""Observers and custom events example.

This example shows how to:
- Create observers for entity lifecycle events
- Create observers for component events
- Use the @monitored decorator for change tracking
- Define and emit custom events
- Create multi-event observers
"""

from typing import List, Optional

from pydantic.dataclasses import dataclass

from relics import (
    Component,
    ComponentObserver,
    CustomEvent,
    Entity,
    EntityObserver,
    OnComponentAdded,
    OnCustomEvent,
    OnEntityCreated,
    World,
    monitored,
)
from relics.types import EntityId


# Define components
@dataclass
class Position(Component):
    """2D position component."""

    x: float
    y: float


@monitored  # Enable change tracking
@dataclass
class Health(Component):
    """Health component with change tracking."""

    current: int
    maximum: int


@dataclass
class Dead(Component):
    """Marker component indicating entity is dead."""

    pass


@dataclass
class Score(Component):
    """Score tracking component."""

    value: int = 0


# Define custom events
@dataclass
class EntityDied(CustomEvent):
    """Emitted when an entity dies."""

    entity_id: EntityId
    killer_id: Optional[EntityId] = None


@dataclass
class DamageTaken(CustomEvent):
    """Emitted when an entity takes damage."""

    entity_id: EntityId
    amount: int
    new_health: int


@dataclass
class LevelUp(CustomEvent):
    """Emitted when a player levels up."""

    entity_id: EntityId
    new_level: int


# Single-event observers
class EntityCreationLogger(OnEntityCreated):
    """Logs all entity creations."""

    prefab = None  # None = all prefabs

    def on_entity_created(self, entity):
        print(f"[LOG] Entity created: {entity.id} (prefab: {entity.prefab})")


class PlayerSpawnObserver(OnEntityCreated):
    """Specific observer for player spawns only."""

    prefab = "player"

    def on_entity_created(self, entity):
        print(f"[PLAYER] Welcome, {entity.id}!")


class DeathObserver(OnComponentAdded):
    """Emits EntityDied event when Dead component is added."""

    component_type = Dead

    def on_component_added(self, entity, component):
        print(f"[DEATH] {entity.id} has died!")
        self.world.emit(EntityDied(entity.id))


class ScoreObserver(OnCustomEvent):
    """Awards points when entities die."""

    event_type = EntityDied

    def __init__(self):
        super().__init__()
        self.total_deaths = 0

    def on_event(self, event):
        self.total_deaths += 1
        print(f"[SCORE] Death recorded. Total deaths: {self.total_deaths}")

        if event.killer_id:
            try:
                killer = self.world.get_entity(event.killer_id)
                if killer.has_component(Score):
                    score = killer.get_component(Score)
                    score.value += 100
                    print(f"[SCORE] {killer.id} earned 100 points! Total: {score.value}")
            except Exception:
                pass  # Killer might not exist


# Multi-event observers
class HealthTracker(ComponentObserver):
    """Tracks all health-related events."""

    component_type = Health

    def __init__(self):
        super().__init__()
        self.events: List[str] = []

    def on_component_added(self, entity, component):
        msg = f"Health added to {entity.id}: {component.current}/{component.maximum}"
        self.events.append(msg)
        print(f"[HEALTH+] {msg}")

    def on_component_changed(self, entity, old_value, new_value):
        diff = new_value.current - old_value.current
        direction = "healed" if diff > 0 else "took damage"
        msg = f"{entity.id} {direction}: {abs(diff)} ({old_value.current} -> {new_value.current})"
        self.events.append(msg)
        print(f"[HEALTH~] {msg}")

        # Emit damage event
        if diff < 0:
            self.world.emit(DamageTaken(entity.id, abs(diff), new_value.current))

    def on_component_removed(self, entity, component):
        msg = f"Health removed from {entity.id}"
        self.events.append(msg)
        print(f"[HEALTH-] {msg}")


class PlayerLifecycleObserver(EntityObserver):
    """Tracks player entity lifecycle."""

    prefab = "player"

    def __init__(self):
        super().__init__()
        self.active_players: List[EntityId] = []

    def on_entity_created(self, entity):
        self.active_players.append(entity.id)
        print(f"[PLAYER] Player joined: {entity.id} (total: {len(self.active_players)})")

    def on_entity_destroyed(self, entity):
        if entity.id in self.active_players:
            self.active_players.remove(entity.id)
        print(f"[PLAYER] Player left: {entity.id} (total: {len(self.active_players)})")


class DamageLogObserver(OnCustomEvent):
    """Logs all damage events."""

    event_type = DamageTaken

    def on_event(self, event):
        print(
            f"[DAMAGE] {event.entity_id} took {event.amount} damage "
            f"(health now: {event.new_health})"
        )


def main():
    """Run the observers and events example."""
    # Create world
    world = World()

    # Register prefabs
    world.register_prefab(
        "player",
        {
            Position: Position(x=0, y=0),
            Health: Health(current=100, maximum=100),
            Score: Score(value=0),
        },
    )

    world.register_prefab(
        "enemy",
        {
            Position: Position(x=50, y=50),
            Health: Health(current=30, maximum=30),
        },
    )

    # Create observers
    health_tracker = HealthTracker()
    player_lifecycle = PlayerLifecycleObserver()
    score_observer = ScoreObserver()

    # Register observers
    world.observe(EntityCreationLogger())
    world.observe(PlayerSpawnObserver())
    world.observe(DeathObserver())
    world.observe(health_tracker)
    world.observe(player_lifecycle)
    world.observe(score_observer)
    world.observe(DamageLogObserver())

    print("=== Spawning Entities ===")
    player = world.spawn("player")
    enemy1 = world.spawn("enemy")
    enemy2 = world.spawn("enemy", {Position: Position(x=60, y=50)})

    # Process spawn events
    world.tick(0)

    print("\n=== Modifying Health ===")

    # Damage the player (triggers ComponentObserver.on_component_changed)
    player_health = player.get_component(Health)
    player_health.current = 80  # -20 damage

    # Heal the player
    player_health.current = 90  # +10 heal

    # Critical hit!
    player_health.current = 40  # -50 damage

    world.tick(0)

    print("\n=== Killing Enemies ===")

    # Kill enemy1
    enemy1.add_component(Dead())
    world.tick(0)

    # Kill enemy2 with killer attribution
    world.emit(EntityDied(enemy2.id, killer_id=player.id))
    enemy2.add_component(Dead())
    world.tick(0)

    print("\n=== Removing Entities ===")

    # Remove player (triggers EntityObserver.on_entity_destroyed)
    world.remove(player)
    world.tick(0)

    print("\n=== Summary ===")
    print(f"Health events tracked: {len(health_tracker.events)}")
    print(f"Active players: {len(player_lifecycle.active_players)}")
    print(f"Total deaths recorded: {score_observer.total_deaths}")


if __name__ == "__main__":
    main()
