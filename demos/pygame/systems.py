"""ECS systems for the ecosystem demo."""

import math
import random
from typing import Any, Optional

import pygame

from relics import Frequency, RunOrder, System, World

from demo.camera import Camera
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
    CAMERA_SPEED,
    COLORS,
    ENTITY_FLOWER,
    FLOWER_COLORS,
    FLOWER_SIZE,
    FOX_SPEED,
    RABBIT_FLEE_RANGE,
    RABBIT_SIZE,
    RABBIT_SPEED,
    SAFE_SPAWN_DISTANCE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def normalize(vx: float, vy: float) -> tuple[float, float]:
    """Normalize a vector to unit length."""
    mag = math.sqrt(vx * vx + vy * vy)
    if mag == 0:
        return 0.0, 0.0
    return vx / mag, vy / mag


class RabbitAISystem(System):
    """
    Rabbit AI system - handles flee/seek behavior.

    Priority 1: If fox within FLEE_RANGE -> flee (opposite direction)
    Priority 2: If flower exists -> seek nearest flower
    Else: idle (slow down)
    """

    def query(self):
        return self.q.with_all([Position, RabbitAI, Velocity])

    def frequency(self):
        return Frequency.every_n_ticks(5)

    def process(self, entities, components, delta):
        # Get all fox positions
        fox_positions = []
        for fox in self.world.query().with_all([Position, FoxAI]).execute_entities():
            fox_pos = fox.get_component(Position)
            fox_positions.append((fox_pos.x, fox_pos.y))

        # Get all flower positions
        flower_data = []
        for flower in self.world.query().with_all([Position, Consumable]).execute_entities():
            flower_pos = flower.get_component(Position)
            flower_data.append((flower.id, flower_pos.x, flower_pos.y))

        for rabbit in entities:
            pos = rabbit.get_component(Position)
            vel = rabbit.get_component(Velocity)
            ai = rabbit.get_component(RabbitAI)

            # Check for nearby foxes (highest priority - flee)
            nearest_fox_dist = float('inf')
            flee_dir_x, flee_dir_y = 0.0, 0.0

            for fx, fy in fox_positions:
                dist = distance(pos.x, pos.y, fx, fy)
                if dist < nearest_fox_dist:
                    nearest_fox_dist = dist
                    # Direction away from fox
                    flee_dir_x = pos.x - fx
                    flee_dir_y = pos.y - fy

            if nearest_fox_dist < RABBIT_FLEE_RANGE:
                # Flee from fox
                ai.state = RabbitState.FLEEING
                norm_x, norm_y = normalize(flee_dir_x, flee_dir_y)
                vel.vx = norm_x * RABBIT_SPEED
                vel.vy = norm_y * RABBIT_SPEED
                continue

            # No fox nearby - seek nearest flower
            if flower_data:
                nearest_flower = None
                nearest_flower_dist = float('inf')

                for flower_id, fx, fy in flower_data:
                    dist = distance(pos.x, pos.y, fx, fy)
                    if dist < nearest_flower_dist:
                        nearest_flower_dist = dist
                        nearest_flower = (fx, fy)

                if nearest_flower:
                    ai.state = RabbitState.SEEKING
                    seek_dir_x = nearest_flower[0] - pos.x
                    seek_dir_y = nearest_flower[1] - pos.y
                    norm_x, norm_y = normalize(seek_dir_x, seek_dir_y)
                    vel.vx = norm_x * RABBIT_SPEED
                    vel.vy = norm_y * RABBIT_SPEED
                    continue

            # No threats or targets - idle (slow down)
            ai.state = RabbitState.IDLE
            vel.vx *= 0.9
            vel.vy *= 0.9
            if abs(vel.vx) < 1:
                vel.vx = 0
            if abs(vel.vy) < 1:
                vel.vy = 0


