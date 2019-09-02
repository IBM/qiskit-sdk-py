# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Common visualization utilities."""

from enum import Enum
import numpy as np
from qiskit.converters import circuit_to_dag
from qiskit.visualization.exceptions import VisualizationError

try:
    import PIL
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _validate_input_state(quantum_state):
    """Validates the input to state visualization functions.

    Args:
        quantum_state (ndarray): Input state / density matrix.
    Returns:
        rho: A 2d numpy array for the density matrix.
    Raises:
        VisualizationError: Invalid input.
    """
    rho = np.asarray(quantum_state)
    if rho.ndim == 1:
        rho = np.outer(rho, np.conj(rho))
    # Check the shape of the input is a square matrix
    shape = np.shape(rho)
    if len(shape) != 2 or shape[0] != shape[1]:
        raise VisualizationError("Input is not a valid quantum state.")
    # Check state is an n-qubit state
    num = int(np.log2(rho.shape[0]))
    if 2 ** num != rho.shape[0]:
        raise VisualizationError("Input is not a multi-qubit quantum state.")
    return rho


def _trim(image):
    """Trim a PIL image and remove white space."""
    if not HAS_PIL:
        raise ImportError('The latex drawer needs pillow installed. '
                          'Run "pip install pillow" before using the '
                          'latex drawer.')
    background = PIL.Image.new(image.mode, image.size, image.getpixel((0, 0)))
    diff = PIL.ImageChops.difference(image, background)
    diff = PIL.ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        image = image.crop(bbox)
    return image


def _get_layered_instructions(circuit, reverse_bits=False, justify=None, idle_wires=True):
    """
    Given a circuit, return a tuple (qregs, cregs, ops) where
    qregs and cregs are the quantum and classical registers
    in order (based on reverse_bits) and ops is a list
    of DAG nodes which type is "operation".
    Args:
        circuit (QuantumCircuit): From where the information is extracted.
        reverse_bits (bool): If true the order of the bits in the registers is
            reversed.
        justify (str) : `left`, `right` or `none`. Defaults to `left`. Says how
            the circuit should be justified.
        idle_wires (bool): Include idle wires. Default is True.
    Returns:
        Tuple(list,list,list): To be consumed by the visualizer directly.
    """
    if justify:
        justify = justify.lower()

    # default to left
    justify = justify if justify in ('right', 'none') else 'left'

    dag = circuit_to_dag(circuit)
    ops = []
    qregs = dag.qubits()
    cregs = dag.clbits()

    if justify == 'none':
        for node in dag.topological_op_nodes():
            ops.append([node])

    if justify == 'left':
        spooler = LayerSpooler(qregs, Justification.LEFT)

        for dag_layer in dag.layers():
            current_index = spooler.last_index()
            dag_nodes = _sorted_nodes(dag_layer)
            for node in dag_nodes:
                spooler.add(node, current_index)

        ops = spooler.as_list()

    if justify == 'right':
        spooler = LayerSpooler(qregs, Justification.RIGHT)

        dag_layers = []

        for dag_layer in dag.layers():
            dag_layers.append(dag_layer)

        # going right to left!
        dag_layers.reverse()

        for dag_layer in dag_layers:
            current_index = 0
            dag_nodes = _sorted_nodes(dag_layer)
            for node in dag_nodes:
                spooler.add(node, current_index)

        ops = spooler.as_list()

    if reverse_bits:
        qregs.reverse()
        cregs.reverse()

    if not idle_wires:
        for wire in dag.idle_wires():
            if wire in qregs:
                qregs.remove(wire)
            if wire in cregs:
                cregs.remove(wire)

    return qregs, cregs, ops


def _sorted_nodes(dag_layer):
    """Convert DAG layer into list of nodes sorted by node_id
    qiskit-terra #2802
    """
    dag_instructions = dag_layer['graph'].op_nodes()
    # sort into the order they were input
    dag_instructions.sort(key=lambda nd: nd._node_id)
    return dag_instructions


def _is_multibit_gate(node):
    """Return True .IFF. node spans multiple qubits
    qiskit-terra #2802
    """
    return len(node.qargs) + len(node.cargs) > 1


