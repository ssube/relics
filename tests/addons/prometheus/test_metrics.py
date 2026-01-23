"""Tests for Prometheus metric definitions."""

from prometheus_client import Counter, Gauge, Histogram, Info

from relics.addons.prometheus import (
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


class TestMetricTypes:
    """Tests for metric type definitions."""

    def test_world_info_is_info(self) -> None:
        """Test that WORLD_INFO is an Info metric."""
        assert isinstance(WORLD_INFO, Info)

    def test_entity_count_is_gauge(self) -> None:
        """Test that ENTITY_COUNT is a Gauge."""
        assert isinstance(ENTITY_COUNT, Gauge)

    def test_entities_by_prefab_is_gauge(self) -> None:
        """Test that ENTITIES_BY_PREFAB is a Gauge."""
        assert isinstance(ENTITIES_BY_PREFAB, Gauge)

    def test_entities_by_component_is_gauge(self) -> None:
        """Test that ENTITIES_BY_COMPONENT is a Gauge."""
        assert isinstance(ENTITIES_BY_COMPONENT, Gauge)

    def test_system_count_is_gauge(self) -> None:
        """Test that SYSTEM_COUNT is a Gauge."""
        assert isinstance(SYSTEM_COUNT, Gauge)

    def test_system_execution_time_is_histogram(self) -> None:
        """Test that SYSTEM_EXECUTION_TIME is a Histogram."""
        assert isinstance(SYSTEM_EXECUTION_TIME, Histogram)

    def test_tick_duration_is_histogram(self) -> None:
        """Test that TICK_DURATION is a Histogram."""
        assert isinstance(TICK_DURATION, Histogram)

    def test_tick_count_is_counter(self) -> None:
        """Test that TICK_COUNT is a Counter."""
        assert isinstance(TICK_COUNT, Counter)

    def test_observer_count_is_gauge(self) -> None:
        """Test that OBSERVER_COUNT is a Gauge."""
        assert isinstance(OBSERVER_COUNT, Gauge)

    def test_observer_queue_length_is_gauge(self) -> None:
        """Test that OBSERVER_QUEUE_LENGTH is a Gauge."""
        assert isinstance(OBSERVER_QUEUE_LENGTH, Gauge)

    def test_observer_events_processed_is_counter(self) -> None:
        """Test that OBSERVER_EVENTS_PROCESSED is a Counter."""
        assert isinstance(OBSERVER_EVENTS_PROCESSED, Counter)

    def test_index_count_is_gauge(self) -> None:
        """Test that INDEX_COUNT is a Gauge."""
        assert isinstance(INDEX_COUNT, Gauge)

    def test_index_entity_count_is_gauge(self) -> None:
        """Test that INDEX_ENTITY_COUNT is a Gauge."""
        assert isinstance(INDEX_ENTITY_COUNT, Gauge)

    def test_relationship_count_is_gauge(self) -> None:
        """Test that RELATIONSHIP_COUNT is a Gauge."""
        assert isinstance(RELATIONSHIP_COUNT, Gauge)

    def test_relationships_by_type_is_gauge(self) -> None:
        """Test that RELATIONSHIPS_BY_TYPE is a Gauge."""
        assert isinstance(RELATIONSHIPS_BY_TYPE, Gauge)

    def test_component_types_count_is_gauge(self) -> None:
        """Test that COMPONENT_TYPES_COUNT is a Gauge."""
        assert isinstance(COMPONENT_TYPES_COUNT, Gauge)

    def test_prefab_count_is_gauge(self) -> None:
        """Test that PREFAB_COUNT is a Gauge."""
        assert isinstance(PREFAB_COUNT, Gauge)

    def test_world_epoch_is_gauge(self) -> None:
        """Test that WORLD_EPOCH is a Gauge."""
        assert isinstance(WORLD_EPOCH, Gauge)


class TestMetricLabels:
    """Tests for metric label definitions."""

    def test_entity_count_has_world_id_label(self) -> None:
        """Test that ENTITY_COUNT has world_id label."""
        labels = ENTITY_COUNT._labelnames
        assert "world_id" in labels

    def test_entities_by_prefab_has_labels(self) -> None:
        """Test that ENTITIES_BY_PREFAB has correct labels."""
        labels = ENTITIES_BY_PREFAB._labelnames
        assert "world_id" in labels
        assert "prefab" in labels

    def test_entities_by_component_has_labels(self) -> None:
        """Test that ENTITIES_BY_COMPONENT has correct labels."""
        labels = ENTITIES_BY_COMPONENT._labelnames
        assert "world_id" in labels
        assert "component" in labels

    def test_system_execution_time_has_labels(self) -> None:
        """Test that SYSTEM_EXECUTION_TIME has correct labels."""
        labels = SYSTEM_EXECUTION_TIME._labelnames
        assert "world_id" in labels
        assert "system_name" in labels

    def test_index_entity_count_has_labels(self) -> None:
        """Test that INDEX_ENTITY_COUNT has correct labels."""
        labels = INDEX_ENTITY_COUNT._labelnames
        assert "world_id" in labels
        assert "index_name" in labels

    def test_relationships_by_type_has_labels(self) -> None:
        """Test that RELATIONSHIPS_BY_TYPE has correct labels."""
        labels = RELATIONSHIPS_BY_TYPE._labelnames
        assert "world_id" in labels
        assert "edge_type" in labels

    def test_observer_events_has_labels(self) -> None:
        """Test that OBSERVER_EVENTS_PROCESSED has correct labels."""
        labels = OBSERVER_EVENTS_PROCESSED._labelnames
        assert "world_id" in labels
        assert "event_type" in labels


class TestMetricOperations:
    """Tests for metric operations."""

    def test_gauge_can_set_value(self) -> None:
        """Test that gauge metrics can set values."""
        ENTITY_COUNT.labels(world_id="test_set").set(42)
        value = ENTITY_COUNT.labels(world_id="test_set")._value.get()
        assert value == 42

    def test_counter_can_increment(self) -> None:
        """Test that counter metrics can increment."""
        initial = TICK_COUNT.labels(world_id="test_inc")._value.get()
        TICK_COUNT.labels(world_id="test_inc").inc()
        after = TICK_COUNT.labels(world_id="test_inc")._value.get()
        assert after == initial + 1

    def test_histogram_can_observe(self) -> None:
        """Test that histogram metrics can observe values."""
        # This should not raise
        TICK_DURATION.labels(world_id="test_obs").observe(0.016)
        SYSTEM_EXECUTION_TIME.labels(
            world_id="test_obs", system_name="TestSystem"
        ).observe(0.001)
