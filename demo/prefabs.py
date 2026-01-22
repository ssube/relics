"""Prefab registration and entity spawning for the ecosystem demo."""

import random
from typing import Optional

from relics import World

from demo.components import (
    BoundingBox,
    CameraInput,
    Color,
    Consumable,
    FoxAI,
    FoxState,
    GameStats,
    Obstacle,
    Position,
    RabbitAI,
    RabbitState,
    Sprite,
    Velocity,
    Viewport,
)
from demo.config import (
    CAMERA_SIZE,
    CAMERA_SPEED,
    ENTITY_CAMERA,
    ENTITY_FLOWER,
    ENTITY_FOX,
    ENTITY_RABBIT,
    ENTITY_STONE,
    ENTITY_TREE,
    FLOWER_COLORS,
    FLOWER_COUNT_MAX,
    FLOWER_COUNT_MIN,
    FLOWER_SIZE,
    FOX_COUNT_MAX,
    FOX_COUNT_MIN,
    FOX_SIGHT_RANGE,
    FOX_SIZE,
    RABBIT_COUNT_MAX,
    RABBIT_COUNT_MIN,
    RABBIT_SIZE,
    SAFE_SPAWN_DISTANCE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STONE_COUNT_MAX,
    STONE_COUNT_MIN,
    STONE_SIZE,
    TREE_COUNT_MAX,
    TREE_COUNT_MIN,
    TREE_SIZE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)


def register_prefabs(world: World) -> None:
    """Register all entity prefabs with the world."""
    # Rabbit prefab
    world.register_prefab(
        ENTITY_RABBIT,
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            BoundingBox: BoundingBox(width=RABBIT_SIZE, height=RABBIT_SIZE),
            Sprite: Sprite(entity_type=ENTITY_RABBIT),
            RabbitAI: RabbitAI(state=RabbitState.IDLE),
        },
    )

    # Fox prefab
    world.register_prefab(
        ENTITY_FOX,
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            BoundingBox: BoundingBox(width=FOX_SIZE, height=FOX_SIZE),
            Sprite: Sprite(entity_type=ENTITY_FOX),
            FoxAI: FoxAI(state=FoxState.IDLE, target_id=None, sight_range=FOX_SIGHT_RANGE),
        },
    )

    # Tree prefab (static obstacle)
    world.register_prefab(
        ENTITY_TREE,
        {
            Position: Position(x=0, y=0),
            BoundingBox: BoundingBox(width=TREE_SIZE, height=TREE_SIZE),
            Sprite: Sprite(entity_type=ENTITY_TREE),
            Obstacle: Obstacle(),
        },
    )

    # Stone prefab (static obstacle)
    world.register_prefab(
        ENTITY_STONE,
        {
            Position: Position(x=0, y=0),
            BoundingBox: BoundingBox(width=STONE_SIZE, height=STONE_SIZE),
            Sprite: Sprite(entity_type=ENTITY_STONE),
            Obstacle: Obstacle(),
        },
    )

    # Flower prefab (consumable)
    world.register_prefab(
        ENTITY_FLOWER,
        {
            Position: Position(x=0, y=0),
            BoundingBox: BoundingBox(width=FLOWER_SIZE, height=FLOWER_SIZE),
            Sprite: Sprite(entity_type=ENTITY_FLOWER),
            Consumable: Consumable(),
        },
    )

    # Camera prefab
    world.register_prefab(
        ENTITY_CAMERA,
        {
            Position: Position(x=0, y=0),
            Velocity: Velocity(vx=0, vy=0),
            BoundingBox: BoundingBox(width=CAMERA_SIZE, height=CAMERA_SIZE),
            Viewport: Viewport(width=SCREEN_WIDTH, height=SCREEN_HEIGHT),
            CameraInput: CameraInput(),
            GameStats: GameStats(),
        },
    )


def get_random_position(
    width: int, height: int, margin: int = 0
) -> tuple[float, float]:
    """Get a random position within world bounds, accounting for entity size."""
    x = random.uniform(margin, WORLD_WIDTH - width - margin)
    y = random.uniform(margin, WORLD_HEIGHT - height - margin)
    return x, y


def rectangles_overlap(
    x1: float, y1: float, w1: int, h1: int,
    x2: float, y2: float, w2: int, h2: int
) -> bool:
    """Check if two rectangles overlap."""
    return (
        x1 < x2 + w2
        and x1 + w1 > x2
        and y1 < y2 + h2
        and y1 + h1 > y2
    )


