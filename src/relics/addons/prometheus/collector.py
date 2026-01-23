"""Prometheus metrics collector for Relics worlds."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, Dict, Optional, Set

from .metrics import (
    COMPONENT_TYPES_COUNT,
    ENTITIES_BY_COMPONENT,
    ENTITIES_BY_PREFAB,
    ENTITY_COUNT,
    INDEX_COUNT,
    INDEX_ENTITY_COUNT,
    OBSERVER_COUNT,
    OBSERVER_QUEUE_LENGTH,
    PREFAB_COUNT,
    RELATIONSHIP_COUNT,
    RELATIONSHIPS_BY_TYPE,
    SYSTEM_COUNT,
    SYSTEM_EXECUTION_TIME,
    TICK_COUNT,
    TICK_DURATION,
    WORLD_EPOCH,
    WORLD_INFO,
)

if TYPE_CHECKING:
    from relics.world import World


class WorldMetricsCollector:
    """Collects and exposes Prometheus metrics for a Relics world.

    This collector can be attached to a World instance to automatically
    track and expose metrics about entities, systems, observers, and more.

    Example:
        >>> from relics import World
        >>> from relics.addons.prometheus import WorldMetricsCollector
        >>>
        >>> world = World()
        >>> collector = WorldMetricsCollector(world, world_id="game_server")
        >>> collector.collect()  # Update all metrics
        >>>
        >>> # Or auto-collect on each tick:
        >>> collector.enable_auto_collect()

    Attributes:
        world: The World instance to collect metrics from.
        world_id: Unique identifier for this world in metrics labels.
    """

    def __init__(
        self,
        world: "World",
        world_id: str = "default",
        collect_on_tick: bool = False,
    ) -> None:
        """Create a metrics collector for a world.

        Args:
            world: The World instance to collect metrics from.
            world_id: Unique identifier for labeling metrics.
            collect_on_tick: If True, automatically collect metrics on each tick.
        """
        self._world: Optional["World"] = world
        self._world_id = world_id
        self._collect_on_tick = collect_on_tick
        self._original_tick: Optional[Callable[..., None]] = None
        self._tracked_prefabs: Set[str] = set()
        self._tracked_components: Set[str] = set()
        self._tracked_indexes: Set[str] = set()
        self._tracked_edge_types: Set[str] = set()

        # Set world info
        WORLD_INFO.info(
            {
                "world_id": world_id,
                "version": "1.0",
            }
        )

        if collect_on_tick:
            self.enable_auto_collect()

    @property
    def world_id(self) -> str:
        """The unique identifier for this world."""
        return self._world_id

    def collect(self) -> None:
        """Collect all metrics from the world.

        This method updates all Prometheus metrics with current values
        from the attached world. Call this periodically or enable
        auto-collection with enable_auto_collect().

        Does nothing if the collector has been detached.
        """
        if self._world is None:
            return

        self._collect_entity_metrics()
        self._collect_system_metrics()
        self._collect_observer_metrics()
        self._collect_index_metrics()
        self._collect_relationship_metrics()
        self._collect_world_state_metrics()

    def _collect_entity_metrics(self) -> None:
        """Collect entity-related metrics."""
        if self._world is None:
            return

        # Total entity count
        ENTITY_COUNT.labels(world_id=self._world_id).set(len(self._world._entities))

        # Entities by prefab
        current_prefabs = set(self._world._prefab_index.keys())

        # Clear old prefabs that no longer exist
        for prefab in self._tracked_prefabs - current_prefabs:
            ENTITIES_BY_PREFAB.labels(world_id=self._world_id, prefab=prefab).set(0)

        # Update current prefabs
        for prefab, entity_ids in self._world._prefab_index.items():
            ENTITIES_BY_PREFAB.labels(world_id=self._world_id, prefab=prefab).set(
                len(entity_ids)
            )

        self._tracked_prefabs = current_prefabs

        # Entities by component type
        current_components = set(
            c.__name__ for c in self._world._component_index.keys()
        )

        # Clear old components
        for component in self._tracked_components - current_components:
            ENTITIES_BY_COMPONENT.labels(
                world_id=self._world_id, component=component
            ).set(0)

        # Update current components
        for comp_type, entity_ids in self._world._component_index.items():
            ENTITIES_BY_COMPONENT.labels(
                world_id=self._world_id, component=comp_type.__name__
            ).set(len(entity_ids))

        self._tracked_components = current_components

        # Component types count
        COMPONENT_TYPES_COUNT.labels(world_id=self._world_id).set(
            len(self._world._component_types)
        )

        # Prefab count
        PREFAB_COUNT.labels(world_id=self._world_id).set(len(self._world._prefabs))

    def _collect_system_metrics(self) -> None:
        """Collect system-related metrics."""
        if self._world is None:
            return

        SYSTEM_COUNT.labels(world_id=self._world_id).set(len(self._world._systems))

    def _collect_observer_metrics(self) -> None:
        """Collect observer-related metrics."""
        if self._world is None:
            return

        OBSERVER_COUNT.labels(world_id=self._world_id).set(len(self._world._observers))

        OBSERVER_QUEUE_LENGTH.labels(world_id=self._world_id).set(
            len(self._world._observer_queue)
        )

    def _collect_index_metrics(self) -> None:
        """Collect index-related metrics."""
        if self._world is None:
            return

        INDEX_COUNT.labels(world_id=self._world_id).set(len(self._world._indexes))

        current_indexes = set(self._world._indexes.keys())

        # Clear old indexes
        for index_name in self._tracked_indexes - current_indexes:
            INDEX_ENTITY_COUNT.labels(
                world_id=self._world_id, index_name=index_name
            ).set(0)

        # Update current indexes
        for index_name, index_view in self._world._indexes.items():
            try:
                INDEX_ENTITY_COUNT.labels(
                    world_id=self._world_id, index_name=index_name
                ).set(index_view.count())
            except Exception:
                # Index may not be initialized yet
                pass

        self._tracked_indexes = current_indexes

    def _collect_relationship_metrics(self) -> None:
        """Collect relationship-related metrics."""
        if self._world is None:
            return

        total_relationships = 0
        edge_type_counts: Dict[str, int] = {}

        for entity_id, edges_by_type in self._world._relationships.items():
            for edge_cls, targets in edges_by_type.items():
                edge_name = edge_cls.__name__
                count = len(targets)
                total_relationships += count
                edge_type_counts[edge_name] = edge_type_counts.get(edge_name, 0) + count

        RELATIONSHIP_COUNT.labels(world_id=self._world_id).set(total_relationships)

        current_edge_types = set(edge_type_counts.keys())

        # Clear old edge types
        for edge_type_name in self._tracked_edge_types - current_edge_types:
            RELATIONSHIPS_BY_TYPE.labels(
                world_id=self._world_id, edge_type=edge_type_name
            ).set(0)

        # Update current edge types
        for edge_type_name, count in edge_type_counts.items():
            RELATIONSHIPS_BY_TYPE.labels(
                world_id=self._world_id, edge_type=edge_type_name
            ).set(count)

        self._tracked_edge_types = current_edge_types

    def _collect_world_state_metrics(self) -> None:
        """Collect world state metrics."""
        if self._world is None:
            return

        WORLD_EPOCH.labels(world_id=self._world_id).set(self._world.epoch)

    def enable_auto_collect(self) -> None:
        """Enable automatic metrics collection on each world tick.

        This wraps the world's tick method to collect metrics and
        record tick duration automatically.
        """
        if self._world is None:
            return

        if self._original_tick is not None:
            return  # Already enabled

        original_tick = self._world.tick
        self._original_tick = original_tick

        def instrumented_tick(
            delta: float,
            *,
            include_groups: list[str] | None = None,
            exclude_groups: list[str] | None = None,
        ) -> None:
            start_time = time.perf_counter()

            # Call original tick with any group filtering
            original_tick(
                delta,
                include_groups=include_groups,
                exclude_groups=exclude_groups,
            )

            # Record tick duration
            duration = time.perf_counter() - start_time
            TICK_DURATION.labels(world_id=self._world_id).observe(duration)
            TICK_COUNT.labels(world_id=self._world_id).inc()

            # Collect all metrics
            self.collect()

        self._world.tick = instrumented_tick  # type: ignore[method-assign]

    def disable_auto_collect(self) -> None:
        """Disable automatic metrics collection.

        Restores the original tick method.
        """
        if self._world is None:
            return

        if self._original_tick is not None:
            self._world.tick = self._original_tick  # type: ignore[method-assign]
            self._original_tick = None

    def record_system_execution(self, system_name: str, duration: float) -> None:
        """Record the execution time of a system.

        Args:
            system_name: Name of the system.
            duration: Execution time in seconds.
        """
        SYSTEM_EXECUTION_TIME.labels(
            world_id=self._world_id, system_name=system_name
        ).observe(duration)

    def record_observer_event(self, event_type: str) -> None:
        """Record an observer event being processed.

        Args:
            event_type: Type of the event (e.g., "component_added").
        """
        from .metrics import OBSERVER_EVENTS_PROCESSED

        OBSERVER_EVENTS_PROCESSED.labels(
            world_id=self._world_id, event_type=event_type
        ).inc()

    def detach(self) -> None:
        """Detach the collector from the world.

        Disables auto-collection and cleans up.
        """
        self.disable_auto_collect()
        self._world = None
