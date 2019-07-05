# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Test synthesis algorithms"""

from qiskit.circuit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info.operators import Operator
from qiskit.extensions.unitary import UnitaryGate
from qiskit.transpiler.synthesis import graysynth, cnot_synth
from qiskit.test import QiskitTestCase


class TestGraySynth(QiskitTestCase):
    """Test the Gray-Synth algorithm."""

    def test_gray_synth(self):
        """Test synthesis of a small parity network via gray_synth.

        The algorithm should take the following matrix as an input:
        S =
        [[0, 1, 1, 0, 1, 1],
         [0, 1, 1, 0, 1, 0],
         [0, 0, 0, 1, 1, 0],
         [1, 0, 0, 1, 1, 1],
         [0, 1, 0, 0, 1, 0],
         [0, 1, 0, 0, 1, 0]]

        Along with some rotation angles:
        ['s', 't', 'z', 's', 't', 't'])

        which together specify the Fourier expansion in the sum-over-paths representation
        of a quantum circuit.

        And should return the following circuit (or an equivalent one):
                          ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
        q_0: |0>──────────┤ X ├┤ X ├┤ T ├┤ X ├┤ X ├┤ X ├┤ X ├┤ T ├┤ X ├┤ T ├┤ X ├┤ X ├┤ Z ├┤ X ├
                          └─┬─┘└─┬─┘└───┘└─┬─┘└─┬─┘└─┬─┘└─┬─┘└───┘└─┬─┘└───┘└─┬─┘└─┬─┘└───┘└─┬─┘
        q_1: |0>────────────┼────┼─────────■────┼────┼────┼─────────┼─────────┼────┼─────────■──
                            │    │              │    │    │         │         │    │
        q_2: |0>───────■────■────┼──────────────■────┼────┼─────────┼────■────┼────┼────────────
                ┌───┐┌─┴─┐┌───┐  │                   │    │         │  ┌─┴─┐  │    │
        q_3: |0>┤ S ├┤ X ├┤ S ├──■───────────────────┼────┼─────────■──┤ X ├──┼────┼────────────
                └───┘└───┘└───┘                      │    │            └───┘  │    │
        q_4: |0>─────────────────────────────────────■────┼───────────────────■────┼────────────
                                                          │                        │
        q_5: |0>──────────────────────────────────────────■────────────────────────■────────────

        """
        cnots = [[0, 1, 1, 0, 1, 1],
                 [0, 1, 1, 0, 1, 0],
                 [0, 0, 0, 1, 1, 0],
                 [1, 0, 0, 1, 1, 1],
                 [0, 1, 0, 0, 1, 0],
                 [0, 1, 0, 0, 1, 0]]
        angles = ['s', 't', 'z', 's', 't', 't']
        c_gray = graysynth(cnots, angles)
        unitary_gray = UnitaryGate(Operator(c_gray))

        # Create the circuit displayed above:
        q = QuantumRegister(6, 'q')
        c_compare = QuantumCircuit(q)
        c_compare.s(q[3])
        c_compare.cx(q[2], q[3])
        c_compare.s(q[3])
        c_compare.cx(q[2], q[0])
        c_compare.cx(q[3], q[0])
        c_compare.t(q[0])
        c_compare.cx(q[1], q[0])
        c_compare.cx(q[2], q[0])
        c_compare.cx(q[4], q[0])
        c_compare.cx(q[5], q[0])
        c_compare.t(q[0])
        c_compare.cx(q[3], q[0])
        c_compare.t(q[0])
        c_compare.cx(q[2], q[3])
        c_compare.cx(q[4], q[0])
        c_compare.cx(q[5], q[0])
        c_compare.z(q[0])
        c_compare.cx(q[1], q[0])
        unitary_compare = UnitaryGate(Operator(c_compare))

        # Check if the two circuits are equivalent
        self.assertEqual(unitary_gray, unitary_compare)

    def test_paper_example(self):
        """Test synthesis of a diagonal operator from the paper.

        The diagonal operator in Example 4.2
            U|x> = e^(2.pi.i.f(x))|x>,
        where
            f(x) = 1/8*(x1^x2 + x0 + x0^x3 + x0^x1^x2 + x0^x1^x3 + x0^x1)

        The algorithm should take the following matrix as an input:
        S = [[0, 1, 1, 1, 1, 1],
             [1, 0, 0, 1, 1, 1],
             [1, 0, 0, 1, 0, 0],
             [0, 0, 1, 0, 1, 0]]

        and only T gates as phase rotations,

        And should return the following circuit (or an equivalent one):
                ┌───┐┌───┐     ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐     ┌───┐
        q_0: |0>┤ T ├┤ X ├─────┤ T ├┤ X ├┤ X ├┤ T ├┤ X ├┤ T ├┤ X ├┤ T ├┤ X ├─────┤ X ├
                ├───┤└─┬─┘┌───┐└───┘└─┬─┘└─┬─┘└───┘└─┬─┘└───┘└─┬─┘└───┘└─┬─┘┌───┐└─┬─┘
        q_1: |0>┤ X ├──┼──┤ T ├───────■────┼─────────┼─────────┼─────────■──┤ X ├──┼──
                └─┬─┘  │  └───┘            │         │         │            └─┬─┘  │
        q_2: |0>──■────┼───────────────────┼─────────■─────────┼──────────────■────┼──
                       │                   │                   │                   │
        q_3: |0>───────■───────────────────■───────────────────■───────────────────■──
        """
        cnots = [[0, 1, 1, 1, 1, 1],
                 [1, 0, 0, 1, 1, 1],
                 [1, 0, 0, 1, 0, 0],
                 [0, 0, 1, 0, 1, 0]]
        angles = ['t'] * 6
        c_gray = graysynth(cnots, angles)
        unitary_gray = UnitaryGate(Operator(c_gray))

        # Create the circuit displayed above:
        q = QuantumRegister(4, 'q')
        c_compare = QuantumCircuit(q)
        c_compare.t(q[0])
        c_compare.cx(q[2], q[1])
        c_compare.cx(q[3], q[0])
        c_compare.t(q[0])
        c_compare.t(q[1])
        c_compare.cx(q[1], q[0])
        c_compare.cx(q[3], q[0])
        c_compare.t(q[0])
        c_compare.cx(q[2], q[0])
        c_compare.t(q[0])
        c_compare.cx(q[3], q[0])
        c_compare.t(q[0])
        c_compare.cx(q[1], q[0])
        c_compare.cx(q[2], q[1])
        c_compare.cx(q[3], q[0])
        unitary_compare = UnitaryGate(Operator(c_compare))

        # Check if the two circuits are equivalent
        self.assertEqual(unitary_gray, unitary_compare)


