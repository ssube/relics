"""Performance tests for scene graph addon."""

import random
import time

from relics import World
from relics.addons.scene_graph import (
    LocalTransform,
    get_descendants,
    get_node,
    setup_scene_graph,
)
from relics.addons.scene_graph.factory import create_child_node, create_root_node
from relics.addons.scene_graph.types import Vec3


class TestPathIndexPerformance:
    """Performance tests for PathIndex operations."""

    def test_path_lookup_1000_nodes(self) -> None:
        """Test O(1) path lookup with 1000 nodes."""
        random.seed(42)
        world = World()
        index = setup_scene_graph(world)

        # Create hierarchy with 1000 nodes
        root = create_root_node(world, "world")
        nodes = [root]
        paths = ["/world"]

        for i in range(999):
            parent = random.choice(nodes)
            child = create_child_node(
                world,
                f"node_{i}",
                parent,
                local_transform=LocalTransform(position=Vec3(float(i % 10), 0.0, 0.0)),
            )
            nodes.append(child)

        world.tick(0)

        # Collect all paths
        for node in nodes[1:]:  # Skip root
            from relics.addons.scene_graph.components import NodePath

            if node.has_component(NodePath):
                paths.append(node.get_component(NodePath).path)

        # Time 1000 random lookups
        start = time.perf_counter()
        for _ in range(1000):
            path = random.choice(paths)
            result = get_node(world, path, index)
            assert result is not None
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\n1000 path lookups: {elapsed_ms:.3f}ms")
        # Should be very fast - use generous threshold for CI
        assert elapsed_ms < 100  # < 100ms for 1000 lookups

    def test_path_index_rebuild(self) -> None:
        """Test index rebuild performance with 100 nodes in a deep chain."""
        random.seed(42)
        world = World()
        index = setup_scene_graph(world)

        # Create a 100-deep chain (O(n²) for creation, so keep it small)
        root = create_root_node(world, "world")
        current = root
        for i in range(99):
            current = create_child_node(world, f"n{i}", current)
        world.tick(0)

        # Time index rebuild
        start = time.perf_counter()
        index.invalidate()
        _ = index.count()  # Trigger rebuild
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nIndex rebuild (100 nodes): {elapsed_ms:.3f}ms")
        assert elapsed_ms < 100


class TestHierarchyTraversalPerformance:
    """Performance tests for hierarchy traversal."""

    def test_deep_hierarchy_traversal(self) -> None:
        """Test traversing a 100-level deep hierarchy."""
        world = World()
        setup_scene_graph(world)

        # Create deep hierarchy (100 levels - creation is O(n²) for deep chains)
        root = create_root_node(world, "root")
        current = root
        for i in range(99):
            current = create_child_node(world, f"level_{i}", current)
        world.tick(0)

        # Time traversal
        start = time.perf_counter()
        descendants = list(get_descendants(world, root))
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nDeep hierarchy traversal (100 levels): {elapsed_ms:.3f}ms")
        assert len(descendants) == 99
        assert elapsed_ms < 100

    def test_wide_hierarchy_traversal(self) -> None:
        """Test traversing a hierarchy with 1000 children."""
        world = World()
        setup_scene_graph(world)

        # Create wide hierarchy (one parent, many children)
        root = create_root_node(world, "root")
        for i in range(1000):
            create_child_node(world, f"child_{i}", root)
        world.tick(0)

        # Time traversal
        start = time.perf_counter()
        descendants = list(get_descendants(world, root))
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nWide hierarchy traversal (1000 children): {elapsed_ms:.3f}ms")
        assert len(descendants) == 1000
        assert elapsed_ms < 100


