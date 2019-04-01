# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Test the ApplyLayout pass"""

import unittest

from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
from qiskit.converters import circuit_to_dag
from qiskit.mapper import CouplingMap, Layout
from qiskit.test import QiskitTestCase
from qiskit.transpiler.passes import ApplyLayout


class TestApplyLayout(QiskitTestCase):
    """ Tests the ApplyLayout pass."""

    def test_single_swap_case(self):
        """Test if the circuit with virtual qubits is transformed into
        the circuit with physical qubits.

        [Circuit with virtual qubits]
          v0:--X---.---M(v1->c1)
               |   |
          v1:--X---|---M(v0->c0)
                   |
          v2:-----(+)--M(v2->c2)

         Initial layout: [('vq', 0), ('vq', 1), ('vq', 2)]
         CouplingMap map: [1]--[0]--[2]

        [Circuit with physical qubits]
          q0:--X---.---M(q0->c1)
               |   |
          q1:--X---|---M(q1->c0)
                   |
          q2:-----(+)--M(q2->c2)
        """
        coupling = CouplingMap([[0, 1], [0, 2]])

        v = QuantumRegister(3, 'v')
        cr = ClassicalRegister(3, 'c')
        circuit = QuantumCircuit(v, cr)
        circuit.swap(v[0], v[1])
        circuit.cx(v[1], v[2])
        circuit.measure(v[1], cr[1])
        circuit.measure(v[2], cr[2])

        initial_layout = Layout([v[i] for i in range(3)])

        q = QuantumRegister(3, 'q')
        expected = QuantumCircuit(q, cr)
        expected.swap(q[0], q[1])
        expected.cx(q[0], q[2])
        expected.measure(q[0], cr[1])
        expected.measure(q[2], cr[2])

        dag = circuit_to_dag(circuit)
        pass_ = ApplyLayout(coupling=coupling, initial_layout=initial_layout)
        after = pass_.run(dag)

        self.assertEqual(circuit_to_dag(expected), after)


if __name__ == '__main__':
    unittest.main()
