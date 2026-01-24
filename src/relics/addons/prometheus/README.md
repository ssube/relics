# Prometheus Metrics Addon

Prometheus-compatible metrics for monitoring Relics worlds in production environments.

## Installation

```bash
pip install relics[prometheus]
```

## Quick Start

```python
from relics import World
from relics.addons.prometheus import WorldMetricsCollector, MetricsServer

# Create world and collector
world = World()
collector = WorldMetricsCollector(world, world_id="game_server")

# Start metrics server
server = MetricsServer(port=8000)
server.start()

# Game loop
while running:
    world.tick(0.016)
    collector.collect()  # Update metrics

server.stop()
```

## Features

- **HTTP metrics endpoint** at `/metrics` in Prometheus text format
- **Automatic collection** option with `collect_on_tick=True`
- **World identification** for multi-world deployments
- **Histogram metrics** for timing data

## Metrics Exposed

### Entity Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `relics_entities_total` | Gauge | Total entity count |
| `relics_entities_by_prefab` | Gauge | Entities per prefab type |
| `relics_entities_by_component` | Gauge | Entities per component type |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `relics_systems_total` | Gauge | Registered system count |
| `relics_system_execution_seconds` | Histogram | System execution time |

### Observer Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `relics_observers_total` | Gauge | Registered observer count |
| `relics_observer_queue_length` | Gauge | Pending observer events |
| `relics_observer_events_processed` | Counter | Total events processed |

### Index Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `relics_indexes_total` | Gauge | Registered index count |
| `relics_index_entities` | Gauge | Entities per index |

### Relationship Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `relics_relationships_total` | Gauge | Total relationship count |
| `relics_relationships_by_type` | Gauge | Relationships per edge type |

### World State Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `relics_world_epoch` | Gauge | Current world epoch/tick number |
| `relics_tick_duration_seconds` | Histogram | World tick duration |
| `relics_tick_count` | Counter | Total ticks processed |

## Usage Examples

### Auto-Collection Mode

```python
# Enable automatic metrics collection on each tick
collector = WorldMetricsCollector(
    world,
    world_id="game_server",
    collect_on_tick=True,  # Auto-collect and record tick duration
)

# Metrics are automatically updated each tick
while running:
    world.tick(0.016)
```

### Get Metrics Programmatically

```python
from relics.addons.prometheus import get_metrics_text

# Get metrics in Prometheus text format
metrics = get_metrics_text()
print(metrics)
```

### Custom Metrics Server Port

```python
server = MetricsServer(port=9090)
server.start()
```

## Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'relics'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 5s
```

## API Reference

### WorldMetricsCollector

```python
collector = WorldMetricsCollector(
    world,                    # World instance to monitor
    world_id="my_world",      # Identifier for this world
    collect_on_tick=False,    # Auto-collect on tick
)

collector.collect()           # Manually collect metrics
```

### MetricsServer

```python
server = MetricsServer(port=8000)
server.start()                # Start HTTP server
server.stop()                 # Stop HTTP server
```

### Utility Functions

```python
from relics.addons.prometheus import get_metrics_text, get_content_type

text = get_metrics_text()     # Get metrics in Prometheus format
content_type = get_content_type()  # Get correct Content-Type header
```
