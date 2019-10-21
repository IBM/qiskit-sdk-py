# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=redefined-builtin

"""Tests PassManager.run()"""

from qiskit import QuantumRegister, QuantumCircuit
from qiskit.extensions.standard import CnotGate
from qiskit.transpiler.preset_passmanagers import level_1_pass_manager
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeMelbourne
from qiskit.transpiler import Layout, CouplingMap
from qiskit.transpiler.transpile_config import TranspileConfig


class TestPassManagerRun(QiskitTestCase):
    """Test default_pass_manager.run(circuit(s))."""

    def test_default_pass_manager_single(self):
        """Test default_pass_manager.run(circuit).

        circuit:
        qr0:-[H]--.------------  -> 1
                  |
        qr1:-----(+)--.--------  -> 2
                      |
        qr2:---------(+)--.----  -> 3
                          |
        qr3:-------------(+)---  -> 5

        device:
        0  -  1  -  2  -  3  -  4  -  5  -  6

              |     |     |     |     |     |

              13 -  12  - 11 -  10 -  9  -  8  -   7
        """
        qr = QuantumRegister(4, 'qr')
        circuit = QuantumCircuit(qr)
        circuit.h(qr[0])
        circuit.cx(qr[0], qr[1])
        circuit.cx(qr[1], qr[2])
        circuit.cx(qr[2], qr[3])

        coupling_map = FakeMelbourne().configuration().coupling_map
        basis_gates = FakeMelbourne().configuration().basis_gates
        initial_layout = [None, qr[0], qr[1], qr[2], None, qr[3]]

        pass_manager = level_1_pass_manager(TranspileConfig(
            basis_gates=basis_gates,
            coupling_map=CouplingMap(coupling_map),
            initial_layout=Layout.from_qubit_list(initial_layout),
            seed_transpiler=42,
            optimization_level=1))
        new_circuit = pass_manager.run(circuit)

        for gate, qargs, _ in new_circuit.data:
            if isinstance(gate, CnotGate):
                self.assertIn([x[1] for x in qargs], coupling_map)

    def test_default_pass_manager_two(self):
        """Test default_pass_manager.run(circuitS).

        circuit1 and circuit2:
        qr0:-[H]--.------------  -> 1
                  |
        qr1:-----(+)--.--------  -> 2
                      |
        qr2:---------(+)--.----  -> 3
                          |
        qr3:-------------(+)---  -> 5

        device:
        0  -  1  -  2  -  3  -  4  -  5  -  6

              |     |     |     |     |     |

              13 -  12  - 11 -  10 -  9  -  8  -   7
        """
        qr = QuantumRegister(4, 'qr')
        circuit1 = QuantumCircuit(qr)
        circuit1.h(qr[0])
        circuit1.cx(qr[0], qr[1])
        circuit1.cx(qr[1], qr[2])
        circuit1.cx(qr[2], qr[3])

        circuit2 = QuantumCircuit(qr)
        circuit2.h(qr[0])
        circuit2.cx(qr[0], qr[1])
        circuit2.cx(qr[1], qr[2])
        circuit2.cx(qr[2], qr[3])

        coupling_map = FakeMelbourne().configuration().coupling_map
        basis_gates = FakeMelbourne().configuration().basis_gates
        initial_layout = [None, qr[0], qr[1], qr[2], None, qr[3]]

        pass_manager = level_1_pass_manager(TranspileConfig(
            basis_gates=basis_gates,
            coupling_map=CouplingMap(coupling_map),
            initial_layout=Layout.from_qubit_list(initial_layout),
            seed_transpiler=42,
            optimization_level=1))
        new_circuit = pass_manager.run([circuit1, circuit2])

        for gate, qargs, _ in new_circuit.data:
            if isinstance(gate, CnotGate):
                self.assertIn([x[1] for x in qargs], coupling_map)
