"""Implementations for permuting on a regular modular architecture."""
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

import logging
from typing import List, Dict, Set, Tuple, Mapping

from qiskit.transpiler.routing import complete, util, Permutation, Swap
import networkx as nx

LOGGER = logging.getLogger(__name__)


def permute(mapping: Mapping[int, int], modulesize: int, modules: int) -> List[List[Swap[int]]]:
    """
    Gives a list of swaps to implement a permutation on the given regular modular graph.

    :param mapping:
    :param modulesize:
    :param modules:
    :return:
    """
    mapping = dict(mapping)
    already_mapped: Dict[int, int] = {}

    in_module = lambda i: _in_module(i, modulesize)

    # Compute upper bound on number of main loop iterations
    degrees = [0] * 2 * modules
    for origin, destination in mapping.items():
        if in_module(origin) != in_module(destination):
            degrees[in_module(origin)] += 1
            degrees[modules + in_module(destination)] += 1
    max_degree = max(degrees)
    assert max_degree <= modulesize, "Maximum degree is too large." \
                                    "Is the mapping a (partial) permutation?"

    # Remove at most n_2 - max_degree mappings within the same module
    available_for_removal = [modulesize - max_degree] * modules # nr of in-module maps we can remove
    for origin, destination in mapping.items():
        module = in_module(origin)
        if module == in_module(destination) and available_for_removal[module] > 0:
            available_for_removal[module] -= 1
            already_mapped[origin] = 0

    def is_local_permutation(mp: Mapping[int, int]) -> bool:
        """Checks if a given permutation operates only within a module."""
        return all(in_module(k) == in_module(mp[k]) for k in mp)

    all_swaps: List[List[Swap[int]]] = []
    iterations: int = 0
    while (not is_local_permutation(mapping)) and iterations < max_degree:
        inter_module_nodes = _distinct_permutation(mapping, set(already_mapped.keys()),
                                                   modulesize, modules)
        already_mapped.update({k: 0 for k in inter_module_nodes})
        # Given the distinct inter-module nodes that need to be routed,
        # move them to the networking node.
        dest_modules = {in_module(mapping[node]) for node in inter_module_nodes
                        if node in mapping}
        inter_module_nodes = {node for node in inter_module_nodes
                              # Do not move if destination module is same as current.
                              # or if no node has the current module as destination, for unmapped.
                              if not(node in mapping and in_module(node) == in_module(mapping[node]))
                                and not(node not in mapping and in_module(node) not in dest_modules)}
        prep_swaps = [(n0, n1)
                      for n0, n1 in ((n, in_module(n) * modulesize) for n in inter_module_nodes)
                      if n0 != n1]
        # Only append if not empty
        prep_swaps_list = []
        if prep_swaps:
            prep_swaps_list.append(prep_swaps)

        all_swaps.extend(prep_swaps_list)

        # Apply the swaps to the permutation to update it.
        util.swap_permutation(prep_swaps_list, mapping, allow_missing_keys=True)
        util.swap_permutation(prep_swaps_list, already_mapped, allow_missing_keys=True)

        # Now route between modules
        inter_module_permutation = {
            node: in_module(mapping[node]) * modulesize
            for node in (in_module(node) * modulesize for node in inter_module_nodes)
            if node in mapping
            }
        inter_module_swaps = list(
            complete.partial_permute(inter_module_permutation,
                                     # only use the nodes in modules that are involved,
                                     # otherwise errors may occur.
                                     nodes=[in_module(node)*modulesize for node in inter_module_nodes]))
        all_swaps.extend(inter_module_swaps)
        util.swap_permutation(inter_module_swaps, mapping, allow_missing_keys=True)
        util.swap_permutation(inter_module_swaps, already_mapped, allow_missing_keys=True)

        iterations += 1

    if not is_local_permutation(mapping):
        raise RuntimeError("Routing is taking too long... Aborting: "
                           "The routing did not succeed in implementing the permutation.")

    # All permutations should now be local to the module
    # and we can simply use a complete graph permutation to put everything in place.
    # Break up the permutations to each module.
    intra_module_permutations = [
        {i * modulesize + j: mapping[i * modulesize + j] for j in range(modulesize)
         if i * modulesize + j in mapping}
        for i in range(modules)
        ]
    # And perform a local complete graph permutations.
    all_intra_swaps: List[List[List[Swap[int]]]] = []
    for module, intra_module_permutation in enumerate(intra_module_permutations):
        all_intra_swaps.append(list(
            complete.partial_permute(intra_module_permutation,
                                     nodes=range(module * modulesize, (module + 1) * modulesize))))
    # Save results.
    intra_swaps = list(util.flatten_swaps(all_intra_swaps))
    if intra_swaps:
        all_swaps.extend(intra_swaps)

    return all_swaps


