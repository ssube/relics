# Relics Performance Benchmarks

This document provides performance benchmarks for the Relics ECS framework.

## Test Environment

### Hardware

| Component | Specification |
|-----------|---------------|
| CPU | AMD Ryzen 9 7940HS (8 cores, 16 threads) |
| Memory | 64 GB DDR5 |
| Architecture | x86_64 |

### Software

| Component | Version |
|-----------|---------|
| Python | 3.11.2 |
| OS | Linux 6.8.0-90-generic (Ubuntu 22.04) |
| Kernel | PREEMPT_DYNAMIC |

### Notes

- All benchmarks use seeded random for reproducibility
- Tests run single-threaded (Python GIL)
- Results may vary on different hardware; scale accordingly

## Quick Reference

| Operation | 100 entities | 10k entities | 1M entities |
|-----------|-------------|--------------|-------------|
| Spawn (simple) | 0.003 ms | 0.004 ms | 0.004 ms |
| Spawn (5 components) | 0.004 ms | 0.003 ms | 0.006 ms |
| Query (full scan) | 0.025 ms | 5.8 ms | 1,105 ms |
| Component access | 0.0002 ms | 0.0002 ms | 0.0002 ms |
| Tick (1 system) | 0.09 ms | 17.6 ms | - |

## Core ECS Operations

### Entity Spawning

Entity spawning is O(1) per entity and scales linearly with the number of components.

| Scale | Simple (1 component) | Complex (5 components) |
|-------|---------------------|------------------------|
| 100 | 339,578 ops/sec | 252,508 ops/sec |
| 10,000 | 260,458 ops/sec | 298,973 ops/sec |
| 1,000,000 | 233,684 ops/sec | 154,094 ops/sec |

**Typical latency:** 0.003-0.007 ms per entity

### Component Access

Component operations are O(1) dictionary lookups, constant regardless of world size.

| Operation | Throughput | Latency |
|-----------|-----------|---------|
| `get_component()` | 4.4M ops/sec | 0.0002 ms |
| `has_component()` | 4.6M ops/sec | 0.0002 ms |
| `add_component()` | 410k ops/sec | 0.002 ms |
| `remove_component()` | 710k ops/sec | 0.001 ms |

### Entity Queries

Queries perform a full scan of all entities, making them O(n) where n is the total entity count.

| Scale | `with_all` (single) | `with_all` (multiple) | `with_any` |
|-------|--------------------|-----------------------|------------|
| 100 | 40,207 ops/sec | 31,086 ops/sec | 36,243 ops/sec |
| 10,000 | 172 ops/sec | 162 ops/sec | 197 ops/sec |
| 1,000,000 | 1 ops/sec | 1 ops/sec | - |

**Performance note:** Query time grows linearly with entity count. For large worlds, use materialized indexes or the spatial addon for filtered queries.

### Relationships

| Operation | 100 entities | 10k entities |
|-----------|-------------|--------------|
| Add relationship | 0.003 ms | 0.003 ms |
| Remove relationship | 0.002 ms | 0.002 ms |
| Query outgoing | 0.0005 ms | 0.0005 ms |
| Query incoming | 0.003 ms | 2.2 ms |

**Note:** Incoming relationship queries are O(n) as they scan all relationships. Outgoing queries are O(1).

### System Tick

Tick performance depends on the number of systems and entities processed.

| Scale | 1 System | 5 Systems |
|-------|----------|-----------|
| 100 entities | 0.09 ms | 0.29 ms |
| 10,000 entities | 17.6 ms | 67 ms |

**Target frame rates:**
- 100 entities: ~60 FPS easily achievable
- 10,000 entities: ~15 FPS with 5 systems (optimize queries for better performance)

## Indexes

### Lazy vs Materialized Indexes

| Operation | Lazy Index | Materialized Index | Speedup |
|-----------|-----------|-------------------|---------|
| count() (100) | 0.05 ms | 0.0001 ms | 463x |
| count() (10k) | 7.4 ms | 0.0001 ms | 63,604x |
| get_entity_ids() (100) | 0.03 ms | 0.0005 ms | 64x |
| get_entity_ids() (10k) | 6.2 ms | 0.04 ms | 146x |