def _get_gate_span(qregs, instruction):
    """Get the list of qubits drawing this gate would cover
    qiskit-terra #2802
    """

    min_index = len(qregs)
    max_index = 0
    for qreg in instruction.qargs:
        index = qregs.index(qreg)

        if index < min_index:
            min_index = index
        if index > max_index:
            max_index = index

    if instruction.cargs:
        return qregs[min_index:]

    return qregs[min_index:max_index + 1]


def _present(node, nodes):
    """Return True .IFF. any qreg in 'node' is present in 'nodes'
    qiskit-terra #2802
    """
    present = False
    for extant in nodes:
        if any(i in extant.qargs for i in node.qargs):
            present = True
            break
    return present


def _any_crossover(qregs, node, nodes):
    """Return True .IFF. 'node' crosses over any in 'nodes'
    qiskit-terra #2802
    """
    gate_span = _get_gate_span(qregs, node)
    all_indices = []
    for check_node in nodes:
        if check_node != node:
            all_indices += _get_gate_span(qregs, check_node)
    return any(i in gate_span for i in all_indices)


class Justification(Enum):
    """Enumerate justification types used in LayerSpooler
    qiskit-terra #2802
    """
    LEFT = 1
    RIGHT = 2


class LayerSpooler():
    """Manipulate list of layer dicts for _get_layered_instructions
    qiskit-terra #2802
    """

    def __init__(self, qregs, justification):
        """Create spool"""
        self.qregs = qregs
        self.justification = justification
        self.spool = []

    def size(self):
        """Return number of entries in spool"""
        return len(self.spool)

    def last_index(self):
        """Return last index in spool"""
        return len(self.spool) - 1

    def as_list(self):
        """Get the spool as a list of layer values"""
        return list(self.spool)

    def append(self, layer):
        """Append to spool"""
        self.spool.append(layer)

    def prepend(self, layer):
        """Prepend layer to spool"""
        self.spool.insert(0, layer)

    def insertable(self, node, nodes):
        """True .IFF. we can add 'node' to layer 'nodes'"""
        return not _any_crossover(self.qregs, node, nodes)

    def slide_from_left(self, node, index):
        """Insert node into first layer where there is no conflict going l > r
        """
        if self.size() == 0:
            self.append([node])
            inserted = True

        else:
            inserted = False
            curr_index = index
            last_insertable_index = None

            while curr_index > -1:
                if self.insertable(node, self.spool[curr_index]):
                    last_insertable_index = curr_index
                # else:
                    # if _present(node, self.spool[curr_index]):
                        # break
                curr_index = curr_index - 1

            if last_insertable_index:
                self.spool[last_insertable_index].append(node)
                inserted = True

            else:
                inserted = False
                curr_index = index
                while curr_index < self.size():
                    if self.insertable(node, self.spool[curr_index]):
                        self.spool[curr_index].append(node)
                        inserted = True
                        break
                    curr_index = curr_index + 1

        if not inserted:
            self.append([node])

    def slide_from_right(self, node, index):
        """Insert node into rightmost layer as long there is no conflict
        """
        if self.size() == 0:
            self.prepend([node])
            inserted = True

        else:
            inserted = False
            curr_index = index
            last_insertable_index = None

            while curr_index < self.size():
                if self.insertable(node, self.spool[curr_index]):
                    last_insertable_index = curr_index
                # else:
                    # if _present(node, self.spool[curr_index]):
                        # break
                curr_index = curr_index + 1

            if last_insertable_index:
                self.spool[last_insertable_index].append(node)
                inserted = True

            else:
                curr_index = index
                while curr_index > -1:
                    if self.insertable(node, self.spool[curr_index]):
                        self.spool[curr_index].append(node)
                        inserted = True
                        break
                    curr_index = curr_index - 1

        if not inserted:
            self.prepend([node])

    def add(self, node, index):
        """Add 'node' where it belongs, starting the try at 'index'
        """
        if self.justification == Justification.LEFT:
            self.slide_from_left(node, index)
        else:
            self.slide_from_right(node, index)
