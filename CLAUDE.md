# Claude Code Guidelines for Relics

This file contains guidelines and rules for AI assistants working on the Relics codebase.

## Project Overview

Relics is a Python ECS (Entity-Component-System) framework with graph database semantics. The project uses:

- **Python 3.11+**
- **Pydantic** for dataclass validation
- **pytest** for testing
- **pytest-cov** for coverage

## Development Commands

### Virtual Environment

```bash
source .venv/bin/activate
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/relics --cov-report=term-missing

# Run specific test file
pytest tests/path/to/test_file.py -v

# Run specific test
pytest tests/path/to/test_file.py::TestClass::test_method -v
```

### Linting

```bash
# Type checking
mypy src/relics/

# Flake8 linting
flake8 src/relics/
```

## API Patterns

### World API

- `world.observe(observer)` - Register an observer (NOT `register_observer`)
- `world.tick(delta)` - Advance simulation, requires delta parameter
- `world.spawn(prefab_name, overrides)` - Create entity from prefab
- `world.query()` - Create a QueryBuilder

### Component Binding

Monitored components (with `@monitored` decorator) are automatically bound to the world when:
1. Added via `entity.add_component()`
2. Spawned with a prefab (monitored components are deep copied)

This enables change tracking for `OnComponentChanged` observers.

### @monitored Decorator Usage

**Recommended: Use the combined `@monitored_component` decorator:**

```python
from relics import monitored_component

# ✅ BEST - combined decorator handles ordering automatically
@monitored_component
class Health(Component):
    current: int
    maximum: int
```

**Alternative: Both decorator orders now work:**

```python
# ✅ Works
@monitored
@dataclass
class Health(Component):
    current: int
    maximum: int

# ✅ Also works (order-independent)
@dataclass
@monitored
class Health(Component):
    current: int
    maximum: int
```

### Observer Events

- `OnEntityCreated` - Triggered when entity spawns (NOT when components added)
- `OnComponentAdded` - Only for components added AFTER entity creation via `add_component()`
- `OnComponentChanged` - Requires `@monitored` decorator on component class
- `OnComponentRemoved` - When component is removed

Important: Prefab components do NOT trigger `OnComponentAdded` during spawn. Use `OnEntityCreated` or lazy initialization to handle entities spawned with prefabs.

## Testing Guidelines

### Coverage Target

Aim for **≥98% coverage** for new code.

### Performance Tests

- Use generous thresholds to avoid flaky failures in CI
- Example: Use `< 30ms` instead of `< 20ms` for timing assertions
- Always seed random number generators for reproducibility: `random.seed(42)`
- Print timing information for debugging: `print(f"\nOperation: {time_ms:.3f}ms")`

### Test Structure

```
tests/
├── test_core_module.py     # Core library tests
└── addons/
    └── addon_name/
        ├── test_components.py
        ├── test_types.py
        ├── test_*.py
        ├── test_integration.py
        └── test_performance.py
```

### Common Test Patterns

```python
# Use pydantic.ValidationError for missing dataclass args, not TypeError
import pydantic
with pytest.raises(pydantic.ValidationError):
    Position2D()  # Missing required args

# Always pass delta to tick()
world.tick(0)  # or world.tick(0.016) for realistic delta

# For lazy-initialized indexes, don't check count before spawning
# BAD: assert index.count() == 0  # Initializes empty
# GOOD: spawn first, then check
```

## Addon Development

### Directory Structure

```
src/relics/addons/
├── __init__.py
└── addon_name/
    ├── __init__.py      # Public API exports
    ├── components.py    # Component types
    ├── types.py         # Supporting types
    └── *.py             # Implementation modules
```

### Pattern: Lazy Initialization

Indexes and caches should use lazy initialization:

```python
def _ensure_initialized(self) -> None:
    if not self._initialized:
        self._rebuild()
        self._initialized = True

def _rebuild(self) -> None:
    # Rebuild from current world state
    # Also bind monitored components here for change tracking
    for entity_id, components in self._world._entities.items():
        if self._component_type in components:
            component = components[self._component_type]
            if hasattr(component, "_bind_to_world"):
                component._bind_to_world(self._world, entity_id)
            # ... add to data structure
```

### Pattern: Dynamic Observer Classes

Create observer classes with dynamic `component_type`:

```python
def create_observer(index, component_type):
    observer_class = type(
        f"Observer_{component_type.__name__}",
        (BaseObserver,),
        {"component_type": component_type},
    )
    return observer_class(index)
```

## Code Style

### Type Hints

- Use type hints throughout
- Import from `typing` for generics: `List`, `Dict`, `Optional`, etc.
- Use `TYPE_CHECKING` for import-time-only types to avoid circular imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from relics.world import World
```

### Docstrings

Use Google-style docstrings:

```python
def method(self, arg: Type) -> ReturnType:
    """Short description.

    Longer description if needed.

    Args:
        arg: Description of argument.

    Returns:
        Description of return value.

    Raises:
        ErrorType: When this error occurs.
    """
```

## Known Quirks

1. **Component sharing**: Without `@monitored`, prefab components are shared between entities (same instance). With `@monitored`, components are deep copied during spawn.

2. **Observer registration order**: Events are queued during operations and processed during `tick()`. The order of observer registration affects callback order.

3. **Index lazy initialization**: Materialized indexes initialize lazily on first access, pulling current world state. Plan accordingly for observer registration timing.
