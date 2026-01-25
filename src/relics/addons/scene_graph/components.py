"""Scene graph components for nodes and transforms."""

from __future__ import annotations

from dataclasses import field

from pydantic.dataclasses import dataclass

from relics.monitored import monitored
from relics.types import Component

from .types import Mat4, Quat, Vec3


@monitored
@dataclass
class NodeName(Component):
    """Local name of a scene node within its parent.

    This component identifies an entity as a scene node. The name
    should be unique among siblings (children of the same parent).

    Attributes:
        name: The local name (e.g., "room_1", "table", "spawn_point").
    """

    name: str


@monitored
@dataclass
class NodePath(Component):
    """Full materialized path from root to this node.

    This component is managed by the scene graph system. Do not
    set it manually - it will be automatically updated when
    nodes are created, renamed, or reparented.

    Attributes:
        path: The full path (e.g., "/world/room_1/table").
    """

    path: str


@monitored
@dataclass
class LocalTransform(Component):
    """Transform relative to parent node.

    Defines the position, rotation, and scale of a node relative
    to its parent. For root nodes, this is relative to the world origin.

    Attributes:
        position: Position offset from parent.
        rotation: Rotation relative to parent.
        scale: Scale factors (1.0 = no scaling).
    """

    position: Vec3 = field(default_factory=Vec3.zero)
    rotation: Quat = field(default_factory=Quat.identity)
    scale: Vec3 = field(default_factory=Vec3.one)

    @staticmethod
    def identity() -> "LocalTransform":
        """Create identity transform (no translation, rotation, or scale)."""
        return LocalTransform(
            position=Vec3.zero(),
            rotation=Quat.identity(),
            scale=Vec3.one(),
        )


@monitored
@dataclass
class WorldTransform(Component):
    """Computed absolute transform in world space.

    This component is managed by the scene graph system. It is
    automatically updated when LocalTransform changes or when
    the node is reparented.

    Attributes:
        position: Absolute position in world space.
        rotation: Absolute rotation in world space.
        scale: Absolute scale in world space.
        matrix: Cached composite transformation matrix.
    """

    position: Vec3 = field(default_factory=Vec3.zero)
    rotation: Quat = field(default_factory=Quat.identity)
    scale: Vec3 = field(default_factory=Vec3.one)
    matrix: Mat4 = field(default_factory=Mat4.identity)

    @staticmethod
    def identity() -> "WorldTransform":
        """Create identity world transform."""
        return WorldTransform(
            position=Vec3.zero(),
            rotation=Quat.identity(),
            scale=Vec3.one(),
            matrix=Mat4.identity(),
        )

    @staticmethod
    def from_local(local: LocalTransform) -> "WorldTransform":
        """Create world transform from local transform (for root nodes)."""
        return WorldTransform(
            position=local.position,
            rotation=local.rotation,
            scale=local.scale,
            matrix=Mat4.from_trs(local.position, local.rotation, local.scale),
        )


@monitored
@dataclass
class LocalOffset(Component):
    """Optional offset for entities relative to their attached node.

    When an entity is attached to a node via AttachedTo, this
    component defines an additional offset from the node's transform.

    Attributes:
        position: Position offset from node.
        rotation: Rotation offset from node.
        scale: Scale multiplier.
    """

    position: Vec3 = field(default_factory=Vec3.zero)
    rotation: Quat = field(default_factory=Quat.identity)
    scale: Vec3 = field(default_factory=Vec3.one)

    @staticmethod
    def identity() -> "LocalOffset":
        """Create identity offset (no offset)."""
        return LocalOffset(
            position=Vec3.zero(),
            rotation=Quat.identity(),
            scale=Vec3.one(),
        )
