"""Prometheus metric definitions for Relics ECS framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram, Info

if TYPE_CHECKING:
    pass

# World identification
WORLD_INFO = Info(
    "relics_world",
    "Information about the Relics world instance",
)

# Entity metrics
ENTITY_COUNT = Gauge(
    "relics_entities_total",
    "Total number of entities in the world",
    ["world_id"],
)

ENTITIES_BY_PREFAB = Gauge(
    "relics_entities_by_prefab",
    "Number of entities per prefab type",
    ["world_id", "prefab"],
)

ENTITIES_BY_COMPONENT = Gauge(
    "relics_entities_by_component",
    "Number of entities per component type",
    ["world_id", "component"],
)

# Index metrics
INDEX_COUNT = Gauge(
    "relics_indexes_total",
    "Total number of indexes registered",
    ["world_id"],
)

INDEX_ENTITY_COUNT = Gauge(
    "relics_index_entities",
    "Number of entities in each index",
    ["world_id", "index_name"],
)

# System metrics
SYSTEM_COUNT = Gauge(
    "relics_systems_total",
    "Total number of systems registered",
    ["world_id"],
)

SYSTEM_EXECUTION_TIME = Histogram(
    "relics_system_execution_seconds",
    "Time spent executing each system",
    ["world_id", "system_name"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)

TICK_DURATION = Histogram(
    "relics_tick_duration_seconds",
    "Duration of world tick operations",
    ["world_id"],
    buckets=(0.001, 0.005, 0.01, 0.016, 0.033, 0.05, 0.1, 0.5, 1.0),
)

TICK_COUNT = Counter(
    "relics_ticks_total",
    "Total number of world ticks",
    ["world_id"],
)

# Observer metrics
OBSERVER_COUNT = Gauge(
    "relics_observers_total",
    "Total number of observers registered",
    ["world_id"],
)

OBSERVER_QUEUE_LENGTH = Gauge(
    "relics_observer_queue_length",
    "Current length of the observer event queue",
    ["world_id"],
)

OBSERVER_EVENTS_PROCESSED = Counter(
    "relics_observer_events_total",
    "Total observer events processed",
    ["world_id", "event_type"],
)

# Relationship metrics
RELATIONSHIP_COUNT = Gauge(
    "relics_relationships_total",
    "Total number of relationships in the world",
    ["world_id"],
)

RELATIONSHIPS_BY_TYPE = Gauge(
    "relics_relationships_by_type",
    "Number of relationships per edge type",
    ["world_id", "edge_type"],
)

# Component metrics
COMPONENT_TYPES_COUNT = Gauge(
    "relics_component_types_total",
    "Total number of component types registered",
    ["world_id"],
)

# Prefab metrics
PREFAB_COUNT = Gauge(
    "relics_prefabs_total",
    "Total number of prefabs registered",
    ["world_id"],
)

# World state
WORLD_EPOCH = Gauge(
    "relics_world_epoch",
    "Current world epoch/tick number",
    ["world_id"],
)