def _in_module(i: int, modulesize: int) -> int:
    """
    Takes the destination node and returns the destination module.

    :param i: The destination node
    :param modulesize: The number of nodes per module
    :return: The destination module.
    """
    return i // modulesize


def _distinct_permutation(mapping: Mapping[int, int],
                          already_mapped: Set[int],
                          modulesize: int,
                          modules: int) -> Set[int]:
    """
    Find a perfect matching in the mapping such that no destination module is repeated.

    :param mapping:
    :param modulesize: The module size
    :param modules: The number of modules
    :return: A dictionary mapping a module to a node that should be routed inter-modules.
    """

    module_unmapped_nodes = [{node for node in range(i * modulesize, (i + 1) * modulesize)
                              if node not in mapping}
                             for i in range(modules)]

    def right_node(module: int) -> int:
        """Shift by the number of modules."""
        return modules + module

    # Construct bipartite graph.
    # The edge set with attributes: the node that added the edge; and weight.
    destination_graph = nx.MultiGraph()
    destination_graph.add_nodes_from(range(modules))
    destination_graph.add_nodes_from((right_node(i) for i in range(modules)))
    for from_node, to_node in mapping.items():
        if from_node not in already_mapped:
            from_module = _in_module(from_node, modulesize)
            to_module = _in_module(to_node, modulesize)
            destination_graph.add_edge(from_module, right_node(to_module), node=from_node)

    # Then add unmapped nodes
    degree = dict(destination_graph.degree) # Fix current degree map
    max_degree = max(degree.values())
    unmapped_graph = nx.Graph()
    for from_module, unmapped_nodes in enumerate(module_unmapped_nodes):
        # Check if the originating module can support outgoing unmapped qubits.
        if not(unmapped_nodes) or degree[from_module] >= max_degree:
            continue

        # Add edges to all destinations for an arbitrary unmapped node.
        unmapped_node = next(iter(unmapped_nodes))
        for to_node in (right_node(to_module) for to_module in range(modules)):
            # Only when there is no mapped vertex that needs to be sent do we allow an unmapped vertex to move
            # Moreover, the destination module need to have empty "slots" available from incoming unmapped vertices
            if not(destination_graph.has_edge(from_module, to_node)) and degree[to_node] < max_degree:
                unmapped_graph.add_edge(from_module, to_node, node=unmapped_node)

    # Merge destination_graph and unmapped_graph to simple graph
    simple_graph = nx.Graph()
    simple_graph.add_nodes_from(range(modules))
    simple_graph.add_nodes_from((right_node(i) for i in range(modules)))
    for graph in (destination_graph, unmapped_graph):
        for e0, e1, data in graph.edges(data=True):
            simple_graph.add_edge(e0, e1, node=data["node"])

    matching = nx.algorithms.bipartite.maximum_matching(simple_graph, top_nodes=range(modules))
    # Check that the matching is perfect.
    # Edges are included in both directions so it's twice as large as the number of modules.
    if len(matching) != 2*modules:
        LOGGER.error("The matching is not perfect. Ignoring...")

    # Then use the full matching and the inverse edge map to find the nodes
    # to be moved into destination modules.
    return {simple_graph[module][matching[module]]["node"] for module in range(modules)}
