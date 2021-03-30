# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""Tests for Stabilizerstate quantum state class."""

import unittest
from test import combine
import logging
from ddt import ddt

import numpy as np

from qiskit.test import QiskitTestCase
# from qiskit import QiskitError
from qiskit import QuantumRegister, QuantumCircuit
# from qiskit import transpile

from qiskit.quantum_info.random import random_clifford, random_pauli
from qiskit.quantum_info.states import StabilizerState
from qiskit.circuit.library import (IGate, XGate, YGate, ZGate, HGate,
                                    SGate, SdgGate, CXGate, CZGate,
                                    SwapGate)
from qiskit.quantum_info.operators import Clifford, Operator


logger = logging.getLogger(__name__)


@ddt
class TestStabilizerState(QiskitTestCase):
    """Tests for StabilizerState class."""

    rng = np.random.default_rng(12345)
    samples = 10
    shots = 1000
    threshold = 0.1 * shots

    @combine(num_qubits=[2, 3, 4, 5])
    def test_init_clifford(self, num_qubits):
        """Test initialization from Clifford."""
        stab1 = StabilizerState(random_clifford(num_qubits, seed=self.rng))
        stab2 = StabilizerState(stab1)
        self.assertEqual(stab1, stab2)

    @combine(num_qubits=[2, 3, 4, 5])
    def test_init_circuit(self, num_qubits):
        """Test initialization from a Clifford circuit."""
        cliff = random_clifford(num_qubits, seed=self.rng)
        stab1 = StabilizerState(cliff.to_circuit())
        stab2 = StabilizerState(cliff)
        self.assertEqual(stab1, stab2)

    @combine(num_qubits=[2, 3, 4, 5])
    def test_init_instruction(self, num_qubits):
        """Test initialization from a Clifford instruction."""
        cliff = random_clifford(num_qubits, seed=self.rng)
        stab1 = StabilizerState(cliff.to_instruction())
        stab2 = StabilizerState(cliff)
        self.assertEqual(stab1, stab2)

    @combine(num_qubits=[2, 3, 4, 5])
    def test_init_pauli(self, num_qubits):
        """Test initialization from pauli."""
        pauli = random_pauli(num_qubits, seed=self.rng)
        stab1 = StabilizerState(pauli)
        stab2 = StabilizerState(stab1)
        self.assertEqual(stab1, stab2)

    @combine(num_qubits=[2, 3, 4, 5])
    def test_to_operator(self, num_qubits):
        """Test to_operator method for returning projector."""
        for _ in range(self.samples):
            stab = StabilizerState(random_clifford(num_qubits, seed=self.rng))
            target = Operator(stab)
            op = StabilizerState(stab).to_operator()
            self.assertEqual(op, target)

    @combine(num_qubits=[2, 3])
    def test_conjugate(self, num_qubits):
        """Test conjugate method."""
        for _ in range(self.samples):
            stab = StabilizerState(random_clifford(num_qubits, seed=self.rng))
            target = StabilizerState(stab.conjugate())
            state = StabilizerState(stab).conjugate()
            self.assertEqual(state, target)

    @combine(num_qubits=[2, 3])
    def test_transpose(self, num_qubits):
        """Test transpose method."""
        for _ in range(self.samples):
            stab = StabilizerState(random_clifford(num_qubits, seed=self.rng))
            target = StabilizerState(stab.transpose())
            state = StabilizerState(stab).transpose()
            self.assertEqual(state, target)

    def test_tensor(self):
        """Test tensor method."""
        for _ in range(self.samples):
            cliff1 = random_clifford(2, seed=self.rng)
            cliff2 = random_clifford(3, seed=self.rng)
            stab1 = StabilizerState(cliff1)
            stab2 = StabilizerState(cliff2)
            target = StabilizerState(cliff1.tensor(cliff2))
            state = stab1.tensor(stab2)
            self.assertEqual(state, target)

    def test_expand(self):
        """Test expand method."""
        for _ in range(self.samples):
            cliff1 = random_clifford(2, seed=self.rng)
            cliff2 = random_clifford(3, seed=self.rng)
            stab1 = StabilizerState(cliff1)
            stab2 = StabilizerState(cliff2)
            target = StabilizerState(cliff1.expand(cliff2))
            state = stab1.expand(stab2)
            self.assertEqual(state, target)

    @combine(num_qubits=[2, 3, 4])
    def test_evolve(self, num_qubits):
        """Test evolve method."""
        for _ in range(self.samples):
            cliff1 = random_clifford(num_qubits, seed=self.rng)
            cliff2 = random_clifford(num_qubits, seed=self.rng)
            stab1 = StabilizerState(cliff1)
            stab2 = StabilizerState(cliff2)
            target = StabilizerState(cliff1.compose(cliff2))
            state = stab1.evolve(stab2)
            self.assertEqual(state, target)

    @combine(num_qubits_1=[4, 5, 6], num_qubits_2=[1, 2, 3])
    def test_evolve_subsystem(self, num_qubits_1, num_qubits_2):
        """Test subsystem evolve method."""
        for _ in range(self.samples):
            cliff1 = random_clifford(num_qubits_1, seed=self.rng)
            cliff2 = random_clifford(num_qubits_2, seed=self.rng)
            stab1 = StabilizerState(cliff1)
            stab2 = StabilizerState(cliff2)
            qargs = sorted(np.random.choice(range(num_qubits_1), num_qubits_2, replace=False))
            target = StabilizerState(cliff1.compose(cliff2, qargs))
            state = stab1.evolve(stab2, qargs)
            self.assertEqual(state, target)

    def test_measure_qubits(self):
        """Test a measurement of a subsystem of qubits"""
        for _ in range(self.samples):
            cliff = Clifford(XGate())
            stab = StabilizerState(cliff)
            value = stab.measure()[0]
            self.assertEqual(value, '1')

            cliff = Clifford(IGate())
            stab = StabilizerState(cliff)
            value = stab.measure()[0]
            self.assertEqual(value, '0')

            cliff = Clifford(HGate())
            stab = StabilizerState(cliff)
            value = stab.measure()[0]
            self.assertIn(value, ['0', '1'])

            num_qubits = 4
            qc = QuantumCircuit(num_qubits)
            stab = StabilizerState(qc)
            value = stab.measure()[0]
            self.assertEqual(value, '0000')
            value = stab.measure([0, 2])[0]
            self.assertEqual(value, '00')
            value = stab.measure([1])[0]
            self.assertEqual(value, '0')

            for i in range(num_qubits):
                qc.x(i)
            stab = StabilizerState(qc)
            value = stab.measure()[0]
            self.assertEqual(value, '1111')
            value = stab.measure([2, 0])[0]
            self.assertEqual(value, '11')
            value = stab.measure([1])[0]
            self.assertEqual(value, '1')

            qc = QuantumCircuit(num_qubits)
            qc.h(0)
            stab = StabilizerState(qc)
            value = stab.measure()[0]
            self.assertIn(value, ['0000', '1000'])
            value = stab.measure([0, 1])[0]
            self.assertIn(value, ['00', '10'])
            value = stab.measure([2])[0]
            self.assertEqual(value, '0')

            qc = QuantumCircuit(num_qubits)
            qc.h(0)
            qc.cx(0, 1)
            qc.cx(0, 2)
            qc.cx(0, 3)
            stab = StabilizerState(qc)
            value = stab.measure()[0]
            self.assertIn(value, ['0000', '1111'])
            value = stab.measure([3, 1])[0]
            self.assertIn(value, ['00', '11'])
            value = stab.measure([2])[0]
            self.assertIn(value, ['0', '1'])

    def test_reset_qubits(self):
        """Test reset method of a subsystem of qubits"""

        empty_qc = QuantumCircuit(1)

        for _ in range(self.samples):
            cliff = Clifford(XGate())
            stab = StabilizerState(cliff)
            value = stab.reset([0])
            target = StabilizerState(empty_qc)
            self.assertEqual(value, target)

            cliff = Clifford(HGate())
            stab = StabilizerState(cliff)
            value = stab.reset([0])
            target = StabilizerState(empty_qc)
            self.assertEqual(value, target)

        num_qubits = 3
        qc = QuantumCircuit(num_qubits)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(0, 2)

        for _ in range(self.samples):
            stab = StabilizerState(qc)
            res = stab.reset()
            value = res.measure()[0]
            self.assertEqual(value, '000')

        for _ in range(self.samples):
            for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:
                stab = StabilizerState(qc)
                res = stab.reset(qargs)
                value = res.measure()[0]
                self.assertEqual(value, '000')

        for _ in range(self.samples):
            stab = StabilizerState(qc)
            res = stab.reset([0])
            value = res.measure()[0]
            self.assertIn(value, ['000', '011'])

        for _ in range(self.samples):
            stab = StabilizerState(qc)
            res = stab.reset([1])
            value = res.measure()[0]
            # self.assertIn(value, ['000', '101'])

        for _ in range(self.samples):
            stab = StabilizerState(qc)
            res = stab.reset([2])
            value = res.measure()[0]
            # self.assertIn(value, ['000', '110'])

        for _ in range(self.samples):
            for qargs in [[0, 1], [1, 0]]:
                stab = StabilizerState(qc)
                res = stab.reset(qargs)
                value = res.measure()[0]
                self.assertIn(value, ['000', '001'])

        for _ in range(self.samples):
            for qargs in [[0, 2], [2, 0]]:
                stab = StabilizerState(qc)
                res = stab.reset(qargs)
                value = res.measure()[0]
                self.assertIn(value, ['000', '010'])

        for _ in range(self.samples):
            for qargs in [[1, 2], [2, 1]]:
                stab = StabilizerState(qc)
                res = stab.reset(qargs)
                value = res.measure()[0]
                # self.assertIn(value, ['000', '100'])


    def test_sample_counts_memory_ghz(self):
        """Test sample_counts and sample_memory method for GHZ state"""

        num_qubits = 3
        qc = QuantumCircuit(num_qubits)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(0, 2)
        stab = StabilizerState(qc)

        # 3-qubit qargs
        target = {'000': self.shots / 2, '111': self.shots / 2}
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = stab.sample_counts(self.shots, qargs=qargs)
                self.assertDictAlmostEqual(counts, target, self.threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = stab.sample_memory(self.shots, qargs=qargs)
                self.assertEqual(len(memory), self.shots)
                self.assertEqual(set(memory), set(target))

        # 2-qubit qargs
        target = {'00': self.shots / 2, '11': self.shots / 2}
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 0]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = stab.sample_counts(self.shots, qargs=qargs)
                self.assertDictAlmostEqual(counts, target, self.threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = stab.sample_memory(self.shots, qargs=qargs)
                self.assertEqual(len(memory), self.shots)
                self.assertEqual(set(memory), set(target))

        # 1-qubit qargs
        target = {'0': self.shots / 2, '1': self.shots / 2}
        for qargs in [[0], [1], [2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = stab.sample_counts(self.shots, qargs=qargs)
                self.assertDictAlmostEqual(counts, target, self.threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = stab.sample_memory(self.shots, qargs=qargs)
                self.assertEqual(len(memory), self.shots)
                self.assertEqual(set(memory), set(target))

    def test_sample_counts_memory_superposition(self):
        """Test sample_counts and sample_memory method of a 3-qubit superposition"""

        num_qubits = 3
        qc = QuantumCircuit(num_qubits)
        qc.h(0)
        qc.h(1)
        qc.h(2)
        stab = StabilizerState(qc)

        # 3-qubit qargs
        target = {'000': self.shots / 8, '001': self.shots / 8,
                  '010': self.shots / 8, '011': self.shots / 8,
                  '100': self.shots / 8, '101': self.shots / 8,
                  '110': self.shots / 8, '111': self.shots / 8}
        for qargs in [[0, 1, 2], [2, 1, 0], [1, 2, 0], [1, 0, 2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = stab.sample_counts(self.shots, qargs=qargs)
                self.assertDictAlmostEqual(counts, target, self.threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = stab.sample_memory(self.shots, qargs=qargs)
                self.assertEqual(len(memory), self.shots)
                self.assertEqual(set(memory), set(target))

        # 2-qubit qargs
        target = {'00': self.shots / 4, '01': self.shots / 4,
                  '10': self.shots / 4, '11': self.shots / 4}
        for qargs in [[0, 1], [2, 1], [1, 2], [1, 0]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = stab.sample_counts(self.shots, qargs=qargs)
                self.assertDictAlmostEqual(counts, target, self.threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = stab.sample_memory(self.shots, qargs=qargs)
                self.assertEqual(len(memory), self.shots)
                self.assertEqual(set(memory), set(target))

        # 1-qubit qargs
        target = {'0': self.shots / 2, '1': self.shots / 2}
        for qargs in [[0], [1], [2]]:

            with self.subTest(msg='counts (qargs={})'.format(qargs)):
                counts = stab.sample_counts(self.shots, qargs=qargs)
                self.assertDictAlmostEqual(counts, target, self.threshold)

            with self.subTest(msg='memory (qargs={})'.format(qargs)):
                memory = stab.sample_memory(self.shots, qargs=qargs)
                self.assertEqual(len(memory), self.shots)
                self.assertEqual(set(memory), set(target))


if __name__ == '__main__':
    unittest.main()
