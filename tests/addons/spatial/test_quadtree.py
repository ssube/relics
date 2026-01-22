"""Tests for QuadTree data structure."""

import pytest

from relics.addons.spatial import Circle, QuadTree, QuadTreeBounds, Rectangle
from relics.types import EntityId


class TestQuadTreeBounds:
    """Tests for QuadTreeBounds."""

    def test_create_bounds(self) -> None:
        """Test creating QuadTreeBounds."""
        bounds = QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50)
        assert bounds.center_x == 50
        assert bounds.center_y == 50
        assert bounds.half_width == 50
        assert bounds.half_height == 50

    def test_min_max_properties(self) -> None:
        """Test min/max coordinate properties."""
        bounds = QuadTreeBounds(
            center_x=100, center_y=100, half_width=50, half_height=30
        )
        assert bounds.min_x == 50
        assert bounds.max_x == 150
        assert bounds.min_y == 70
        assert bounds.max_y == 130

    def test_contains_point(self) -> None:
        """Test point containment."""
        bounds = QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50)
        assert bounds.contains_point(50, 50)
        assert bounds.contains_point(0, 0)
        assert bounds.contains_point(100, 100)
        assert not bounds.contains_point(-1, 50)
        assert not bounds.contains_point(101, 50)

    def test_get_quadrant(self) -> None:
        """Test quadrant determination."""
        bounds = QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50)
        # NW: x <= center, y > center
        assert bounds.get_quadrant(25, 75) == 0
        # NE: x > center, y > center
        assert bounds.get_quadrant(75, 75) == 1
        # SW: x <= center, y <= center
        assert bounds.get_quadrant(25, 25) == 2
        # SE: x > center, y <= center
        assert bounds.get_quadrant(75, 25) == 3

    def test_subdivide(self) -> None:
        """Test bounds subdivision."""
        bounds = QuadTreeBounds(
            center_x=100, center_y=100, half_width=100, half_height=100
        )
        nw, ne, sw, se = bounds.subdivide()

        # Check NW quadrant
        assert nw.center_x == 50
        assert nw.center_y == 150
        assert nw.half_width == 50
        assert nw.half_height == 50

        # Check NE quadrant
        assert ne.center_x == 150
        assert ne.center_y == 150

        # Check SW quadrant
        assert sw.center_x == 50
        assert sw.center_y == 50

        # Check SE quadrant
        assert se.center_x == 150
        assert se.center_y == 50

    def test_intersects_region_circle(self) -> None:
        """Test intersection with circle region."""
        bounds = QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50)
        circle_inside = Circle(center_x=50, center_y=50, radius=10)
        circle_outside = Circle(center_x=200, center_y=200, radius=10)

        assert bounds.intersects_region(circle_inside)
        assert not bounds.intersects_region(circle_outside)


