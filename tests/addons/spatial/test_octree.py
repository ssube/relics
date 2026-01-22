"""Tests for Octree data structure."""

import pytest

from relics.addons.spatial import Box, Octree, OctreeBounds, Sphere
from relics.types import EntityId


class TestOctreeBounds:
    """Tests for OctreeBounds."""

    def test_create_bounds(self) -> None:
        """Test creating OctreeBounds."""
        bounds = OctreeBounds(
            center_x=50, center_y=50, center_z=50,
            half_width=50, half_height=50, half_depth=50
        )
        assert bounds.center_x == 50
        assert bounds.center_y == 50
        assert bounds.center_z == 50
        assert bounds.half_width == 50
        assert bounds.half_height == 50
        assert bounds.half_depth == 50

    def test_min_max_properties(self) -> None:
        """Test min/max coordinate properties."""
        bounds = OctreeBounds(
            center_x=100, center_y=100, center_z=100,
            half_width=50, half_height=30, half_depth=20
        )
        assert bounds.min_x == 50
        assert bounds.max_x == 150
        assert bounds.min_y == 70
        assert bounds.max_y == 130
        assert bounds.min_z == 80
        assert bounds.max_z == 120

    def test_contains_point(self) -> None:
        """Test point containment."""
        bounds = OctreeBounds(
            center_x=50, center_y=50, center_z=50,
            half_width=50, half_height=50, half_depth=50
        )
        assert bounds.contains_point(50, 50, 50)
        assert bounds.contains_point(0, 0, 0)
        assert bounds.contains_point(100, 100, 100)
        assert not bounds.contains_point(-1, 50, 50)
        assert not bounds.contains_point(50, -1, 50)
        assert not bounds.contains_point(50, 50, -1)
        assert not bounds.contains_point(101, 50, 50)

    def test_get_octant(self) -> None:
        """Test octant determination."""
        bounds = OctreeBounds(
            center_x=50, center_y=50, center_z=50,
            half_width=50, half_height=50, half_depth=50
        )
        # Octant numbering based on (X>center, Y>center, Z>center)
        # 0: ---, 1: +--, 2: -+-, 3: ++-, 4: --+, 5: +-+, 6: -++, 7: +++
        assert bounds.get_octant(25, 25, 25) == 0  # ---
        assert bounds.get_octant(75, 25, 25) == 1  # +--
        assert bounds.get_octant(25, 75, 25) == 2  # -+-
        assert bounds.get_octant(75, 75, 25) == 3  # ++-
        assert bounds.get_octant(25, 25, 75) == 4  # --+
        assert bounds.get_octant(75, 25, 75) == 5  # +-+
        assert bounds.get_octant(25, 75, 75) == 6  # -++
        assert bounds.get_octant(75, 75, 75) == 7  # +++

    def test_subdivide(self) -> None:
        """Test bounds subdivision."""
        bounds = OctreeBounds(
            center_x=100, center_y=100, center_z=100,
            half_width=100, half_height=100, half_depth=100
        )
        children = bounds.subdivide()

        assert len(children) == 8

        # Check that all children have correct half-extents
        for child in children:
            assert child.half_width == 50
            assert child.half_height == 50
            assert child.half_depth == 50

    def test_intersects_region_sphere(self) -> None:
        """Test intersection with sphere region."""
        bounds = OctreeBounds(
            center_x=50, center_y=50, center_z=50,
            half_width=50, half_height=50, half_depth=50
        )
        sphere_inside = Sphere(center_x=50, center_y=50, center_z=50, radius=10)
        sphere_outside = Sphere(center_x=200, center_y=200, center_z=200, radius=10)

        assert bounds.intersects_region(sphere_inside)
        assert not bounds.intersects_region(sphere_outside)


