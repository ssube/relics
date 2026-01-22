# Future Persistence Drivers

This document outlines potential persistence drivers that could be added to Relics.

## Currently Implemented

| Driver | Storage | Use Case |
|--------|---------|----------|
| `JSONPersistenceDriver` | JSON files | Human-readable, portable save files |
| `SQLitePersistenceDriver` | SQLite database | Structured queries, efficient updates |
| `InMemoryPersistenceDriver` | RAM | Testing, undo/redo, temporary checkpoints |

## Candidates for Future Implementation

### PicklePersistenceDriver

**Priority:** Medium

Python's native binary serialization format.

**Pros:**
- Zero dependencies (stdlib)
- Fastest serialization for Python objects
- Handles complex nested structures automatically
- Smaller file sizes than JSON

**Cons:**
- Python-specific (not portable to other languages)
- Security risk with untrusted data (arbitrary code execution)
- Version compatibility issues (pickle protocol changes)

**Use Cases:**
- Local-only save files where performance matters
- Cache files that don't need human readability
- Internal checkpoints in Python-only applications

**Implementation Notes:**
```python
import pickle

def save(self, world, path, relic_name=None):
    data = self._world_to_data(world, relic_name)
    with open(path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
```

---

### YAMLPersistenceDriver

**Priority:** Low

Human-readable configuration format with comments support.

**Pros:**
- More readable than JSON for humans
- Supports comments (useful for annotated save files)
- Popular in game modding communities
- Better multiline string handling

**Cons:**
- Requires PyYAML dependency
- Slower than JSON for large files
- More complex parsing rules
- Security concerns with `yaml.load()` (use `safe_load`)

**Use Cases:**
- Modding-friendly games where users edit save files
- Configuration-heavy applications
- Debug/development save files

**Dependencies:**
```
pyyaml>=6.0
```

---

### MessagePackPersistenceDriver

**Priority:** Low

Binary serialization format (like JSON but binary).

**Pros:**
- 2-10x smaller than JSON
- 2-5x faster serialization than JSON
- Cross-language compatible
- Compact type encoding

**Cons:**
- Requires msgpack dependency
- Not human-readable
- Less tooling than JSON
- Slightly more complex debugging

**Use Cases:**
- Performance-critical applications
- Network transmission of world state
- Large world saves where size matters

**Dependencies:**
```
msgpack>=1.0
```

---

### CompressedJSONDriver

**Priority:** Low

JSON with compression (gzip/lz4).

**Pros:**
- 5-10x smaller files than plain JSON
- Still JSON-compatible (can decompress to edit)
- No new serialization format to learn
- gzip is stdlib, lz4 is faster but requires dependency

**Cons:**
- Slower save/load (compression overhead)
- Not directly human-readable
- Memory overhead for compression buffer

**Use Cases:**
- Large world saves where disk space matters
- Archival/backup saves
- Network transmission

**Implementation Notes:**
```python
import gzip
import json

def save(self, world, path, relic_name=None):
    data = self._world_to_data(world, relic_name)
    with gzip.open(path, "wt") as f:
        json.dump(data, f)
```

---

### RedisDriver

**Priority:** Low

In-memory data store with persistence and pub/sub.

**Pros:**
- Distributed/shared world state
- Built-in pub/sub for multiplayer events
- Fast read/write operations
- TTL support for temporary data

**Cons:**
- Requires Redis server running
- Requires redis-py dependency
- More complex deployment
- Network latency considerations

**Use Cases:**
- Multiplayer game servers
- Distributed simulations
- Shared world state between processes
- Session storage with automatic expiry

**Dependencies:**
```
redis>=4.0
```

---

### PostgreSQLDriver / MySQLDriver

**Priority:** Very Low

Full relational database support.

**Pros:**
- Industrial-strength data integrity
- Complex queries across save files
- Multi-user access with transactions
- Built-in backup/replication

**Cons:**
- Requires database server
- Significant deployment complexity
- Slower than file-based storage for single-user
- Overkill for most game scenarios

**Use Cases:**
- MMO game backends
- Analytics across many world saves
- Enterprise applications
- When you need ACID transactions

---

## Implementation Guidelines

When implementing a new driver:

1. **Inherit from `PersistenceDriver`** - All drivers must implement the abstract interface
2. **Deep copy on save/load** - Prevent reference sharing between driver and world
3. **Handle missing types gracefully** - Skip unknown components/edges during load
4. **Support registries** - Accept component_registry and edge_registry parameters
5. **Test with relationships** - Ensure edges are properly serialized
6. **Test round-trip** - Verify save → load preserves all data

Example test pattern:
```python
def test_round_trip(driver):
    world = create_test_world()
    driver.save(world, path)

    world2 = World()
    driver.load(world2, path, component_registry, edge_registry)

    assert_worlds_equal(world, world2)
```

## Contributing

To contribute a new driver:

1. Create `src/relics/persistence/drivers/{name}.py`
2. Implement `PersistenceDriver` interface
3. Add tests in `tests/persistence/test_{name}_driver.py`
4. Update `drivers/__init__.py` exports
5. Update `persistence/__init__.py` exports
6. Add documentation to this file