class TestQuadTree:
    """Tests for QuadTree."""

    def test_create_quadtree(self) -> None:
        """Test creating a QuadTree."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)
        assert tree.count() == 0

    def test_insert_entity(self) -> None:
        """Test inserting an entity."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        assert tree.insert(entity_id, 100, 100)
        assert tree.count() == 1
        assert tree.contains(entity_id)

    def test_insert_out_of_bounds(self) -> None:
        """Test inserting entity outside bounds."""
        bounds = QuadTreeBounds(center_x=50, center_y=50, half_width=50, half_height=50)
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        assert not tree.insert(entity_id, 200, 200)  # Outside bounds
        assert tree.count() == 0

    def test_remove_entity(self) -> None:
        """Test removing an entity."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        tree.insert(entity_id, 100, 100)
        assert tree.count() == 1

        assert tree.remove(entity_id)
        assert tree.count() == 0
        assert not tree.contains(entity_id)

    def test_remove_nonexistent(self) -> None:
        """Test removing entity that doesn't exist."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        assert not tree.remove(entity_id)

    def test_update_entity(self) -> None:
        """Test updating entity position."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        tree.insert(entity_id, 100, 100)

        assert tree.get_position(entity_id) == (100, 100)

        tree.update(entity_id, 200, 200)
        assert tree.get_position(entity_id) == (200, 200)
        assert tree.count() == 1

    def test_query_circle(self) -> None:
        """Test circle query."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        # Insert entities at known positions
        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)
        e3 = EntityId(prefab="test", sequence=3)

        tree.insert(e1, 100, 100)  # Inside circle
        tree.insert(e2, 110, 110)  # Inside circle
        tree.insert(e3, 900, 900)  # Outside circle

        circle = Circle(center_x=100, center_y=100, radius=50)
        results = list(tree.query(circle))

        assert len(results) == 2
        assert e1 in results
        assert e2 in results
        assert e3 not in results

    def test_query_rectangle(self) -> None:
        """Test rectangle query."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)
        e3 = EntityId(prefab="test", sequence=3)

        tree.insert(e1, 150, 150)  # Inside rectangle
        tree.insert(e2, 200, 200)  # Inside rectangle
        tree.insert(e3, 400, 400)  # Outside rectangle

        rect = Rectangle(min_x=100, min_y=100, max_x=300, max_y=300)
        results = list(tree.query(rect))

        assert len(results) == 2
        assert e1 in results
        assert e2 in results
        assert e3 not in results

    def test_query_all(self) -> None:
        """Test getting all entities."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)

        tree.insert(e1, 100, 100)
        tree.insert(e2, 200, 200)

        results = list(tree.query_all())
        assert len(results) == 2

        entity_ids = {r[0] for r in results}
        assert e1 in entity_ids
        assert e2 in entity_ids

    def test_get_entity_ids(self) -> None:
        """Test getting all entity IDs."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)

        tree.insert(e1, 100, 100)
        tree.insert(e2, 200, 200)

        entity_ids = tree.get_entity_ids()
        assert len(entity_ids) == 2
        assert e1 in entity_ids
        assert e2 in entity_ids

    def test_clear(self) -> None:
        """Test clearing the tree."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        for i in range(10):
            tree.insert(EntityId(prefab="test", sequence=i), i * 50, i * 50)

        assert tree.count() == 10
        tree.clear()
        assert tree.count() == 0

    def test_subdivision(self) -> None:
        """Test that tree subdivides when capacity exceeded."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds, max_entities_per_node=4, max_depth=4)

        # Insert more than max_entities_per_node entities
        for i in range(10):
            tree.insert(EntityId(prefab="test", sequence=i), 100 + i * 10, 100 + i * 10)

        assert tree.count() == 10

        # All entities should still be queryable
        rect = Rectangle(min_x=0, min_y=0, max_x=1000, max_y=1000)
        results = list(tree.query(rect))
        assert len(results) == 10

    def test_insert_updates_existing(self) -> None:
        """Test that inserting existing entity updates its position."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        tree.insert(entity_id, 100, 100)
        tree.insert(entity_id, 200, 200)

        assert tree.count() == 1
        assert tree.get_position(entity_id) == (200, 200)

    def test_bounds_property(self) -> None:
        """Test accessing bounds property."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        assert tree.bounds == bounds
        assert tree.bounds.center_x == 500

    def test_remove_from_subdivided_tree(self) -> None:
        """Test removing entities from a tree that has subdivided."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Low capacity to force subdivision
        tree = QuadTree(bounds, max_entities_per_node=2, max_depth=4)

        # Insert entities to force subdivision
        entities = []
        for i in range(10):
            e = EntityId(prefab="test", sequence=i)
            tree.insert(e, 100 + i * 50, 100 + i * 50)
            entities.append(e)

        assert tree.count() == 10

        # Remove entities one by one
        for e in entities:
            assert tree.remove(e)

        assert tree.count() == 0

    def test_query_all_from_subdivided_tree(self) -> None:
        """Test query_all returns entities from all child nodes."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Low capacity to force subdivision
        tree = QuadTree(bounds, max_entities_per_node=2, max_depth=4)

        # Insert entities spread across different quadrants
        entities = []
        positions = [
            (100, 100),  # SW
            (900, 100),  # SE
            (100, 900),  # NW
            (900, 900),  # NE
            (200, 200),
            (800, 200),
            (200, 800),
            (800, 800),
        ]
        for i, (x, y) in enumerate(positions):
            e = EntityId(prefab="test", sequence=i)
            tree.insert(e, x, y)
            entities.append(e)

        # query_all should return all entities
        results = list(tree.query_all())
        assert len(results) == 8

        result_ids = {r[0] for r in results}
        for e in entities:
            assert e in result_ids

    def test_count_from_subdivided_tree(self) -> None:
        """Test count returns correct count from subdivided tree."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Low capacity to force subdivision
        tree = QuadTree(bounds, max_entities_per_node=2, max_depth=4)

        # Insert entities to force subdivision
        for i in range(20):
            e = EntityId(prefab="test", sequence=i)
            tree.insert(e, 100 + i * 40, 100 + i * 40)

        # Count should still be accurate
        assert tree.count() == 20

    def test_get_position_nonexistent(self) -> None:
        """Test get_position returns None for nonexistent entity."""
        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        tree = QuadTree(bounds)

        entity_id = EntityId(prefab="test", sequence=999)
        assert tree.get_position(entity_id) is None


