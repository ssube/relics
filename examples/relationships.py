"""Relationships example demonstrating graph-like entity connections.

This example shows how to:
- Define edge types for relationships
- Add and remove relationships between entities
- Query entities by their relationships
- Use relationship validation
- Handle relationship events with observers
"""

from typing import List

from pydantic.dataclasses import dataclass

from relics import (
    Component,
    Edge,
    Entity,
    OnRelationshipAdded,
    OnRelationshipRemoved,
    RelationshipObserver,
    RelationshipValidationError,
    World,
)


# Define components
@dataclass
class Team(Component):
    """Team membership component."""

    team_id: str
    name: str


@dataclass
class Position(Component):
    """2D position component."""

    x: float
    y: float


# Define edge types
@dataclass
class AllyTo(Edge):
    """Alliance relationship between entities."""

    trust_level: float = 1.0

    def validate(self, source: Entity, target: Entity) -> bool:
        """Validate that both entities are on the same team."""
        if not source.has_component(Team) or not target.has_component(Team):
            raise RelationshipValidationError(
                "Both entities must have Team component"
            )

        source_team = source.get_component(Team)
        target_team = target.get_component(Team)

        if source_team.team_id != target_team.team_id:
            raise RelationshipValidationError(
                f"Cannot ally: {source_team.name} vs {target_team.name}"
            )
        return True


@dataclass
class EnemyOf(Edge):
    """Enemy relationship between entities."""

    threat_level: int = 1


@dataclass
class ParentOf(Edge):
    """Parent-child relationship."""

    def validate(self, source: Entity, target: Entity) -> bool:
        """Cannot be your own parent."""
        if source.id == target.id:
            raise RelationshipValidationError("Cannot be your own parent")
        return True


# Define observers
class AllianceObserver(RelationshipObserver):
    """Observer that tracks all alliance events."""

    edge_type = AllyTo

    def __init__(self):
        super().__init__()
        self.alliances: List[tuple] = []

    def on_relationship_added(self, source, edge, target):
        """Log when alliance is formed."""
        print(f"Alliance formed: {source.id} -> {target.id} (trust: {edge.trust_level})")
        self.alliances.append((source.id, target.id, edge.trust_level))

    def on_relationship_removed(self, source, edge, target):
        """Log when alliance is broken."""
        print(f"Alliance broken: {source.id} -> {target.id}")


class EnemyAddedObserver(OnRelationshipAdded):
    """Observer for when enemy relationships are created."""

    edge_type = EnemyOf

    def on_relationship_added(self, source, edge, target):
        """Log enemy relationship."""
        print(f"Enemy declared: {source.id} vs {target.id} (threat: {edge.threat_level})")


def main():
    """Run the relationships example."""
    # Create world
    world = World()

    # Register prefabs
    world.register_prefab(
        "hero",
        {
            Position: Position(x=0, y=0),
            Team: Team(team_id="heroes", name="Heroes"),
        },
    )

    world.register_prefab(
        "villain",
        {
            Position: Position(x=100, y=100),
            Team: Team(team_id="villains", name="Villains"),
        },
    )

    # Register observers
    alliance_observer = AllianceObserver()
    world.observe(alliance_observer)
    world.observe(EnemyAddedObserver())

    # Spawn entities
    hero1 = world.spawn("hero", {Position: Position(x=0, y=0)})
    hero2 = world.spawn("hero", {Position: Position(x=10, y=0)})
    hero3 = world.spawn("hero", {Position: Position(x=20, y=0)})
    villain1 = world.spawn("villain")
    villain2 = world.spawn("villain", {Position: Position(x=110, y=100)})

    print("=== Creating Relationships ===")

    # Create alliances between heroes
    hero1.add_relationship(AllyTo(trust_level=1.0), hero2.id)
    hero1.add_relationship(AllyTo(trust_level=0.8), hero3.id)
    hero2.add_relationship(AllyTo(trust_level=0.9), hero1.id)  # Mutual alliance

    # Create enemy relationships
    hero1.add_relationship(EnemyOf(threat_level=5), villain1.id)
    villain1.add_relationship(EnemyOf(threat_level=3), hero1.id)

    # Process observer queue
    world.tick(0)

    print("\n=== Querying Relationships ===")

    # Get hero1's allies
    print(f"\n{hero1.id}'s allies:")
    for edge, target_id in hero1.get_relationships(AllyTo):
        target = world.get_entity(target_id)
        print(f"  -> {target_id} (trust: {edge.trust_level})")

    # Get entities that are allied TO hero1 (incoming)
    print(f"\nEntities allied to {hero1.id}:")
    for source_id, edge in hero1.get_incoming_relationships(AllyTo):
        print(f"  <- {source_id} (trust: {edge.trust_level})")

    # Query all entities with outgoing ally relationships
    print("\nAll entities with allies:")
    allies_query = world.query().with_relationship(AllyTo)
    for entity in allies_query.execute_entities():
        count = len(entity.get_relationships(AllyTo))
        print(f"  {entity.id} has {count} ally/allies")

    # Query all entities that have incoming ally relationships
    print("\nAll entities with incoming alliances:")
    targeted_query = world.query().with_incoming(AllyTo)
    for entity in targeted_query.execute_entities():
        count = len(entity.get_incoming_relationships(AllyTo))
        print(f"  {entity.id} has {count} ally/allies pointing to them")

    print("\n=== Testing Validation ===")

    # Try to create invalid alliance (cross-team)
    try:
        hero1.add_relationship(AllyTo(), villain1.id)
        print("ERROR: Should have raised validation error!")
    except RelationshipValidationError as e:
        print(f"Validation correctly rejected cross-team alliance: {e}")

    print("\n=== Removing Relationships ===")

    # Remove an alliance
    hero1.remove_relationship(AllyTo, hero2.id)
    world.tick(0)

    # Verify removal
    print(f"\n{hero1.id}'s remaining allies:")
    for edge, target_id in hero1.get_relationships(AllyTo):
        print(f"  -> {target_id}")

    # Check if relationship still exists
    print(f"\nRelationship checks:")
    print(f"  hero1 -> hero2: {hero1.has_relationship(AllyTo, hero2.id)}")
    print(f"  hero1 -> hero3: {hero1.has_relationship(AllyTo, hero3.id)}")

    print(f"\nTotal alliances tracked: {len(alliance_observer.alliances)}")


if __name__ == "__main__":
    main()