class TestOctree:
    """Tests for Octree."""

    def test_create_octree(self) -> None:
        """Test creating an Octree."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)
        assert tree.count() == 0

    def test_insert_entity(self) -> None:
        """Test inserting an entity."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        assert tree.insert(entity_id, 100, 100, 100)
        assert tree.count() == 1
        assert tree.contains(entity_id)

    def test_insert_out_of_bounds(self) -> None:
        """Test inserting entity outside bounds."""
        bounds = OctreeBounds(
            center_x=50, center_y=50, center_z=50,
            half_width=50, half_height=50, half_depth=50
        )
        tree = Octree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        assert not tree.insert(entity_id, 200, 200, 200)  # Outside bounds
        assert tree.count() == 0

    def test_remove_entity(self) -> None:
        """Test removing an entity."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        tree.insert(entity_id, 100, 100, 100)
        assert tree.count() == 1

        assert tree.remove(entity_id)
        assert tree.count() == 0
        assert not tree.contains(entity_id)

    def test_update_entity(self) -> None:
        """Test updating entity position."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        entity_id = EntityId(prefab="test", sequence=1)
        tree.insert(entity_id, 100, 100, 100)

        assert tree.get_position(entity_id) == (100, 100, 100)

        tree.update(entity_id, 200, 200, 200)
        assert tree.get_position(entity_id) == (200, 200, 200)
        assert tree.count() == 1

    def test_query_sphere(self) -> None:
        """Test sphere query."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        # Insert entities at known positions
        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)
        e3 = EntityId(prefab="test", sequence=3)

        tree.insert(e1, 100, 100, 100)  # Inside sphere
        tree.insert(e2, 110, 110, 110)  # Inside sphere
        tree.insert(e3, 900, 900, 900)  # Outside sphere

        sphere = Sphere(center_x=100, center_y=100, center_z=100, radius=50)
        results = list(tree.query(sphere))

        assert len(results) == 2
        assert e1 in results
        assert e2 in results
        assert e3 not in results

    def test_query_box(self) -> None:
        """Test box query."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)
        e3 = EntityId(prefab="test", sequence=3)

        tree.insert(e1, 150, 150, 150)  # Inside box
        tree.insert(e2, 200, 200, 200)  # Inside box
        tree.insert(e3, 400, 400, 400)  # Outside box

        box = Box(min_x=100, min_y=100, min_z=100, max_x=300, max_y=300, max_z=300)
        results = list(tree.query(box))

        assert len(results) == 2
        assert e1 in results
        assert e2 in results
        assert e3 not in results

    def test_query_all(self) -> None:
        """Test getting all entities."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        e1 = EntityId(prefab="test", sequence=1)
        e2 = EntityId(prefab="test", sequence=2)

        tree.insert(e1, 100, 100, 100)
        tree.insert(e2, 200, 200, 200)

        results = list(tree.query_all())
        assert len(results) == 2

        entity_ids = {r[0] for r in results}
        assert e1 in entity_ids
        assert e2 in entity_ids

    def test_clear(self) -> None:
        """Test clearing the tree."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds)

        for i in range(10):
            tree.insert(
                EntityId(prefab="test", sequence=i),
                i * 50, i * 50, i * 50
            )

        assert tree.count() == 10
        tree.clear()
        assert tree.count() == 0

    def test_subdivision(self) -> None:
        """Test that tree subdivides when capacity exceeded."""
        bounds = OctreeBounds(
            center_x=500, center_y=500, center_z=500,
            half_width=500, half_height=500, half_depth=500
        )
        tree = Octree(bounds, max_entities_per_node=4, max_depth=4)

        # Insert more than max_entities_per_node entities
        for i in range(10):
            tree.insert(
                EntityId(prefab="test", sequence=i),
                100 + i * 10, 100 + i * 10, 100 + i * 10
            )

        assert tree.count() == 10

        # All entities should still be queryable
        box = Box(min_x=0, min_y=0, min_z=0, max_x=1000, max_y=1000, max_z=1000)
        results = list(tree.query(box))
        assert len(results) == 10