class FoxAISystem(System):
    """
    Fox AI system - handles chase behavior.

    Always chases the nearest rabbit within sight range.
    """

    def query(self):
        return self.q.with_all([Position, FoxAI, Velocity])

    def frequency(self):
        return Frequency.every_n_ticks(5)

    def deps(self):
        return {}  # No dependencies, runs early

    def process(self, entities, components, delta):
        # Get all rabbit positions
        rabbit_data = []
        for rabbit in self.world.query().with_all([Position, RabbitAI]).execute_entities():
            rabbit_pos = rabbit.get_component(Position)
            rabbit_data.append((rabbit.id, rabbit_pos.x, rabbit_pos.y))

        for fox in entities:
            pos = fox.get_component(Position)
            vel = fox.get_component(Velocity)
            ai = fox.get_component(FoxAI)

            # Always find the nearest rabbit (allows switching to closer targets)
            nearest_rabbit = None
            nearest_dist = float('inf')

            for rabbit_id, rx, ry in rabbit_data:
                dist = distance(pos.x, pos.y, rx, ry)
                if dist < ai.sight_range and dist < nearest_dist:
                    nearest_dist = dist
                    nearest_rabbit = (rabbit_id, rx, ry)

            if nearest_rabbit:
                # Chase nearest rabbit
                ai.state = FoxState.CHASING
                ai.target_id = nearest_rabbit[0]
                chase_dir_x = nearest_rabbit[1] - pos.x
                chase_dir_y = nearest_rabbit[2] - pos.y
                norm_x, norm_y = normalize(chase_dir_x, chase_dir_y)
                vel.vx = norm_x * FOX_SPEED
                vel.vy = norm_y * FOX_SPEED
            else:
                # No rabbits in range - idle
                ai.state = FoxState.IDLE
                ai.target_id = None
                vel.vx *= 0.95
                vel.vy *= 0.95
                if abs(vel.vx) < 1:
                    vel.vx = 0
                if abs(vel.vy) < 1:
                    vel.vy = 0


class CameraSystem(System):
    """
    Camera system - converts input to movement.

    Takes input from Camera entity's CameraInput component
    and applies it to the Velocity component.
    """

    def query(self):
        return self.q.with_all([Viewport, CameraInput, Velocity])

    def deps(self):
        return {RunOrder.AFTER: [RabbitAISystem, FoxAISystem]}

    def process(self, entities, components, delta):
        for camera in entities:
            camera_input = camera.get_component(CameraInput)
            vel = camera.get_component(Velocity)

            # Apply sprint multiplier
            speed = CAMERA_SPEED * 2 if camera_input.sprint else CAMERA_SPEED

            # Convert input to velocity
            vel.vx = 0
            vel.vy = 0

            if camera_input.move_left:
                vel.vx -= speed
            if camera_input.move_right:
                vel.vx += speed
            if camera_input.move_up:
                vel.vy -= speed
            if camera_input.move_down:
                vel.vy += speed

            # Normalize diagonal movement
            if vel.vx != 0 and vel.vy != 0:
                norm_x, norm_y = normalize(vel.vx, vel.vy)
                vel.vx = norm_x * speed
                vel.vy = norm_y * speed


class MovementSystem(System):
    """
    Movement system - applies velocity to position.

    Runs after AI systems to apply calculated velocities.
    """

    def query(self):
        return self.q.with_all([Position, Velocity])

    def deps(self):
        return {RunOrder.AFTER: [RabbitAISystem, FoxAISystem, CameraSystem]}

    def process(self, entities, components, delta):
        for entity in entities:
            pos = entity.get_component(Position)
            vel = entity.get_component(Velocity)

            pos.x += vel.vx * delta
            pos.y += vel.vy * delta