class TestQuadTreeNodeDirectly:
    """Tests for QuadTreeNode methods directly."""

    def test_node_count_with_children(self) -> None:
        """Test QuadTreeNode.count() includes entities from children."""
        from relics.addons.spatial.quadtree import QuadTreeNode

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Very low capacity to force subdivision
        node = QuadTreeNode(bounds=bounds, max_entities=1, max_depth=4, depth=0)

        # Insert entities to trigger subdivision
        for i in range(4):
            node.insert(
                EntityId(prefab="test", sequence=i), 100 + i * 200, 100 + i * 200
            )

        # Verify children were created
        assert node.children is not None

        # count() should traverse children
        assert node.count() == 4

    def test_node_get_all_entities_with_children(self) -> None:
        """Test QuadTreeNode.get_all_entities() includes entities from children."""
        from relics.addons.spatial.quadtree import QuadTreeNode

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Very low capacity to force subdivision
        node = QuadTreeNode(bounds=bounds, max_entities=1, max_depth=4, depth=0)

        entities = []
        for i in range(4):
            e = EntityId(prefab="test", sequence=i)
            node.insert(e, 100 + i * 200, 100 + i * 200)
            entities.append(e)

        # Verify children were created
        assert node.children is not None

        # get_all_entities() should traverse children
        results = list(node.get_all_entities())
        assert len(results) == 4

        result_ids = {r[0] for r in results}
        for e in entities:
            assert e in result_ids

    def test_node_remove_from_children(self) -> None:
        """Test QuadTreeNode.remove() from child nodes."""
        from relics.addons.spatial.quadtree import QuadTreeNode

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Very low capacity to force subdivision
        node = QuadTreeNode(bounds=bounds, max_entities=1, max_depth=4, depth=0)

        entities = []
        for i in range(4):
            e = EntityId(prefab="test", sequence=i)
            node.insert(e, 100 + i * 200, 100 + i * 200)
            entities.append(e)

        # Verify children were created
        assert node.children is not None

        # Remove from child nodes
        for e in entities:
            assert node.remove(e)

        assert node.count() == 0

    def test_node_double_subdivide_no_effect(self) -> None:
        """Test that calling _subdivide on already subdivided node has no effect."""
        from relics.addons.spatial.quadtree import QuadTreeNode

        bounds = QuadTreeBounds(
            center_x=500, center_y=500, half_width=500, half_height=500
        )
        # Very low capacity to force subdivision
        node = QuadTreeNode(bounds=bounds, max_entities=1, max_depth=4, depth=0)

        # Insert to trigger subdivision
        for i in range(4):
            node.insert(
                EntityId(prefab="test", sequence=i), 100 + i * 200, 100 + i * 200
            )

        assert node.children is not None
        old_children = node.children

        # Try to subdivide again
        node._subdivide()

        # Children should be the same (no effect)
        assert node.children is old_children
