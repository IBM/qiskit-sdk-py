# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.


"""Commutation analysis and transformation pass testing"""

import unittest

from qiskit import QuantumRegister, QuantumCircuit
from qiskit.transpiler import PropertySet
from qiskit.transpiler.passes import CommutationAnalysis
from qiskit.converters import circuit_to_dag
from qiskit.test import QiskitTestCase


class TestCommutationAnalysis(QiskitTestCase):
    """Test the Communttion pass."""

    def setUp(self):
        self.pass_ = CommutationAnalysis()
        self.pset = self.pass_.property_set = PropertySet()

    def assertCommutationSet(self, result, expected):
        """ Compares the result of propertyset["commutation_set"] with a dictionary of the form
        {'q[0]': [ [node_id, ...], [node_id, ...] ]}
        """
        result_to_compare = {}
        for qbit_str, sets in result.items():
            if not isinstance(qbit_str, str):
                continue
            result_to_compare[qbit_str] = []
            for commutation_set in sets[1:-1]:
                result_to_compare[qbit_str].append(
                    sorted([node._node_id for node in commutation_set]))

        for qbit_str, sets in expected.items():
            for commutation_set in sets:
                commutation_set.sort()

        self.assertDictEqual(result_to_compare, expected)

    def test_commutation_set_property_is_created(self):
        """Test property is created"""
        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.h(qr)
        dag = circuit_to_dag(circuit)

        self.assertIsNone(self.pset['commutation_set'])
        self.pass_.run(dag)
        self.assertIsNotNone(self.pset['commutation_set'])

    def test_all_gates(self):
        """Test all gates on 1 and 2 qubits

        qr0:----[H]---[x]---[y]---[t]---[s]---[rz]---[u1]---[u2]---[u3]---.---.---.--
                                                                          |   |   |
        qr1:-------------------------------------------------------------(+)-(Y)--.--
        """
        qr = QuantumRegister(2, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.h(qr[0])
        circuit.x(qr[0])
        circuit.y(qr[0])
        circuit.t(qr[0])
        circuit.s(qr[0])
        circuit.rz(0.5, qr[0])
        circuit.u1(0.5, qr[0])
        circuit.u2(0.5, 0.6, qr[0])
        circuit.u3(0.5, 0.6, 0.7, qr[0])
        circuit.cx(qr[0], qr[1])
        circuit.cy(qr[0], qr[1])
        circuit.cz(qr[0], qr[1])
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[5], [6], [7], [8, 9, 10, 11], [12], [13], [14], [15], [16]],
                    'qr[1]': [[14], [15], [16]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_non_commutative_circuit(self):
        """A simple circuit where no gates commute

        qr0:---[H]---

        qr1:---[H]---

        qr2:---[H]---
        """
        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.h(qr)
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[7]], 'qr[1]': [[8]], 'qr[2]': [[9]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_non_commutative_circuit_2(self):
        """A simple circuit where no gates commute

        qr0:----.-------------
                |
        qr1:---(+)------.-----
                        |
        qr2:---[H]-----(+)----
        """
        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.h(qr[2])
        circuit.cx(qr[1], qr[2])
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[7]], 'qr[1]': [[7], [9]], 'qr[2]': [[8], [9]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_commutative_circuit(self):
        """A simple circuit where two CNOTs commute

        qr0:----.------------
                |
        qr1:---(+)-----(+)---
                        |
        qr2:---[H]------.----
        """

        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.h(qr[2])
        circuit.cx(qr[2], qr[1])
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[7]], 'qr[1]': [[7, 9]], 'qr[2]': [[8], [9]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_commutative_circuit_2(self):
        """A simple circuit where a CNOT and a Z gate commute,
        and a CNOT and a CNOT commute

        qr0:----.-----[Z]-----
                |
        qr1:---(+)----(+)----
                       |
        qr2:---[H]-----.----
        """

        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.z(qr[0])
        circuit.h(qr[2])
        circuit.cx(qr[2], qr[1])
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[7, 8]], 'qr[1]': [[7, 10]], 'qr[2]': [[9], [10]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_commutative_circuit_3(self):
        """A simple circuit where multiple gates commute

        qr0:----.-----[Z]-----.----[z]-----
                |             |
        qr1:---(+)----(+)----(+)----.------
                       |            |
        qr2:---[H]-----.-----[x]---(+)-----
        """
        qr = QuantumRegister(3, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.h(qr[2])
        circuit.z(qr[0])
        circuit.cx(qr[2], qr[1])
        circuit.cx(qr[0], qr[1])
        circuit.x(qr[2])
        circuit.z(qr[0])
        circuit.cx(qr[1], qr[2])
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[7, 9, 11, 13]],
                    'qr[1]': [[7, 10, 11], [14]],
                    'qr[2]': [[8], [10], [12, 14]]}

        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_jordan_wigner_type_circuit(self):
        """A Jordan-Wigner type circuit where consecutive CNOTs commute

        qr0:----.-------------------------------------------------------------.----
                |                                                             |
        qr1:---(+)----.-------------------------------------------------.----(+)---
                      |                                                 |
        qr2:---------(+)----.-------------------------------------.----(+)---------
                            |                                     |
        qr3:---------------(+)----.-------------------------.----(+)---------------
                                  |                         |
        qr4:---------------------(+)----.-------------.----(+)---------------------
                                        |             |
        qr5:---------------------------(+)----[z]----(+)---------------------------
        """
        qr = QuantumRegister(6, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.cx(qr[1], qr[2])
        circuit.cx(qr[2], qr[3])
        circuit.cx(qr[3], qr[4])
        circuit.cx(qr[4], qr[5])
        circuit.z(qr[5])
        circuit.cx(qr[4], qr[5])
        circuit.cx(qr[3], qr[4])
        circuit.cx(qr[2], qr[3])
        circuit.cx(qr[1], qr[2])
        circuit.cx(qr[0], qr[1])

        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[13, 23]],
                    'qr[1]': [[13], [14, 22], [23]],
                    'qr[2]': [[14], [15, 21], [22]],
                    'qr[3]': [[15], [16, 20], [21]],
                    'qr[4]': [[16], [17, 19], [20]],
                    'qr[5]': [[17], [18], [19]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)

    def test_all_commute_circuit(self):
        """Test circuit with that all commute"""
        qr = QuantumRegister(5, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.cx(qr[0], qr[1])
        circuit.cx(qr[2], qr[1])
        circuit.cx(qr[4], qr[3])
        circuit.cx(qr[2], qr[3])
        circuit.z(qr[0])
        circuit.z(qr[4])
        circuit.cx(qr[0], qr[1])
        circuit.cx(qr[2], qr[1])
        circuit.cx(qr[4], qr[3])
        circuit.cx(qr[2], qr[3])
        dag = circuit_to_dag(circuit)

        self.pass_.run(dag)

        expected = {'qr[0]': [[11, 15, 17]],
                    'qr[1]': [[11, 12, 17, 18]],
                    'qr[2]': [[12, 14, 18, 20]],
                    'qr[3]': [[13, 14, 19, 20]],
                    'qr[4]': [[13, 16, 19]]}
        self.assertCommutationSet(self.pset["commutation_set"], expected)


if __name__ == '__main__':
    unittest.main()
