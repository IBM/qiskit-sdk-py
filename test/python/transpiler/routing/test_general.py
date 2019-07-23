"""Test cases for the permutation.complete package"""
#  arct performs circuit transformations of quantum circuit for architectures
#  Copyright (C) 2019  Andrew M. Childs, Eddie Schoute, Cem M. Unsal
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import itertools
from unittest import TestCase

import networkx as nx
from numpy import random

from qiskit.transpiler.routing import util
from qiskit.transpiler.routing.general import ApproximateTokenSwapper


class TestGeneral(TestCase):
    """The test cases"""
    def setUp(self) -> None:
        """Set up test cases."""
        random.seed(0)

    def test_simple(self) -> None:
        """Test a simple permutation on a path graph of size 4."""
        graph = nx.path_graph(4)
        permutation = {0: 0, 1: 3, 3: 1, 2: 2}
        swapper: ApproximateTokenSwapper[int] = ApproximateTokenSwapper(graph)

        out = list(swapper.map(permutation))
        self.assertEqual(3, len(out))
        util.swap_permutation([out], permutation)
        self.assertEqual({i: i for i in range(4)}, permutation)

    def test_small(self) -> None:
        """Test an inverting permutation on a small path graph of size 8"""
        graph = nx.path_graph(8)
        permutation = {i: 7 - i for i in range(8)}
        swapper : ApproximateTokenSwapper[int]= ApproximateTokenSwapper(graph)

        out = list(swapper.map(permutation))
        util.swap_permutation([out], permutation)
        self.assertEqual({i: i for i in range(8)}, permutation)

    def test_bug1(self) -> None:
        """Tests for a bug that occured in happy swap chains of length >2."""
        graph = nx.Graph()
        graph.add_edges_from([(0, 1), (0, 2), (0, 3), (0, 4),
                              (1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4), (3, 6)])
        permutation = {0: 4, 1: 0, 2: 3, 3: 6, 4: 2, 6: 1}
        swapper: ApproximateTokenSwapper[int] = ApproximateTokenSwapper(graph)

        out = list(swapper.map(permutation))
        util.swap_permutation([out], permutation)
        self.assertEqual({i: i for i in permutation}, permutation)

    def test_partial_simple(self) -> None:
        """Test a partial mapping on a small graph."""
        graph = nx.path_graph(4)
        mapping = {0: 3}
        swapper : ApproximateTokenSwapper[int]= ApproximateTokenSwapper(graph)
        out = list(swapper.map(mapping))
        self.assertEqual(3, len(out))
        util.swap_permutation([out], mapping, allow_missing_keys=True)
        self.assertEqual({3: 3}, mapping)

    def test_partial_small(self) -> None:
        """Test an partial inverting permutation on a small path graph of size 5"""
        graph = nx.path_graph(4)
        permutation = {i: 3 - i for i in range(2)}
        swapper: ApproximateTokenSwapper[int] = ApproximateTokenSwapper(graph)

        out = list(swapper.map(permutation))
        self.assertEqual(5, len(out))
        util.swap_permutation([out], permutation, allow_missing_keys=True)
        self.assertEqual({i:i for i in permutation.values()}, permutation)

    def test_large_partial_random(self) -> None:
        """Test a random (partial) mapping on a large randomly generated graph"""
        size = 10 ** 3
        # Note that graph may have "gaps" in the node counts, i.e. the numbering is noncontiguous.
        graph = nx.dense_gnm_random_graph(size, size ** 2 // 10)
        graph.remove_edges_from((i, i) for i in graph.nodes)  # Remove self-loops.
        # Make sure the graph is connected by adding C_n
        nodes = list(graph.nodes)
        graph.add_edges_from((node, nodes[(i + 1) % len(nodes)]) for i, node in enumerate(nodes))
        swapper: ApproximateTokenSwapper[int] = ApproximateTokenSwapper(graph)

        # Generate a randomized permutation.
        rand_perm = random.permutation(graph.nodes())
        permutation = dict(zip(graph.nodes(), rand_perm))
        mapping = dict(itertools.islice(permutation.items(), 0, size, 2))  # Drop every 2nd element.

        out = list(swapper.map(mapping, trials=40))
        util.swap_permutation([out], mapping, allow_missing_keys=True)
        self.assertEqual({i: i for i in mapping.values()}, mapping)