class BoundsSystem(System):
    """
    Bounds system - keeps entities within world bounds.

    Runs after MovementSystem to clamp positions.
    """

    def query(self):
        return self.q.with_all([Position, BoundingBox])

    def deps(self):
        return {RunOrder.AFTER: [MovementSystem]}

    def process(self, entities, components, delta):
        for entity in entities:
            pos = entity.get_component(Position)
            bbox = entity.get_component(BoundingBox)

            # Special handling for camera - use viewport size for bounds
            if entity.has_component(Viewport):
                viewport = entity.get_component(Viewport)
                max_x = WORLD_WIDTH - viewport.width
                max_y = WORLD_HEIGHT - viewport.height
            else:
                max_x = WORLD_WIDTH - bbox.width
                max_y = WORLD_HEIGHT - bbox.height

            # Clamp position and zero velocity if hitting bounds
            old_x, old_y = pos.x, pos.y
            pos.x = max(0, min(pos.x, max_x))
            pos.y = max(0, min(pos.y, max_y))

            # Zero out velocity component when hitting bounds to prevent jittering
            if entity.has_component(Velocity):
                vel = entity.get_component(Velocity)
                if pos.x != old_x:  # Hit horizontal bound
                    vel.vx = 0
                if pos.y != old_y:  # Hit vertical bound
                    vel.vy = 0


