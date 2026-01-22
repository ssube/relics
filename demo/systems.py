"""ECS systems for the ecosystem demo."""

import math
import random
from typing import Any, Optional

import pygame

from relics import RunOrder, System, World

from demo.camera import Camera
from demo.components import (
    BoundingBox,
    CameraInput,
    CameraMarker,
    Consumable,
    FlowerMarker,
    FoxAI,
    FoxState,
    Position,
    RabbitAI,
    RabbitState,
    Sprite,
    Velocity,
)
from demo.config import (
    CAMERA_SPEED,
    COLORS,
    ENTITY_CAMERA,
    ENTITY_FLOWER,
    FLOWER_SIZE,
    FOX_SIGHT_RANGE,
    RABBIT_FLEE_RANGE,
    RABBIT_SIZE,
    RABBIT_SPEED,
    FOX_SPEED,
    SAFE_SPAWN_DISTANCE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
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

    def process(self, entities, components, delta):
        # Get all fox positions
        fox_positions = []
        for fox in self.world.query().with_all([Position, FoxAI]).execute_entities():
            fox_pos = fox.get_component(Position)
            fox_positions.append((fox_pos.x, fox_pos.y))

        # Get all flower positions
        flower_data = []
        for flower in self.world.query().with_all([Position, FlowerMarker]).execute_entities():
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

    If chasing and target out of SIGHT_RANGE -> stop chasing
    If not chasing and rabbit in SIGHT_RANGE -> start chasing
    Chase: move toward target rabbit
    """

    def query(self):
        return self.q.with_all([Position, FoxAI, Velocity])

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

            # If currently chasing, check if target is still valid
            if ai.state == FoxState.CHASING and ai.target_id is not None:
                # Find target rabbit
                target_found = False
                for rabbit_id, rx, ry in rabbit_data:
                    if rabbit_id == ai.target_id:
                        target_dist = distance(pos.x, pos.y, rx, ry)
                        if target_dist <= ai.sight_range:
                            # Continue chasing
                            target_found = True
                            chase_dir_x = rx - pos.x
                            chase_dir_y = ry - pos.y
                            norm_x, norm_y = normalize(chase_dir_x, chase_dir_y)
                            vel.vx = norm_x * FOX_SPEED
                            vel.vy = norm_y * FOX_SPEED
                        break

                if not target_found:
                    # Lost target - stop chasing
                    ai.state = FoxState.IDLE
                    ai.target_id = None
                    vel.vx = 0
                    vel.vy = 0
                continue

            # Not chasing - look for nearby rabbits
            nearest_rabbit = None
            nearest_dist = float('inf')

            for rabbit_id, rx, ry in rabbit_data:
                dist = distance(pos.x, pos.y, rx, ry)
                if dist < ai.sight_range and dist < nearest_dist:
                    nearest_dist = dist
                    nearest_rabbit = (rabbit_id, rx, ry)

            if nearest_rabbit:
                # Start chasing
                ai.state = FoxState.CHASING
                ai.target_id = nearest_rabbit[0]
                chase_dir_x = nearest_rabbit[1] - pos.x
                chase_dir_y = nearest_rabbit[2] - pos.y
                norm_x, norm_y = normalize(chase_dir_x, chase_dir_y)
                vel.vx = norm_x * FOX_SPEED
                vel.vy = norm_y * FOX_SPEED
            else:
                # Idle - slow down
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
        return self.q.with_all([CameraMarker, CameraInput, Velocity])

    def deps(self):
        return {RunOrder.AFTER: [RabbitAISystem, FoxAISystem]}

    def process(self, entities, components, delta):
        for camera in entities:
            camera_input = camera.get_component(CameraInput)
            vel = camera.get_component(Velocity)

            # Convert input to velocity
            vel.vx = 0
            vel.vy = 0

            if camera_input.move_left:
                vel.vx -= CAMERA_SPEED
            if camera_input.move_right:
                vel.vx += CAMERA_SPEED
            if camera_input.move_up:
                vel.vy -= CAMERA_SPEED
            if camera_input.move_down:
                vel.vy += CAMERA_SPEED

            # Normalize diagonal movement
            if vel.vx != 0 and vel.vy != 0:
                norm_x, norm_y = normalize(vel.vx, vel.vy)
                vel.vx = norm_x * CAMERA_SPEED
                vel.vy = norm_y * CAMERA_SPEED


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

            # Special handling for camera - use screen size for bounds
            if entity.has_component(CameraMarker):
                max_x = WORLD_WIDTH - SCREEN_WIDTH
                max_y = WORLD_HEIGHT - SCREEN_HEIGHT
            else:
                max_x = WORLD_WIDTH - bbox.width
                max_y = WORLD_HEIGHT - bbox.height

            pos.x = max(0, min(pos.x, max_x))
            pos.y = max(0, min(pos.y, max_y))


class CollisionSystem(System):
    """
    Collision system - handles entity interactions.

    Fox-Rabbit: AABB collision -> respawn rabbit at safe location
    Rabbit-Flower: AABB collision -> remove flower, spawn new one
    """

    def query(self):
        return self.q.with_all([Position, BoundingBox])

    def deps(self):
        return {RunOrder.AFTER: [BoundsSystem]}

    def process(self, entities, components, delta):
        # Get foxes and rabbits for collision detection
        foxes = []
        rabbits = []
        flowers = []

        for entity in entities:
            if entity.has_component(FoxAI):
                pos = entity.get_component(Position)
                bbox = entity.get_component(BoundingBox)
                foxes.append((entity, pos.x, pos.y, bbox.width, bbox.height))
            elif entity.has_component(RabbitAI):
                pos = entity.get_component(Position)
                bbox = entity.get_component(BoundingBox)
                rabbits.append((entity, pos.x, pos.y, bbox.width, bbox.height))
            elif entity.has_component(FlowerMarker):
                pos = entity.get_component(Position)
                bbox = entity.get_component(BoundingBox)
                flowers.append((entity, pos.x, pos.y, bbox.width, bbox.height))

        # Check fox-rabbit collisions
        for fox, fx, fy, fw, fh in foxes:
            for rabbit, rx, ry, rw, rh in rabbits:
                if self._aabb_collision(fx, fy, fw, fh, rx, ry, rw, rh):
                    # Respawn rabbit at safe location
                    self._respawn_rabbit(rabbit)

        # Check rabbit-flower collisions
        for rabbit, rx, ry, rw, rh in rabbits:
            for flower, flx, fly, flw, flh in flowers:
                if self._aabb_collision(rx, ry, rw, rh, flx, fly, flw, flh):
                    # Remove flower and spawn new one
                    self._consume_flower(flower)

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

        # Spawn new flower at random position
        x = random.uniform(0, WORLD_WIDTH - FLOWER_SIZE)
        y = random.uniform(0, WORLD_HEIGHT - FLOWER_SIZE)
        self.world.spawn(ENTITY_FLOWER, {Position: Position(x=x, y=y)})


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
        for entity in self.world.query().with_all([CameraMarker, Position]).execute_entities():
            pos = entity.get_component(Position)
            self.camera.x = pos.x
            self.camera.y = pos.y
            self.camera.clamp_to_world()
            break

        # Query all renderable entities
        renderables = []
        for entity in self.world.query().with_all([Position, Sprite, BoundingBox]).execute_entities():
            # Skip camera entity
            if entity.has_component(CameraMarker):
                continue

            pos = entity.get_component(Position)
            sprite = entity.get_component(Sprite)
            bbox = entity.get_component(BoundingBox)

            # Frustum culling - only render visible entities
            if self.camera.is_visible(pos.x, pos.y, bbox.width, bbox.height):
                renderables.append((pos, sprite, bbox))

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
        for pos, sprite, bbox in renderables:
            screen_x, screen_y = self.camera.world_to_screen(pos.x, pos.y)
            color = COLORS.get(sprite.entity_type.upper(), (255, 0, 255))
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

        for entity in self.world.query().with_all([CameraMarker, CameraInput]).execute_entities():
            camera_input = entity.get_component(CameraInput)

            camera_input.move_left = keys[pygame.K_a]
            camera_input.move_right = keys[pygame.K_d]
            camera_input.move_up = keys[pygame.K_w]
            camera_input.move_down = keys[pygame.K_s]
            break