def find_non_overlapping_position(
    world: World,
    width: int,
    height: int,
    max_attempts: int = 100,
    margin: int = 0,
) -> Optional[tuple[float, float]]:
    """Find a position that doesn't overlap with existing entities."""
    for _ in range(max_attempts):
        x, y = get_random_position(width, height, margin)

        # Check against all existing entities with positions and bounding boxes
        overlaps = False
        for entity in world.query().with_all([Position, BoundingBox]).execute_entities():
            pos = entity.get_component(Position)
            bbox = entity.get_component(BoundingBox)
            if rectangles_overlap(x, y, width, height, pos.x, pos.y, bbox.width, bbox.height):
                overlaps = True
                break

        if not overlaps:
            return x, y

    # Fallback: return random position if we can't find non-overlapping one
    return get_random_position(width, height, margin)


def get_safe_position(world: World, width: int, height: int) -> tuple[float, float]:
    """Find a position away from all foxes for rabbit respawn."""
    max_attempts = 100

    # Get all fox positions
    fox_positions = []
    for entity in world.query().with_all([Position, FoxAI]).execute_entities():
        pos = entity.get_component(Position)
        fox_positions.append((pos.x, pos.y))

    for _ in range(max_attempts):
        x, y = get_random_position(width, height)

        # Check distance from all foxes
        safe = True
        for fx, fy in fox_positions:
            dist = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5
            if dist < SAFE_SPAWN_DISTANCE:
                safe = False
                break

        if safe:
            # Also check for overlaps with other entities
            overlaps = False
            for entity in world.query().with_all([Position, BoundingBox]).execute_entities():
                pos = entity.get_component(Position)
                bbox = entity.get_component(BoundingBox)
                if rectangles_overlap(x, y, width, height, pos.x, pos.y, bbox.width, bbox.height):
                    overlaps = True
                    break

            if not overlaps:
                return x, y

    # Fallback: return any random position
    return get_random_position(width, height)


def spawn_initial_entities(world: World) -> None:
    """Spawn all initial entities at random non-overlapping positions."""
    # Randomize entity counts
    rabbit_count = random.randint(RABBIT_COUNT_MIN, RABBIT_COUNT_MAX)
    fox_count = random.randint(FOX_COUNT_MIN, FOX_COUNT_MAX)
    tree_count = random.randint(TREE_COUNT_MIN, TREE_COUNT_MAX)
    stone_count = random.randint(STONE_COUNT_MIN, STONE_COUNT_MAX)
    flower_count = random.randint(FLOWER_COUNT_MIN, FLOWER_COUNT_MAX)

    # Spawn trees first (largest static obstacles)
    for _ in range(tree_count):
        pos = find_non_overlapping_position(world, TREE_SIZE, TREE_SIZE)
        if pos:
            world.spawn(ENTITY_TREE, {Position: Position(x=pos[0], y=pos[1])})

    # Spawn stones
    for _ in range(stone_count):
        pos = find_non_overlapping_position(world, STONE_SIZE, STONE_SIZE)
        if pos:
            world.spawn(ENTITY_STONE, {Position: Position(x=pos[0], y=pos[1])})

    # Spawn flowers with random colors
    for _ in range(flower_count):
        pos = find_non_overlapping_position(world, FLOWER_SIZE, FLOWER_SIZE)
        if pos:
            color = random.choice(FLOWER_COLORS)
            world.spawn(ENTITY_FLOWER, {
                Position: Position(x=pos[0], y=pos[1]),
                Color: Color(r=color[0], g=color[1], b=color[2]),
            })

    # Spawn foxes (before rabbits, so rabbits can avoid them)
    for _ in range(fox_count):
        pos = find_non_overlapping_position(world, FOX_SIZE, FOX_SIZE)
        if pos:
            world.spawn(ENTITY_FOX, {Position: Position(x=pos[0], y=pos[1])})

    # Spawn rabbits (after foxes, using safe positions)
    for _ in range(rabbit_count):
        pos = get_safe_position(world, RABBIT_SIZE, RABBIT_SIZE)
        world.spawn(ENTITY_RABBIT, {Position: Position(x=pos[0], y=pos[1])})

    # Spawn camera entity at center of world
    center_x = (WORLD_WIDTH - CAMERA_SIZE) / 2
    center_y = (WORLD_HEIGHT - CAMERA_SIZE) / 2
    world.spawn(ENTITY_CAMERA, {Position: Position(x=center_x, y=center_y)})

    print(f"Spawned: {rabbit_count} rabbits, {fox_count} foxes, "
          f"{tree_count} trees, {stone_count} stones, {flower_count} flowers")
