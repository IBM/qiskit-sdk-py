# -*- coding: utf-8 -*-

# Copyright 2017, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=no-member

"""
Directed graph object for representing coupling between qubits.

The nodes of the graph correspond to named qubits and the directed edges
indicate which qubits are coupled and the permitted direction of CNOT gates.
The object has a distance_qubits function that can be used to map quantum circuits
onto a device with this coupling.
"""
import warnings
from collections import OrderedDict
import networkx as nx
from qiskit import _quantumregister
from ._couplingerror import CouplingError


class Coupling:
    """
    Directed graph specifying fixed coupling.

    Nodes correspond to qubits and directed edges correspond to permitted
    CNOT gates
    """

    # pylint: disable=invalid-name

    @staticmethod
    def coupling_dict2list(couplingdict):
        """Convert coupling map dictionary into list.

        Example dictionary format: {0: [1, 2], 1: [2]}
        Example list format: [[0, 1], [0, 2], [1, 2]]

        We do not do any checking of the input.

        Return coupling map in list format.
        """
        if not couplingdict:
            return None
        couplinglist = []
        for ctl, tgtlist in couplingdict.items():
            for tgt in tgtlist:
                couplinglist.append([ctl, tgt])
        return couplinglist

    @staticmethod
    def coupling_list2dict(couplinglist):
        """Convert coupling map list into dictionary.

        Example list format: [[0, 1], [0, 2], [1, 2]]
        Example dictionary format: {0: [1, 2], 1: [2]}

        We do not do any checking of the input.

        Return coupling map in dict format.
        """
        if not couplinglist:
            return None
        couplingdict = {}
        for pair in couplinglist:
            if pair[0] in couplingdict:
                couplingdict[pair[0]].append(pair[1])
            else:
                couplingdict[pair[0]] = [pair[1]]
        return couplingdict

    def __init__(self, couplingdict=None):
        """
        Create coupling graph.

        By default, the coupling graph has no nodes. The optional couplingdict
        specifies the graph as an adjacency list. For example,
        couplingdict = {0: [1, 2], 1: [2]}.
        """
        self.graph = nx.DiGraph()
        if isinstance(couplingdict, dict):
            for origin, destinations in couplingdict.items():
                for destination in destinations:
                    self.add_edge(origin, destination)
        # self.qubits is dict from qubit (reg,idx) tuples to node indices
        self.qubits = OrderedDict()
        # self.index_to_qubit is a dict from node indices to qubits
        self.index_to_qubit = {}
        # self.node_counter is integer counter for labeling nodes
        self.node_counter = 0
        # self.G is the coupling digraph
        self.G = nx.DiGraph()
        # self.dist is a dict of dicts from node pairs to distances
        # it must be computed, it is the distance_qubits on the digraph
        self.dist = None
        # Add edges to the graph if the couplingdict is present
        if couplingdict is not None:
            couplinglist = Coupling.coupling_dict2list(couplingdict)
            num_qubits = 1 + max(max(x[0] for x in couplinglist),
                                 max(x[1] for x in couplinglist))
            reg = _quantumregister.QuantumRegister(num_qubits, 'q')
            for v0, alist in couplingdict.items():
                for v1 in alist:
                    self.add_edge_qubit((reg, v0), (reg, v1))

    def size(self):
        """Return the number of wires in this graph."""
        return len(self.graph.nodes)

    def get_qubits(self):
        """Return the qubits in this graph as a sorted (qreg, index) tuples."""
        return sorted(list(self.qubits.keys()))

    def get_edges_qubits(self): #TODO remove
        """Return a list of edges in the coupling graph.

        Each edge is a pair of qubits and each qubit is a tuple (qreg, index).
        """
        warnings.warn("get_edges_qubits is being removed", DeprecationWarning, stacklevel=2)

        return list(map(lambda x: (self.index_to_qubit[x[0]],
                                   self.index_to_qubit[x[1]]), self.G.edges()))

    def get_edges(self):
        """Return a list of edges in the coupling graph.

        Each edge is a pair of wires.
        """
        return [edge for edge in self.graph.edges()]

    def add_qubit(self, qubit):
        """
        Add a qubit to the coupling graph.

        qubit = tuple (reg, idx) for qubit
        """
        # TODO remove
        if qubit in self.qubits:
            raise CouplingError("%s already in coupling graph" % qubit)
        if not isinstance(qubit, tuple):
            raise CouplingError("qubit %s is not a tuple")
        if not (isinstance(qubit[0], _quantumregister.QuantumRegister) and
                isinstance(qubit[1], int)):
            raise CouplingError("qubit %s is not of the right form, it must"
                                " be: (reg, idx)")

        self.node_counter += 1
        self.G.add_node(self.node_counter)
        self.G.node[self.node_counter]["name"] = str((qubit[0].name, qubit[1]))
        self.qubits[qubit] = self.node_counter
        self.index_to_qubit[self.node_counter] = qubit


    def add_wire(self, wire):
        """
        Add a wire to the coupling graph as a node.

        wire (int): A wire
        """
        if not isinstance(wire, int):
            raise CouplingError("Wires should be numbers.")
        if wire in self.wires:
            raise CouplingError("The wire %s is already in the coupling graph" % wire)

        self.graph.add_node(wire)

    def add_edge_qubit(self, s_qubit, d_qubit):
        """
        Add directed edge to coupling graph.

        s_qubit = source qubit tuple
        d_qubit = destination qubit tuple
        """
        #TODO remove!
        if s_qubit not in self.qubits:
            self.add_qubit(s_qubit)
        if d_qubit not in self.qubits:
            self.add_qubit(d_qubit)
        self.G.add_edge(self.qubits[s_qubit], self.qubits[d_qubit])

    def add_edge(self, src_wire, dst_wire):
        """
        Add directed edge to coupling graph.

        src_wire (int): source wire
        dst_wire (int): destination wire
        """
        if src_wire not in self.wires:
            self.add_wire(src_wire)
        if dst_wire not in self.wires:
            self.add_wire(dst_wire)
        self.graph.add_edge(src_wire, dst_wire)

    @property
    def wires(self):
        return [wire for wire in self.graph.nodes]


    def is_connected(self):
        """
        Test if the graph is connected.

        Return True if connected, False otherwise
        """
        try:
            return nx.is_weakly_connected(self.graph)
        except nx.exception.NetworkXException:
            return False

    def connected(self): # TODO remove!
        """
        Test if the graph is connected.

        Return True if connected, False otherwise
        """
        warnings.warn("connected is being removed", DeprecationWarning, stacklevel=2)
        try:
            return nx.is_weakly_connected(self.G)
        except nx.exception.NetworkXException:
            return False

    def compute_distance(self):
        """
        Compute the undirected distance function on pairs of nodes.

        The distance_qubits map self.dist is computed from the graph using
        all_pairs_shortest_path_length.
        """
        if not self.connected():
            raise CouplingError("coupling graph not connected")
        lengths = dict(nx.all_pairs_shortest_path_length(self.G.to_undirected()))
        self.dist = {}
        for i in self.qubits.keys():
            self.dist[i] = {}
            for j in self.qubits.keys():
                self.dist[i][j] = lengths[self.qubits[i]][self.qubits[j]]

    def distance(self, wire1, wire2):
        """Return the undirected distance between wire1 and wire2."""
        try:
            return len(nx.shortest_path(self.graph.to_undirected(), source=wire1, target=wire2))-1
        except nx.exception.NetworkXNoPath:
            raise CouplingError("Nodes %s and %s are not connected" % (str(wire1), str(wire2)))

    def __str__(self): #TODO Remove
        """Return a string representation of the coupling graph."""
        s = ""
        if self.qubits:
            s += "qubits: "
            s += ", ".join(["%s[%d] @ %d" % (k[0].name, k[1], v)
                            for k, v in self.qubits.items()])
        if self.get_edges_qubits():
            s += "\nedges: "
            s += ", ".join(
                ["%s[%d]-%s[%d]" % (e[0][0].name, e[0][1], e[1][0].name, e[1][1])
                 for e in self.get_edges_qubits()])
        return s

    def __repr__(self): #TODO rename to __str__
        """Return a string representation of the coupling graph."""
        s = ""
        if self.get_edges():
            s += "["
            s += ", ".join([ "(%s, %s)" % (src,dst) for (src,dst) in self.get_edges()])
            s += "]"
        return s
