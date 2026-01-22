# Inventory Tree - Equipment and Containers

Character equipment and nested container hierarchy.

## Features Demonstrated

- **Custom Edge types** - Relationships with data (equipment slots)
- **add_relationship()** - Creating relationships between entities
- **remove_relationship()** - Breaking relationships
- **get_relationships()** - Getting outgoing relationships
- **get_incoming_relationships()** - Getting incoming relationships
- **Hierarchy traversal** - Iterating over children and descendants
- **Cascade deletion** - Destroying entities and all their children

## Running

```bash
cd /path/to/relics
source .venv/bin/activate
python demos/inventory_tree/main.py
```

## Key Concepts

### Edge Types

Edges define typed relationships between entities:

```python
@pydantic.dataclasses.dataclass
class Equipped(Edge):
    """Character has item in equipment slot."""
    slot: str  # "main_hand", "head", etc.

@pydantic.dataclasses.dataclass
class Contains(Edge):
    """Container holds an item."""
    pass
```

### Creating Relationships

Use `add_relationship()` to connect entities:

```python
# Equip sword in main hand
character.add_relationship(Equipped(slot="main_hand"), sword.id)

# Put item in container
backpack.add_relationship(Contains(), potion.id)
```

### Querying Relationships

Get outgoing relationships (what this entity connects to):

```python
for edge, target_id in entity.get_relationships(Equipped):
    target = world.get_entity(target_id)
    print(f"Equipped {target} in {edge.slot}")
```

Get incoming relationships (what connects to this entity):

```python
for source_id, edge in entity.get_incoming_relationships(Contains):
    parent = world.get_entity(source_id)
    print(f"This item is inside {parent}")
```

### Hierarchy Traversal

Helper functions for tree navigation:

```python
def get_children(entity, edge_type):
    """Get direct children via edge type."""
    for edge, target_id in entity.get_relationships(edge_type):
        yield world.get_entity(target_id)

def get_parent(entity, edge_type):
    """Get parent via edge type."""
    incoming = entity.get_incoming_relationships(edge_type)
    if incoming:
        source_id, edge = incoming[0]
        return world.get_entity(source_id)
    return None

def get_all_descendants(entity, edge_type):
    """Recursively get all descendants."""
    for child in get_children(entity, edge_type):
        yield child
        yield from get_all_descendants(child, edge_type)
```

### Cascade Deletion

Destroy an entity and all its children:

```python
def destroy_with_children(world, entity, edge_type):
    # First destroy children (depth-first)
    for child in get_children(entity, edge_type):
        destroy_with_children(world, child, edge_type)
    # Then destroy this entity
    world.remove(entity)
```

### Removing Relationships

Break relationships before destroying:

```python
# Remove item from backpack
backpack.remove_relationship(Contains, item.id)

# Now safe to destroy the item
world.remove(item)
```

## Inventory Structure

The demo creates this hierarchy:

```
[Character] Adventurer
  [Item] Iron Sword <main_hand>
  [Item] Wooden Shield <off_hand>
  [Item] Leather Helmet <head>
  [Container] Backpack <back>
    [Item] Health Potion x5
    [Item] Gold Coin x47
    [Item] Torch
    [Container] Coin Pouch
      [Item] Ruby
      [Item] Emerald
```

## Next Demo

Continue to [spatial_aoe](../spatial_aoe/) to learn about spatial indexing and queries.