**Recommendation:** Use materialized indexes for frequently-accessed component sets. They maintain O(1) count and entity ID access at the cost of update overhead.

## Spatial Addon

### 2D Spatial Queries (QuadTree)

| Scale | Circle Query | Rectangle Query |
|-------|-------------|-----------------|
| 100 | 0.016 ms | ~0.016 ms |
| 1,000 | 0.045 ms | ~0.045 ms |
| 5,000 | 0.061 ms | ~0.061 ms |
| 10,000 | 0.107 ms | ~0.107 ms |

**Scaling:** O(log n + k) where k is the number of results. Far better than O(n) full scans.

### 3D Spatial Queries (Octree)

| Scale | Sphere Query |
|-------|-------------|
| 10,000 | 0.179 ms |

### Nearest Neighbor

| Scale | k=10 |
|-------|------|
| 5,000 | 3.2 ms |

**Note:** Current nearest neighbor implementation is O(n). For better performance with large entity counts, consider spatial partitioning optimizations.

### Lazy vs Materialized Spatial Index

| Index Type | 1k entities, 20 queries |
|------------|------------------------|
| Lazy 2D | 5.90 ms total |
| Materialized 2D | 0.83 ms total |

**Speedup:** 7x faster with materialized index

### Bulk Operations

| Operation | Time |
|-----------|------|
| Insert 10k entities | 80 ms |
| Update 1k positions | 31 ms |

## Procedural Prefabs Addon

### Spawning Performance

| Scenario | Time per Entity |
|----------|-----------------|
| Simple entity | 0.008 ms |
| With parameters | 0.016 ms |
| With 2 attachments | 0.025 ms |
| With conditionals | 0.008 ms |
| From 100-item list | 0.013 ms |

### Hierarchy Operations

| Operation | Time |
|-----------|------|
| Get 100 children | 0.023 ms |
| Cascade delete (4 levels) | 0.016 ms per root |

### Memory Efficiency

Spawning 5,000 entities: 38 ms total (0.008 ms per entity)

## Use Case Recommendations

### Small Games (< 1,000 entities)

All operations are fast enough for real-time use:
- Use simple queries freely
- Lazy indexes are fine
- 60+ FPS easily achievable

### Medium Games (1,000 - 10,000 entities)

Some optimization needed:
- Use materialized indexes for hot paths
- Use spatial addon for position-based queries
- Batch component updates where possible
- Target 30-60 FPS

### Large Simulations (> 10,000 entities)

Significant optimization required:
- Always use materialized indexes
- Use spatial indexes for all position queries
- Consider splitting world into regions
- Profile and optimize system queries
- May need to accept lower tick rates (10-30 FPS)

### Real-Time Requirements

For 60 FPS, you have ~16.7 ms per frame budget:

| Entity Count | Systems | Approx Frame Time | Achievable? |
|--------------|---------|-------------------|-------------|
| 100 | 5 | 0.3 ms | Yes |
| 1,000 | 5 | 3 ms | Yes |
| 5,000 | 5 | 15 ms | Marginal |
| 10,000 | 5 | 67 ms | No (use optimization) |

## Known Bottlenecks

### Query Full Scan

**Location:** `src/relics/query.py`

Queries scan all entities in the world. For large entity counts, consider:
- Using materialized indexes
- Caching query results
- Using the spatial addon for position-based filtering

### Observer Queue

**Location:** `src/relics/world.py`

Observer event processing uses list operations. For very high event throughput, this may become a bottleneck.

### Incoming Relationship Queries

**Location:** `src/relics/entity.py`

`get_incoming_relationships()` scans all relationships in the world. For entity graphs with many relationships, consider caching or indexing incoming edges.

## Running Benchmarks

```bash
# Run all performance tests
pytest -m perf tests/test_performance.py -v -s

# Run spatial addon benchmarks
pytest tests/addons/spatial/test_performance.py -v -s

# Run procedural prefabs benchmarks
pytest tests/addons/procedural_prefabs/test_performance.py -v -s
```
