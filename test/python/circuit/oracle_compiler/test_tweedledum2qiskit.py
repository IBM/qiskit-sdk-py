# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import unittest

from qiskit.circuit.oracle_compiler import LogicNetwork
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library.standard_gates import XGate


class TestTweedledum2Qiskit(unittest.TestCase):
    """Tests LogicNetwork.tweedledum2qiskit static method."""
    def test_x(self):
        tweedledum_circuit = {'num_qubits': 1, 'gates': [{'gate': 'X', 'qubits': [0]}]}
        circuit = LogicNetwork.tweedledum2qiskit(tweedledum_circuit)

        expected = QuantumCircuit(1)
        expected.x(0)

        self.assertEqual(circuit, expected)

    def test_cx_0_1(self):
        tweedledum_circuit = {'num_qubits': 2, 'gates': [{'gate': 'X',
                                                          'qubits': [1],
                                                          'control_qubits': [0],
                                                          'control_state': '1'}]}
        circuit = LogicNetwork.tweedledum2qiskit(tweedledum_circuit)

        expected = QuantumCircuit(2)
        expected.append(XGate().control(1, ctrl_state='1'), [0, 1])

        self.assertEqual(circuit, expected)

    def test_cx_1_0(self):
        tweedledum_circuit = {'num_qubits': 2, 'gates': [{'gate': 'X',
                                                          'qubits': [0],
                                                          'control_qubits': [1],
                                                          'control_state': '1'}]}
        circuit = LogicNetwork.tweedledum2qiskit(tweedledum_circuit)

        expected = QuantumCircuit(2)
        expected.append(XGate().control(1, ctrl_state='1'), [1, 0])

        self.assertEqual(expected, circuit)

    def test_cx_qreg(self):
        qr = QuantumRegister(2, 'qr')
        tweedledum_circuit = {'num_qubits': 2, 'gates': [{'gate': 'X',
                                                          'qubits': [0],
                                                          'control_qubits': [1],
                                                          'control_state': '1'}]}
        circuit = LogicNetwork.tweedledum2qiskit(tweedledum_circuit, qregs=[qr])

        expected = QuantumCircuit(qr)
        expected.append(XGate().control(1, ctrl_state='1'), [qr[1], qr[0]])

        self.assertEqual(expected, circuit)


if __name__ == '__main__':
    unittest.main()
