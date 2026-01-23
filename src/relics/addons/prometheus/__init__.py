"""Prometheus metrics addon for Relics ECS framework.

This addon provides Prometheus-compatible metrics for monitoring
Relics worlds in production environments.

Components:
    - WorldMetricsCollector: Collects metrics from a World instance
    - MetricsServer: HTTP server exposing /metrics endpoint

Metrics exposed:
    - relics_entities_total: Total entity count
    - relics_entities_by_prefab: Entities per prefab type
    - relics_entities_by_component: Entities per component type
    - relics_systems_total: Registered system count
    - relics_system_execution_seconds: System execution time histogram
    - relics_observers_total: Registered observer count
    - relics_observer_queue_length: Pending observer events
    - relics_indexes_total: Registered index count
    - relics_index_entities: Entities per index
    - relics_relationships_total: Total relationship count
    - relics_tick_duration_seconds: World tick duration histogram
    - relics_world_epoch: Current world epoch/tick number

Example - Basic Usage:
    >>> from relics import World
    >>> from relics.addons.prometheus import WorldMetricsCollector, MetricsServer
    >>>
    >>> # Create world and collector
    >>> world = World()
    >>> collector = WorldMetricsCollector(world, world_id="game_server")
    >>>
    >>> # Start metrics server
    >>> server = MetricsServer(port=8000)
    >>> server.start()
    >>>
    >>> # In game loop
    >>> while running:
    ...     world.tick(0.016)
    ...     collector.collect()  # Update metrics
    >>>
    >>> server.stop()

Example - Auto-Collection:
    >>> # Enable automatic metrics collection on each tick
    >>> collector = WorldMetricsCollector(
    ...     world,
    ...     world_id="game_server",
    ...     collect_on_tick=True,  # Auto-collect and record tick duration
    ... )
    >>>
    >>> # Metrics are automatically updated each tick
    >>> while running:
    ...     world.tick(0.016)

Example - Get Metrics Programmatically:
    >>> from relics.addons.prometheus import get_metrics_text
    >>>
    >>> # Get metrics in Prometheus text format
    >>> metrics = get_metrics_text()
    >>> print(metrics)

Prometheus Configuration:
    Add this to your prometheus.yml:
    ```yaml
    scrape_configs:
      - job_name: 'relics'
        static_configs:
          - targets: ['localhost:8000']
    ```
"""

from .collector import WorldMetricsCollector
from .metrics import (
    COMPONENT_TYPES_COUNT,
    ENTITIES_BY_COMPONENT,
    ENTITIES_BY_PREFAB,
    ENTITY_COUNT,
    INDEX_COUNT,
    INDEX_ENTITY_COUNT,
    OBSERVER_COUNT,
    OBSERVER_EVENTS_PROCESSED,
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
from .server import MetricsServer, get_content_type, get_metrics_text

__all__ = [
    # Collector
    "WorldMetricsCollector",
    # Server
    "MetricsServer",
    "get_metrics_text",
    "get_content_type",
    # Metrics - Info
    "WORLD_INFO",
    # Metrics - Entities
    "ENTITY_COUNT",
    "ENTITIES_BY_PREFAB",
    "ENTITIES_BY_COMPONENT",
    # Metrics - Systems
    "SYSTEM_COUNT",
    "SYSTEM_EXECUTION_TIME",
    # Metrics - Observers
    "OBSERVER_COUNT",
    "OBSERVER_QUEUE_LENGTH",
    "OBSERVER_EVENTS_PROCESSED",
    # Metrics - Indexes
    "INDEX_COUNT",
    "INDEX_ENTITY_COUNT",
    # Metrics - Relationships
    "RELATIONSHIP_COUNT",
    "RELATIONSHIPS_BY_TYPE",
    # Metrics - World State
    "WORLD_EPOCH",
    "TICK_DURATION",
    "TICK_COUNT",
    "COMPONENT_TYPES_COUNT",
    "PREFAB_COUNT",
]