class CollisionSystem(System):
    """
    Collision system - handles entity interactions.

    - Fox-Rabbit: AABB collision -> respawn rabbit at safe location
    - Rabbit-Flower: AABB collision -> remove flower, spawn new one
    - Mobile entities vs obstacles (trees/stones): push out of collision
    - Rabbit-Rabbit: separate overlapping rabbits
    """

    def query(self):
        return self.q.with_all([Position, BoundingBox])

    def deps(self):
        return {RunOrder.AFTER: [BoundsSystem]}

    def process(self, entities, components, delta):
        # Categorize entities
        mobile = []  # Entities that can move (have Velocity)
        foxes = []
        rabbits = []
        consumables = []  # Things that can be eaten (flowers)
        obstacles = []  # Trees and stones (static)

        for entity in entities:
            pos = entity.get_component(Position)
            bbox = entity.get_component(BoundingBox)

            if entity.has_component(FoxAI):
                foxes.append((entity, pos, bbox))
                mobile.append((entity, pos, bbox))
            elif entity.has_component(RabbitAI):
                rabbits.append((entity, pos, bbox))
                mobile.append((entity, pos, bbox))
            elif entity.has_component(Consumable):
                consumables.append((entity, pos, bbox))
            elif entity.has_component(Obstacle):
                obstacles.append((entity, pos, bbox))

        # Handle mobile entity vs obstacle collisions
        for entity, pos, bbox in mobile:
            for obs_entity, obs_pos, obs_bbox in obstacles:
                # Distance-squared early out (use max dimension as threshold)
                max_size = max(bbox.width, bbox.height, obs_bbox.width, obs_bbox.height)
                dx = pos.x - obs_pos.x
                dy = pos.y - obs_pos.y
                if dx * dx + dy * dy > (max_size * 2) ** 2:
                    continue

                if self._aabb_collision(
                    pos.x, pos.y, bbox.width, bbox.height,
                    obs_pos.x, obs_pos.y, obs_bbox.width, obs_bbox.height
                ):
                    self._push_out_of_collision(pos, bbox, obs_pos, obs_bbox)

        # Handle mobile-to-mobile collisions (all-to-all)
        for i, (entity1, pos1, bbox1) in enumerate(mobile):
            for entity2, pos2, bbox2 in mobile[i + 1:]:
                # Distance-squared early out
                max_size = max(bbox1.width, bbox1.height, bbox2.width, bbox2.height)
                dx = pos1.x - pos2.x
                dy = pos1.y - pos2.y
                if dx * dx + dy * dy > (max_size * 2) ** 2:
                    continue

                if self._aabb_collision(
                    pos1.x, pos1.y, bbox1.width, bbox1.height,
                    pos2.x, pos2.y, bbox2.width, bbox2.height
                ):
                    self._separate_entities(pos1, bbox1, pos2, bbox2)

        # Get game stats from camera entity
        stats = None
        for cam in self.world.query().with_all([Viewport, GameStats]).execute_entities():
            stats = cam.get_component(GameStats)
            break

        # Check fox-rabbit collisions (fox catches rabbit - special interaction)
        for fox, fox_pos, fox_bbox in foxes:
            for rabbit, rabbit_pos, rabbit_bbox in rabbits:
                if self._aabb_collision(
                    fox_pos.x, fox_pos.y, fox_bbox.width, fox_bbox.height,
                    rabbit_pos.x, rabbit_pos.y, rabbit_bbox.width, rabbit_bbox.height
                ):
                    print(f"[EVENT] Fox caught a rabbit! Rabbit respawning...")
                    self._respawn_rabbit(rabbit)
                    if stats:
                        stats.rabbits_eaten += 1

        # Check rabbit-consumable collisions (rabbit eats consumable - special interaction)
        for rabbit, rabbit_pos, rabbit_bbox in rabbits:
            for consumable, cons_pos, cons_bbox in consumables:
                if self._aabb_collision(
                    rabbit_pos.x, rabbit_pos.y, rabbit_bbox.width, rabbit_bbox.height,
                    cons_pos.x, cons_pos.y, cons_bbox.width, cons_bbox.height
                ):
                    print(f"[EVENT] Rabbit ate a flower! New flower spawning...")
                    self._consume_flower(consumable)
                    if stats:
                        stats.flowers_eaten += 1

    def _aabb_collision(
        self,
        x1: float, y1: float, w1: int, h1: int,
        x2: float, y2: float, w2: int, h2: int
    ) -> bool:
        """Check if two axis-aligned bounding boxes collide."""
        return (
            x1 < x2 + w2
            and x1 + w1 > x2
            and y1 < y2 + h2
            and y1 + h1 > y2
        )

    def _push_out_of_collision(self, pos, bbox, obs_pos, obs_bbox) -> None:
        """Push an entity out of collision with an obstacle."""
        # Calculate overlap on each axis
        overlap_left = (pos.x + bbox.width) - obs_pos.x
        overlap_right = (obs_pos.x + obs_bbox.width) - pos.x
        overlap_top = (pos.y + bbox.height) - obs_pos.y
        overlap_bottom = (obs_pos.y + obs_bbox.height) - pos.y

        # Find minimum overlap and push out on that axis
        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

        if min_overlap == overlap_left:
            pos.x = obs_pos.x - bbox.width
        elif min_overlap == overlap_right:
            pos.x = obs_pos.x + obs_bbox.width
        elif min_overlap == overlap_top:
            pos.y = obs_pos.y - bbox.height
        else:
            pos.y = obs_pos.y + obs_bbox.height

    def _separate_entities(self, pos1, bbox1, pos2, bbox2) -> None:
        """Separate two overlapping entities by pushing them apart."""
        # Calculate centers
        cx1 = pos1.x + bbox1.width / 2
        cy1 = pos1.y + bbox1.height / 2
        cx2 = pos2.x + bbox2.width / 2
        cy2 = pos2.y + bbox2.height / 2

        # Direction from entity 2 to entity 1
        dx = cx1 - cx2
        dy = cy1 - cy2
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0:
            # Entities at same position, push in random direction
            dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
            dist = math.sqrt(dx * dx + dy * dy)
            if dist == 0:
                dx, dy = 1, 0
                dist = 1

        # Normalize and push apart by half the overlap each
        dx /= dist
        dy /= dist
        push_dist = 2.0  # Small push to separate

        pos1.x += dx * push_dist
        pos1.y += dy * push_dist
        pos2.x -= dx * push_dist
        pos2.y -= dy * push_dist

    def _respawn_rabbit(self, rabbit) -> None:
        """Respawn rabbit at a safe location away from foxes."""
        # Get all fox positions
        fox_positions = []
        for fox in self.world.query().with_all([Position, FoxAI]).execute_entities():
            fox_pos = fox.get_component(Position)
            fox_positions.append((fox_pos.x, fox_pos.y))

        # Find safe position
        max_attempts = 100
        for _ in range(max_attempts):
            x = random.uniform(0, WORLD_WIDTH - RABBIT_SIZE)
            y = random.uniform(0, WORLD_HEIGHT - RABBIT_SIZE)

            safe = True
            for fx, fy in fox_positions:
                if distance(x, y, fx, fy) < SAFE_SPAWN_DISTANCE:
                    safe = False
                    break

            if safe:
                pos = rabbit.get_component(Position)
                pos.x = x
                pos.y = y
                # Reset velocity
                vel = rabbit.get_component(Velocity)
                vel.vx = 0
                vel.vy = 0
                return

        # Fallback: random position
        pos = rabbit.get_component(Position)
        pos.x = random.uniform(0, WORLD_WIDTH - RABBIT_SIZE)
        pos.y = random.uniform(0, WORLD_HEIGHT - RABBIT_SIZE)

    def _consume_flower(self, flower) -> None:
        """Remove flower and spawn a new one elsewhere."""
        # Remove the consumed flower
        self.world.remove(flower)

        # Spawn new flower at random position with random color
        x = random.uniform(0, WORLD_WIDTH - FLOWER_SIZE)
        y = random.uniform(0, WORLD_HEIGHT - FLOWER_SIZE)
        color = random.choice(FLOWER_COLORS)
        self.world.spawn(ENTITY_FLOWER, {
            Position: Position(x=x, y=y),
            Color: Color(r=color[0], g=color[1], b=color[2]),
        })