class TestPatelMarkovHayes(QiskitTestCase):
    """Test the Patel-Markov-Hayes algorithm for synthesizing linear
    CNOT-only circuits."""

    def test_patel_markov_hayes(self):
        """Test synthesis of a small linear circuit
        (example from paper, Figure 3).

        The algorithm should take the following matrix as an input:
        S = [[1, 1, 0, 0, 0, 0],
             [1, 0, 0, 1, 1, 0],
             [0, 1, 0, 0, 1, 0],
             [1, 1, 1, 1, 1, 1],
             [1, 1, 0, 1, 1, 1],
             [0, 0, 1, 1, 1, 0]]

        And should return the following circuit (or an equivalent one):
                          ┌───┐
        q_0: |0>──────────┤ X ├──────────────────────────────────────────■────■────■──
                          └─┬─┘┌───┐                                   ┌─┴─┐  │    │
        q_1: |0>────────────■──┤ X ├────────────────────────────────■──┤ X ├──┼────┼──
                     ┌───┐     └─┬─┘┌───┐          ┌───┐          ┌─┴─┐└───┘  │    │
        q_2: |0>─────┤ X ├───────┼──┤ X ├───────■──┤ X ├───────■──┤ X ├───────┼────┼──
                ┌───┐└─┬─┘       │  └─┬─┘┌───┐┌─┴─┐└─┬─┘       │  └───┘       │  ┌─┴─┐
        q_3: |0>┤ X ├──┼─────────■────┼──┤ X ├┤ X ├──■────■────┼──────────────┼──┤ X ├
                └─┬─┘  │              │  └─┬─┘├───┤       │  ┌─┴─┐          ┌─┴─┐└───┘
        q_4: |0>──■────┼──────────────■────■──┤ X ├───────┼──┤ X ├──────────┤ X ├─────
                       │                      └─┬─┘     ┌─┴─┐└───┘          └───┘
        q_5: |0>───────■────────────────────────■───────┤ X ├─────────────────────────
                                                        └───┘
        """
        state = [[1, 1, 0, 0, 0, 0],
                 [1, 0, 0, 1, 1, 0],
                 [0, 1, 0, 0, 1, 0],
                 [1, 1, 1, 1, 1, 1],
                 [1, 1, 0, 1, 1, 1],
                 [0, 0, 1, 1, 1, 0]]
        c_patel = cnot_synth(state)

        # Create the circuit displayed above:
        q = QuantumRegister(6, 'q')
        c_compare = QuantumCircuit(q)
        c_compare.cx(q[4], q[3])
        c_compare.cx(q[5], q[2])
        c_compare.cx(q[1], q[0])
        c_compare.cx(q[3], q[1])
        c_compare.cx(q[4], q[2])
        c_compare.cx(q[4], q[3])
        c_compare.cx(q[5], q[4])
        c_compare.cx(q[2], q[3])
        c_compare.cx(q[3], q[2])
        c_compare.cx(q[3], q[5])
        c_compare.cx(q[2], q[4])
        c_compare.cx(q[1], q[2])
        c_compare.cx(q[0], q[1])
        c_compare.cx(q[0], q[4])
        c_compare.cx(q[0], q[3])

        # Check if the two circuits are equivalent
        self.assertEqual(c_patel, c_compare)
