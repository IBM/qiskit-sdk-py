# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=missing-docstring

from qiskit import QuantumRegister
from qiskit.mapper import Coupling, CouplingError
from .common import QiskitTestCase


class OldCouplingTest(QiskitTestCase):
    # TODO Remove
    def test_coupling_dict2list(self):
        input_dict = {0: [1, 2], 1: [2]}
        result = Coupling.coupling_dict2list(input_dict)
        expected = [[0, 1], [0, 2], [1, 2]]
        self.assertEqual(expected, result)

    def test_coupling_dict2list_empty_dict(self):
        self.assertIsNone(Coupling.coupling_dict2list({}))

    def test_coupling_list2dict(self):
        input_list = [[0, 1], [0, 2], [1, 2]]
        result = Coupling.coupling_list2dict(input_list)
        expected = {0: [1, 2], 1: [2]}
        self.assertEqual(expected, result)

    def test_coupling_list2dict_empty_list(self):
        self.assertIsNone(Coupling.coupling_list2dict([]))

    def test_empty_coupling_class(self):
        coupling = Coupling()
        self.assertEqual(0, coupling.size())
        self.assertEqual([], coupling.get_qubits())
        self.assertEqual([], coupling.get_edges_qubits())
        self.assertFalse(coupling.connected())
        self.assertEqual("", str(coupling))

    def test_coupling_str(self):
        coupling_dict = {0: [1, 2], 1: [2]}
        coupling = Coupling(coupling_dict)
        expected = ("qubits: q[0] @ 1, q[1] @ 2, q[2] @ 3\n"
                    "edges: q[0]-q[1], q[0]-q[2], q[1]-q[2]")
        self.assertEqual(expected, str(coupling))

    def test_coupling_compute_distance(self):
        coupling_dict = {0: [1, 2], 1: [2]}
        coupling = Coupling(coupling_dict)
        self.assertTrue(coupling.connected())
        coupling.compute_distance()
        qubits = coupling.get_qubits()
        result = coupling.distance_qubits(qubits[0], qubits[1])
        self.assertEqual(1, result)

    def test_coupling_compute_distance_coupling_error(self):
        coupling = Coupling()
        self.assertRaises(CouplingError, coupling.compute_distance)

    def test_add_qubit(self):
        coupling = Coupling()
        self.assertEqual("", str(coupling))
        coupling.add_qubit((QuantumRegister(1, 'q'), 0))
        self.assertEqual("qubits: q[0] @ 1", str(coupling))

    def test_add_qubit_not_tuple(self):
        coupling = Coupling()
        self.assertRaises(CouplingError, coupling.add_qubit, QuantumRegister(1, 'q0'))

    def test_add_qubit_tuple_incorrect_form(self):
        coupling = Coupling()
        self.assertRaises(CouplingError, coupling.add_qubit,
                          (QuantumRegister(1, 'q'), '0'))

    def test_add_edge(self):
        coupling = Coupling()
        self.assertEqual("", str(coupling))
        coupling.add_edge_qubit((QuantumRegister(2, 'q'), 0), (QuantumRegister(1, 'q'), 1))
        expected = ("qubits: q[0] @ 1, q[1] @ 2\n"
                    "edges: q[0]-q[1]")
        self.assertEqual(expected, str(coupling))

    def test_distance_error(self):
        """Test distance_qubits method validation."""
        graph = Coupling({0: [1, 2], 1: [2]})
        self.assertRaises(CouplingError, graph.distance_qubits, (QuantumRegister(3, 'q0'), 0),
                          (QuantumRegister(3, 'q1'), 1))

class CouplingTest(QiskitTestCase):

    def test_empty_coupling_class(self):
        coupling = Coupling()
        self.assertEqual(0, len(coupling))
        self.assertEqual([], coupling.wires)
        self.assertEqual([], coupling.get_edges_qubits())
        self.assertFalse(coupling.is_connected())
        self.assertEqual("", repr(coupling))

    def test_coupling_str(self):
        coupling_dict = {0: [1, 2], 1: [2]}
        coupling = Coupling(coupling_dict)
        expected = ("[(0, 1), (0, 2), (1, 2)]")
        self.assertEqual(expected, repr(coupling))

    def test_coupling_distance(self):
        coupling_dict = {0: [1, 2], 1: [2]}
        coupling = Coupling(coupling_dict)
        self.assertTrue(coupling.is_connected())
        coupling.compute_distance()
        wires = coupling.wires
        result = coupling.distance(wires[0], wires[1])
        self.assertEqual(1, result)

    def test_add_wire(self):
        coupling = Coupling()
        self.assertEqual("", repr(coupling))
        coupling.add_wire(0)
        self.assertEqual([0], coupling.wires)
        self.assertEqual("", repr(coupling))

    def test_add_wire_not_int(self):
        coupling = Coupling()
        self.assertRaises(CouplingError, coupling.add_wire, 'q')

    def test_add_edge(self):
        coupling = Coupling()
        self.assertEqual("", repr(coupling))
        coupling.add_edge(0, 1)
        expected = ("[(0, 1)]")
        self.assertEqual(expected, repr(coupling))

    def test_distance_error(self):
        """Test distance between unconected wires."""
        graph = Coupling()
        graph.add_wire(0)
        graph.add_wire(1)
        self.assertRaises(CouplingError, graph.distance, 0, 1)
