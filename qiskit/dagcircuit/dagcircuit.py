# This code is part of Qiskit.
#
# (C) Copyright IBM 2017.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""
Object to represent a quantum circuit as a directed acyclic graph (DAG).

The nodes in the graph are either input/output nodes or operation nodes.
The edges correspond to qubits or bits in the circuit. A directed edge
from node A to node B means that the (qu)bit passes from the output of A
to the input of B. The object's methods allow circuits to be constructed,
composed, and modified. Some natural properties like depth can be computed
directly from the graph.
"""
from collections import OrderedDict
from typing import Tuple, Optional, List, Union, Dict, Set, Any, Iterator
import copy
import itertools
import warnings
import math

import retworkx as rx
import networkx as nx

from qiskit.circuit.quantumregister import QuantumRegister, Qubit
from qiskit.circuit.classicalregister import ClassicalRegister, Clbit
from qiskit.circuit.gate import Gate
from qiskit.dagcircuit.exceptions import DAGCircuitError
from qiskit.dagcircuit.dagnode import DAGNode
from qiskit.circuit.instruction import Instruction
from qiskit.circuit.bit import Bit
from qiskit.circuit.register import Register

class DAGCircuit:
    """
    Quantum circuit as a directed acyclic graph.

    There are 3 types of nodes in the graph: inputs, outputs, and operations.
    The nodes are connected by directed edges that correspond to qubits and
    bits.
    """

    # pylint: disable=invalid-name

    def __init__(self):
        """Create an empty circuit."""

        # Circuit name.  Generally, this corresponds to the name
        # of the QuantumCircuit from which the DAG was generated.
        self.name = None

        # Set of wires (Register,idx) in the dag
        self._wires = set()

        # Map from wire (Register,idx) to input nodes of the graph
        self.input_map = OrderedDict()

        # Map from wire (Register,idx) to output nodes of the graph
        self.output_map = OrderedDict()

        # Directed multigraph whose nodes are inputs, outputs, or operations.
        # Operation nodes have equal in- and out-degrees and carry
        # additional data about the operation, including the argument order
        # and parameter values.
        # Input nodes have out-degree 1 and output nodes have in-degree 1.
        # Edges carry wire labels (reg,idx) and each operation has
        # corresponding in- and out-edges with the same wire labels.
        self._multi_graph = rx.PyDAG()

        # Map of qreg/creg name to Register object.
        self.qregs = OrderedDict()
        self.cregs = OrderedDict()

        # List of Qubit/Clbit wires that the DAG acts on.
        class DummyCallableList(list):
            """Dummy class so we can deprecate dag.qubits() and do
            dag.qubits as property.
            """
            def __call__(self):
                warnings.warn('dag.qubits() and dag.clbits() are no longer methods. Use '
                              'dag.qubits and dag.clbits properties instead.', DeprecationWarning,
                              stacklevel=2)
                return self
        self._qubits = DummyCallableList()  # TODO: make these a regular empty list [] after the
        self._clbits = DummyCallableList()  # DeprecationWarning period, and remove name underscore.

        self._global_phase = 0

    def to_networkx(self):
        """Returns a copy of the DAGCircuit in networkx format."""
        G = nx.MultiDiGraph()
        for node in self._multi_graph.nodes():
            G.add_node(node)
        for node_id in rx.topological_sort(self._multi_graph):
            for source_id, dest_id, edge in self._multi_graph.in_edges(node_id):
                G.add_edge(self._multi_graph.get_node_data(source_id),
                           self._multi_graph.get_node_data(dest_id),
                           **edge)
        return G

    @classmethod
    def from_networkx(cls, graph):
        """Take a networkx MultiDigraph and create a new DAGCircuit.

        Args:
            graph (networkx.MultiDiGraph): The graph to create a DAGCircuit
                object from. The format of this MultiDiGraph format must be
                in the same format as returned by to_networkx.

        Returns:
            DAGCircuit: The dagcircuit object created from the networkx
                MultiDiGraph.
        """

        dag = DAGCircuit()
        for node in nx.topological_sort(graph):
            if node.type == 'out':
                continue
            if node.type == 'in':
                dag._add_wire(node.wire)
            elif node.type == 'op':
                dag.apply_operation_back(node.op.copy(), node.qargs,
                                         node.cargs, node.condition)
        return dag

    @property
    def qubits(self):
        """Return a list of qubits (as a list of Qubit instances)."""
        # TODO: remove this property after DeprecationWarning period (~9/2020)
        return self._qubits

    @property
    def clbits(self):
        """Return a list of classical bits (as a list of Clbit instances)."""
        # TODO: remove this property after DeprecationWarning period (~9/2020)
        return self._clbits

    @property
    def wires(self):
        """Return a list of the wires in order."""
        out_list = [bit for reg in self.qregs.values() for bit in reg]
        out_list += [bit for reg in self.cregs.values() for bit in reg]
        return out_list

    @property
    def node_counter(self) -> int:
        """
        Returns the number of nodes in the dag.
        """
        return len(self._multi_graph)

    @property
    def global_phase(self):
        """Return the global phase of the circuit."""
        return self._global_phase

    @global_phase.setter
    def global_phase(self, angle):
        """Set the global phase of the circuit.

        Args:
            angle (float, ParameterExpression)
        """
        from qiskit.circuit.parameterexpression import ParameterExpression  # needed?
        if isinstance(angle, ParameterExpression):
            self._global_phase = angle
        else:
            # Set the phase to the [-2 * pi, 2 * pi] interval
            angle = float(angle)
            if not angle:
                self._global_phase = 0
            elif angle < 0:
                self._global_phase = angle % (-2 * math.pi)
            else:
                self._global_phase = angle % (2 * math.pi)

    def remove_all_ops_named(self, opname: str):
        """Remove all operation nodes with the given ``opname``.

        Args:
            opname: The name of an operation. For example: "cx".
        """
        for n in self.named_nodes(opname):
            self.remove_op_node(n)

    def add_qreg(self, qreg: QuantumRegister):
        """Add all wires in a quantum register."""
        if not isinstance(qreg, QuantumRegister):
            raise DAGCircuitError("not a QuantumRegister instance.")
        if qreg.name in self.qregs:
            raise DAGCircuitError("duplicate register %s" % qreg.name)
        self.qregs[qreg.name] = qreg
        for j in range(qreg.size):
            self.qubits.append(qreg[j])
            self._add_wire(qreg[j])

    def add_creg(self, creg: ClassicalRegister):
        """Add all wires in a classical register."""
        if not isinstance(creg, ClassicalRegister):
            raise DAGCircuitError("not a ClassicalRegister instance.")
        if creg.name in self.cregs:
            raise DAGCircuitError("duplicate register %s" % creg.name)
        self.cregs[creg.name] = creg
        for j in range(creg.size):
            self.clbits.append(creg[j])
            self._add_wire(creg[j])

    def _add_wire(self, wire: Bit):
        """Add a qubit or bit to the circuit.

        Args:
            wire: the wire to be added
            This adds a pair of in and out nodes connected by an edge.

        Raises:
            DAGCircuitError: if trying to add duplicate wire
        """
        if wire not in self._wires:
            self._wires.add(wire)

            wire_name = "%s[%s]" % (wire.register.name, wire.index)

            inp_node = DAGNode(type='in', name=wire_name, wire=wire)
            outp_node = DAGNode(type='out', name=wire_name, wire=wire)

            input_map_id = self._multi_graph.add_node(inp_node)
            output_map_id = self._multi_graph.add_node(outp_node)
            inp_node._node_id = input_map_id
            outp_node._node_id = output_map_id
            self.input_map[wire] = inp_node
            self.output_map[wire] = outp_node
            self._multi_graph.add_edge(inp_node._node_id,
                                       outp_node._node_id,
                                       {'name': wire_name,
                                        'wire': wire})
        else:
            raise DAGCircuitError("duplicate wire %s" % (wire,))

    def _check_condition(self, name: str, condition: Optional[Tuple[ClassicalRegister, int]]):
        """Verify that the condition is valid.

        Args:
            name: used for error reporting
            condition: a condition tuple (ClassicalRegister,int)

        Raises:
            DAGCircuitError: if conditioning on an invalid register
        """
        # Verify creg exists
        if condition is not None and condition[0].name not in self.cregs:
            raise DAGCircuitError("invalid creg in condition for %s" % name)

    def _check_bits(self, args: List[Bit], amap: Dict[Bit, Any]):
        """Check the values of a list of (qu)bit arguments.

        For each element of args, check that amap contains it.

        Args:
            args: the elements to be checked
            amap: a dictionary keyed on Qubits/Clbits

        Raises:
            DAGCircuitError: if a qubit is not contained in amap
        """
        # Check for each wire
        for wire in args:
            if wire not in amap:
                raise DAGCircuitError("(qu)bit %s[%d] not found" %
                                      (wire.register.name, wire.index))

    def _bits_in_condition(self, cond: Optional[Tuple[ClassicalRegister, int]]) -> List[Clbit]:
        """Return a list of bits in the given condition.

        Args:
            cond: optional condition

        Returns:
            A list of classical bits
        """
        return [] if cond is None else list(cond[0])

    def _add_op_node(self, op: Instruction,
                     qargs: List[Qubit], cargs: List[Qubit]) -> DAGNode:
        """Add a new operation node to the graph and assign properties.

        Args:
            op: the operation associated with the DAG node
            qargs: list of quantum wires to attach to.
            cargs: list of classical wires to attach to.

        Returns:
            int: The integer node index for the new op node on the DAG
        """
        # Add a new operation node to the graph
        new_node = DAGNode(type="op", op=op, name=op.name, qargs=qargs,
                           cargs=cargs)
        node_index = self._multi_graph.add_node(new_node)
        new_node._node_id = node_index
        return node_index

    def apply_operation_back(self, op: Instruction,
                             qargs: Optional[List[Qubit]] = None,
                             cargs: Optional[List[Clbit]] = None,
                             condition: Optional[Tuple[ClassicalRegister,
                                                       int]] = None) -> 'DAGNode':
        """Apply an operation to the output of the circuit.

        Args:
            op: the operation associated with the DAG node
            qargs: qubits that ``op`` will be applied to
            cargs: cbits that ``op`` will be applied to
            condition: DEPRACTED optional condition (ClassicalRegister, int)

        Returns:
            The current max node

        Raises:
            DAGCircuitError: if a leaf node is connected to multiple outputs

        """
        if condition:
            warnings.warn("Use of condition arg is deprecated, set condition in instruction",
                          DeprecationWarning)
        op.condition = condition if op.condition is None else op.condition

        qargs = qargs or []
        cargs = cargs or []

        all_cbits = self._bits_in_condition(op.condition)
        all_cbits = set(all_cbits).union(cargs)

        self._check_condition(op.name, op.condition)
        self._check_bits(qargs, self.output_map)
        self._check_bits(all_cbits, self.output_map)

        node_index = self._add_op_node(op, qargs, cargs)

        # Add new in-edges from predecessors of the output nodes to the
        # operation node while deleting the old in-edges of the output nodes
        # and adding new edges from the operation node to each output node
        al = [qargs, all_cbits]
        for q in itertools.chain(*al):
            ie = self._multi_graph.predecessors(self.output_map[q]._node_id)

            if len(ie) != 1:
                raise DAGCircuitError("output node has multiple in-edges")

            self._multi_graph.add_edge(
                ie[0]._node_id, node_index,
                {'name': "%s[%s]" % (q.register.name, q.index), 'wire': q})

            self._multi_graph.remove_edge(ie[0]._node_id, self.output_map[q]._node_id)
            self._multi_graph.add_edge(
                node_index, self.output_map[q]._node_id,
                dict(name="%s[%s]" % (q.register.name, q.index), wire=q))

        return self._multi_graph.get_node_data(node_index)

    def apply_operation_front(self, op: Instruction,
                              qargs: List[Qubit], cargs: List[Clbit],
                              condition: Optional[Tuple[ClassicalRegister,
                                                        int]] = None) -> 'DAGNode':
        """Apply an operation to the input of the circuit.

        Args:
            op: the operation associated with the DAG node
            qargs: qubits that ``op`` will be applied to
            cargs: cbits that ``op`` will be applied to
            condition: DEPRACTED optional condition (ClassicalRegister, int)

        Returns:
            The current max node

        Raises:
            DAGCircuitError: if initial nodes connected to multiple out edges
        """
        if condition:
            warnings.warn("Use of condition arg is deprecated, set condition in instruction",
                          DeprecationWarning)

        op.condition = condition if op.condition is None else op.condition
        all_cbits = self._bits_in_condition(op.condition)
        all_cbits.extend(cargs)

        self._check_condition(op.name, op.condition)
        self._check_bits(qargs, self.input_map)
        self._check_bits(all_cbits, self.input_map)
        node_index = self._add_op_node(op, qargs, cargs)

        # Add new out-edges to successors of the input nodes from the
        # operation node while deleting the old out-edges of the input nodes
        # and adding new edges to the operation node from each input node
        al = [qargs, all_cbits]
        for q in itertools.chain(*al):
            ie = self._multi_graph.successors(self.input_map[q]._node_id)
            if len(ie) != 1:
                raise DAGCircuitError("input node has multiple out-edges")
            self._multi_graph.add_edge(node_index, ie[0]._node_id,
                                       dict(name="%s[%s]" % (q.register.name, q.index), wire=q))
            self._multi_graph.remove_edge(self.input_map[q]._node_id, ie[0]._node_id)
            self._multi_graph.add_edge(self.input_map[q]._node_id, node_index,
                                       dict(name="%s[%s]" % (q.register.name, q.index), wire=q))

        return self._multi_graph.get_node_data(node_index)

    def _check_edgemap_registers(self, edge_map: Dict[Bit, Bit],
                                 keyregs: Dict[str, Register],
                                 valregs: Dict[str, Register],
                                 valreg: bool = True) -> Set[Register]:
        """Check that wiremap neither fragments nor leaves duplicate registers.

        1. There are no fragmented registers. A register in keyregs
        is fragmented if not all of its (qu)bits are renamed by edge_map.
        2. There are no duplicate registers. A register is duplicate if
        it appears in both self and keyregs but not in edge_map.

        Args:
            edge_map: map from Bit in keyregs to Bit in valregs
            keyregs: a map from register names to Register objects
            valregs: a map from register names to Register objects
            valreg: if False the method ignores valregs and does not
                add regs for bits in the edge_map image that don't appear in valregs

        Returns:
            The set of regs to add to self

        Raises:
            DAGCircuitError: if the wiremap fragments, or duplicates exist
        """
        # FIXME: some mixing of objects and strings here are awkward (due to
        # self.qregs/self.cregs still keying on string.
        add_regs = set()
        reg_frag_chk = {}
        for v in keyregs.values():
            reg_frag_chk[v] = {j: False for j in range(len(v))}
        for k in edge_map.keys():
            if k.register.name in keyregs:
                reg_frag_chk[k.register][k.index] = True
        for k, v in reg_frag_chk.items():
            s = set(v.values())
            if len(s) == 2:
                raise DAGCircuitError("edge_map fragments reg %s" % k)
            if s == {False}:
                if k in self.qregs.values() or k in self.cregs.values():
                    raise DAGCircuitError("unmapped duplicate reg %s" % k)
                # Add registers that appear only in keyregs
                add_regs.add(k)
            else:
                if valreg:
                    # If mapping to a register not in valregs, add it.
                    # (k,0) exists in edge_map because edge_map doesn't
                    # fragment k
                    if not edge_map[k[0]].register.name in valregs:
                        size = max(map(lambda x: x.index,
                                       filter(lambda x: x.register == edge_map[k[0]].register,
                                              edge_map.values())))
                        qreg = QuantumRegister(size + 1, edge_map[k[0]].register.name)
                        add_regs.add(qreg)
        return add_regs

    def _check_wiremap_validity(self, wire_map: Dict[Bit, Bit],
                                keymap: Dict[Bit, Any], valmap: Dict[Bit, Any]):
        """Check that the wiremap is consistent.

        Check that the wiremap refers to valid wires and that
        those wires have consistent types.

        Args:
            wire_map: map from Bit in keymap to Bit in valmap
            keymap: a map whose keys are wire_map keys
            valmap: a map whose keys are wire_map values

        Raises:
            DAGCircuitError: if wire_map not valid
        """
        for k, v in wire_map.items():
            kname = "%s[%d]" % (k.register.name, k.index)
            vname = "%s[%d]" % (v.register.name, v.index)
            if k not in keymap:
                raise DAGCircuitError("invalid wire mapping key %s" % kname)
            if v not in valmap:
                raise DAGCircuitError("invalid wire mapping value %s" % vname)
            if type(k) is not type(v):
                raise DAGCircuitError("inconsistent wire_map at (%s,%s)" %
                                      (kname, vname))

    @staticmethod
    def _map_condition(
            wire_map: Dict[Bit, Bit],
            condition: Optional[Tuple[ClassicalRegister, int]]
    ) -> Tuple[ClassicalRegister, int]:
        """Use the wire_map dict to change the condition tuple's creg name.

        Args:
            wire_map: a map from wires to wires
            condition: optional condition

        Returns:
            New condition

        Raises:
            DAGCircuitError: if condition register not in wire_map
        """
        if condition is None:
            new_condition = None
        else:
            # if there is a condition, map the condition bits to the
            # composed cregs based on the wire_map
            cond_val = condition[1]
            new_cond_val = 0
            new_creg = None
            for bit in wire_map:
                if isinstance(bit, Clbit):
                    new_creg = wire_map[bit].register
                    if 2**(bit.index) & cond_val:
                        new_cond_val += 2**(wire_map[bit].index)
            if new_creg is None:
                raise DAGCircuitError("Condition registers not found in wire_map.")
            new_condition = (new_creg, new_cond_val)
        return new_condition

    def extend_back(self, dag: 'DAGCircuit', edge_map: Optional[Dict[Bit, Bit]] = None):
        """DEPRECATED: Add `dag` at the end of `self`, using `edge_map`.
        Apply ``dag`` to the output of this circuit.

        Args:
            dag: circuit to append
            edge_map: map from the output wires of ``dag`` to input
                wires of self. The key and value can either be of
                type Qubit or Clbit depending on the type of the node.
        """
        warnings.warn("dag.extend_back is deprecated, please use dag.compose.",
                      DeprecationWarning, stacklevel=2)
        edge_map = edge_map or {}
        for qreg in dag.qregs.values():
            if qreg.name not in self.qregs:
                self.add_qreg(QuantumRegister(qreg.size, qreg.name))
            edge_map.update([(qbit, qbit) for qbit in qreg if qbit not in edge_map])

        for creg in dag.cregs.values():
            if creg.name not in self.cregs:
                self.add_creg(ClassicalRegister(creg.size, creg.name))
            edge_map.update([(cbit, cbit) for cbit in creg if cbit not in edge_map])

        self.compose_back(dag, edge_map)

    def compose_back(self, input_circuit: 'DAGCircuit', edge_map: Optional[Dict[Bit, Bit]] = None):
        """DEPRECATED: use DAGCircuit.compose() instead.
        """
        warnings.warn("dag.compose_back is deprecated, please use dag.compose.",
                      DeprecationWarning, stacklevel=2)
        self.compose(input_circuit, edge_map)

    def compose(self, other, edge_map=None, qubits=None, clbits=None, front=False, inplace=True):
        """Compose the ``other`` circuit onto the output of this circuit.

        A subset of input wires of ``other`` are mapped
        to a subset of output wires of this circuit.

        ``other`` can be narrower or of equal width to ``self``.

        Args:
            other (DAGCircuit): circuit to compose with self
            edge_map (dict): DEPRECATED - a {Bit: Bit} map from input wires of other
                to output wires of self (i.e. rhs->lhs).
                The key, value pairs can be either Qubit or Clbit mappings.
            qubits (list[Qubit|int]): qubits of self to compose onto.
            clbits (list[Clbit|int]): clbits of self to compose onto.
            front (bool): If True, front composition will be performed (not implemented yet)
            inplace (bool): If True, modify the object. Otherwise return composed circuit.

        Returns:
            DAGCircuit: the composed dag (returns None if inplace==True).

        Raises:
            DAGCircuitError: if ``other`` is wider or there are duplicate edge mappings.
        """
        if front:
            raise DAGCircuitError("Front composition not supported yet.")

        if len(other.qubits) > len(self.qubits) or \
           len(other.clbits) > len(self.clbits):
            raise DAGCircuitError("Trying to compose with another DAGCircuit "
                                  "which has more 'in' edges.")

        if edge_map is not None:
            warnings.warn("edge_map arg as a dictionary is deprecated. "
                          "Use qubits and clbits args to specify a list of "
                          "self edges to compose onto.", DeprecationWarning,
                          stacklevel=2)

        # number of qubits and clbits must match number in circuit or None
        identity_qubit_map = dict(zip(other.qubits, self.qubits))
        identity_clbit_map = dict(zip(other.clbits, self.clbits))
        if qubits is None:
            qubit_map = identity_qubit_map
        elif len(qubits) != len(other.qubits):
            raise DAGCircuitError("Number of items in qubits parameter does not"
                                  " match number of qubits in the circuit.")
        else:
            qubit_map = {other.qubits[i]: (self.qubits[q] if isinstance(q, int) else q)
                         for i, q in enumerate(qubits)}
        if clbits is None:
            clbit_map = identity_clbit_map
        elif len(clbits) != len(other.clbits):
            raise DAGCircuitError("Number of items in clbits parameter does not"
                                  " match number of clbits in the circuit.")
        else:
            clbit_map = {other.clbits[i]: (self.clbits[c] if isinstance(c, int) else c)
                         for i, c in enumerate(clbits)}
        edge_map = edge_map or {**qubit_map, **clbit_map} or None

        # if no edge_map, try to do a 1-1 mapping in order
        if edge_map is None:
            edge_map = {**identity_qubit_map, **identity_clbit_map}

        # Check the edge_map for duplicate values
        if len(set(edge_map.values())) != len(edge_map):
            raise DAGCircuitError("duplicates in wire_map")

        # Compose
        if inplace:
            dag = self
        else:
            dag = copy.deepcopy(self)
        dag.global_phase += other.global_phase

        for nd in other.topological_nodes():
            if nd.type == "in":
                # if in edge_map, get new name, else use existing name
                m_wire = edge_map.get(nd.wire, nd.wire)
                # the mapped wire should already exist
                if m_wire not in dag.output_map:
                    raise DAGCircuitError("wire %s[%d] not in self" % (
                        m_wire.register.name, m_wire.index))
                if nd.wire not in other._wires:
                    raise DAGCircuitError("inconsistent wire type for %s[%d] in other"
                                          % (nd.register.name, nd.wire.index))
            elif nd.type == "out":
                # ignore output nodes
                pass
            elif nd.type == "op":
                condition = dag._map_condition(edge_map, nd.condition)
                dag._check_condition(nd.name, condition)
                m_qargs = list(map(lambda x: edge_map.get(x, x), nd.qargs))
                m_cargs = list(map(lambda x: edge_map.get(x, x), nd.cargs))
                op = nd.op.copy()
                op.condition = condition
                dag.apply_operation_back(op, m_qargs, m_cargs)
            else:
                raise DAGCircuitError("bad node type %s" % nd.type)

        if not inplace:
            return dag
        else:
            return None

    def idle_wires(self, ignore=None) -> Iterator[Bit]:
        """Return idle wires.

        Args:
            ignore (list(str)): List of node names to ignore. Default: []

        Yields:
            Bit in idle wire.
        """
        if ignore is None:
            ignore = []
        for wire in self._wires:
            nodes = [node for node in self.nodes_on_wire(wire, only_ops=False)
                     if node.name not in ignore]
            if len(nodes) == 2:
                yield wire

    def size(self) -> int:
        """Return the number of operations."""
        return len(self._multi_graph) - 2 * len(self._wires)

    def depth(self) -> int:
        """Return the circuit depth.

        Returns:
            The circuit depth.

        Raises:
            DAGCircuitError: if not a directed acyclic graph
        """
        if not rx.is_directed_acyclic_graph(self._multi_graph):
            raise DAGCircuitError("not a DAG")

        depth = rx.dag_longest_path_length(self._multi_graph) - 1
        return depth if depth >= 0 else 0

    def width(self) -> int:
        """Return the total number of qubits + clbits used by the circuit."""
        return len(self._wires)

    def num_qubits(self) -> int:
        """Return the total number of qubits used by the circuit."""
        return len(self._wires) - self.num_clbits()

    def num_clbits(self) -> int:
        """Return the total number of classical bits used by the circuit."""
        return sum(creg.size for creg in self.cregs.values())

    def num_tensor_factors(self) -> int:
        """Compute how many components the circuit can decompose into."""
        return rx.number_weakly_connected_components(self._multi_graph)

    def _check_wires_list(self, wires: List[Bit], node: 'DAGNode'):
        """Check that a list of wires is compatible with a node to be replaced.

        - no duplicate names
        - correct length for operation
        Raise an exception otherwise.

        Args:
            wires: gives an order for (qu)bits
                in the input circuit that is replacing the node.
            node: a node in the dag

        Raises:
            DAGCircuitError: if check doesn't pass.
        """
        if len(set(wires)) != len(wires):
            raise DAGCircuitError("duplicate wires")

        wire_tot = len(node.qargs) + len(node.cargs)
        if node.condition is not None:
            wire_tot += node.condition[0].size

        if len(wires) != wire_tot:
            raise DAGCircuitError("expected %d wires, got %d"
                                  % (wire_tot, len(wires)))

    def _make_pred_succ_maps(self, node: 'DAGNode') -> Tuple[Dict[Bit, 'DAGNode'],
                                                             Dict[Bit, 'DAGNode']]:
        """Return predecessor and successor dictionaries.

        Args:
            node: reference to multi_graph node

        Returns:
            tuple: predecessor_map, successor_map
                These map from wire (Register, int) to the node ids for the
                predecessor (successor) nodes of the input node.
        """

        pred_map = {e[2]['wire']: e[0] for e in
                    self._multi_graph.in_edges(node._node_id)}
        succ_map = {e[2]['wire']: e[1] for e in
                    self._multi_graph.out_edges(node._node_id)}
        return pred_map, succ_map

    def _full_pred_succ_maps(self, pred_map: Dict[Bit, 'DAGNode'],
                             succ_map: Dict[Bit, 'DAGNode'], input_circuit: 'DAGCircuit',
                             wire_map: Dict[Bit, Bit]) -> Tuple[Dict[Bit, 'DAGNode'],
                                                                Dict[Bit, 'DAGNode']]:
        """Map all wires of the input circuit.

        Map all wires of the input circuit to predecessor and
        successor nodes in self, keyed on wires in self.

        Args:
            pred_map: predecessor_map returned from _make_pred_succ_maps
            succ_map: successor_map returned from _make_pred_succ_maps
            input_circuit: the input circuit
            wire_map: the map from wires of input_circuit to wires of self

        Returns:
            tuple: full_pred_map, full_succ_map

        Raises:
            DAGCircuitError: if more than one predecessor for output nodes
        """
        full_pred_map = {}
        full_succ_map = {}
        for w in input_circuit.input_map:
            # If w is wire mapped, find the corresponding predecessor
            # of the node
            if w in wire_map:
                full_pred_map[wire_map[w]] = pred_map[wire_map[w]]
                full_succ_map[wire_map[w]] = succ_map[wire_map[w]]
            else:
                # Otherwise, use the corresponding output nodes of self
                # and compute the predecessor.
                full_succ_map[w] = self.output_map[w]
                full_pred_map[w] = self._multi_graph.predecessors(
                    self.output_map[w])[0]
                if len(self._multi_graph.predecessors(self.output_map[w])) != 1:
                    raise DAGCircuitError("too many predecessors for %s[%d] "
                                          "output node" % (w.register, w.index))

        return full_pred_map, full_succ_map

    def __eq__(self, other):
        # TODO remove deepcopy calls after
        # https://github.com/mtreinish/retworkx/issues/27 is fixed
        slf = copy.deepcopy(self._multi_graph)
        oth = copy.deepcopy(other._multi_graph)

        return rx.is_isomorphic_node_match(slf, oth,
                                           DAGNode.semantic_eq)

    def topological_nodes(self):
        """
        Yield nodes in topological order.

        Returns:
            generator(DAGNode): node in topological order
        """

        def _key(x):
            return x.sort_key

        return iter(rx.lexicographical_topological_sort(
            self._multi_graph, key=_key))

    def topological_op_nodes(self) -> Iterator['DAGNode']:
        """Yield op nodes in topological order."""
        return (nd for nd in self.topological_nodes() if nd.type == 'op')

    def substitute_node_with_dag(self, node: 'DAGNode', input_dag: 'DAGCircuit',
                                 wires: Optional[List[Bit]] = None):
        """Replace ``node`` with ``input_dag``.

        Args:
            node: node to substitute
            input_dag: circuit that will substitute the node
            wires: gives an order for (qu)bits in the input circuit.
                This order gets matched to the node wires by qargs first,
                then cargs, then conditions.

        Raises:
            DAGCircuitError: if met with unexpected predecessor/successors
        """
        in_dag = input_dag
        condition = node.condition
        # the dag must be amended if used in a
        # conditional context. delete the op nodes and replay
        # them with the condition.
        if condition:
            in_dag = copy.deepcopy(input_dag)
            in_dag.add_creg(condition[0])
            to_replay = []
            for sorted_node in in_dag.topological_nodes():
                if sorted_node.type == "op":
                    sorted_node.op.condition = condition
                    to_replay.append(sorted_node)
            for input_node in in_dag.op_nodes():
                in_dag.remove_op_node(input_node)
            for replay_node in to_replay:
                in_dag.apply_operation_back(replay_node.op, replay_node.qargs,
                                            replay_node.cargs)

        if wires is None:
            wires = in_dag.wires

        self._check_wires_list(wires, node)

        # Create a proxy wire_map to identify fragments and duplicates
        # and determine what registers need to be added to self
        proxy_map = {w: QuantumRegister(1, 'proxy') for w in wires}
        add_qregs = self._check_edgemap_registers(proxy_map,
                                                  in_dag.qregs,
                                                  {}, False)
        for qreg in add_qregs:
            self.add_qreg(qreg)

        add_cregs = self._check_edgemap_registers(proxy_map,
                                                  in_dag.cregs,
                                                  {}, False)
        for creg in add_cregs:
            self.add_creg(creg)

        # Replace the node by iterating through the input_circuit.
        # Constructing and checking the validity of the wire_map.
        # If a gate is conditioned, we expect the replacement subcircuit
        # to depend on those condition bits as well.
        if node.type != "op":
            raise DAGCircuitError("expected node type \"op\", got %s"
                                  % node.type)

        condition_bit_list = self._bits_in_condition(node.condition)

        wire_map = dict(zip(wires, list(node.qargs) + list(node.cargs) + list(condition_bit_list)))
        self._check_wiremap_validity(wire_map, wires, self.input_map)
        pred_map, succ_map = self._make_pred_succ_maps(node)
        full_pred_map, full_succ_map = self._full_pred_succ_maps(pred_map, succ_map,
                                                                 in_dag, wire_map)

        if condition_bit_list:
            # If we are replacing a conditional node, map input dag through
            # wire_map to verify that it will not modify any of the conditioning
            # bits.
            condition_bits = set(condition_bit_list)

            for op_node in in_dag.op_nodes():
                mapped_cargs = {wire_map[carg] for carg in op_node.cargs}

                if condition_bits & mapped_cargs:
                    raise DAGCircuitError('Mapped DAG would alter clbits '
                                          'on which it would be conditioned.')

        # Now that we know the connections, delete node
        self._multi_graph.remove_node(node._node_id)

        # Iterate over nodes of input_circuit
        for sorted_node in in_dag.topological_op_nodes():
            # Insert a new node
            condition = self._map_condition(wire_map, sorted_node.condition)
            m_qargs = list(map(lambda x: wire_map.get(x, x),
                               sorted_node.qargs))
            m_cargs = list(map(lambda x: wire_map.get(x, x),
                               sorted_node.cargs))
            node_index = self._add_op_node(sorted_node.op, m_qargs, m_cargs)

            # Add edges from predecessor nodes to new node
            # and update predecessor nodes that change
            all_cbits = self._bits_in_condition(condition)
            all_cbits.extend(m_cargs)
            al = [m_qargs, all_cbits]
            for q in itertools.chain(*al):
                self._multi_graph.add_edge(full_pred_map[q],
                                           node_index,
                                           dict(name="%s[%s]" % (q.register.name, q.index),
                                                wire=q))
                full_pred_map[q] = node_index

        # Connect all predecessors and successors, and remove
        # residual edges between input and output nodes
        for w in full_pred_map:
            self._multi_graph.add_edge(full_pred_map[w],
                                       full_succ_map[w],
                                       dict(name="%s[%s]" % (w.register.name, w.index),
                                            wire=w))
            o_pred = self._multi_graph.predecessors(self.output_map[w]._node_id)
            if len(o_pred) > 1:
                if len(o_pred) != 2:
                    raise DAGCircuitError("expected 2 predecessors here")

                p = [x for x in o_pred if x != full_pred_map[w]]
                if len(p) != 1:
                    raise DAGCircuitError("expected 1 predecessor to pass filter")

                self._multi_graph.remove_edge(p[0], self.output_map[w])

    def substitute_node(self, node: 'DAGNode', op: Instruction, inplace: bool = False) -> 'DAGNode':
        """Replace ``node`` with a single instruction. qargs, cargs and
        conditions for the new instruction will be inferred from the node to be
        replaced. The new instruction will be checked to match the shape of the
        replaced instruction.

        Args:
            node: Node to be replaced
            op: The :class:`qiskit.circuit.Instruction` instance to be added to the DAG
            inplace: Default False. If True, existing DAG node will be modified
                to include ``op``. Otherwise, a new DAG node will be used.

        Returns:
            The new node containing the added instruction.

        Raises:
            DAGCircuitError: If replacement instruction was incompatible with
                location of target node.
        """

        if node.type != 'op':
            raise DAGCircuitError('Only DAGNodes of type "op" can be replaced.')

        if (
                node.op.num_qubits != op.num_qubits
                or node.op.num_clbits != op.num_clbits
        ):
            raise DAGCircuitError(
                'Cannot replace node of width ({} qubits, {} clbits) with '
                'instruction of mismatched width ({} qubits, {} clbits).'.format(
                    node.op.num_qubits, node.op.num_clbits,
                    op.num_qubits, op.num_clbits))

        if inplace:
            node.op = op
            node.name = op.name
            return node

        new_node = copy.copy(node)
        new_node.op = op
        new_node.name = op.name

        node_index = self._multi_graph.add_node(new_node)
        new_node._node_id = node_index

        in_edges = self._multi_graph.in_edges(node._node_id)
        out_edges = self._multi_graph.out_edges(node._node_id)

        for src_id, _, data in in_edges:
            self._multi_graph.add_edge(src_id, node_index, data)
        for _, dest_id, data in out_edges:
            self._multi_graph.add_edge(node_index, dest_id, data)

        self._multi_graph.remove_node(node._node_id)

        return new_node

    def node(self, node_id: int) -> 'DAGNode':
        """Get the node in the dag.

        Args:
            node_id: Node identifier.

        Returns:
            The node with the given ``node_id``.
        """
        return self._multi_graph.get_node_data(node_id)

    def nodes(self) -> Iterator['DAGNode']:
        """Iterator for node values.

        Yield:
            Nodes in this circuit.
        """
        yield from self._multi_graph.nodes()

    def edges(self, nodes: Optional[Union[List['DAGNode'], 'DAGNode']] = None) \
            -> Iterator[Tuple['DAGNode', 'DAGNode', Dict[str, Bit]]]:
        """
        Iterator for edges incident to ``nodes``.

        This works by returning the output edges from the specified nodes. If
        no nodes are specified all edges from the graph are returned.

        Args:
            nodes: Either a list of nodes or a single
                input node. If none is specified all edges are returned from
                the graph.

        Yield:
            edge: the edge in the same format as out_edges the tuple
                (source node, destination node, edge data)
        """
        if nodes is None:
            nodes = self._multi_graph.nodes()

        elif isinstance(nodes, DAGNode):
            nodes = [nodes]
        for node in nodes:
            raw_nodes = self._multi_graph.out_edges(node._node_id)
            for source, dest, edge in raw_nodes:
                yield (self._multi_graph.get_node_data(source),
                       self._multi_graph.get_node_data(dest),
                       edge)

    def op_nodes(self, op: Optional[Instruction] = None,
                 include_directives: bool = True) -> List[DAGNode]:
        """Get the list of "op" nodes in the dag.

        Args:
            op: :class:`qiskit.circuit.Instruction` subclass op nodes to
                return. If None, return all op nodes.
            include_directives: include `barrier`, `snapshot` etc.

        Returns:
            The list of nodes containing the given ``op``.
        """
        nodes = []
        for node in self._multi_graph.nodes():
            if node.type == "op":
                if not include_directives and node.name in ['snapshot', 'barrier']:
                    continue
                if op is None or isinstance(node.op, op):
                    nodes.append(node)
        return nodes

    def gate_nodes(self) -> List['DAGNode']:
        """Return the list of gate nodes in the dag."""
        nodes = []
        for node in self.op_nodes():
            if isinstance(node.op, Gate):
                nodes.append(node)
        return nodes

    def named_nodes(self, *names: str) -> List['DAGNode']:
        """Returns list of "op" nodes with the given name.

        Args:
            names: operation names

        Returns:
            list of op nodes with given ``names``
        """
        named_nodes = []
        for node in self._multi_graph.nodes():
            if node.type == 'op' and node.op.name in names:
                named_nodes.append(node)
        return named_nodes

    def twoQ_gates(self) -> List[DAGNode]:
        """Get list of 2-qubit gates. Ignore snapshot, barriers, and the like."""
        warnings.warn('deprecated function, use dag.two_qubit_ops(). '
                      'filter output by isinstance(op, Gate) to only get unitary Gates.',
                      DeprecationWarning, stacklevel=2)
        two_q_gates = []
        for node in self.gate_nodes():
            if len(node.qargs) == 2:
                two_q_gates.append(node)
        return two_q_gates

    def threeQ_or_more_gates(self) -> List[DAGNode]:
        """Get list of 3-or-more-qubit gates: (id, data)."""
        warnings.warn('deprecated function, use dag.multi_qubit_ops(). '
                      'filter output by isinstance(op, Gate) to only get unitary Gates.',
                      DeprecationWarning, stacklevel=2)
        three_q_gates = []
        for node in self.gate_nodes():
            if len(node.qargs) >= 3:
                three_q_gates.append(node)
        return three_q_gates

    def two_qubit_ops(self):
        """Get list of 2 qubit operations. Ignore directives like snapshot and barrier."""
        ops = []
        for node in self.op_nodes(include_directives=False):
            if len(node.qargs) == 2:
                ops.append(node)
        return ops

    def multi_qubit_ops(self):
        """Get list of 3+ qubit operations. Ignore directives like snapshot and barrier."""
        ops = []
        for node in self.op_nodes(include_directives=False):
            if len(node.qargs) >= 3:
                ops.append(node)
        return ops

    def longest_path(self) -> List[DAGNode]:
        """Returns the longest path in the dag as a list of DAGNodes."""
        return [self._multi_graph.get_node_data(x) for x in rx.dag_longest_path(self._multi_graph)]

    def successors(self, node):
        """Returns iterator of the successors of a node as DAGNodes."""
        return iter(self._multi_graph.successors(node._node_id))

    def predecessors(self, node):
        """Returns iterator of the predecessors of a node as DAGNodes."""
        return iter(self._multi_graph.predecessors(node._node_id))

    def quantum_predecessors(self, node: DAGNode) -> Iterator[DAGNode]:
        """
        Returns iterator of the predecessors of a node that are
        connected by a quantum edge.

        Args:
            node: The node to return predecessors of.

        Yields:
            The predecessors of ``node`` that are connected by a quantum edge.
        """
        for predecessor in self.predecessors(node):
            if any(isinstance(x['wire'], Qubit) for x in
                   self._multi_graph.get_all_edge_data(
                       predecessor._node_id, node._node_id)):
                yield predecessor

    def ancestors(self, node: 'DAGNode') -> Set['DAGNode']:
        """Returns set of the ancestors of a node as DAGNodes.

        Args:
            node: The node to return ancestors of.

        Returns:
            The ancestors of ``node``
        """
        return {
            self._multi_graph.get_node_data(x) for x in rx.ancestors(
                self._multi_graph, node._node_id)}

    def descendants(self, node: 'DAGNode') -> Set['DAGNode']:
        """Returns set of the descendants of a node as DAGNodes.

        Args:
            node: The node to return descendants of.

        Returns:
            The descendants of ``node``
        """
        return {
            self._multi_graph.get_node_data(x) for x in rx.descendants(
                self._multi_graph, node._node_id)}

    def bfs_successors(self, node: 'DAGNode') -> Iterator[Tuple['DAGNode', List['DAGNode']]]:
        """
        Returns an iterator of tuples containing the current node and a list
        of is its successors in  BFS order.

        Args:
            node: Starting node for breadth-first search

        Returns:
            ``node`` and its successors in bredth-first search order.
        """
        return iter(rx.bfs_successors(self._multi_graph, node._node_id))

    def quantum_successors(self, node: 'DAGNode') -> Iterator['DAGNode']:
        """Returns iterator of the successors of a node that are
        connected by a quantum edge."""
        for successor in self.successors(node):
            if any(isinstance(x['wire'], Qubit) for x in
                   self._multi_graph.get_all_edge_data(
                       node._node_id, successor._node_id)):
                yield successor

    def remove_op_node(self, node: 'DAGNode'):
        """Remove the given operation node.

        Add edges from its predecessors to its successors.

        Args:
            node: An operation node.

        Raises:
            DAGCircuitError: If the given ``node`` is not an op node
        """
        if node.type != 'op':
            raise DAGCircuitError('The method remove_op_node only works on op node types. An "%s" '
                                  'node type was wrongly provided.' % node.type)

        pred_map, succ_map = self._make_pred_succ_maps(node)

        # remove from graph and map
        self._multi_graph.remove_node(node._node_id)

        for w in pred_map.keys():
            self._multi_graph.add_edge(pred_map[w], succ_map[w],
                                       dict(name="%s[%s]" % (w.register.name, w.index), wire=w))

    def remove_ancestors_of(self, node: DAGNode):
        """Remove all of the ancestor operation nodes of node."""
        anc = rx.ancestors(self._multi_graph, node)
        # TODO: probably better to do all at once using
        # multi_graph.remove_nodes_from; same for related functions ...
        for anc_node in anc:
            if anc_node.type == "op":
                self.remove_op_node(anc_node)

    def remove_descendants_of(self, node: DAGNode):
        """Remove all of the descendant operation nodes of node."""
        desc = rx.descendants(self._multi_graph, node)
        for desc_node in desc:
            if desc_node.type == "op":
                self.remove_op_node(desc_node)

    def remove_nonancestors_of(self, node: DAGNode):
        """Remove all of the non-ancestors operation nodes of node."""
        anc = rx.ancestors(self._multi_graph, node)
        comp = list(set(self._multi_graph.nodes()) - set(anc))
        for n in comp:
            if n.type == "op":
                self.remove_op_node(n)

    def remove_nondescendants_of(self, node: DAGNode):
        """Remove all of the non-descendants operation nodes of node."""
        dec = rx.descendants(self._multi_graph, node)
        comp = list(set(self._multi_graph.nodes()) - set(dec))
        for n in comp:
            if n.type == "op":
                self.remove_op_node(n)

    def front_layer(self):
        """Return a list of op nodes in the first layer of this dag.
        """
        graph_layers = self.multigraph_layers()
        try:
            next(graph_layers)  # Remove input nodes
        except StopIteration:
            return []

        op_nodes = [node for node in next(graph_layers) if node.type == "op"]

        return op_nodes

    def layers(self) -> Iterator[Dict[str, Union['DAGCircuit', List[List[Qubit]]]]]:
        """Yield a shallow view on a layer of this DAGCircuit for all d layers of this circuit.

        A layer is a circuit whose gates act on disjoint qubits, i.e.,
        a layer has depth 1. The total number of layers equals the
        circuit depth d. The layers are indexed from 0 to d-1 with the
        earliest layer at index 0. The layers are constructed using a
        greedy algorithm. Each returned layer is a dict containing
        {"graph": circuit graph, "partition": list of qubit lists}.

        The returned layer contains new (but semantically equivalent) DAGNodes.
        These are not the same as nodes of the original dag, but are equivalent
        via DAGNode.semantic_eq(node1, node2).
        """
        # TODO: Gates that use the same cbits will end up in different
        #   layers as this is currently implemented. This may not be
        #   the desired behavior.
        graph_layers = self.multigraph_layers()
        try:
            next(graph_layers)  # Remove input nodes
        except StopIteration:
            return

        for graph_layer in graph_layers:

            # Get the op nodes from the layer, removing any input and output nodes.
            op_nodes = [node for node in graph_layer if node.type == "op"]

            # Sort to make sure they are in the order they were added to the original DAG
            # It has to be done by node_id as graph_layer is just a list of nodes
            # with no implied topology
            # Drawing tools rely on _node_id to infer order of node creation
            # so we need this to be preserved by layers()
            op_nodes.sort(key=lambda nd: nd._node_id)

            # Stop yielding once there are no more op_nodes in a layer.
            if not op_nodes:
                return

            # Construct a shallow copy of self
            new_layer = DAGCircuit()
            new_layer.name = self.name

            # add in the registers - this adds the input/output nodes
            for creg in self.cregs.values():
                new_layer.add_creg(creg)
            for qreg in self.qregs.values():
                new_layer.add_qreg(qreg)

            for node in op_nodes:
                # this creates new DAGNodes in the new_layer
                new_layer.apply_operation_back(node.op,
                                               node.qargs,
                                               node.cargs)

            # The quantum registers that have an operation in this layer.
            support_list = [
                op_node.qargs
                for op_node in new_layer.op_nodes()
                if op_node.name not in {"barrier", "snapshot", "save", "load", "noise"}
            ]

            yield {"graph": new_layer, "partition": support_list}

    def serial_layers(self) -> Iterator[Dict[str, Union['DAGCircuit', List[List[Qubit]]]]]:
        """Yield a layer for all gates of this circuit.

        A serial layer is a circuit with one gate. The layers have the
        same structure as in
        :py:meth:`~qiskit.dagcircuit.DAGCircuit.layers()`.
        """
        for next_node in self.topological_op_nodes():
            new_layer = DAGCircuit()
            for qreg in self.qregs.values():
                new_layer.add_qreg(qreg)
            for creg in self.cregs.values():
                new_layer.add_creg(creg)
            # Save the support of the operation we add to the layer
            support_list = []
            # Operation data
            op = copy.copy(next_node.op)
            qa = copy.copy(next_node.qargs)
            ca = copy.copy(next_node.cargs)
            co = copy.copy(next_node.condition)
            _ = self._bits_in_condition(co)

            # Add node to new_layer
            new_layer.apply_operation_back(op, qa, ca)
            # Add operation to partition
            if next_node.name not in ["barrier",
                                      "snapshot", "save", "load", "noise"]:
                support_list.append(list(qa))
            l_dict = {"graph": new_layer, "partition": support_list}
            yield l_dict

    def multigraph_layers(self):
        """Yield layers of the multigraph."""
        first_layer = [x._node_id for x in self.input_map.values()]
        return iter(rx.layers(self._multi_graph, first_layer))

    def collect_runs(self, namelist: Union[str, List[str]]) -> Set[Tuple['DAGNode', ...]]:
        """Return a set of non-conditional runs of "op" nodes with the given names.

        Nodes must have only one successor to continue the run.

        For example::

            # For a dag with 'h q[0]; cx q[0],q[1]; cx q[0],q[1]; h q[1];'

            collect_runs("cx")
            # Would return: {(<DAGNode of first cx>, <DAGNode of second cx>)}

            collect_runs("h")
            # Would return: {(<DAGNode of first h>,), (<DAGNode of second h>,)}

            collect_runs(["h", "cx"])
            # Would return: {(<DAGNode of first h>, <DAGNode of first cx>, DAGNode of second cx),
            #                (<DAGNode of second h>,)}

        Args:
              namelist: name(s) of operations.
                Can contain names that are not in the circuit's basis.

        Returns:
            A set of tuples containing op nodes with the given names from ``namelist``
        """
        group_list = []

        # Iterate through the nodes of self in topological order
        # and form tuples containing sequences of gates
        # on the same qubit(s).
        topo_ops = list(self.topological_op_nodes())
        nodes_seen = dict(zip(topo_ops, [False] * len(topo_ops)))
        for node in topo_ops:
            if node.name in namelist and node.condition is None \
                    and not nodes_seen[node]:
                group = [node]
                nodes_seen[node] = True
                s = self._multi_graph.successors(node._node_id)
                while len(s) == 1 and \
                        s[0].type == "op" and \
                        s[0].name in namelist and \
                        s[0].condition is None:
                    group.append(s[0])
                    nodes_seen[s[0]] = True
                    s = self._multi_graph.successors(s[0]._node_id)
                if len(group) >= 1:
                    group_list.append(tuple(group))
        return set(group_list)

    def nodes_on_wire(self, wire: Bit, only_ops: bool = False) -> Iterator['DAGNode']:
        """
        Iterator for nodes that affect a given wire.

        Args:
            wire: the wire to be looked at.
            only_ops: True if only the ops nodes are wanted;
                otherwise, all nodes are returned.

        Yield:
             The successive ops on the given wire

        Raises:
            DAGCircuitError: if the given wire doesn't exist in the DAG
        """
        current_node = self.input_map.get(wire, None)

        if not current_node:
            raise DAGCircuitError('The given wire %s is not present in the circuit'
                                  % str(wire))

        more_nodes = True
        while more_nodes:
            more_nodes = False
            # allow user to just get ops on the wire - not the input/output nodes
            if current_node.type == 'op' or not only_ops:
                yield current_node

            try:
                current_node = self._multi_graph.find_adjacent_node_by_edge(
                    current_node._node_id, lambda x: wire == x['wire'])
                more_nodes = True
            except rx.NoSuitableNeighbors:
                pass

    def count_ops(self) -> Dict[str, int]:
        """Count the occurrences of operation names.

        Returns:
            A dictionary of counts keyed on the operation name.
        """
        op_dict = {}
        for node in self.topological_op_nodes():
            name = node.name
            if name not in op_dict:
                op_dict[name] = 1
            else:
                op_dict[name] += 1
        return op_dict

    def count_ops_longest_path(self) -> Dict[str, int]:
        """Count the occurrences of operation names on the longest path.

        Returns:
            A dictionary of counts keyed on the operation name.
        """
        op_dict = {}
        path = self.longest_path()
        path = path[1:-1]     # remove qubits at beginning and end of path
        for node in path:
            name = node.name
            if name not in op_dict:
                op_dict[name] = 1
            else:
                op_dict[name] += 1
        return op_dict

    def properties(self) -> Dict[str, Union[int, Dict[str, int]]]:
        """Return a dictionary of circuit properties."""
        summary = {"size": self.size(),
                   "depth": self.depth(),
                   "width": self.width(),
                   "qubits": self.num_qubits(),
                   "bits": self.num_clbits(),
                   "factors": self.num_tensor_factors(),
                   "operations": self.count_ops()}
        return summary

    def draw(self, scale: float = 0.7,
             filename: Optional[str] = None,
             style: str = 'color') -> None:
        """
        Draws the dag circuit.

        This function needs `pydot <https://github.com/erocarrera/pydot>`_, which in turn needs
        `Graphviz <https://www.graphviz.org/>`_ to be installed.

        Args:
            scale: scaling factor
            filename: file path to save image to (format inferred from name)
            style:

                'plain': B&W graph;
                'color' (default): color input/output/op nodes

        Returns:
            If running in Jupyter notebook and not saving to file, returns an
            Ipython.display.image of the graph.
            Otherwise, returns None.
        """
        from qiskit.visualization.dag_visualization import dag_drawer
        return dag_drawer(dag=self, scale=scale, filename=filename, style=style)