class TestTransformPropagationPerformance:
    """Performance tests for transform propagation."""

    def test_transform_propagation_deep(self) -> None:
        """Test transform propagation through deep hierarchy."""
        world = World()
        setup_scene_graph(world)

        # Create deep hierarchy
        root = create_root_node(world, "root")
        current = root
        for i in range(100):
            current = create_child_node(
                world,
                f"level_{i}",
                current,
                local_transform=LocalTransform(position=Vec3(1.0, 0.0, 0.0)),
            )
        world.tick(0)

        # Time transform update at root
        start = time.perf_counter()
        root.get_component(LocalTransform).position = Vec3(10.0, 0.0, 0.0)
        world.tick(0)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nTransform propagation (100 levels): {elapsed_ms:.3f}ms")
        assert elapsed_ms < 50

    def test_transform_propagation_wide(self) -> None:
        """Test transform propagation to many children."""
        world = World()
        setup_scene_graph(world)

        # Create wide hierarchy
        root = create_root_node(world, "root")
        for i in range(100):
            create_child_node(
                world,
                f"child_{i}",
                root,
                local_transform=LocalTransform(position=Vec3(float(i), 0.0, 0.0)),
            )
        world.tick(0)

        # Time transform update at root
        start = time.perf_counter()
        root.get_component(LocalTransform).position = Vec3(100.0, 0.0, 0.0)
        world.tick(0)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nTransform propagation (100 children): {elapsed_ms:.3f}ms")
        assert elapsed_ms < 50


class TestCreationPerformance:
    """Performance tests for node creation."""

    def test_create_1000_nodes(self) -> None:
        """Test creating 1000 nodes."""
        random.seed(42)
        world = World()
        setup_scene_graph(world)

        start = time.perf_counter()
        root = create_root_node(world, "world")
        nodes = [root]
        for i in range(999):
            parent = random.choice(nodes)
            child = create_child_node(world, f"node_{i}", parent)
            nodes.append(child)
        world.tick(0)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nCreate 1000 nodes + tick: {elapsed_ms:.3f}ms")
        assert elapsed_ms < 2000  # < 2 seconds

    def test_incremental_creation(self) -> None:
        """Test incremental node creation with ticks."""
        random.seed(42)
        world = World()
        setup_scene_graph(world)

        root = create_root_node(world, "world")
        world.tick(0)

        nodes = [root]

        start = time.perf_counter()
        for i in range(100):
            parent = random.choice(nodes)
            child = create_child_node(world, f"node_{i}", parent)
            nodes.append(child)
            world.tick(0)  # Tick after each creation
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\n100 incremental creates with ticks: {elapsed_ms:.3f}ms")
        assert elapsed_ms < 1000  # < 1 second


class TestMathOperationsPerformance:
    """Performance tests for math type operations."""

    def test_vec3_operations(self) -> None:
        """Test Vec3 operation performance."""
        random.seed(42)
        vecs = [
            Vec3(random.random(), random.random(), random.random()) for _ in range(1000)
        ]

        start = time.perf_counter()
        for _ in range(100):
            for i in range(len(vecs) - 1):
                _ = vecs[i] + vecs[i + 1]
                _ = vecs[i] - vecs[i + 1]
                _ = vecs[i] * 2.0
                _ = vecs[i].dot(vecs[i + 1])
                _ = vecs[i].cross(vecs[i + 1])
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nVec3 operations (100 * 999 * 5): {elapsed_ms:.3f}ms")
        assert elapsed_ms < 1000

    def test_quat_operations(self) -> None:
        """Test Quat operation performance."""
        from relics.addons.scene_graph.types import Quat

        random.seed(42)
        quats = [
            Quat(
                random.random(), random.random(), random.random(), random.random()
            ).normalized()
            for _ in range(1000)
        ]
        vec = Vec3(1.0, 0.0, 0.0)

        start = time.perf_counter()
        for _ in range(100):
            for i in range(len(quats) - 1):
                _ = quats[i] * quats[i + 1]
                _ = quats[i].conjugate()
                _ = quats[i].rotate_vector(vec)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nQuat operations (100 * 999 * 3): {elapsed_ms:.3f}ms")
        assert elapsed_ms < 1000

    def test_mat4_operations(self) -> None:
        """Test Mat4 operation performance."""
        from relics.addons.scene_graph.types import Mat4, Quat

        random.seed(42)
        matrices = [
            Mat4.from_trs(
                Vec3(random.random(), random.random(), random.random()),
                Quat.identity(),
                Vec3(1.0, 1.0, 1.0),
            )
            for _ in range(100)
        ]
        point = Vec3(1.0, 2.0, 3.0)

        start = time.perf_counter()
        for _ in range(100):
            for i in range(len(matrices) - 1):
                _ = matrices[i] * matrices[i + 1]
                _ = matrices[i].transform_point(point)
        elapsed = time.perf_counter() - start
        elapsed_ms = elapsed * 1000

        print(f"\nMat4 operations (100 * 99 * 2): {elapsed_ms:.3f}ms")
        assert elapsed_ms < 500
