"""Shared test fixtures for Relics ECS performance tests."""

from typing import Dict, List, Type

from pydantic.dataclasses import dataclass

from relics import Component, Edge, World

# =============================================================================
# Optional Dependency Handling
# =============================================================================

# Skip addon tests if their optional dependencies are not installed.
# This prevents ImportError during test collection.

collect_ignore_glob = []

try:
    import prometheus_client  # noqa: F401
except ImportError:
    collect_ignore_glob.append("addons/prometheus/test_*.py")

try:
    import websockets  # noqa: F401
except ImportError:
    collect_ignore_glob.append("addons/websocket/test_*.py")

# =============================================================================
# Reusable Components
# =============================================================================


@dataclass
class Position(Component):
    """2D position component."""

    x: float = 0.0
    y: float = 0.0


@dataclass
class Velocity(Component):
    """2D velocity component."""

    vx: float = 0.0
    vy: float = 0.0


@dataclass
class Health(Component):
    """Health component with current and maximum values."""

    current: int = 100
    maximum: int = 100


@dataclass
class Inventory(Component):
    """Inventory component with items and capacity."""

    items: List[str] = None  # type: ignore[assignment]
    capacity: int = 10

    def __post_init__(self) -> None:
        if self.items is None:
            self.items = []


@dataclass
class AI(Component):
    """AI component with state and target."""

    state: str = "idle"
    target_id: str = ""
    aggression: float = 0.5


# =============================================================================
# Reusable Edges
# =============================================================================


@dataclass
class ParentOf(Edge):
    """Parent-child relationship edge."""

    pass


@dataclass
class AllyTo(Edge):
    """Alliance relationship edge."""

    trust_level: float = 1.0


@dataclass
class Targets(Edge):
    """Targeting relationship edge."""

    priority: int = 0


# =============================================================================
# Helper Functions
# =============================================================================


def register_standard_prefabs(world: World) -> None:
    """Register standard prefabs for testing.

    Prefabs registered:
    - simple: Position only
    - movable: Position + Velocity
    - player: Position + Velocity + Health + Inventory
    - npc: Position + Velocity + Health + AI
    - complex: All 5 components

    Args:
        world: The World instance to register prefabs in.
    """
    # Simple prefab - 1 component
    world.register_prefab(
        "simple",
        {Position: Position(x=0, y=0)},
    )

    # Movable prefab - 2 components
    world.register_prefab(
        "movable",
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
        },
    )

    # Player prefab - 4 components
    world.register_prefab(
        "player",
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            Health: Health(current=100, maximum=100),
            Inventory: Inventory(items=[], capacity=20),
        },
    )

    # NPC prefab - 4 components
    world.register_prefab(
        "npc",
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            Health: Health(current=50, maximum=50),
            AI: AI(state="idle", target_id="", aggression=0.5),
        },
    )

    # Complex prefab - 5 components
    world.register_prefab(
        "complex",
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            Health: Health(current=100, maximum=100),
            Inventory: Inventory(items=[], capacity=10),
            AI: AI(state="patrol", target_id="", aggression=0.3),
        },
    )


def get_standard_components() -> Dict[str, Type[Component]]:
    """Get dictionary of standard component types.

    Returns:
        Dictionary mapping component names to their types.
    """
    return {
        "Position": Position,
        "Velocity": Velocity,
        "Health": Health,
        "Inventory": Inventory,
        "AI": AI,
    }


def get_standard_edges() -> Dict[str, Type[Edge]]:
    """Get dictionary of standard edge types.

    Returns:
        Dictionary mapping edge names to their types.
    """
    return {
        "ParentOf": ParentOf,
        "AllyTo": AllyTo,
        "Targets": Targets,
    }


# =============================================================================
# Scale Parameters
# =============================================================================

PERF_SCALES = [100, 10_000, 1_000_000]
PERF_SCALE_IDS = ["100", "10k", "1M"]