class RenderSystem:
    """
    Render system - draws entities to screen.

    This is not a standard ECS system because it needs direct
    access to pygame's screen surface and the camera.
    """

    def __init__(self, screen: pygame.Surface, camera: Camera, world: World):
        self.screen = screen
        self.camera = camera
        self.world = world

    def render(self) -> None:
        """Render all visible entities."""
        # Fill background with grass color
        self.screen.fill(COLORS["GRASS"])

        # Update camera position from camera entity
        for entity in self.world.query().with_all([Viewport, Position]).execute_entities():
            pos = entity.get_component(Position)
            viewport = entity.get_component(Viewport)
            self.camera.width = viewport.width
            self.camera.height = viewport.height
            self.camera.x = pos.x
            self.camera.y = pos.y
            self.camera.clamp_to_world()
            break

        # Query all renderable entities
        renderables = []
        for entity in self.world.query().with_all([Position, Sprite, BoundingBox]).execute_entities():
            # Skip camera entity
            if entity.has_component(Viewport):
                continue

            pos = entity.get_component(Position)
            sprite = entity.get_component(Sprite)
            bbox = entity.get_component(BoundingBox)

            # Get color from Color component if present, otherwise from global COLORS dict
            if entity.has_component(Color):
                color_comp = entity.get_component(Color)
                color = (color_comp.r, color_comp.g, color_comp.b)
            else:
                color = COLORS.get(sprite.entity_type.upper(), (255, 0, 255))

            # Frustum culling - only render visible entities
            if self.camera.is_visible(pos.x, pos.y, bbox.width, bbox.height):
                renderables.append((pos, sprite, bbox, color))

        # Sort by entity type for consistent layering (trees behind animals)
        layer_order = {
            "tree": 0,
            "stone": 1,
            "flower": 2,
            "rabbit": 3,
            "fox": 4,
        }
        renderables.sort(key=lambda r: layer_order.get(r[1].entity_type, 5))

        # Draw entities
        for pos, sprite, bbox, color in renderables:
            screen_x, screen_y = self.camera.world_to_screen(pos.x, pos.y)
            pygame.draw.rect(
                self.screen,
                color,
                (int(screen_x), int(screen_y), bbox.width, bbox.height)
            )


class InputSystem:
    """
    Input system - reads pygame input and buffers it on camera entity.

    This is not a standard ECS system because it needs direct
    access to pygame's input state.
    """

    def __init__(self, world: World):
        self.world = world

    def update(self) -> None:
        """Read input and update camera's CameraInput component."""
        keys = pygame.key.get_pressed()

        for entity in self.world.query().with_all([Viewport, CameraInput]).execute_entities():
            camera_input = entity.get_component(CameraInput)

            camera_input.move_left = keys[pygame.K_a]
            camera_input.move_right = keys[pygame.K_d]
            camera_input.move_up = keys[pygame.K_w]
            camera_input.move_down = keys[pygame.K_s]
            camera_input.sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            break
